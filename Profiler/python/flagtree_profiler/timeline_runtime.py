"""Per-invocation ownership for deferred timeline captures.

Transport operations own physical allocation, stream completion and readback.
This module never inserts a device barrier or interprets a vendor clock. It is
used by the timeline collector; legacy count/native hooks retain their ABI.
"""
import copy
import threading
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass

# Keep active owners alive even if a caller drops a failed session. Removing a
# Python reference is not evidence that device writers stopped. Recovery remains
# explicit; these entries are observable instead of silently freeing resources.
_RETAINED_POOLS = {}


@dataclass(frozen=True)
class TimelineReadback:
    """Acquired bytes, even when their integrity checks fail.

    A transport failure that acquired no bytes still raises. Integrity failures
    travel with the bytes so the owner can persist the evidence before rejecting
    interpretation. ``guard`` contains only the allocation's guard, not a second
    copy of its entire payload.
    """
    raw: bytes
    guard: bytes = b''
    validation_errors: tuple = ()

    def __post_init__(self):
        if (type(self.raw) is not bytes or type(self.guard) is not bytes
                or type(self.validation_errors) is not tuple or any(
                    type(item) is not str or not item
                    for item in self.validation_errors)):
            raise ValueError('Invalid timeline readback result')


def retained_owner_statuses():
    return {key: len(pool._owners) for key, pool in _RETAINED_POOLS.items()}


