"""Independent-window arithmetic and counter reset rejection."""
import copy
import unittest

from flagtree.profiler.timeline_calibration import empirical_period_bounds, frozen_window_scale


def anchor(tick):
    return dict(raw_tick=tick,
                before_ns=1000 + 2 * tick - 1,
                after_ns=1000 + 2 * tick + 1)


class CalibrationTests(unittest.TestCase):

    def setUp(self):
        self.training = [anchor(tick) for tick in (10, 20, 30, 40)]
        self.heldout = [anchor(tick) for tick in (100, 110, 120, 130)]
        self.options = dict(bits=16,
                            admission_ns=1090,
                            completion_ns=1180,
                            raw_min=50,
                            raw_max=80)

    def derive(self, **kwargs):
        return frozen_window_scale(self.training, self.heldout,
                                   **(self.options | kwargs))

    def test_frozen_period_not_narrowed_by_later_samples(self):
        view = self.derive()
        self.assertEqual(view['nominal_period_ns'], [2, 1])
        self.assertEqual(view['period_uncertainty_ns'], [1, 15])
        self.assertFalse(view['read_precision_verified'])
        self.assertFalse(view['shared_epoch_verified'])
        self.assertFalse(view['refitted_from_capture'])
        # The additional independent samples narrow feasibility, not the
        # uncertainty originally frozen from training.
        self.assertNotEqual(view['training_period_ns'],
                            view['validation_bounds_ns'])

    def test_cross_window_reset_cannot_hide_behind_matching_local_rate(self):
        self.heldout = [
            dict(row, raw_tick=row['raw_tick'] + 2000) for row in self.heldout
        ]
        with self.assertRaises(ValueError):
            self.derive()

    def test_non_affine_rate_rejected(self):
        self.heldout[-1]['raw_tick'] += 10
        with self.assertRaises(ValueError):
            self.derive()

    def test_capture_must_be_enclosed_in_both_coordinates(self):
        for kwargs in [
                dict(raw_min=39),
                dict(raw_max=100),
                dict(admission_ns=1080),
                dict(completion_ns=1201),
                dict(raw_min=81, raw_max=80),
                dict(raw_min=True)
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.derive(**kwargs)

    def test_bad_anchor_extents_and_order(self):
        for field, value in [('raw_tick', True), ('after_ns', 0),
                             ('before_ns', -1), ('raw_tick', 1 << 16)]:
            rows = copy.deepcopy(self.training)
            rows[0][field] = value
            with self.subTest(field=field,
                              value=value), self.assertRaises(ValueError):
                empirical_period_bounds(rows, bits=16)
        for rows in [[], self.training[::-1], self.training * 20]:
            with self.assertRaises(ValueError):
                empirical_period_bounds(rows, bits=16)


if __name__ == '__main__':
    unittest.main()
