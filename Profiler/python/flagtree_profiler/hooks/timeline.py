"""NVIDIA timeline integration for the real instrumentation hook.

Raw timestamps and compiler logical facts are retained now. Clock/epoch and
machine-boundary certification are separate gates; no ns or hardware busy is
invented by this collector.
"""
import copy
from contextvars import ContextVar
import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import time


def _persist(path, payload, *, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == payload:
            return
        if not replace:
            raise RuntimeError(
                'Refusing to replace different timeline evidence: ' +
                str(path))
    fd, temporary = tempfile.mkstemp(prefix='.timeline-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class TimelineAllocator:

    def __init__(self, hook):
        self.hook = hook

    def validate_launch(self,
                        *,
                        function,
                        grid,
                        scratch_size,
                        alignment,
                        num_ctas,
                        stream=None):
        import torch
        from ..timeline_storage import plan_compact_storage
        hook = self.hook
        if hook._timeline_current.get() is not None:
            raise RuntimeError(
                'Previous timeline launch still owns the current submission')
        if type(stream) is not int:
            raise RuntimeError(
                'Timeline requires preallocation stream admission ABI v2')
        metadata = hook.observation_metadata.get(function)
        if metadata is None:
            raise RuntimeError(
                'Actual loaded timeline function metadata is missing')
        compiler = metadata.get('compiler_metadata') or {}
        if (scratch_size != compiler.get('profile_scratch_size')
                or num_ctas != compiler.get('num_ctas')
                or alignment != hook.profile_buffer_alignment):
            raise RuntimeError(
                'Timeline launch contradicts actual compiled scratch ABI')
        plan = metadata['automatic_plan']
        layout = plan_compact_storage(plan,
                                      grid=grid,
                                      scratch_size=scratch_size,
                                      alignment=alignment,
                                      num_ctas=num_ctas)
        hook._timeline_zero.set(not layout['raw_bytes'])
        if not layout['raw_bytes']:
            return
        identity = hook.timeline_pool.prepare(plan,
                                              binary_id=metadata['binary_id'],
                                              function=function,
                                              grid=grid,
                                              scratch_size=scratch_size,
                                              alignment=alignment,
                                              num_ctas=num_ctas,
                                              device=int(
                                                  torch.cuda.current_device()),
                                              stream=stream)
        hook._timeline_current.set(identity)
        hook._timeline_descriptors[identity] = {
            'metadata': copy.deepcopy(metadata),
            'launch': None
        }

    def __call__(self, size, alignment, stream):
        hook = self.hook
        if hook._timeline_zero.get():
            if size != 0:
                raise RuntimeError(
                    'Zero-grid timeline launch requested nonzero records')
            return None
        identity = hook._timeline_current.get()
        snapshot = hook.timeline_pool.snapshot(identity)
        if (size != snapshot['layout']['logical_request_bytes']
                or alignment != snapshot['layout']['alignment']
                or stream != snapshot['stream']):
            raise RuntimeError(
                'Timeline allocation has no matching launch admission')
        return hook.timeline_pool.allocate(identity)


class TimelineInstrumentationMixin:

    def _init_timeline(self):
        from ..timeline_cuda_runtime import CudaTimelineTransport
        self._init_timeline_state(CudaTimelineTransport())
        self.allocator = TimelineAllocator(self)

    def _init_timeline_state(self, transport, *, guard_bytes=0):
        from ..timeline_runtime import TimelineOwnerPool
        self.timeline_pool = TimelineOwnerPool(transport,
                                               guard_bytes=guard_bytes)
        self._timeline_current = ContextVar('timeline_current_owner',
                                            default=None)
        self._timeline_zero = ContextVar('timeline_zero_grid', default=False)
        self._timeline_descriptors = {}
        self._timeline_rows = []
        self._timeline_machine = {}
        self._timeline_pending = {}
        self._timeline_directory = None
        self._timeline_flush_attempt = 0

    def _timeline_fingerprint(self):
        from ..native import compiler_binding
        from triton._C import libtriton
        from .. import timeline_runtime, timeline_cuda_runtime
        from .. import timeline_events, timeline_events_nvidia, timeline_nvidia_machine
        binding = compiler_binding()
        if (getattr(binding, 'TIMELINE_RECORD_VERSION', None) != 3
                or getattr(binding, 'TIMELINE_STORAGE_VERSION', None) != 1
                or getattr(binding, 'TIMELINE_BOUNDARY_VERSION', None) != 3
                or getattr(binding, 'TIMELINE_MARKER_VERSION', None) != 1):
            raise RuntimeError(
                'Timeline requires its matching native compiler ABI')
        driver = importlib.import_module('triton.backends.nvidia.driver')
        if getattr(driver.CudaLauncher, 'profile_admission_version',
                   None) != 2:
            raise RuntimeError(
                'Rebuild the launcher with preallocation-admission.patch v2')
        paths = [
            libtriton.__file__, driver.__file__, __file__,
            str(Path(__file__).with_name('instrumentation.py')),
            timeline_events.__file__, timeline_events_nvidia.__file__,
            timeline_nvidia_machine.__file__, timeline_runtime.__file__,
            timeline_cuda_runtime.__file__
        ]
        return hashlib.sha256(''.join(
            hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for path in paths).encode()).hexdigest()

    def _timeline_enter(self, metadata):
        if self._timeline_zero.get():
            return
        identity = self._timeline_current.get()
        if identity is None:
            raise RuntimeError(
                'Timeline launch is missing its admitted allocation')
        owner = self.timeline_pool.snapshot(identity)
        bridge = getattr(metadata, '_flagprism_invocation_identity',
                         None) or {}
        if (metadata.data.get('function') != owner['function']
                or metadata.data.get('stream') != owner['stream']
                or bridge.get('binary_id') != owner['binary_id']
                or not bridge.get('invocation_id')):
            raise RuntimeError(
                'Timeline launch identity does not match its binary/stream owner'
            )
        self._timeline_descriptors[identity]['launch'] = copy.deepcopy(bridge)
        self.timeline_pool.mark_submitting(identity)

    def _timeline_exit(self, metadata):
        if self._timeline_zero.get():
            self._timeline_zero.set(False)
            return
        identity = self._timeline_current.get()
        self.timeline_pool.finish_submission(identity)
        self._timeline_current.set(None)

    def _timeline_abort(self, error=None):
        identity = self._timeline_current.get()
        self._timeline_zero.set(False)
        if identity is None:
            return
        try:
            self.timeline_pool.abort(identity)
            self._timeline_current.set(None)
        except BaseException as cleanup_error:
            if error is not None and hasattr(error, 'add_note'):
                error.add_note('Timeline writer remains retained: ' +
                               repr(cleanup_error))
            else:
                raise

    def _retain_timeline_original(self, identity, directory, deadline):
        """Durably retain one owner independently of decoding/visualization."""
        owner = self.timeline_pool.snapshot(identity)
        if owner['state'] in ('armed', 'submitting', 'quarantined',
                              'admitted'):
            self.timeline_pool.abort(identity)
            if identity not in self.timeline_pool.invocation_ids:
                self._timeline_descriptors.pop(identity, None)
                return
            owner = self.timeline_pool.snapshot(identity)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                'Timeline finalization budget exhausted; owner retained')
        if owner['state'] == 'read_failed':
            raw = self.timeline_pool.retry_read(identity,
                                                timeout=min(remaining, 60))
        else:
            raw = self.timeline_pool.read(identity, timeout=min(remaining, 60))
        owner = self.timeline_pool.snapshot(identity)
        descriptor = self._timeline_descriptors[identity]
        metadata = descriptor['metadata']
        prefix = Path('captures') / identity
        _persist(directory / prefix.with_suffix('.raw'), raw)
        guard = self.timeline_pool.readback_guard(identity)
        guard_file = None
        if guard:
            guard_file = str(prefix.with_suffix('.guard.raw'))
            _persist(directory / guard_file, guard)
        capture = dict(owner=owner,
                       launch=descriptor['launch'],
                       metadata=metadata,
                       raw_file=str(prefix.with_suffix('.raw')),
                       raw_sha256=hashlib.sha256(raw).hexdigest(),
                       clock_status='unverified',
                       time_arrow_verified=False,
                       capture_status='raw_persisted_pending_decode')
        if guard_file is not None:
            capture['readback_guard'] = dict(
                file=guard_file,
                bytes=len(guard),
                sha256=hashlib.sha256(guard).hexdigest())
        _persist(directory / prefix.with_suffix('.input.json'),
                 (json.dumps(capture, indent=2) + '\n').encode())
        # Retain compiler/source objects before giving up the device owner.
        # A decoder failure must not prevent another invocation's raw salvage.
        for artifact in metadata.get('timeline_artifacts', []):
            payload = Path(artifact['path']).read_bytes()
            if hashlib.sha256(payload).hexdigest() != artifact['sha256']:
                raise RuntimeError(
                    'Compiled timeline artifact changed before export')
            _persist(directory / artifact['retained_file'], payload)
        self._timeline_pending[identity] = str(
            prefix.with_suffix('.input.json'))
        self.timeline_pool.release(identity)
        self._timeline_descriptors.pop(identity, None)

    def _decode_timeline_original(self, identity, directory, deadline):
        from ..timeline_nvidia import decode_timeline_ring
        from ..timeline_nvidia_async import derive_cp_async_facts
        from ..timeline_events_nvidia import canonicalize_nvidia_capture
        from ..timeline_nvidia_machine import inspect_capture_binary
        input_file = directory / self._timeline_pending[identity]
        capture = json.loads(input_file.read_text())
        owner, metadata = capture['owner'], capture['metadata']
        raw = (directory / capture['raw_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != capture['raw_sha256']:
            raise RuntimeError('Retained timeline raw changed before decoding')
        guard = capture.get('readback_guard')
        if guard is not None:
            payload = (directory / guard['file']).read_bytes()
            if len(payload) != guard['bytes'] or hashlib.sha256(
                    payload).hexdigest() != guard['sha256']:
                raise RuntimeError(
                    'Retained timeline guard changed before decoding')
        integrity = owner.get('readback_integrity', {})
        if integrity.get('status') == 'invalid':
            raise ValueError('Timeline readback integrity failed: ' +
                             repr(integrity['errors']))
        prefix = Path('captures') / identity
        capture['capture_status'] = 'aborted'
        if owner['submission_outcome'] == 'returned':
            warps = metadata['compiler_metadata']['num_warps']
            decoded = decode_timeline_ring(
                raw,
                scratch_size=owner['layout']['scratch_size'],
                total_warps=warps,
                selected_warps=tuple(range(warps)),
                slots=tuple(tuple(slot) for slot in owner['layout']['slots']),
                scope_ids=frozenset(
                    int(k) for k, _ in metadata['scope_id_names']),
                record_version=owner['plan']['timeline_record_version'])
            capture['capture_status'] = 'raw_complete' if decoded[
                'complete'] else 'incomplete'
            capture['decoded_file'] = str(prefix.with_suffix('.decoded.json'))
            capture['async_file'] = str(prefix.with_suffix('.async.json'))
            facts = derive_cp_async_facts(decoded,
                                          owner['plan'],
                                          capture_id=owner['capture_id'],
                                          invocation_id=identity,
                                          binary_id=owner['binary_id'])
            canonical = canonicalize_nvidia_capture(
                decoded,
                owner=owner,
                metadata=metadata,
                raw_sha256=capture['raw_sha256'],
                raw_bytes=len(raw))
            capture['events_file'] = str(prefix.with_suffix('.events.json'))
            for suffix, value in (('.events.json', canonical),
                                  ('.decoded.json', decoded), ('.async.json',
                                                               facts)):
                _persist(directory / prefix.with_suffix(suffix),
                         (json.dumps(value, indent=2) + '\n').encode())
        key = (str(directory), owner['binary_id'])
        if key not in self._timeline_machine:
            self._timeline_machine[key] = inspect_capture_binary(
                directory,
                metadata=metadata,
                plan=owner['plan'],
                deadline=deadline)
        capture['machine_counter_mapping'] = self._timeline_machine[key]
        if owner['submission_outcome'] == 'returned':
            from ..timeline_unit_nvidia import load_counter_unit_proofs
            from ..timeline_views import derive_counter_ns_views
            from ..timeline_perfetto import write_counter_exports
            try:
                proofs = load_counter_unit_proofs(directory, capture,
                                                  canonical)
            except (ValueError, OSError, KeyError, TypeError) as error:
                capture['counter_ns_status'] = dict(status='unavailable',
                                                    reason=str(error))
            else:
                views = derive_counter_ns_views(canonical, proofs)
                capture['counter_ns_exports'] = write_counter_exports(
                    directory, prefix, views, canonical, proofs=proofs)
                capture['counter_ns_status'] = dict(
                    status='counter_unit_only',
                    read_precision_status='unverified',
                    time_arrows_verified=False)
        _persist(directory / prefix.with_suffix('.json'),
                 (json.dumps(capture, indent=2) + '\n').encode())
        self._timeline_rows.append(
            dict(invocation_id=identity,
                 capture_id=owner['capture_id'],
                 binary_id=owner['binary_id'],
                 capture_file=str(prefix.with_suffix('.json')),
                 capture_status=capture['capture_status']))
        del self._timeline_pending[identity]

    def flush_timeline(self, base):
        """Salvage all owners before derived work; retry without application replay."""
        directory = Path(base).with_suffix('.timeline').resolve()
        if self._timeline_directory not in (None, str(directory)):
            raise RuntimeError(
                'Recover timeline into its original evidence directory')
        self._timeline_directory = str(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self._timeline_flush_attempt += 1
        deadline = time.monotonic() + 60
        errors, failures = [], []

        def failed(identity, stage, error):
            errors.append(error)
            failures.append(
                dict(invocation_id=identity,
                     stage=stage,
                     error_type=type(error).__name__,
                     error=str(error)))

        # No decoder/formatter can stop this pass. Failed reads remain owned;
        # safely saved captures no longer consume device-owner admission budget.
        waiting = list(self.timeline_pool.invocation_ids)
        while waiting and time.monotonic() < deadline:
            progressed = False
            for identity in tuple(waiting):
                if time.monotonic() >= deadline:
                    break
                try:
                    owner = self.timeline_pool.snapshot(identity)
                    if owner['state'] in ('armed', 'submitting', 'quarantined',
                                          'admitted'):
                        self.timeline_pool.abort(identity)
                        if identity not in self.timeline_pool.invocation_ids:
                            self._timeline_descriptors.pop(identity, None)
                            waiting.remove(identity)
                            progressed = True
                            continue
                    if not self.timeline_pool.completion_ready_now(identity):
                        continue
                    self._retain_timeline_original(identity, directory,
                                                   deadline)
                    waiting.remove(identity)
                    progressed = True
                except Exception as error:
                    failed(identity, 'retain_original', error)
                    waiting.remove(identity)
            if waiting and not progressed:
                time.sleep(min(0.001, max(0, deadline - time.monotonic())))
        for identity in waiting:
            failed(
                identity, 'retain_original',
                TimeoutError(
                    'Timeline finalization budget exhausted; owner and acquired bytes retained'
                ))
        for identity in tuple(self._timeline_pending):
            # A failed resource release remains retryable in the owner pool.
            if identity in self.timeline_pool.invocation_ids:
                continue
            try:
                self._decode_timeline_original(identity, directory, deadline)
            except Exception as error:
                failed(identity, 'decode_export', error)
        attempt = dict(schema_version=1,
                       attempt=self._timeline_flush_attempt,
                       failures=failures,
                       pending_decode=list(self._timeline_pending),
                       retained_owners=list(self.timeline_pool.invocation_ids))
        try:
            _persist(
                directory / 'attempts' /
                f'flush-{self._timeline_flush_attempt:04d}.json',
                (json.dumps(attempt, indent=2) + '\n').encode())
        except Exception as error:
            failed(None, 'persist_attempt', error)
        index = dict(
            schema_version=1,
            status='partial_clock_unverified',
            captures=self._timeline_rows,
            clock_status='unverified',
            failures=failures,
            pending_decode=list(self._timeline_pending),
            retained_owners=list(self.timeline_pool.invocation_ids),
            retained_owner_states={
                identity: self.timeline_pool.snapshot(identity)
                for identity in self.timeline_pool.invocation_ids
            },
            notes=[
                'Raw ticks are not certified ns or a shared epoch.',
                'Logical async facts are not verified time arrows.',
                'Public collection alone does not satisfy full timeline acceptance.'
            ])
        try:
            _persist(directory / 'index.json',
                     (json.dumps(index, indent=2) + '\n').encode(),
                     replace=True)
            from ..timeline_perfetto import write_trace_index
            write_trace_index(directory, self._timeline_rows)
        except Exception as error:
            failed(None, 'persist_index', error)
        if errors:
            first = errors[0]
            if hasattr(first, 'add_note'):
                first.add_note('Timeline finalization failures: ' +
                               repr(failures))
                first.add_note('Timeline originals retained at ' +
                               str(directory))
            raise first
        return directory
