"""CPU algebra contracts only; causal ordering/clock qualification need devices."""
import unittest
from flagtree.profiler.timeline_clock import bound_causal_offset


class CausalClockBounds(unittest.TestCase):
    def test_intersection_preserves_asymmetric_delay(self):
        self.assertEqual(bound_causal_offset([(100,145,160,130),
                                              (200,244,260,225)]), (35,44))
        # The midpoint is an optional coordinate, not an asserted true offset.
        self.assertEqual(bound_causal_offset([(100,145,160,130)]), (30,45))

    def test_endpoint_bounds_expand_inequalities(self):
        self.assertEqual(bound_causal_offset([(100,145,160,130),
            (200,244,260,225)], endpoint_errors=(1,2,3,4)), (28,47))
        self.assertEqual(bound_causal_offset([(0,0,0,0)]), (0,0))

    def test_large_absolute_timestamps_are_exact(self):
        base=2**63+17
        self.assertEqual(bound_causal_offset([
            tuple(base+x for x in [100,145,160,130]),
            tuple(base+x for x in [200,244,260,225])]), (35,44))

    def test_negative_offset_is_not_clamped(self):
        self.assertEqual(bound_causal_offset([(100,65,80,130)]), (-50,-35))

    def test_inconsistent_offsets_do_not_fit_or_drop_samples(self):
        with self.assertRaisesRegex(ValueError,'no fixed clock offset'):
            bound_causal_offset([(100,145,160,130),(200,344,360,225)])

    def test_local_reversal_is_not_reinterpreted_as_wrap(self):
        for sample in [(200,145,160,130),(100,145,140,130)]:
            with self.assertRaisesRegex(ValueError,'Local clock reversed'):
                bound_causal_offset([sample])

    def test_timestamp_types_and_width(self):
        for value in [True,1.5,-1,2**64,None,'1']:
            with self.assertRaises(ValueError):
                bound_causal_offset([(value,145,160,130)])

    def test_uncertainty_and_budget_are_explicit(self):
        for errors in [(1,2,3),[1,2,3,4],(True,0,0,0),(0,-1,0,0),(0,0,1.0,0)]:
            with self.assertRaises(ValueError):
                bound_causal_offset([(100,145,160,130)],endpoint_errors=errors)
        for budget in [0,True,1.0,65537]:
            with self.assertRaises(ValueError):
                bound_causal_offset([(100,145,160,130)],max_samples=budget)

    def test_missing_malformed_and_excess_samples(self):
        for values in [[],None,{},[(1,2,3)],['1234']]:
            with self.assertRaises(ValueError): bound_causal_offset(values)
        with self.assertRaises(ValueError):
            bound_causal_offset([(100,145,160,130)]*2,max_samples=1)


if __name__ == '__main__':
    unittest.main()
