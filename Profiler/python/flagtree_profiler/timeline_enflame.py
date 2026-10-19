"""Deferred GCU timeline collection using the common invocation owner.

The SDK owns the physical two-ring layout. This module binds actual launches
and stream-local completion to that producer; it does not certify clocks or
source-region boundaries, nor does it label observer brackets as engine busy.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path

from .hooks.timeline import TimelineInstrumentationMixin, _persist


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def plan_enflame_storage(plan, *, grid, scratch_size, alignment, num_ctas,
                         max_raw_bytes):
    """Pure admission in physical bytes; no SDK allocation or synchronization."""
    metadata = plan.get('compiler_metadata', {})
    _need(
        metadata.get('hash') == plan.get('binary_id'),
        'GCU plan/binary mismatch')
    execution = metadata.get(
        'debug_record_layout') == 'gcu_execution_timeline_v3'
    version = 3 if execution else 2
    for name, expected in (('debug_dynamic_storage_version', version),
                           ('debug_dynamic_publisher_version',
                            version), ('debug_dynamic_index_bits', 32)):
        _need(
            type(metadata.get(name)) is int and metadata[name] == expected,
            'Unsupported GCU ' + name)
    _need(
        metadata.get('debug_record_layout')
        in ('gcu_first_last_timeline_v2', 'gcu_execution_timeline_v3') and
        metadata.get('debug_dynamic_program_policy') == 'runtime_first_last',
        'GCU timeline requires the compact first/last publisher')
    _need(
        type(grid) in (list, tuple) and len(grid) == 3
        and all(type(dim) is int and 0 <= dim <= 0x7fffffff for dim in grid),
        'Actual GCU grid is invalid')
    volume = grid[0] * grid[1] * grid[2]
    _need(volume <= 0x7fffffff, 'GCU grid exceeds bounded program indexing')
    capacity = metadata.get('debug_record_capacity')
    _need(
        type(capacity) is int and 1 <= capacity <= 16384,
        'Invalid GCU capacity')
    record_bytes = 128 if execution else 64
    stride = 32 + record_bytes * capacity
    if execution:
        manifest = metadata.get("debug_execution_manifest")
        _need(
            type(manifest) is dict and capacity <= 4096
            and manifest.get("capacity") == capacity
            and manifest.get("record_size") == 128
            and manifest.get("slot_bytes") == stride,
            "Invalid late GCU execution geometry")
    _need(
        type(scratch_size) is int and scratch_size == stride
        and metadata.get('debug_dynamic_slot_bytes') == stride,
        'GCU physical slot extent contradicts the compiler manifest')
    # The actual record contains u64 fields at 8-byte aligned offsets.
    _need(
        type(alignment) is int and alignment == 8 and num_ctas is None,
        'Invalid GCU physical storage request')
    programs = () if not volume else (0, ) if volume == 1 else (0, volume - 1)
    size = len(programs) * stride
    _need(
        type(max_raw_bytes) is int and 0 < max_raw_bytes <= 0x7fffffff
        and size <= max_raw_bytes,
        'GCU compact allocation exceeds admission budget')
    return dict(storage_version=version,
                publisher_version=version,
                grid=tuple(grid),
                slots=tuple(enumerate(programs)),
                programs=programs,
                scratch_size=stride,
                alignment=8,
                raw_bytes=size)


class EnflameTimelineTransport:

    def __init__(self):
        import torch
        import torch_gcu  # noqa: F401
        from flagtree.debugger.native import compiler_binding, runtime_binding
        self.torch = torch
        self.binding = runtime_binding()
        compiler = compiler_binding()
        for module in (self.binding, compiler):
            for name in ('GCU_TIMELINE_STORAGE_VERSION',
                         'GCU_TIMELINE_PUBLISHER_VERSION'):
                _need(
                    getattr(module, name, None) == 2,
                    'GCU requires matching ' + name)
            _need(
                getattr(module, 'GCU_TIMELINE_CLOCK_IDENTITY_VERSION',
                        None) == 1,
                'GCU timeline clock identity requires a matching rebuilt native component'
            )

    def validate_executable(self, function, *, binary_id):
        _need(
            type(function) is dict
            and function.get('kind') == 'gcu.compiled_kernel'
            and function.get('binary_id') == binary_id
            and type(function.get('binary_sha256')) is str
            and len(function['binary_sha256']) == 64,
            'GCU requires an identity from the actual compiled executable')

    def plan_storage(self, plan, **kwargs):
        return plan_enflame_storage(plan, **kwargs)

    def validate_target(self, *, device, stream):
        from flagtree.debugger.graph_guard import require_eager
        _need(self.torch.gcu.current_device() == device,
              'GCU launch device changed')
        require_eager('enflame', stream=stream)

    def allocate(self, owner):
        # Event/wrapper construction precedes native allocation. Neither may
        # initialize the record storage before the owner receives the handle.
        external = self.torch.gcu.ExternalStream(owner['stream'],
                                                 device=owner['device'])
        event = self.torch.gcu.Event(enable_timing=False)
        plan = owner['plan']
        handle = self.binding.allocate_timeline_launch(
            plan['compiler_metadata'], owner['stream'],
            plan['runtime_metadata'])
        if int(handle.hidden_arg_value) % owner['layout']['alignment']:
            handle.release(
            )  # No initialization or device writer was submitted.
            raise RuntimeError('GCU allocation does not meet record alignment')
        return dict(handle=handle, stream=external, event=event)

    def initialize(self, owner):
        owner['resource']['handle'].initialize()

    def launch_buffer(self, owner):
        return int(owner['resource']['handle'].hidden_arg_value)

    def record_completion(self, owner):
        owner['resource']['event'].record(owner['resource']['stream'])

    def completion_ready(self, owner):
        return owner['resource']['event'].query()

    def read_raw(self, owner):
        # The common owner has already observed this launch's completion.
        # Native read_raw copies while retaining both device and host buffers.
        run = owner['resource']['handle'].read_raw()
        from .hooks.launch import _json_value
        owner['native_export_metadata'] = _json_value({
            key: value
            for key, value in run.items() if key != 'raw_buffer'
        })
        return bytes(run['raw_buffer'])

    def release(self, owner):
        owner['resource']['handle'].release()
        owner['resource'] = None


class EnflameTimelineCollector(TimelineInstrumentationMixin):

    def __init__(self):
        from flagtree.debugger.gcu_timeline import tool_identity
        self._execution_tool_identity = tool_identity()
        self._init_timeline_state(EnflameTimelineTransport())
        self._clock_anchors = None
        self._clock_initial_sha = None
        self._clock_file = 'clock/enflame-window-v2.json'
        self._clock_document = None

    def prepare_clock_calibration(self):
        from .timeline_enflame_clock import EnflameClockAnchors
        from .timeline_views import document_sha256
        self._clock_anchors = EnflameClockAnchors()
        self._clock_initial_sha = document_sha256(self._clock_anchors.evidence)

    def _before_timeline_decode(self, directory, deadline):
        # Completed raw owners have already been durably retained. Closing a
        # calibration window must never prevent that salvage pass.
        import time
        if self._clock_anchors is None:
            return
        from .timeline_store import persist
        from .timeline_store import json_bytes
        if self._clock_document is not None:
            persist(directory, self._clock_file,
                    json_bytes(self._clock_document))
            return
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError('No finalization budget for clock anchors')
            evidence = self._clock_anchors.finish()
        except Exception as error:
            evidence = copy.deepcopy(self._clock_anchors.evidence)
            evidence['error'] = dict(type=type(error).__name__,
                                     reason=str(error))
        evidence['initial_snapshot_sha256'] = self._clock_initial_sha
        self._clock_document = evidence
        persist(directory, self._clock_file, json_bytes(evidence))

    def activate(self):
        from flagtree.debugger import register_launch_prepare_hook
        register_launch_prepare_hook(self.prepare_launch)

    def prepare_launch(self, metadata, stream, launch_metadata, kernel_args):
        from flagtree.debugger import api
        from .hooks.launch import _json_value
        self.timeline_pool._check_thread()
        actual = _json_value(api._build_launch_metadata_dict(metadata))
        _need(
            type(actual.get('debug_clock_identity_version')) is int
            and actual['debug_clock_identity_version'] == 1
            and actual.get('debug_clock_identity_primitive')
            == 'llvm.dtu.movs.sipinfo',
            'GCU automatic timeline requires freshly compiled full clock identity metadata'
        )
        if actual.get('debug_execution_version') == 1:
            from flagtree.debugger.gcu_timeline import tool_identity
            _need(
                actual.get('debug_execution_tool_identity') == tool_identity(),
                'GCU execution cache refers to a different recorder/compiler/SDK'
            )
        identity_object = (
            launch_metadata.get('_flagprism_launch_identity_object')
            if isinstance(launch_metadata, dict) else launch_metadata)
        bridge = getattr(identity_object, '_flagprism_launch_context', None)
        _need(
            type(bridge) is dict and bridge.get('kernel') is not None,
            'GCU timeline requires the actual per-launch compiled kernel')
        kernel = bridge['kernel']
        binary = bytes(kernel.kernel)
        _need(kernel.hash == actual.get('hash'),
              'GCU launch/compiler binary mismatch')
        materialized = api._materialize_launch_metadata(launch_metadata)
        grid = api._normalize_launch_grid(materialized)
        _need(grid is not None, 'GCU timeline requires the actual launch grid')
        runtime = api._infer_runtime_metadata(metadata, kernel_args)
        runtime.update(
            grid=grid,
            record_layout=actual['debug_record_layout'],
            records_per_instance=actual['debug_records_per_instance'],
            record_plan=actual['debug_record_plan'])
        plan = dict(binary_id=kernel.hash,
                    compiler_metadata=actual,
                    runtime_metadata=runtime)
        stride = actual.get('debug_dynamic_slot_bytes')
        layout = plan_enflame_storage(
            plan,
            grid=grid,
            scratch_size=stride,
            alignment=8,
            num_ctas=None,
            max_raw_bytes=self.timeline_pool.max_pending_bytes)
        if not layout['raw_bytes']:
            return api.PreparedKernelLaunch(kernel_args=(0, ),
                                            synchronize=False)
        executable = dict(kind='gcu.compiled_kernel',
                          binary_id=kernel.hash,
                          binary_sha256=hashlib.sha256(binary).hexdigest())
        fn = getattr(kernel.src, 'fn', None)
        snapshot = dict(binary_base64=base64.b64encode(binary).decode(),
                        executable=executable,
                        kernel_source=getattr(fn, 'src', None),
                        compiler_artifacts={
                            name: value
                            for name, value in kernel.asm.items()
                            if type(value) is str
                        })
        identity = self.timeline_pool.prepare(
            plan,
            binary_id=kernel.hash,
            function=executable,
            grid=grid,
            scratch_size=stride,
            alignment=8,
            num_ctas=None,
            device=int(
                self.timeline_pool.transport.torch.gcu.current_device()),
            stream=int(stream))
        self._timeline_descriptors[identity] = dict(
            launch=None,
            metadata=dict(
                compiler_metadata=actual,
                compiled_snapshot=snapshot,
                clock_calibration_file=self._clock_file,
                clock_calibration_initial_sha256=self._clock_initial_sha))
        try:
            pointer = self.timeline_pool.allocate(identity)
            self.timeline_pool.mark_submitting(identity)
        except BaseException as error:
            try:
                self.timeline_pool.abort(identity)
            except BaseException as cleanup:
                if hasattr(error, 'add_note'):
                    error.add_note('GCU timeline owner retained: ' +
                                   repr(cleanup))
            raise

        def submitted(error):
            if error is not None:
                self.timeline_pool.abort(identity)
                return
            association = getattr(identity_object,
                                  '_flagprism_invocation_identity', None)
            if (not isinstance(association, dict)
                    or association.get('evidence')
                    != 'same_launch_metadata_object'
                    or association.get('binary_id') != kernel.hash):
                self.timeline_pool.abort(identity)
                raise RuntimeError(
                    'GCU timeline launch association is unavailable')
            self._timeline_descriptors[identity]['launch'] = copy.deepcopy(
                association)
            self.timeline_pool.finish_submission(identity)

        return api.PreparedKernelLaunch(kernel_args=(pointer, ),
                                        finalize=submitted,
                                        synchronize=False)

    def _decode_timeline_original(self, identity, directory, deadline):
        from .timeline_events_enflame import attach_enflame_timeline_export
        input_file = directory / self._timeline_pending[identity]
        capture = json.loads(input_file.read_text())
        owner = capture['owner']
        raw = (directory / capture['raw_file']).read_bytes()
        _need(
            hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
            'Retained GCU raw changed before decoding')
        _need(
            owner.get('readback_integrity', {}).get('status') != 'invalid',
            'GCU readback integrity is invalid')
        prefix = Path('captures') / identity
        if owner['submission_outcome'] == 'returned':
            association = capture['launch']
            native = dict(owner['native_export_metadata'])
            runtime = dict(native['runtime_metadata'])
            runtime.update(profiler_invocation_id=association['invocation_id'],
                           profiler_association_evidence=association)
            exported = attach_enflame_timeline_export(
                dict(native,
                     raw_buffer=raw,
                     runtime_metadata=runtime,
                     record_layout=capture['metadata']['compiler_metadata']
                     ['debug_record_layout'],
                     capture_status='raw_complete'),
                capture['metadata']['compiler_metadata'],
                capture_id=owner['capture_id'])
            canonical = exported['canonical_timeline']
            capture.update(events_file=str(prefix.with_suffix('.events.json')),
                           capture_status='raw_complete'
                           if canonical['complete'] else 'incomplete')
            _persist(directory / capture['events_file'],
                     (json.dumps(canonical, indent=2) + '\n').encode())
            try:
                from .timeline_unit_enflame import load_counter_unit_proofs
                from .timeline_views import derive_counter_ns_views
                from .timeline_perfetto import write_counter_exports
                proofs = load_counter_unit_proofs(directory, capture,
                                                  canonical)
                views = derive_counter_ns_views(canonical, proofs)
                capture['counter_ns_exports'] = write_counter_exports(
                    directory, prefix, views, canonical, proofs=proofs)
                capture['counter_ns_status'] = dict(
                    status='empirical_counter_unit_for_enclosed_window',
                    read_precision_status='unverified',
                    time_arrows_verified=False)
            except (ValueError, OSError, KeyError, TypeError,
                    UnicodeError) as error:
                capture['counter_ns_status'] = dict(status='unavailable',
                                                    reason=str(error))
            try:
                from .timeline_enflame_dependencies import load_observed_dependency_inputs
                from .timeline_dependency_perfetto import write_dependency_exports
                dependency_batch, dependency_proofs = load_observed_dependency_inputs(
                    directory, capture, raw, canonical=canonical)
                capture[
                    'observed_dependency_exports'] = write_dependency_exports(
                        directory, dependency_batch, dependency_proofs)
                capture['observed_dependency_status'] = dict(
                    status='observed_tag_generations',
                    time_arrows_verified=True,
                    read_precision_status='unverified',
                    precise_hardware_completion_time_verified=False)
            except (ValueError, OSError, KeyError, TypeError,
                    UnicodeError) as error:
                capture['observed_dependency_status'] = dict(
                    status='unavailable', reason=str(error))
            # Feed the same normal bundle/source-presence pipeline as advanced
            # capture, after retaining the independent original above.
            from flagtree.debugger import api
            api._exported_runs.append(exported)
        else:
            capture['capture_status'] = 'aborted'
        _persist(directory / prefix.with_suffix('.json'),
                 (json.dumps(capture, indent=2) + '\n').encode())
        self._timeline_rows.append(
            dict(invocation_id=identity,
                 capture_id=owner['capture_id'],
                 binary_id=owner['binary_id'],
                 capture_file=str(prefix.with_suffix('.json')),
                 capture_status=capture['capture_status']))
        del self._timeline_pending[identity]
