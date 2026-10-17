"""CPU contract tests; execute in an existing server Docker, including -O."""
import unittest
from flagtree.profiler.timeline_storage import plan_compact_storage


class CompactStorageTests(unittest.TestCase):
    def plan(self, **overrides):
        p = dict(timeline_storage_version=1, timeline_record_version=2,
                 timeline_storage_policy='compact_selected_programs',
                 timeline_default_program_selection='runtime_first_last')
        p.update(overrides)
        return p

    def call(self, plan=None, **kwargs):
        args = dict(grid=(7, 1, 1), scratch_size=32800, alignment=128, num_ctas=1)
        args.update(kwargs)
        return plan_compact_storage(self.plan() if plan is None else plan, **args)

    def test_actual_grid_and_compact_budget(self):
        for grid, expected in [((1, 1, 1), (0,)), ((7, 1, 1), (0, 6)),
                               ((3, 5, 1), (0, 14)), ((2, 3, 4), (0, 23))]:
            with self.subTest(grid=grid):
                row = self.call(grid=grid)
                self.assertEqual(row['programs'], expected)
                self.assertEqual(row['slots'], tuple(enumerate(expected)))
                self.assertEqual(row['raw_bytes'], len(expected) * 32800)
        # Full-grid scratch would exceed the budget; compact storage does not.
        self.assertEqual(self.call(grid=(1000000, 1, 1))['raw_bytes'], 65600)

    def test_fixed_binary_selection_order(self):
        row = self.call(self.plan(timeline_fixed_programs=[6, 0, 2]))
        self.assertEqual(row['slots'], ((0, 6), (1, 0), (2, 2)))

    def test_zero_grid_has_no_events(self):
        self.assertEqual(self.call(grid=(0, 3, 1))['raw_bytes'], 0)
        self.assertEqual(self.call(grid=(0, 3, 1))['slots'], ())

    def test_legacy_unknown_and_forged_storage(self):
        for key, value in [('timeline_storage_version', None),
                           ('timeline_storage_version', True),
                           ('timeline_storage_version', 2),
                           ('timeline_record_version', 1),
                           ('timeline_storage_policy', 'full_grid'),
                           ('timeline_default_program_selection', 'cached_grid')]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    self.call(self.plan(**{key: value}))

    def test_invalid_grid_and_cluster(self):
        for grid in [(2, 3), (True, 1, 1), (-1, 1, 1),
                     (0x100000000, 1, 1), (65536, 65536, 1)]:
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                self.call(grid=grid)
        for n in (0, 2, True):
            with self.subTest(num_ctas=n), self.assertRaises(ValueError):
                self.call(num_ctas=n)

    def test_invalid_fixed_programs(self):
        for programs in [None, [], [0, 0], [7], [-1], [True], '0', [0x80000000]]:
            with self.subTest(programs=programs), self.assertRaises(ValueError):
                self.call(self.plan(timeline_fixed_programs=programs))

    def test_physical_budget_and_alignment(self):
        for opts in [dict(scratch_size=0), dict(scratch_size=True),
                     dict(alignment=3), dict(alignment=0),
                     dict(max_raw_bytes=65599), dict(max_raw_bytes=True)]:
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                self.call(**opts)


if __name__ == '__main__':
    unittest.main()
