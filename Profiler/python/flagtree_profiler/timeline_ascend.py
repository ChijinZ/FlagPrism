"""Deferred Ascend stream transport and automatic public timeline collector."""
import base64
import copy
import hashlib
import json
from pathlib import Path

from .hooks.timeline import TimelineInstrumentationMixin, _persist
from .timeline_events_ascend import LAYOUT, compiler_actors, retained_binary


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def plan_ascend_storage(plan, *, grid, scratch_size, alignment, num_ctas,
                        max_raw_bytes):
    metadata = plan.get('compiler_metadata') or {}
    _need(
        metadata.get('hash') == plan.get('binary_id'),
        'Ascend plan/binary mismatch')
    compiler_actors(metadata)
    _need(
        type(grid) in (list, tuple) and len(grid) == 3
        and all(type(x) is int and 0 <= x <= 0x7fffffff for x in grid),
        'Invalid actual Ascend grid')
    volume = grid[0] * grid[1] * grid[2]
    _need(volume <= 0x7fffffff, 'Ascend logical grid exceeds bounded indexing')
    capacity = metadata['debug_record_capacity']
    stride = 64 + 64 * capacity
    _need(
        type(scratch_size) is int and scratch_size == stride
        and type(alignment) is int and alignment == 64 and num_ctas is None,
        'Ascend storage request contradicts the paired publisher')
    programs = () if not volume else (0, ) if volume == 1 else (0, volume - 1)
    size = len(programs) * 3 * stride
    _need(
        type(max_raw_bytes) is int and 0 < max_raw_bytes <= 0x7fffffff
        and size <= max_raw_bytes,
        'Ascend compact storage exceeds the admission budget')
    return dict(storage_version=1,
                publisher_version=1,
                grid=tuple(grid),
                programs=programs,
                slots=tuple(enumerate(programs)),
                alignment=64,
                scratch_size=stride,
                raw_bytes=size)


class AscendTimelineTransport:

    def __init__(self):
        import torch
        import torch_npu  # noqa: F401
        self.torch = torch
        self._prepared = {}

    def validate_executable(self, function, *, binary_id):
        kernel = self._prepared.get(binary_id)
        _need(
            kernel is not None and kernel.hash == binary_id
            and kernel.function is not None and type(function) is dict
            and function.get('kind') == 'ascend.compiled_kernel'
            and function.get('binary_id') == binary_id
            and function.get('binary_sha256') == hashlib.sha256(
                bytes(kernel.kernel)).hexdigest(),
            'Ascend requires the actual loaded compiled executable')

    def plan_storage(self, plan, **kwargs):
        return plan_ascend_storage(plan, **kwargs)

    def validate_target(self, *, device, stream):
        from flagtree.debugger.graph_guard import require_eager
        _need(self.torch.npu.current_device() == device,
              'Ascend launch device changed')
        actual = self.torch.npu.current_stream(device)
        _need(
            int(actual.npu_stream) == stream,
            'Ascend launch stream differs from the actual current queue')
        require_eager('ascend', stream=stream)

    def allocate(self, owner):
        torch = self.torch
        with torch.npu.device(owner['device']):
            stream = torch.npu.current_stream(owner['device'])
            _need(
                int(stream.npu_stream) == owner['stream'],
                'Ascend queue changed before allocation')
            event = torch.npu.Event(enable_timing=False)
            # No initialization is submitted until the owner holds all resources.
            allocation = torch.empty(owner['physical_bytes'],
                                     dtype=torch.uint8,
                                     device='npu:' + str(owner['device']))
        _need(
            owner['guard_bytes'] == 128 and allocation.data_ptr() % 64 == 0,
            'Ascend timeline requires aligned storage and both allocation guards'
        )
        return dict(allocation=allocation,
                    buffer=allocation[64:-64],
                    stream=stream,
                    event=event,
                    kernel_ref=self._prepared[owner['binary_id']])

    def initialize(self, owner):
        resource = owner['resource']
        with self.torch.npu.device(owner['device']), self.torch.npu.stream(
                resource['stream']):
            resource['buffer'].zero_()
            resource['allocation'][:64].fill_(165)
            resource['allocation'][-64:].fill_(165)

    def launch_buffer(self, owner):
        return int(owner['resource']['buffer'].data_ptr())

    def record_completion(self, owner):
        with self.torch.npu.device(owner['device']):
            owner['resource']['event'].record(owner['resource']['stream'])

    def completion_ready(self, owner):
        with self.torch.npu.device(owner['device']):
            return owner['resource']['event'].query()

    def read_raw(self, owner):
        from .timeline_runtime import TimelineReadback
        resource = owner['resource']
        with self.torch.npu.device(owner['device']), self.torch.npu.stream(
                resource['stream']):
            data = resource['allocation'].cpu().numpy().tobytes()
        guard = data[:64] + data[-64:]
        errors = () if guard == bytes([165]) * 128 else (
            'allocation_guard_changed', )
        return TimelineReadback(data[64:-64], guard, errors)

    def release(self, owner):
        owner['resource'] = None


