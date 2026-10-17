"""Exact, uncertainty-bounded clock arithmetic for timeline producers.

These functions validate arithmetic and identity, not physical clock evidence.
A backend must separately establish and retain the target/getter, scale,
epoch/scope, reset behavior and independent elapsed-window evidence. No clock
rate is inferred from event counts, names, or whole-kernel duration.
"""
from dataclasses import dataclass
from fractions import Fraction


def _integer(value, field, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{field} must be an integer >= {minimum}')
    return value


def _ceil(value):
    return -(-value.numerator // value.denominator)


@dataclass(frozen=True)
class TickScale:
    period_numerator: int
    period_denominator: int = 1
    uncertainty_numerator: int = 0
    uncertainty_denominator: int = 1
    read_error_ns: int = 0

    def __post_init__(self):
        for field in ('period_numerator', 'period_denominator',
                      'uncertainty_denominator'):
            _integer(getattr(self, field), field, 1)
        _integer(self.uncertainty_numerator, 'uncertainty_numerator')
        _integer(self.read_error_ns, 'read_error_ns')
        if self.uncertainty >= self.period:
            raise ValueError('Clock uncertainty must leave a positive rate')

    @property
    def period(self):
        return Fraction(self.period_numerator, self.period_denominator)

    @property
    def uncertainty(self):
        return Fraction(self.uncertainty_numerator,
                        self.uncertainty_denominator)

    def offset(self, ticks):
        """Convert an already-unwrapped integer difference, never absolute float.

        Floor is explicit. The error includes fractional rounding and the
        declared endpoint read bound; zero-width events are never stretched.
        """
        _integer(ticks, 'unwrapped tick difference')
        exact = ticks * self.period
        nominal = exact.numerator // exact.denominator
        error = ticks * self.uncertainty + self.read_error_ns
        if exact.denominator != 1:
            error += exact - nominal
        return nominal, _ceil(error)

    def elapsed_ticks(self, start, end, *, bits, max_elapsed_ns,
                      allow_wrap=False):
        """Require an independent window even when end >= start.

        This handles at most one uniquely determined wrap. Reset/epoch evidence
        is the producer's responsibility; a caller boolean is not that proof.
        """
        _integer(bits, 'timer bits', 1)
        if bits > 64:
            raise ValueError('Timer width exceeds the supported raw uint64')
        _integer(start, 'start tick')
        _integer(end, 'end tick')
        _integer(max_elapsed_ns, 'independent elapsed window')
        if type(allow_wrap) is not bool:
            raise ValueError('allow_wrap must be a boolean')
        modulus = 1 << bits
        if start >= modulus or end >= modulus:
            raise ValueError('Raw tick exceeds the declared encoding width')
        minimum_period = self.period - self.uncertainty
        window_with_error = max_elapsed_ns + 2 * self.read_error_ns
        if window_with_error >= modulus * minimum_period:
            raise ValueError('Elapsed window cannot exclude a complete wrap')
        if end < start and not allow_wrap:
            raise ValueError('Decreasing ticks require admitted wrap evidence')
        delta = (end - start) % modulus
        if delta * minimum_period > window_with_error:
            raise ValueError('Tick difference contradicts the elapsed window')
        return delta


@dataclass(frozen=True)
class TimeBound:
    domain_id: str
    epoch_id: str
    ns: int
    error_ns: int = 0

    def __post_init__(self):
        for value in (self.domain_id, self.epoch_id):
            if not isinstance(value, str) or not value:
                raise ValueError('Time bound requires explicit domain and epoch')
        _integer(self.ns, 'relative nanoseconds')
        _integer(self.error_ns, 'endpoint uncertainty')


def compare_points(left, right):
    """Compare only matching coordinates; uncertainty is not a sorting hint."""
    if not isinstance(left, TimeBound) or not isinstance(right, TimeBound):
        raise TypeError('Expected explicit bounded time points')
    if (left.domain_id, left.epoch_id) != (right.domain_id, right.epoch_id):
        raise ValueError('Independent clock domains/epochs are not comparable')
    if left.ns + left.error_ns < right.ns - right.error_ns:
        return 'before'
    if left.ns - left.error_ns > right.ns + right.error_ns:
        return 'after'
    return 'unresolved'
