import functools
import importlib
import base64
import hashlib
import json
import os
import threading
from contextvars import ContextVar
from pathlib import Path
from typing import Dict, Optional, Union, Any

import triton
from triton._C.libtriton import ir as triton_ir
try:
    from triton._C.libtriton import amd as triton_amd
except ImportError:
    triton_amd = None
try:
    from triton._C.libtriton import nvidia as triton_nvidia
except ImportError:
    triton_nvidia = None
from triton._C.libtriton import passes as triton_passes
from triton.compiler import LazyDict
from triton.runtime.jit import JITFunction
from triton.runtime._allocation import set_profile_allocator, NullAllocator
from triton.backends import backends

from .hook import Hook, HookManager
from .timeline import TimelineInstrumentationMixin
from ..flags import set_instrumentation_on, set_instrumentation_off
from .. import mode
from ..native import compiler_binding, runtime_binding

triton_proton = compiler_binding()
profiler_native = runtime_binding()

# TODO(fywkevin): add support for major.minor
VERSION = 1
# Part of the compilation cache identity: old auto binaries have no inventory.
AUTOMATIC_INVENTORY_VERSION = 2
AUTOMATIC_SELECTION_POLICY_VERSION = 2


class CudaAllocator:

    def __init__(self, instrumentation_hook):
        self.instrumentation_hook = instrumentation_hook
        self._census_admission = ContextVar(
            'nvidia_census_allocation_admission', default=None)

    def validate_launch(self,
                        *,
                        function,
                        grid,
                        scratch_size,
                        alignment,
                        num_ctas,
                        stream=None):
        if not self.instrumentation_hook.census:
            return
        self._census_admission.set(None)
        from ..nvidia_census import census_descriptor
        from math import prod
        metadata = self.instrumentation_hook.observation_metadata.get(function)
        if metadata is None:
            raise RuntimeError(
                'NVIDIA census preallocation requires actual function metadata'
            )
        compiler = metadata.get('compiler_metadata') or {}
        if (type(scratch_size) is not int or scratch_size < 0
                or type(num_ctas) is not int
                or num_ctas != compiler.get('num_ctas', 1)
                or scratch_size != compiler.get('profile_scratch_size')
                or alignment
                != self.instrumentation_hook.profile_buffer_alignment):
            raise RuntimeError(
                'NVIDIA census preallocation contradicts compiler scratch ABI')
        # Geometry validation belongs to the common descriptor builder; do not
        # derive the source-site count from the padded allocation size.
        if (not isinstance(grid, (list, tuple)) or len(grid) != 3
                or any(type(value) is not int or value < 0 for value in grid)):
            raise RuntimeError(
                'NVIDIA census preallocation requires actual launch geometry')
        size = prod(grid) * num_ctas * scratch_size
        allocated = max((size + alignment - 1) // alignment * alignment,
                        self.instrumentation_hook.profile_buffer_size)
        try:
            census_descriptor(
                metadata, {'grid': grid}, allocated,
                self.instrumentation_hook.observation_plan['output_selection'])
        except RuntimeError as error:
            raise RuntimeError('NVIDIA census preallocation rejected: ' +
                               str(error)) from error

        self._census_admission.set((size, alignment))

    def __call__(self, size: int, alignment: int, stream: Optional[int]):
        if self.instrumentation_hook.census:
            admitted = self._census_admission.get()
            self._census_admission.set(None)
            if admitted != (size, alignment):
                raise RuntimeError(
                    'NVIDIA census allocation requires compiler/launch preflight; rebuild the launcher with preallocation-admission.patch'
                )
        if alignment != self.instrumentation_hook.profile_buffer_alignment:
            raise RuntimeError(
                f"Alignment mismatch: {alignment} != {self.instrumentation_hook.profile_buffer_alignment}"
            )
        aligned_size = (size + alignment - 1) // alignment * alignment
        # Note: profile_buffer_size may be smaller than the aligned size if the kernel launches many blocks
        # and the host CPU cannot store all profiling data in memory. This streaming mode is not yet implemented.
        # In the future, we should support copying data incrementally from device to host to enable
        # more efficient profiling data processing, rather than relying solely on post-processing.
        aligned_size = max(aligned_size,
                           self.instrumentation_hook.profile_buffer_size)

        if self.instrumentation_hook.census and aligned_size > self.instrumentation_hook.observation_plan[
                'output_selection']['max_census_bytes']:
            raise RuntimeError(
                'NVIDIA source census byte budget exceeded before allocation')
        # Create the buffer
        import torch
        buffer = torch.empty((aligned_size, ),
                             dtype=torch.uint8,
                             device="cuda")
        if self.instrumentation_hook.census:
            target_stream = torch.cuda.current_stream(
            ) if stream is None else torch.cuda.ExternalStream(stream)
            with torch.cuda.stream(target_stream):
                buffer.zero_()
        self.instrumentation_hook.buffer = buffer
        return buffer