class AscendTimelineCollector(TimelineInstrumentationMixin):

    def __init__(self):
        self._init_timeline_state(AscendTimelineTransport(), guard_bytes=128)

    def activate(self):
        from flagtree.debugger import register_launch_prepare_hook
        register_launch_prepare_hook(self.prepare_launch)

    def prepare_launch(self, metadata, stream, launch_metadata, kernel_args):
        from flagtree.debugger import api
        from .hooks.launch import _json_value
        self.timeline_pool._check_thread()
        actual = _json_value(api._build_launch_metadata_dict(metadata))
        identity_object = (
            launch_metadata.get('_flagprism_launch_identity_object')
            if isinstance(launch_metadata, dict) else launch_metadata)
        bridge = getattr(identity_object, '_flagprism_launch_context', None)
        _need(
            type(bridge) is dict and bridge.get('kernel') is not None,
            'Ascend timeline requires the actual per-launch compiled kernel')
        kernel = bridge['kernel']
        binary = bytes(kernel.kernel)
        _need(
            actual.get('hash') == kernel.hash
            and retained_binary(actual) == binary,
            'Actual loaded binary differs from the retained SDK output')
        grid = api._normalize_launch_grid(
            api._materialize_launch_metadata(launch_metadata))
        _need(grid is not None, 'Actual Ascend grid is unavailable')
        runtime = api._infer_runtime_metadata(metadata, kernel_args)
        runtime.update(
            grid=grid,
            record_layout=LAYOUT,
            record_plan=[],
            records_per_instance=actual['debug_records_per_instance'])
        plan = dict(binary_id=kernel.hash,
                    compiler_metadata=actual,
                    runtime_metadata=runtime)
        stride = 64 + 64 * actual['debug_record_capacity']
        layout = plan_ascend_storage(
            plan,
            grid=grid,
            scratch_size=stride,
            alignment=64,
            num_ctas=None,
            max_raw_bytes=self.timeline_pool.max_pending_bytes)
        if not layout['raw_bytes']:
            return api.PreparedKernelLaunch(kernel_args=(0, ),
                                            synchronize=False)
        executable = dict(kind='ascend.compiled_kernel',
                          binary_id=kernel.hash,
                          binary_sha256=hashlib.sha256(binary).hexdigest(),
                          entry_name=kernel.name)
        transport = self.timeline_pool.transport
        transport._prepared[kernel.hash] = kernel
        identity = None
        try:
            identity = self.timeline_pool.prepare(
                plan,
                binary_id=kernel.hash,
                function=executable,
                grid=grid,
                scratch_size=stride,
                alignment=64,
                num_ctas=None,
                device=int(transport.torch.npu.current_device()),
                stream=int(stream))
            fn = getattr(kernel.src, 'fn', None)
            snapshot = dict(binary_base64=base64.b64encode(binary).decode(),
                            executable=executable,
                            kernel_source=getattr(fn, 'src', None),
                            compiler_artifacts={
                                k: v
                                for k, v in kernel.asm.items()
                                if type(v) is str
                            })
            self._timeline_descriptors[identity] = dict(
                launch=None,
                metadata=dict(compiler_metadata=actual,
                              compiled_snapshot=snapshot,
                              runtime_device=dict(
                                  device=int(
                                      transport.torch.npu.current_device()),
                                  name=transport.torch.npu.get_device_name(
                                      transport.torch.npu.current_device()))))
            pointer = self.timeline_pool.allocate(identity)
            self.timeline_pool.mark_submitting(identity)
        except BaseException as error:
            if identity is not None:
                try:
                    self.timeline_pool.abort(identity)
                except BaseException as cleanup:
                    if hasattr(error, 'add_note'):
                        error.add_note('Ascend owner retained: ' +
                                       repr(cleanup))
            raise
        finally:
            transport._prepared.pop(kernel.hash, None)

        def submitted(error):
            if error is not None:
                self.timeline_pool.abort(identity)
                return
            association = getattr(identity_object,
                                  '_flagprism_invocation_identity', None)
            if (type(association) is not dict or association.get('evidence')
                    != 'same_launch_metadata_object'
                    or association.get('binary_id') != kernel.hash):
                self.timeline_pool.abort(identity)
                raise RuntimeError(
                    'Actual Ascend launch association is unavailable')
            self._timeline_descriptors[identity]['launch'] = copy.deepcopy(
                association)
            self.timeline_pool.finish_submission(identity)

        return api.PreparedKernelLaunch(kernel_args=(pointer, ),
                                        finalize=submitted,
                                        synchronize=False)

    def _decode_timeline_original(self, identity, directory, deadline):
        from .timeline_events_ascend import attach_ascend_timeline_export
        capture = json.loads(
            (directory / self._timeline_pending[identity]).read_text())
        owner = capture['owner']
        raw = (directory / capture['raw_file']).read_bytes()
        _need(
            hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
            'Retained Ascend raw changed')
        _need(
            owner.get('readback_integrity', {}).get('status') != 'invalid',
            'Ascend readback integrity failed')
        prefix = Path('captures') / identity
        capture['capture_status'] = 'aborted'
        if owner['submission_outcome'] == 'returned':
            exported = attach_ascend_timeline_export(
                raw,
                owner=owner,
                metadata=capture['metadata']['compiler_metadata'],
                association=capture['launch'])
            batch = exported['canonical_timeline']
            capture.update(events_file=str(prefix.with_suffix('.events.json')),
                           capture_status='raw_complete'
                           if batch['complete'] else 'incomplete')
            _persist(directory / capture['events_file'],
                     (json.dumps(batch, indent=2) + '\n').encode())
            from .timeline_ascend_machine import inspect_capture_binary
            capture['machine_counter_mapping'] = inspect_capture_binary(
                directory, metadata=capture['metadata'], deadline=deadline)
            try:
                from .timeline_unit_ascend import load_counter_unit_proofs
                from .timeline_views import derive_counter_ns_views
                from .timeline_perfetto import write_counter_exports
                proofs = load_counter_unit_proofs(directory, capture, batch)
                views = derive_counter_ns_views(batch, proofs)
                capture['counter_ns_exports'] = write_counter_exports(
                    directory, prefix, views, batch, proofs=proofs)
                capture['counter_ns_status'] = dict(
                    status='counter_unit_only',
                    read_precision_status='unverified',
                    time_arrows_verified=False)
            except (ValueError, OSError, KeyError, TypeError,
                    UnicodeError) as error:
                capture['counter_ns_status'] = dict(status='unavailable',
                                                    reason=str(error))
            from flagtree.debugger import api
            api._exported_runs.append(exported)
        _persist(directory / prefix.with_suffix('.json'),
                 (json.dumps(capture, indent=2) + '\n').encode())
        self._timeline_rows.append(
            dict(invocation_id=identity,
                 capture_id=owner['capture_id'],
                 binary_id=owner['binary_id'],
                 capture_file=str(prefix.with_suffix('.json')),
                 capture_status=capture['capture_status']))
        del self._timeline_pending[identity]