class TimelineOwnerPool:
    """Bounded single-host-thread pool with independent stream-local owners.

    ``read``'s deadline bounds completion polling. Individual SDK calls also
    require the outer process deadline used by the CLI/test controller. A stuck
    driver call is not safely interrupted by releasing its memory from Python.
    """

    def __init__(self,
                 transport,
                 *,
                 max_pending_bytes=8 * 1024 * 1024,
                 max_owners=64,
                 guard_bytes=0,
                 max_cumulative_raw_bytes=None):
        for name, value, low, high in (('max_pending_bytes', max_pending_bytes,
                                        1, 0x7fffffff), ('max_owners',
                                                         max_owners, 1, 4096),
                                       ('guard_bytes', guard_bytes, 0, 4096)):
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'Invalid {name}')
        if max_cumulative_raw_bytes is not None and (
                type(max_cumulative_raw_bytes) is not int
                or not 1 <= max_cumulative_raw_bytes <= 0x7fffffff):
            raise ValueError('Invalid max_cumulative_raw_bytes')
        self.max_cumulative_raw_bytes = max_cumulative_raw_bytes
        self.cumulative_admitted_raw_bytes = 0
        self.cumulative_admitted_physical_bytes = 0
        self.transport = transport
        self.max_pending_bytes = max_pending_bytes
        self.max_owners = max_owners
        self.guard_bytes = guard_bytes
        self.capture_id = 'timeline-' + uuid.uuid4().hex
        self._thread = threading.current_thread()
        self._owners = {}
        self._bytes = 0
        self._closed = False

    def _check_thread(self):
        if threading.current_thread() is not self._thread:
            raise RuntimeError(
                'Timeline owner pool does not support host-thread sharing')

    def _owner(self, invocation_id):
        self._check_thread()
        try:
            return self._owners[invocation_id]
        except (KeyError, TypeError) as error:
            raise ValueError('Unknown timeline invocation owner') from error

    @property
    def pending_bytes(self):
        self._check_thread()
        return self._bytes

    @property
    def invocation_ids(self):
        self._check_thread()
        return tuple(self._owners)

    def prepare(self, plan, *, binary_id, function, grid, scratch_size,
                alignment, num_ctas, device, stream):
        self._check_thread()
        if self._closed:
            raise RuntimeError('Timeline owner pool is closed')
        if (not isinstance(plan, Mapping) or type(binary_id) is not str
                or not binary_id or plan.get('binary_id') != binary_id):
            raise ValueError('Timeline plan is not bound to the loaded binary')
        validate_executable = getattr(self.transport, 'validate_executable',
                                      None)
        if validate_executable is not None:
            validate_executable(function, binary_id=binary_id)
        elif type(function) is not int or function <= 0:
            raise ValueError('An actual loaded function handle is required')
        if type(device) is not int or device < 0:
            raise ValueError('An actual device ordinal is required')
        if type(stream) is not int or stream < 0:
            raise ValueError('An actual stream handle is required')
        # All admission, including session totals, precedes any allocation.
        layout = self.transport.plan_storage(
            plan,
            grid=grid,
            scratch_size=scratch_size,
            alignment=alignment,
            num_ctas=num_ctas,
            max_raw_bytes=self.max_pending_bytes)
        if (not isinstance(layout, Mapping)
                or type(layout.get('raw_bytes')) is not int
                or not 0 <= layout['raw_bytes'] <= self.max_pending_bytes):
            raise ValueError(
                'Backend returned an invalid physical byte requirement')
        if not layout['raw_bytes']:
            raise ValueError('Zero-grid launches have no timeline owner')
        layout = copy.deepcopy(layout)
        physical_bytes = layout['raw_bytes'] + self.guard_bytes
        if (len(self._owners) >= self.max_owners
                or self._bytes + physical_bytes > self.max_pending_bytes):
            raise RuntimeError(
                'Timeline pending-owner budget exceeded before allocation')
        if (self.max_cumulative_raw_bytes is not None
                and self.cumulative_admitted_physical_bytes + physical_bytes
                > self.max_cumulative_raw_bytes):
            raise RuntimeError(
                'Timeline cumulative raw budget exceeded before allocation')
        self.transport.validate_target(device=device, stream=stream)
        invocation_id = 'invocation-' + uuid.uuid4().hex
        self._owners[invocation_id] = {
            'capture_id': self.capture_id,
            'invocation_id': invocation_id,
            'binary_id': binary_id,
            'function': copy.deepcopy(function),
            'device': device,
            'stream': stream,
            'plan': copy.deepcopy(plan),
            'layout': layout,
            'physical_bytes': physical_bytes,
            'guard_bytes': self.guard_bytes,
            'state': 'admitted',
            'resource': None,
            'raw': None,
            'host_admission_ns': time.monotonic_ns(),
            'host_window_clock': 'python.monotonic_ns',
            'submission_outcome': 'not_submitted',
            'error': None,
        }
        self._bytes += physical_bytes
        self.cumulative_admitted_raw_bytes += layout['raw_bytes']
        self.cumulative_admitted_physical_bytes += physical_bytes
        _RETAINED_POOLS[self.capture_id] = self
        return invocation_id

    def allocate(self, invocation_id):
        owner = self._owner(invocation_id)
        if owner['state'] != 'admitted':
            raise RuntimeError('Timeline owner allocation is not repeatable')
        try:
            resource = self.transport.allocate(owner)
        except BaseException as error:
            # allocate() must not submit device writes before handing ownership
            # back. initialize() is separate so even partial writes stay owned.
            owner['error'] = repr(error)
            raise
        owner['resource'] = resource
        owner['state'] = 'armed'
        try:
            self.transport.initialize(owner)
        except BaseException as error:
            owner.update(state='quarantined', error=repr(error))
            raise
        return self.transport.launch_buffer(owner)

    def mark_submitting(self, invocation_id):
        owner = self._owner(invocation_id)
        if owner['state'] != 'armed':
            raise RuntimeError('Timeline owner is not armed for submission')
        # Set before the launcher, which can fail after partial device work.
        owner.update(state='submitting', submission_outcome='uncertain')

    def finish_submission(self, invocation_id):
        owner = self._owner(invocation_id)
        if owner['state'] != 'submitting':
            raise RuntimeError('Timeline submission has no matching owner')
        try:
            self.transport.record_completion(owner)
        except BaseException as error:
            owner.update(state='quarantined', error=repr(error))
            raise
        owner.update(state='completion_pending', submission_outcome='returned')

    def abort(self, invocation_id):
        """Safely cancel unsubmitted state or retain possibly submitted writes."""
        owner = self._owner(invocation_id)
        if owner['state'] == 'admitted':
            self._remove(invocation_id)
            return
        if owner['state'] not in ('armed', 'submitting', 'quarantined'):
            raise RuntimeError('Cannot abort this timeline owner state')
        # Initialization itself may have written on the stream, so even an
        # armed-but-never-launched allocation requires completion proof.
        try:
            self.transport.record_completion(owner)
        except BaseException as error:
            owner.update(state='quarantined', error=repr(error))
            raise
        owner.update(state='completion_pending', submission_outcome='aborted')

    def snapshot(self, invocation_id):
        owner = self._owner(invocation_id)
        return copy.deepcopy({
            key: value
            for key, value in owner.items()
            if key not in ('resource', 'raw', 'readback_guard')
        })

    def completion_ready_now(self, invocation_id):
        """Nonblocking readiness for fair finalization; never reads or frees."""
        owner = self._owner(invocation_id)
        if owner['state'] in ('raw_ready',
                              'read_failed') or owner.get('completion_known'):
            return True
        if owner['state'] != 'completion_pending':
            return False
        try:
            ready = self.transport.completion_ready(owner)
            if type(ready) is not bool:
                raise RuntimeError('Transport completion query is not boolean')
        except BaseException as error:
            owner.update(state='quarantined', error=repr(error))
            raise
        if ready:
            owner['completion_known'] = True
            owner['host_completion_observed_ns'] = time.monotonic_ns()
        return ready

    def readback_guard(self, invocation_id):
        owner = self._owner(invocation_id)
        if owner['state'] != 'raw_ready':
            raise RuntimeError('Readback evidence is not available')
        return owner.get('readback_guard', b'')

    def read(self, invocation_id, *, timeout=60.0):
        owner = self._owner(invocation_id)
        if type(timeout) not in (int, float) or not 0 < timeout <= 300:
            raise ValueError(
                'Completion polling deadline must be in (0, 300] seconds')
        if owner['state'] == 'raw_ready':
            return owner['raw']
        if owner['state'] != 'completion_pending':
            raise RuntimeError('No completion proof is armed for this owner')
        deadline = time.monotonic() + timeout
        try:
            while True:
                ready = self.completion_ready_now(invocation_id)
                if ready:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        'Timeline writer is still pending; allocation retained'
                    )
                time.sleep(min(0.001, max(0, deadline - time.monotonic())))
        except TimeoutError:
            # The handle is still usable for a later poll; timeout != terminal.
            raise
        except BaseException as error:
            owner.update(state='quarantined', error=repr(error))
            raise
        owner['state'] = 'completion_observed'
        try:
            acquired = self.transport.read_raw(owner)
            legacy_bytes = type(acquired) is bytes
            if legacy_bytes:
                acquired = TimelineReadback(acquired)
            if not isinstance(acquired, TimelineReadback):
                raise RuntimeError(
                    'Transport did not return acquired timeline bytes')
        except BaseException as error:
            # Device completion was proven, but retain bytes/resource for an
            # explicit retry rather than replaying the application.
            owner.update(state='read_failed', error=repr(error))
            raise
        errors = list(acquired.validation_errors)
        if len(acquired.raw) != owner['layout']['raw_bytes']:
            errors.append('raw_extent_differs_from_admission')
        if not legacy_bytes and len(acquired.guard) != owner['guard_bytes']:
            # Legacy transports returning bytes do not promise a guard artifact.
            # Their own guard validation is unchanged; new transports return it.
            errors.append('guard_extent_differs_from_admission')
        owner.update(state='raw_ready',
                     raw=acquired.raw,
                     readback_guard=acquired.guard,
                     readback_integrity=dict(
                         status='invalid' if errors else 'passed',
                         errors=errors,
                         actual_raw_bytes=len(acquired.raw),
                         expected_raw_bytes=owner['layout']['raw_bytes'],
                         guard_bytes=len(acquired.guard)))
        return acquired.raw

    def retry_read(self, invocation_id, *, timeout=60.0):
        owner = self._owner(invocation_id)
        if owner['state'] != 'read_failed':
            raise RuntimeError('Owner has no retryable readback failure')
        owner['state'] = 'completion_pending'
        return self.read(invocation_id, timeout=timeout)

    def release(self, invocation_id):
        owner = self._owner(invocation_id)
        if owner['state'] != 'raw_ready':
            raise RuntimeError(
                'Cannot release a timeline writer without completed raw data')
        try:
            self.transport.release(owner)
        except BaseException as error:
            owner.update(error=repr(error), release_status='outcome_unknown')
            raise
        self._remove(invocation_id)

    def _remove(self, invocation_id):
        owner = self._owners.pop(invocation_id)
        self._bytes -= owner['physical_bytes']
        if not self._owners:
            _RETAINED_POOLS.pop(self.capture_id, None)

    def close(self):
        self._check_thread()
        # No implicit wait/replay or freeing pending allocations in __del__.
        if self._owners:
            raise RuntimeError(
                'Timeline owners remain; explicitly drain or recover them')
        self._closed = True