class Instrumentation:

    def __init__(self, ir_map: Dict[str, Any]):
        self.manager = ir_map

    def register(self, ir: str, func):
        if ir in self.manager:
            raise RuntimeError(f"IR already registered: {ir}")
        self.manager[ir] = func

    def patch(self, ir: str, pm, context):
        self.load_dialects(context)
        if ir in self.manager:
            self.manager[ir](pm)

    def transform_optimized_llvm(self, llvm_text, metadata):
        """Text callback after optimization; never an MLIR pass manager hook."""
        callback = self.manager.get("optimized_llvm")
        if callback is None:
            return llvm_text
        result = callback(llvm_text, metadata)
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError(
                "Optimized LLVM callback must return nonempty text")
        return result

    def load_dialects(self, ctx):
        triton_proton.load_dialects(ctx)


def _interpret_mode(
    mode_obj: Union[str,
                    mode.InstrumentationMode]) -> mode.InstrumentationMode:
    if isinstance(mode_obj, mode.InstrumentationMode):
        return mode_obj
    elif not mode_obj:
        mode_obj = "default"

    parts = mode_obj.split(":")
    mode_name = parts[0]
    opts: Dict[str, str] = {}
    for opt in parts[1:]:
        if "=" in opt:
            key, val = opt.split("=", 1)
            opts[key] = val
        else:
            raise ValueError(f"Malformed instrumentation option: '{opt}'")

    # Get option values or empty strings
    options = {
        "metric_type": opts.get("metric_type", "cycle"),
        "buffer_type": opts.get("buffer_type", "shared"),
        "buffer_strategy": opts.get("buffer_strategy", "circular"),
        "buffer_size": int(opts.get("buffer_size", "0")),
        "granularity": opts.get("granularity", "warp"),
        "sampling_strategy": opts.get("sampling_strategy", "none"),
        "sampling_options": opts.get("sampling_options", ""),
        "optimizations": opts.get("optimizations", "")
    }

    # Helper function to validate and map options to their enum values
    def get_option_value(opt_name, mapping):
        value = options[opt_name]
        if value and value not in mapping:
            raise ValueError(f"Unknown {opt_name}: {value}")
        return mapping[value] if value else value

    # Look up enum values for each option
    options["metric_type"] = get_option_value("metric_type", mode.metric_types)
    options["buffer_type"] = get_option_value("buffer_type", mode.buffer_types)
    options["buffer_strategy"] = get_option_value("buffer_strategy",
                                                  mode.buffer_strategies)
    options["granularity"] = get_option_value("granularity",
                                              mode.granularities)
    options["sampling_strategy"] = get_option_value("sampling_strategy",
                                                    mode.sampling_strategies)

    values = ([value.strip() for value in options["optimizations"].split(",")]
              if len(options["optimizations"]) > 0 else [])
    for value in values:
        if value not in mode.optimizations:
            raise ValueError(f"Unknown optimization: {value}")
    options["optimizations"] = [mode.optimizations[value] for value in values]

    # Create the appropriate mode instance
    if mode_name == "default":
        return mode.Default(**options)
    elif mode_name == "mma":
        return mode.MMA(**options)
    else:
        raise ValueError(f"Unknown mode: {mode_obj}")


def _get_backend_name() -> str:
    backend = triton.runtime.driver.active.get_current_target().backend
    if backend == "cuda":
        return "nvidia"
    elif backend == "hip":
        return "amd"
    else:
        raise RuntimeError(f"Unsupported backend: {backend}")


