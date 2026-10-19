"""Frozen empirical counter scale from independent, enclosing host anchors.

This arithmetic is conditional on one affine counter over the supplied window.
It does not establish a getter identity, hardware read precision, shared epoch,
or a future frequency. A backend must retain those separate physical facts.
"""
from fractions import Fraction

from .timeline_events import _integer


def _anchors(rows, *, bits):
    _integer(bits, 'counter width', 1, 64)
    if type(rows) not in (list, tuple) or not 2 <= len(rows) <= 64:
        raise ValueError('Expected two to 64 actual clock anchors')
    previous = None
    for row in rows:
        if type(row) is not dict:
            raise ValueError('An anchor must be a mapping')
        for field in ('before_ns', 'after_ns', 'raw_tick'):
            _integer(row.get(field), field)
        if not row['before_ns'] < row['after_ns'] or row[
                'raw_tick'] >= 1 << bits:
            raise ValueError('Invalid host window or counter width')
        if previous is not None and (previous['after_ns'] >= row['before_ns']
                                     or previous['raw_tick']
                                     >= row['raw_tick']):
            raise ValueError('Unordered anchors or counter reset/wrap')
        previous = row
    return rows


def empirical_period_bounds(rows, *, bits):
    """Exact feasible ns/tick interval for an affine counter, no midpoint fit."""
    rows = _anchors(rows, bits=bits)
    lower, upper = None, None
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            ticks = right['raw_tick'] - left['raw_tick']
            lo = Fraction(right['before_ns'] - left['after_ns'], ticks)
            hi = Fraction(right['after_ns'] - left['before_ns'], ticks)
            lower = lo if lower is None else max(lower, lo)
            upper = hi if upper is None else min(upper, hi)
    if not 0 < lower <= upper:
        raise ValueError('No consistent positive empirical affine scale')
    return lower, upper


def frozen_window_scale(training, heldout, *, bits, admission_ns,
                        completion_ns, raw_min, raw_max):
    """Validate later anchors/capture against a frozen training scale interval.

    No held-out sample or user-kernel duration refits the exported scale. Both
    host and raw capture extents must lie strictly inside the enclosing anchors.
    All cross-window pairs participate in validation, so a counter reset or an
    incompatible epoch cannot hide behind individually plausible slopes.
    """
    _integer(admission_ns, 'capture admission ns')
    _integer(completion_ns, 'capture completion ns')
    _integer(raw_min, 'minimum capture tick')
    _integer(raw_max, 'maximum capture tick')
    training = _anchors(training, bits=bits)
    heldout = _anchors(heldout, bits=bits)
    lo, hi = empirical_period_bounds(training, bits=bits)
    check_lo, check_hi = empirical_period_bounds(list(training) +
                                                 list(heldout),
                                                 bits=bits)
    if max(lo, check_lo) > min(hi, check_hi):
        raise ValueError('Frozen scale failed independent enclosing anchors')
    if not (training[-1]['after_ns'] <= admission_ns < completion_ns <=
            heldout[0]['before_ns'] and training[-1]['raw_tick'] < raw_min <=
            raw_max < heldout[0]['raw_tick']):
        raise ValueError(
            'Capture is outside the validated host/counter window')
    period = (lo + hi) / 2
    uncertainty = (hi - lo) / 2
    # A conservative scale bound must exclude a complete counter wrap.
    if heldout[-1]['after_ns'] - training[0]['before_ns'] >= (1 << bits) * lo:
        raise ValueError('Calibration window cannot exclude a complete wrap')

    def encode(value):
        return [value.numerator, value.denominator]

    return dict(
        schema_version=1,
        status='empirical_affine_scale_for_enclosed_window',
        timer_bits=bits,
        training_period_ns=[encode(lo), encode(hi)],
        nominal_period_ns=encode(period),
        period_uncertainty_ns=encode(uncertainty),
        frozen_training=True,
        refitted_from_capture=False,
        validation_bounds_ns=[encode(check_lo),
                              encode(check_hi)],
        valid_host_window_ns=[
            training[-1]['after_ns'], heldout[0]['before_ns']
        ],
        valid_counter_window=[
            training[-1]['raw_tick'], heldout[0]['raw_tick']
        ],
        read_precision_verified=False,
        shared_epoch_verified=False,
        assumption=
        'One affine counter over this empirically validated window; no future frequency guarantee'
    )
