"""Owner safety contracts; fake transport is not CUDA/device evidence."""
import gc
import threading
import unittest
import weakref

from flagtree.profiler.timeline_runtime import TimelineOwnerPool, retained_owner_statuses
from flagtree.profiler.timeline_storage import plan_compact_storage


class Transport:
    def __init__(self):
        self.actions = []
        self.ready = False
        self.fail = None

    def plan_storage(self, plan, **kwargs):
        return plan_compact_storage(plan, **kwargs)

    def validate_target(self, **kwargs):
        self.actions.append(('validate', kwargs))

    def allocate(self, owner):
        self.actions.append(('allocate', owner['invocation_id']))
        if self.fail == 'allocate':
            raise RuntimeError('allocation failure without writes')
        return bytearray(owner['physical_bytes'])

    def initialize(self, owner):
        self.actions.append(('initialize', owner['invocation_id']))
        if self.fail == 'initialize':
            raise RuntimeError('partially initialized writes')

    def launch_buffer(self, owner):
        return owner['resource']

    def record_completion(self, owner):
        self.actions.append(('record', owner['invocation_id']))
        if self.fail == 'record':
            raise RuntimeError('completion handle failure')

    def completion_ready(self, owner):
        self.actions.append(('query', owner['invocation_id']))
        return self.ready

    def read_raw(self, owner):
        self.actions.append(('read', owner['invocation_id']))
        if self.fail == 'read':
            raise RuntimeError('D2H failure')
        return bytes(owner['layout']['raw_bytes'])

    def release(self, owner):
        self.actions.append(('release', owner['invocation_id']))
        owner['resource'] = None


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.backend = Transport()
        self.pool = TimelineOwnerPool(self.backend, max_pending_bytes=2048, guard_bytes=32)
        self.plan = dict(binary_id='binary-A', timeline_storage_version=1,
                         timeline_record_version=2,
                         timeline_storage_policy='compact_selected_programs',
                         timeline_default_program_selection='runtime_first_last')

    def tearDown(self):
        self.backend.fail, self.backend.ready = None, True
        for identity in self.pool.invocation_ids:
            state = self.pool.snapshot(identity)['state']
            if state == 'admitted':
                self.pool.abort(identity)
                continue
            if state in ('armed', 'submitting', 'quarantined'):
                self.pool.abort(identity)
            if state == 'read_failed':
                self.pool.retry_read(identity)
            else:
                self.pool.read(identity)
            self.pool.release(identity)
        self.pool.close()

    def prepare(self, **overrides):
        args = dict(binary_id='binary-A', function=42, grid=(7, 1, 1),
                    scratch_size=128, alignment=128, num_ctas=1, device=0, stream=12)
        args.update(overrides)
        return self.pool.prepare(self.plan, **args)

    def submit(self, identity):
        self.pool.allocate(identity)
        self.pool.mark_submitting(identity)
        self.pool.finish_submission(identity)

    def test_distinct_owners_no_launch_wait(self):
        a, b = self.prepare(), self.prepare(stream=13)
        self.submit(a)
        self.submit(b)
        self.assertNotEqual(a, b)
        self.assertEqual(self.pool.pending_bytes, 576)
        self.assertFalse(any(a[0] in ('query', 'read') for a in self.backend.actions))
        self.backend.ready = True
        self.assertEqual(len(self.pool.read(a)), 256)
        self.pool.release(a)
        self.assertEqual(self.pool.snapshot(b)['stream'], 13)

    def test_snapshot_isolation(self):
        a = self.prepare()
        self.plan['binary_id'] = 'changed'
        snapshot = self.pool.snapshot(a)
        snapshot['layout']['grid'] = (1, 1, 1)
        snapshot['plan']['binary_id'] = 'forged'
        self.assertEqual(self.pool.snapshot(a)['plan']['binary_id'], 'binary-A')
        self.assertEqual(self.pool.snapshot(a)['layout']['grid'], (7, 1, 1))

    def test_wrong_binary_no_allocation(self):
        with self.assertRaises(ValueError):
            self.prepare(binary_id='binary-B')
        self.assertFalse(self.backend.actions)

    def test_pending_budget_rejects_before_allocate(self):
        a = self.prepare()
        self.submit(a)
        with self.assertRaises(RuntimeError):
            self.prepare(scratch_size=1024)
        self.assertEqual(self.pool.invocation_ids, (a,))
        self.assertEqual(len([a for a in self.backend.actions if a[0] == 'allocate']), 1)

    def test_owner_count_budget(self):
        self.pool.max_owners = 1
        a = self.prepare()
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.assertEqual(self.pool.invocation_ids, (a,))

    def test_no_early_release(self):
        a = self.prepare()
        self.submit(a)
        with self.assertRaises(RuntimeError):
            self.pool.release(a)
        with self.assertRaises(RuntimeError):
            self.pool.close()
        self.assertFalse(any(a[0] == 'release' for a in self.backend.actions))

    def test_timeout_is_not_writer_completion(self):
        a = self.prepare()
        self.submit(a)
        with self.assertRaises(TimeoutError):
            self.pool.read(a, timeout=0.001)
        self.assertEqual(self.pool.snapshot(a)['state'], 'completion_pending')
        self.assertEqual(self.pool.pending_bytes, 288)
        self.backend.ready = True
        self.assertEqual(len(self.pool.read(a)), 256)

    def test_cancel_admitted_has_no_device_resource(self):
        a = self.prepare()
        self.pool.abort(a)
        self.assertEqual(self.pool.pending_bytes, 0)
        self.assertFalse(any(a[0] in ('allocate', 'record') for a in self.backend.actions))

    def test_cancel_armed_waits_for_initializer(self):
        a = self.prepare()
        self.pool.allocate(a)
        self.pool.abort(a)
        self.assertEqual(self.pool.snapshot(a)['submission_outcome'], 'aborted')
        with self.assertRaises(RuntimeError):
            self.pool.release(a)

    def test_initialization_failure_retains_resource(self):
        a = self.prepare()
        self.backend.fail = 'initialize'
        with self.assertRaises(RuntimeError):
            self.pool.allocate(a)
        self.assertEqual(self.pool.snapshot(a)['state'], 'quarantined')
        self.assertIn(self.pool.capture_id, retained_owner_statuses())

    def test_completion_handle_failure_retains_resource(self):
        a = self.prepare()
        self.pool.allocate(a)
        self.pool.mark_submitting(a)
        self.backend.fail = 'record'
        with self.assertRaises(RuntimeError):
            self.pool.finish_submission(a)
        self.assertEqual(self.pool.snapshot(a)['state'], 'quarantined')

    def test_read_failure_retries_without_relaunch(self):
        a = self.prepare()
        self.submit(a)
        self.backend.ready, self.backend.fail = True, 'read'
        with self.assertRaises(RuntimeError):
            self.pool.read(a)
        self.assertEqual(self.pool.snapshot(a)['state'], 'read_failed')
        self.backend.fail = None
        self.assertEqual(len(self.pool.retry_read(a)), 256)
        self.assertEqual(len([a for a in self.backend.actions if a[0] == 'allocate']), 1)

    def test_host_thread_rejected_before_allocation(self):
        errors = []
        def worker():
            try:
                self.prepare()
            except BaseException as error:
                errors.append(error)
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)
        self.assertFalse(self.backend.actions)

    def test_abandoned_pool_retained_until_safe_recovery(self):
        a = self.prepare()
        self.submit(a)
        ref = weakref.ref(self.pool)
        self.pool = None
        gc.collect()
        self.assertIsNotNone(ref())
        self.pool = ref()

    def test_release_requires_known_invocation(self):
        with self.assertRaises(ValueError):
            self.pool.release('some-other-invocation')

    def test_nonboolean_completion_cannot_authorize_readback(self):
        a = self.prepare()
        self.submit(a)
        self.backend.ready = 1
        with self.assertRaises(RuntimeError):
            self.pool.read(a)
        self.assertEqual(self.pool.snapshot(a)['state'], 'quarantined')
        self.assertFalse(any(action[0] == 'read' for action in self.backend.actions))


if __name__ == '__main__':
    unittest.main()
