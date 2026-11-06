"""Capacity-aware admission tests; no device execution or timing claims."""
import unittest

from flagtree.profiler.timeline_ascend import ascend_pending_byte_budget
from flagtree.profiler.timeline_runtime import TimelineOwnerPool


class GeometryTransport:
    def __init__(self, capacity):
        self.raw_bytes = 6 * (64 + 64 * capacity)
        self.validations = 0

    def plan_storage(self, plan, **kwargs):
        return dict(raw_bytes=self.raw_bytes)

    def validate_target(self, **kwargs):
        self.validations += 1


class AscendCapacityBudget(unittest.TestCase):
    def test_default_and_small_requests_keep_existing_policy(self):
        for capacity in (None, 1, 2048):
            self.assertEqual(ascend_pending_byte_budget(capacity), 8 * 1024**2)
        for capacity in (True, 0, 16385, 2.5):
            with self.assertRaises(ValueError):
                ascend_pending_byte_budget(capacity)

    def test_same_number_of_full_size_launches_are_admitted(self):
        # A split kernel and its merge are independent pending owners. The old
        # fixed budget admitted one 16384-pair launch and rejected its merge.
        counts = []
        for capacity in (2048, 4096, 8192, 16384):
            transport = GeometryTransport(capacity)
            budget = ascend_pending_byte_budget(capacity)
            pool = TimelineOwnerPool(transport, guard_bytes=128,
                                     max_pending_bytes=budget)
            physical = transport.raw_bytes + 128
            count = budget // physical
            for _ in range(count):
                pool.prepare({'binary_id': 'binary'}, binary_id='binary', function=1, grid=(2, 1, 1),
                             scratch_size=64 + 64*capacity, alignment=64,
                             num_ctas=None, device=0, stream=0)
            self.assertGreaterEqual(count, 2)
            self.assertEqual(pool.pending_bytes, count * physical)
            with self.assertRaisesRegex(RuntimeError, 'pending-owner budget'):
                pool.prepare({'binary_id': 'binary'}, binary_id='binary', function=1, grid=(2, 1, 1),
                             scratch_size=64 + 64*capacity, alignment=64,
                             num_ctas=None, device=0, stream=0)
            self.assertEqual(transport.validations, count)
            counts.append(count)
        self.assertEqual(counts, [10]*4)


if __name__ == '__main__':
    unittest.main()
