import functools
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
from ..flags import set_instrumentation_on, set_instrumentation_off
from .. import mode
from ..native import compiler_binding, runtime_binding

triton_proton = compiler_binding()
profiler_native = runtime_binding()

# TODO(fywkevin): add support for major.minor
VERSION = 1


class CudaAllocator:

    def __init__(self, instrumentation_hook):
        self.instrumentation_hook = instrumentation_hook

    def __call__(self, size: int, alignment: int, stream: Optional[int]):
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

        # Create the buffer
        import torch
        buffer = torch.empty((aligned_size, ),
                             dtype=torch.uint8,
                             device="cuda")
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


class InstrumentationHook(Hook):
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

    def activate(self):
        if InstrumentationHook.active_count > 0:
            raise RuntimeError(
                "Only one instance of the instrumentation hook can be active at a time."
            )

        InstrumentationHook.active_count += 1

        set_instrumentation_on()

        device = triton.runtime.driver.active.get_current_device()
        max_shared_mem = triton.runtime.driver.active.utils.get_device_properties(
            device)["max_shared_mem"]
        backend_name = _get_backend_name()
        self.capture_observations = backend_name == "nvidia"
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

        backends[backend_name].compiler.instrumentation = Instrumentation({
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

        @functools.wraps(original_run)
        def instrumented_run(jit_function, *args, **kwargs):
            # Own the shared scratch allocator before compilation/allocation,
            # not just after the launcher has already chosen a device buffer.
            locked = instrumentation_hook.capture_observations
            if locked and not instrumentation_hook._observation_run_lock.acquire(
                    blocking=False):
                raise RuntimeError(
                    'Concurrent NVIDIA instrumented JIT launches are unsupported'
                )
            try:
                kwargs["instrumentation_mode"] = str(original_mode)
                if instrumentation_hook.selected_programs is not None:
                    kwargs[
                        "instrumentation_mode"] += ':selected_programs=' + ','.join(
                            map(str, instrumentation_hook.selected_programs))
                return original_run(jit_function, *args, **kwargs)
            finally:
                if locked:
                    instrumentation_hook._observation_run_lock.release()

        JITFunction.run = instrumented_run

    def deactivate(self):
        if InstrumentationHook.active_count == 0:
            return

        InstrumentationHook.active_count -= 1

        backend_name = _get_backend_name()

        # No instrumentation passes are registered anymore
        backends[backend_name].compiler.instrumentation = {}

        # No runtime instrumentation hook is active anymore
        set_instrumentation_off()

        # Restore original JIT function run method
        if hasattr(JITFunction.run, "__wrapped__"):
            JITFunction.run = JITFunction.run.__wrapped__

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
            self.observation_metadata[function] = {
                'binary_id':
                hash,
                'scope_id_names':
                list(scope_id_names),
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
                    'NVIDIA source_control_interval requires explicit Proton scopes; annotate the kernel with enter_scope/exit_scope and enable Triton semantics'
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
            profiler_native.enter_instrumented_op(
                stream, func,
                self._data_ptr() if has_scopes else 0,
                alloc_size if has_scopes else 0)
        except BaseException:
            self.abort_enter(metadata)
            raise

    def abort_enter(self, metadata: LazyDict, error=None) -> None:
        # A failed pre-launch hook has no completed GPU buffer to parse.
        if self._observation_entered.get():
            self._observation_stack.set(self._observation_stack.get()[:-1])
            self._observation_entered.set(False)
            self._observation_lock.release()

    def exit(self, metadata: LazyDict) -> None:
        func = metadata.data.get("function")
        stream = metadata.data.get("stream")
        alloc_size = 0 if self.buffer is None else self.buffer.element_size(
        ) * self.buffer.numel()
        try:
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
                value['compiler_site'] = {
                    'kind':
                    'explicit_proton_scope',
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