class InstrumentationHook(TimelineInstrumentationMixin, Hook):
    priority: int = 0
    # It's important to note that only one instance of the instrumentation hook can be active at a time.
    active_count: int = 0
    enable_host_buffer: bool = False
    host_buffer: Optional[Any] = None
    # FIXME(fywkevin): change to a more reasonable value after we have support for periodic buffer dumping.
    profile_buffer_size: int = 1
    profile_buffer_alignment: int = 128
    # Kernel handles remain cached across profiling sessions. The load callback
    # overwrites entries if a new handle is initialized, matching native maps.
    _function_metadata_paths = {}
    _function_observation_metadata = {}
    observation_captures = []
    observation_capture_sequence = 0

    @classmethod
    def peek_observation_captures(cls, session=None):
        """Snapshot captures without consuming any session membership."""
        import copy

        return [
            copy.deepcopy({
                key: value
                for key, value in capture.items() if key != 'session_ids'
            }) for capture in cls.observation_captures
            if session is None or session in capture['session_ids']
        ]

    @classmethod
    def ack_observation_captures(cls, session, capture_ids):
        """Acknowledge only specified, durably saved captures for one session."""
        capture_ids = set(capture_ids)
        if any(not isinstance(value, str) or not value
               for value in capture_ids):
            raise ValueError(
                'Native observation acknowledgements require capture IDs')
        retained = []
        for capture in cls.observation_captures:
            members = capture['session_ids']
            if capture.get('capture_id') in capture_ids:
                if session is None:
                    members.clear()
                elif session in members:
                    members.remove(session)
            if members:
                retained.append(capture)
        cls.observation_captures = retained

    @classmethod
    def take_observation_captures(cls, session=None):
        """Drain one session's immutable per-launch ring captures."""
        result, retained = [], []
        for capture in cls.observation_captures:
            members = capture['session_ids']
            if session is None or session in members:
                result.append({
                    key: value
                    for key, value in capture.items() if key != 'session_ids'
                })
                if session is None:
                    members.clear()
                else:
                    members.remove(session)
            if members:
                retained.append(capture)
        cls.observation_captures = retained
        return result

    def __init__(self,
                 mode_obj: Union[None, str, mode.InstrumentationMode],
                 *,
                 observation_plan=None):
        # Mapping of function objects to their scope ID pairs
        self.mode: mode.InstrumentationMode = _interpret_mode(mode_obj)
        self.observation_plan = observation_plan
        self.census = bool(observation_plan and observation_plan.get("census"))
        self.timeline = bool(observation_plan
                             and observation_plan.get('timeline'))
        self.automatic = bool(observation_plan
                              and observation_plan.get('automatic'))
        self.max_sites = observation_plan.get('max_sites',
                                              8) if observation_plan else 8
        self.selected_programs = None if observation_plan is None else observation_plan[
            "output_selection"]["programs"]

        self.allocator = CudaAllocator(self)
        self.buffer = None
        self.metadata_path = type(self)._function_metadata_paths
        self.observation_metadata = type(self)._function_observation_metadata
        self._observation_lock = threading.Lock()
        self._observation_run_lock = threading.Lock()
        self._observation_entered = ContextVar('proton_observation_entered',
                                               default=False)
        self._observation_stack = ContextVar('proton_observation_stack',
                                             default=())
        self.capture_observations = False
        self._activated = False
        self._run_activation = None
        self._previous_run = None
        self._installed_run = None
        if self.timeline:
            self._init_timeline()

    def activate(self):
        if InstrumentationHook.active_count > 0:
            raise RuntimeError(
                "Only one instance of the instrumentation hook can be active at a time."
            )
        if self.automatic and (
                _get_backend_name() != 'nvidia'
                or not hasattr(triton_proton, 'add_automatic_proton_scopes')
                or getattr(triton_proton, 'AUTOMATIC_INVENTORY_VERSION',
                           0) != AUTOMATIC_INVENTORY_VERSION
                or getattr(triton_proton, 'AUTOMATIC_SELECTION_POLICY_VERSION',
                           0) != AUTOMATIC_SELECTION_POLICY_VERSION):
            raise RuntimeError(
                'Automatic NVIDIA profiling requires the matching FlagPrism compiler plugin'
            )

        if self.census and (getattr(
                triton_proton, 'SOURCE_CENSUS_VERSION', 0) != 1 or getattr(
                    triton_proton, 'SOURCE_CENSUS_PARTITION_VERSION', 0) != 2):
            raise RuntimeError(
                'NVIDIA source census requires the matching version-1 compiler plugin'
            )
        if self.automatic:
            # Register the packaged frontend statement metadata component before
            # compiling ordinary scripts. Importing it does not enable debugger
            # collection, execute a kernel or replay the application.
            importlib.import_module('flagtree.debugger')
        if self.timeline:
            if _get_backend_name() != 'nvidia':
                raise RuntimeError(
                    'Timeline hook is not yet implemented on this backend')
            self._timeline_cache_key = self._timeline_fingerprint()

        InstrumentationHook.active_count += 1
        self._activated = True

        set_instrumentation_on()

        device = triton.runtime.driver.active.get_current_device()
        max_shared_mem = triton.runtime.driver.active.utils.get_device_properties(
            device)["max_shared_mem"]
        backend_name = _get_backend_name()
        self.capture_observations = backend_name == "nvidia" and not self.timeline
        if self.capture_observations:
            profiler_native.set_raw_capture_enabled(True)
            profiler_native.set_observation_programs(self.selected_programs
                                                     or [])

        def to_llvmir_passes(pm):
            if self.selected_programs is not None:
                triton_proton.add_select_proton_programs(
                    pm, self.selected_programs)
            is_long_clk = False if mode.Optimize.CLOCK32 in self.mode.optimizations else True
            triton_proton.add_convert_proton_to_protongpu(
                pm, self.mode.metric_type, self.mode.sampling_strategy,
                self.mode.sampling_options, self.mode.granularity,
                self.mode.buffer_strategy, self.mode.buffer_type,
                self.mode.buffer_size, max_shared_mem,
                self.profile_buffer_size, self.profile_buffer_alignment,
                is_long_clk)
            triton_passes.common.add_cse(pm)

            if mode.Optimize.SCHED_STORES in self.mode.optimizations:
                triton_proton.add_schedule_buffer_store(pm)

            triton_proton.add_allocate_proton_shared_memory(pm)

            if mode.Optimize.SCHED_BARRIERS in self.mode.optimizations and backend_name == "amd":
                triton_proton.add_sched_barriers(pm)

        def to_llvm_passes(pm):
            triton_proton.add_allocate_proton_global_scratch_buffer(pm)
            if backend_name == "nvidia":
                triton_proton.add_convert_proton_nvidia_gpu_to_llvm(pm)
            elif backend_name == "amd":
                arch = triton.runtime.driver.active.utils.get_device_properties(
                    device)["arch"].split(":")[0]
                triton_proton.add_convert_proton_amd_gpu_to_llvm(pm, arch)

        def automatic_scopes(pm):
            if not self.automatic:
                return
            if self.census:
                triton_proton.add_automatic_proton_scopes(
                    pm, self.max_sites, True)
            elif self.timeline:
                triton_proton.add_automatic_proton_scopes(
                    pm, self.max_sites, False, True)
                if self.selected_programs is not None:
                    triton_proton.add_select_proton_programs(
                        pm, self.selected_programs)
            else:
                triton_proton.add_automatic_proton_scopes(pm, self.max_sites)

        backends[backend_name].compiler.instrumentation = Instrumentation({
            "ttgpuir_complete":
            automatic_scopes,
            "ttgpuir_to_llvmir":
            lambda pm: to_llvmir_passes(pm),
            "llvmir_to_llvm":
            lambda pm: to_llvm_passes(pm),
        })

        # Set up the profiling allocator
        set_profile_allocator(self.allocator)

        original_run = JITFunction.run

        original_mode = self.mode
        instrumentation_hook = self
        # Each closure owns one activation epoch. Reactivating this hook must
        # never revive an older closure retained by a third-party wrapper.
        run_activation = {'enabled': False}

        @functools.wraps(original_run)
        def instrumented_run(jit_function, *args, **kwargs):
            # A third-party wrapper may still retain this closure after our
            # session ends. Disabled wrappers are transparent and never inject
            # options for compiler passes/allocators that have been removed.
            if not run_activation['enabled']:
                return original_run(jit_function, *args, **kwargs)
            if instrumentation_hook.timeline:
                # Reject host-thread sharing before compiler/allocator effects.
                instrumentation_hook.timeline_pool._check_thread()
            # Own the shared scratch allocator before compilation/allocation,
            # not just after the launcher has already chosen a device buffer.
            locked = instrumentation_hook.capture_observations
            if locked:
                import torch
                if torch.cuda.is_current_stream_capturing():
                    raise RuntimeError(
                        "NVIDIA detailed instrumentation supports eager launches only; "
                        "CUDA graph capture is unsupported. Use backend='cupti', "
                        "hook='triton' for native-only CUDA graph profiling.")
            if locked and not instrumentation_hook._observation_run_lock.acquire(
                    blocking=False):
                raise RuntimeError(
                    'Concurrent NVIDIA instrumented JIT launches are unsupported'
                )
            try:
                kwargs["instrumentation_mode"] = str(original_mode)
                if instrumentation_hook.automatic:
                    kwargs[
                        "instrumentation_mode"] += f':automatic={AUTOMATIC_INVENTORY_VERSION}:control_policy={AUTOMATIC_SELECTION_POLICY_VERSION}:source_metadata=1:max_sites={instrumentation_hook.max_sites}'
                if instrumentation_hook.census:
                    kwargs[
                        'instrumentation_mode'] += ':source_census=1:partition_observers=2'
                if instrumentation_hook.timeline:
                    kwargs['instrumentation_mode'] += (
                        ':timeline_timer=1:timeline_record=3:timeline_storage=1:timeline_plan=1:timeline_boundary=3:timeline_marker=1:deps='
                        + instrumentation_hook._timeline_cache_key)
                if instrumentation_hook.selected_programs is not None:
                    kwargs[
                        "instrumentation_mode"] += ':selected_programs=' + ','.join(
                            map(str, instrumentation_hook.selected_programs))
                return original_run(jit_function, *args, **kwargs)
            except BaseException as error:
                if instrumentation_hook.timeline:
                    instrumentation_hook._timeline_abort(error)
                raise
            finally:
                if locked:
                    instrumentation_hook._observation_run_lock.release()

        self._previous_run = original_run
        self._installed_run = instrumented_run
        self._run_activation = run_activation
        run_activation['enabled'] = True
        JITFunction.run = instrumented_run

    def deactivate(self):
        if self._run_activation is not None:
            self._run_activation['enabled'] = False
        if not self._activated:
            return

        self._activated = False
        InstrumentationHook.active_count -= 1

        backend_name = _get_backend_name()

        # No instrumentation passes are registered anymore
        backends[backend_name].compiler.instrumentation = {}

        # No runtime instrumentation hook is active anymore
        set_instrumentation_off()

        # Restore original JIT function run method
        if JITFunction.run is self._installed_run:
            JITFunction.run = self._previous_run

        # Reset profile allocator
        set_profile_allocator(NullAllocator())

        # Reset host memory for external processing
        if InstrumentationHook.enable_host_buffer or self.capture_observations:
            InstrumentationHook.host_buffer = None

        # Reset the buffer reference
        if self.capture_observations:
            profiler_native.set_raw_capture_enabled(False)
            profiler_native.set_observation_programs([])
        self.buffer = None

    def init_handle(self, module: Any, function: Any, name: str,
                    metadata_group: Dict[str, str], hash: str) -> None:
        if not function:
            return

        # Find the IR path in metadata
        ir_path = next((path for key, path in metadata_group.items()
                        if key.endswith(("ttgir"))), None)
        metadata_path = next((path for key, path in metadata_group.items()
                              if key.endswith(("json"))), None)
        self.metadata_path[function] = metadata_path

        if ir_path:
            context = triton_ir.context()
            triton_ir.load_dialects(context)
            backend_name = _get_backend_name()
            if backend_name == "nvidia":
                if triton_nvidia is not None:
                    triton_nvidia.load_dialects(context)
            elif backend_name == "amd":
                if triton_amd is not None:
                    triton_amd.load_dialects(context)
            triton_proton.load_dialects(context)
            module = triton_ir.parse_mlir_module(ir_path, context)
            module.context = context

            scope_id_names = triton_proton.get_scope_id_names(module)
            scope_id_parents = triton_proton.get_scope_id_parents(module)
            from ..source_origins_nvidia import capture_scope_origins
            scope_origins, origin_sources = capture_scope_origins(
                triton_proton.get_scope_id_origins(module),
                binary_id=hash,
                compiler_ir_path=ir_path)
            automatic_plan = None
            if self.automatic:
                automatic_plan = triton_proton.get_automatic_proton_plan(
                    module)
                if any(
                        origin.get('automatic')
                        for origin in scope_origins.values()):
                    if automatic_plan.get(
                            'schema_version') != AUTOMATIC_INVENTORY_VERSION:
                        raise RuntimeError(
                            'Automatic NVIDIA compiler inventory is missing or stale; rebuild matching compiler and clear the old cache'
                        )
                    if len(automatic_plan.get(
                            'inventory', [])) != automatic_plan.get(
                                'proton.automatic_candidates'):
                        raise RuntimeError(
                            'Automatic NVIDIA compiler inventory candidate count is inconsistent'
                        )
                automatic_plan.update(
                    binary_id=hash,
                    compiler_ir_sha256=hashlib.sha256(
                        Path(ir_path).read_bytes()).hexdigest(),
                    max_sites=self.max_sites,
                    policy=
                    'source_statements_then_evenly_spaced_internal_operations',
                    semantics=
                    ('compiler_source_region_visit_counts_without_timestamps'
                     if self.census else
                     'compiler_operation_control_intervals_without_completion_barriers'
                     ))
                if self.timeline:
                    automatic_plan.update(
                        policy=automatic_plan.get('timeline_selection_policy'),
                        semantics=
                        'uncertified_compiler_observer_globaltimer_ticks')
            self.observation_metadata[function] = {
                'binary_id':
                hash,
                'scope_id_names':
                list(scope_id_names),
                'automatic_plan':
                automatic_plan,
                'scope_id_origins':
                scope_origins,
                'scope_origin_sources':
                origin_sources,
                'scope_id_parents':
                list(scope_id_parents),
                'compiler_ir_sha256':
                hashlib.sha256(Path(ir_path).read_bytes()).hexdigest(),
                'compiler_metadata':
                json.loads(Path(metadata_path).read_text())
                if metadata_path else None,
            }
            if self.timeline:
                artifacts = []
                prefix = 'binaries/' + hashlib.sha256(
                    hash.encode()).hexdigest()
                for index, path in enumerate(metadata_group.values()):
                    path = Path(path)
                    if path.is_file():
                        artifacts.append(
                            dict(path=str(path),
                                 sha256=hashlib.sha256(
                                     path.read_bytes()).hexdigest(),
                                 retained_file=prefix + '/' + str(index) +
                                 path.suffix))
                self.observation_metadata[function][
                    'timeline_artifacts'] = artifacts
            else:
                profiler_native.init_function_metadata(function, name,
                                                       scope_id_names,
                                                       scope_id_parents,
                                                       metadata_path)
        else:
            raise RuntimeError(
                f"IR path not found in metadata for function {function}")

    def _data_ptr(self) -> int:
        return 0 if self.buffer is None else self.buffer.data_ptr()

    def enter(self, metadata: LazyDict) -> None:
        if self.timeline:
            try:
                return self._timeline_enter(metadata)
            except BaseException as error:
                self._timeline_abort(error)
                raise
        func = metadata.data.get("function")
        stream = metadata.data.get("stream")
        alloc_size = 0 if self.buffer is None else self.buffer.element_size(
        ) * self.buffer.numel()
        if self.capture_observations:
            if not self._observation_lock.acquire(blocking=False):
                raise RuntimeError(
                    'Concurrent NVIDIA instrumented launches share one buffer and are unsupported'
                )
            self._observation_entered.set(True)
        try:
            if self.capture_observations and any(
                    int(site) > 255 or int(site) < 0
                    for site, _ in self.observation_metadata.get(func, {}).get(
                        'scope_id_names', [])):
                raise RuntimeError(
                    'NVIDIA Proton scope identity exceeds the eight-bit ring ABI; reduce the number of explicit scopes'
                )
            if self.observation_plan is not None and not self.observation_metadata.get(
                    func, {}).get('scope_id_names'):
                raise RuntimeError(
                    'NVIDIA collection found no internal observation locations; automatic mode requires the FlagTree ttgpuir_complete compiler hook, while manual mode requires explicit Proton scopes'
                )
            if self.capture_observations:
                from .launch import LaunchHook, id as launch_scope
                identity = getattr(metadata, '_flagprism_invocation_identity',
                                   None)
                identity = identity if isinstance(identity, dict) else {}
                scope_id = launch_scope.get() if LaunchHook(
                ) in HookManager.active_hooks else None
                if identity.get('scope_id') != scope_id:
                    scope_id = None
                binary_id = self.observation_metadata.get(func,
                                                          {}).get('binary_id')
                rows = [
                    row for row in LaunchHook.launches
                    if row['scope_id'] == scope_id
                    and row['binary_id'] == binary_id
                ]
                associated = len(rows) == 1 and identity.get(
                    'binary_id') == binary_id
                session_ids = {
                    session
                    for session, hooks in HookManager.session_hooks.items()
                    if hooks.get(self, False)
                }
                self._observation_stack.set(self._observation_stack.get() + (
                    {
                        'scope_id': scope_id if associated else None,
                        'invocation_id':
                        f'launch-{scope_id}' if associated else None,
                        'association_evidence': {
                            'basis':
                            'same_metadata_object_and_active_launch_hook_scope',
                            'metadata_bridge': identity.get('evidence'),
                            'scope_id': scope_id,
                            'binary_id': binary_id
                        } if associated else None,
                        'session_ids': session_ids,
                        'function': func,
                        'stream_handle': int(stream),
                        'grid': list(rows[0]['grid']) if associated else None,
                    }, ))
            has_scopes = bool(
                self.observation_metadata.get(func, {}).get('scope_id_names'))
            if self.selected_programs is not None and (
                    self.observation_metadata.get(
                        func, {}).get('compiler_metadata') or {}).get(
                            'num_ctas', 1) != 1:
                raise RuntimeError(
                    'NVIDIA program selection requires num_ctas=1; CTA clusters are unsupported'
                )
            if self.census:
                from ..nvidia_census import census_descriptor
                census_descriptor(self.observation_metadata[func],
                                  self._observation_stack.get()[-1],
                                  alloc_size,
                                  self.observation_plan['output_selection'])
                return
            profiler_native.enter_instrumented_op(
                stream, func,
                self._data_ptr() if has_scopes else 0,
                alloc_size if has_scopes else 0)
        except BaseException:
            self.abort_enter(metadata)
            raise

    def abort_enter(self, metadata: LazyDict, error=None) -> None:
        if self.timeline:
            return self._timeline_abort(error)
        # A failed pre-launch hook has no completed GPU buffer to parse.
        if self._observation_entered.get():
            self._observation_stack.set(self._observation_stack.get()[:-1])
            self._observation_entered.set(False)
            self._observation_lock.release()

    def exit(self, metadata: LazyDict) -> None:
        if self.timeline:
            return self._timeline_exit(metadata)
        func = metadata.data.get("function")
        stream = metadata.data.get("stream")
        alloc_size = 0 if self.buffer is None else self.buffer.element_size(
        ) * self.buffer.numel()
        try:
            if self.census:
                self._export_census_capture(func, stream)
                return
            has_scopes = bool(
                self.observation_metadata.get(func, {}).get('scope_id_names'))
            profiler_native.exit_instrumented_op(
                stream, func,
                self._data_ptr() if has_scopes else 0,
                alloc_size if has_scopes else 0)
            has_scopes = bool(
                self.observation_metadata.get(func, {}).get('scope_id_names'))
            if has_scopes and (InstrumentationHook.enable_host_buffer
                               or self.capture_observations):
                self._populate_host_buffer(func, stream)
            if self.capture_observations and has_scopes:
                self._export_observation_capture(func)
            elif self.capture_observations:
                # Legacy modes accept kernels without annotations. They have no
                # scratch payload; an explicit request was rejected at enter.
                self._observation_stack.set(self._observation_stack.get()[:-1])
        finally:
            if self._observation_entered.get():
                self._observation_stack.set(())
                self._observation_entered.set(False)
                self._observation_lock.release()

    def _export_census_capture(self, function, stream):
        import torch
        from ..nvidia_census import census_descriptor
        from ..source_census import decode_source_census
        stack = self._observation_stack.get()
        launch = stack[-1]
        self._observation_stack.set(stack[:-1])
        torch.cuda.ExternalStream(stream).synchronize()
        raw = self.buffer.cpu().numpy().tobytes()
        cls = type(self)
        sequence = cls.observation_capture_sequence
        cls.observation_capture_sequence += 1
        capture_id = f'census-{os.getpid()}-{sequence}'
        metadata = self.observation_metadata[function]
        selection = self.observation_plan['output_selection']
        descriptor = census_descriptor(metadata, launch, len(raw), selection)
        descriptor['raw_sha256'] = hashlib.sha256(raw).hexdigest()
        capture = dict(
            metadata,
            capture_id=capture_id,
            scope_id=launch['scope_id'],
            process_id=os.getpid(),
            stream_handle=launch['stream_handle'],
            invocation_id=launch['invocation_id'],
            session_ids=launch['session_ids'],
            census=descriptor,
            raw_encoding='base64_source_census_v1',
            raw_sha256=descriptor['raw_sha256'],
            raw_base64=base64.b64encode(raw).decode('ascii'),
            collection_boundary=
            'after_original_application_stream_synchronization',
            capture_notes=[
                'Single original launch; all logical programs; source-region visits by compiler-declared default/partition single-writer observers; logical partition IDs are not physical warp IDs; mask activity unobserved; no synthetic intervals.'
            ])
        try:
            capture['decoded'] = decode_source_census(
                raw,
                descriptor,
                capture_id=capture_id,
                invocation_id=launch['invocation_id'],
                binary_id=metadata['binary_id'],
                association_evidence=launch['association_evidence'],
                max_cells=selection['max_census_cells'],
                max_bytes=selection['max_census_bytes'])
        except BaseException as error:
            capture.update(decoded={'observations': []},
                           capture_status='decode_failed',
                           decode_error={
                               'type': type(error).__name__,
                               'message': str(error)
                           })
            cls.observation_captures.append(capture)
            raise
        cls.observation_captures.append(capture)

    def _export_observation_capture(self, function):
        from ..observations_nvidia import decode_proton_ring, select_observations
        from ..observations import observation
        stack = self._observation_stack.get()
        launch = stack[-1] if stack else {
            'scope_id': None,
            'invocation_id': None,
            'association_evidence': None,
            'session_ids': set(),
        }
        self._observation_stack.set(stack[:-1])
        if InstrumentationHook.host_buffer is None:
            raise RuntimeError('NVIDIA instrumentation produced no host ring')
        raw = InstrumentationHook.host_buffer.numpy().tobytes()
        cls = type(self)
        sequence = cls.observation_capture_sequence
        cls.observation_capture_sequence += 1
        capture_id = f'proton-{os.getpid()}-{sequence}'
        metadata = self.observation_metadata.get(function, {})

        def retain(decoded, error=None):
            capture = {
                'capture_id':
                capture_id,
                'scope_id':
                launch['scope_id'],
                'process_id':
                os.getpid(),
                'stream_handle':
                launch.get('stream_handle'),
                'invocation_id':
                launch['invocation_id'],
                'session_ids':
                launch['session_ids'],
                **metadata,
                'raw_encoding':
                'base64_proton_ring_v1',
                'raw_sha256':
                hashlib.sha256(raw).hexdigest(),
                'raw_base64':
                base64.b64encode(raw).decode('ascii'),
                'decoded':
                decoded,
                'collection_boundary':
                'after_inherited_native_buffer_synchronization',
                'capture_notes': [
                    'Raw export reuses the inherited native parser host transfer; owned bytes are copied before its callback returns.'
                ],
            }
            if error is not None:
                capture['capture_status'] = 'decode_failed'
                capture['decode_error'] = {
                    'type': type(error).__name__,
                    'message': str(error)
                }
            cls.observation_captures.append(capture)

        try:
            scopes = dict(metadata.get('scope_id_names', []))
            decoded = decode_proton_ring(
                raw,
                capture_id=capture_id,
                invocation_id=launch['invocation_id'],
                association_evidence=launch['association_evidence'],
                scopes=scopes,
                granularity=str(self.mode.granularity).lower().split('.')[-1],
                clock_bits=32
                if mode.Optimize.CLOCK32 in self.mode.optimizations else 43)
            if self.observation_plan is not None:
                decoded = select_observations(decoded, self.observation_plan)
            for value in decoded['observations']:
                origin = metadata.get('scope_id_origins',
                                      {}).get(str(value['site']), {})
                if origin.get('automatic'):
                    value[
                        'collection_site'] = 'automatic_compiler_operation_boundaries'
                value['compiler_site'] = {
                    'kind':
                    'automatic_compiler_operation'
                    if origin.get('automatic') else 'explicit_proton_scope',
                    'binary_id':
                    metadata.get('binary_id'),
                    'scope_id':
                    value['site'],
                    'origin':
                    metadata.get('scope_id_origins',
                                 {}).get(str(value['site']), {
                                     'status': 'unknown',
                                     'semantic': 'source_region_origin'
                                 }),
                }
            decoded['observations'] = [
                observation(value) for value in decoded['observations']
            ]
        except BaseException as error:
            retain({'observations': []}, error)
            raise
        retain(decoded)

    def _populate_host_buffer(self, function: Any, stream: Any = None) -> None:
        if function and self.metadata_path[function]:
            import torch
            import struct
            import json

            def encode_target(target: Dict[str, Any]) -> int:
                #TODO(fywkevin): also account for `arch`
                if target["backend"] == "cuda":
                    return 1
                elif target["backend"] == "hip":
                    return 2
                return 0

            alloc_size = 0 if self.buffer is None else self.buffer.element_size(
            ) * self.buffer.numel()
            sampled_warps = self.mode.sampling_options.strip().split(",")
            data = {}
            with open(self.metadata_path[function], 'r') as file:
                data = json.load(file)

            device_type = encode_target(data["target"])
            scratch_mem_size = data["profile_scratch_size"]
            total_unit = data["num_warps"]
            uid_num = total_unit if self.mode.sampling_strategy == triton_proton.SAMPLING_STRATEGY.NONE else len(
                sampled_warps)
            block_num = int(alloc_size / scratch_mem_size)

            # Binary trace layout:
            # +------------------+
            # |     version      |  4 bytes
            # +------------------+
            # |  header_offset   |  4 bytes
            # +------------------+
            # |   header_size    |  4 bytes
            # +------------------+
            # |  payload_offset  |  4 bytes
            # +------------------+
            # |   payload_size   |  4 bytes
            # +------------------+
            # |   device_type    |  4 bytes
            # +------------------+
            # |    block_num     |  4 bytes
            # +------------------+
            # |   total_unit     |  4 bytes
            # +------------------+
            # | scratch_mem_size |  4 bytes
            # +------------------+
            # |     uid_num      |  4 bytes
            # +------------------+
            # |                  |
            # |     uid_vec      |  uid_num * 4 bytes
            # |                  |
            # +------------------+
            # |                  |
            # |     payload      |  size_payload bytes
            # |                  |
            # +------------------+

            is_all_warps = self.mode.sampling_options == "" and self.mode.granularity == triton_proton.GRANULARITY.WARP
            if is_all_warps:
                uid_vec = [i for i in range(total_unit)]
            else:
                uid_vec = [int(i) for i in sampled_warps]

            header_size = 40 + uid_num * 4
            header_offset = 4
            payload_offset = header_size
            payload_size = alloc_size
            header_values = [
                VERSION, header_offset, header_size, payload_offset,
                payload_size, device_type, block_num, total_unit,
                scratch_mem_size, uid_num, *uid_vec
            ]
            header_bytes = struct.pack("I" * len(header_values),
                                       *header_values)

            InstrumentationHook.host_buffer = torch.empty(header_size +
                                                          alloc_size,
                                                          dtype=torch.uint8,
                                                          device="cpu")
            config_portion = InstrumentationHook.host_buffer[:header_size]
            config_portion.copy_(
                torch.tensor(list(header_bytes), dtype=torch.uint8))
            data_portion = InstrumentationHook.host_buffer[
                header_size:].view_as(self.buffer)
            if self.capture_observations:
                payload = profiler_native.get_raw_host_buffer(
                    int(function), int(stream))
                if len(payload) != alloc_size:
                    raise RuntimeError(
                        'Native raw instrumentation payload size mismatch')
                host_payload = torch.frombuffer(bytearray(payload),
                                                dtype=torch.uint8)
                data_portion.view(torch.uint8).copy_(host_payload)
            else:
                data_portion.copy_(self.buffer.cpu())
