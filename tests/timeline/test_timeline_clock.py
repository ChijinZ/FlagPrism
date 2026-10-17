"""Clock correctness cases, including -O rejection and real calibration bounds.

Source-level CPU tests; independent installed-device qualification is separate.
Run this file only in a server Docker with the staged clock module alongside it.
"""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('clock_under_test', args.module)
    clock = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = clock
    spec.loader.exec_module(clock)
    checks = []

    def check(name, condition):
        require(condition, name)
        checks.append(name)

    def rejected(name, call):
        try:
            call()
        except (ValueError, TypeError):
            checks.append(name)
            return
        raise RuntimeError('Invalid clock input was accepted: ' + name)

    unit = clock.TickScale(1)
    origin = 2**63 + 17
    delta = unit.elapsed_ticks(origin, origin + 13, bits=64,
                               max_elapsed_ns=100)
    check('large-absolute-tick-small-difference', unit.offset(delta) == (13, 0))
    check('rational-floor-and-rounding-bound',
          clock.TickScale(1, 3).offset(2) == (0, 1))
    check('rational-no-rounding-when-exact',
          clock.TickScale(1, 3).offset(6) == (2, 0))
    check('ascend-50mhz-arithmetic-not-hardware-proof',
          clock.TickScale(20).offset(7) == (140, 0))
    check('zero-is-not-stretched', unit.offset(0) == (0, 0))
    check('unique-bounded-wrap', unit.elapsed_ticks(
        250, 5, bits=8, max_elapsed_ns=20, allow_wrap=True) == 11)
    rejected('decreasing-without-wrap-admission', lambda: unit.elapsed_ticks(
        250, 5, bits=8, max_elapsed_ns=20))
    rejected('complete-wrap-even-if-end-is-greater', lambda: unit.elapsed_ticks(
        1, 2, bits=8, max_elapsed_ns=256, allow_wrap=True))
    rejected('complete-wrap-even-if-end-is-equal', lambda: unit.elapsed_ticks(
        1, 1, bits=8, max_elapsed_ns=300, allow_wrap=True))
    rejected('endpoint-errors-can-make-wrap-ambiguous', lambda:
             clock.TickScale(1, read_error_ns=2).elapsed_ticks(
                 1, 2, bits=8, max_elapsed_ns=253, allow_wrap=True))
    rejected('delta-exceeds-independent-window', lambda: unit.elapsed_ticks(
        3, 100, bits=8, max_elapsed_ns=10))
    rejected('raw-outside-encoding', lambda: unit.elapsed_ticks(
        256, 257, bits=8, max_elapsed_ns=10))
    rejected('unknown-frequency', lambda: clock.TickScale(None))
    rejected('float-period', lambda: clock.TickScale(1.0))
    rejected('boolean-period', lambda: clock.TickScale(True))
    rejected('zero-denominator', lambda: clock.TickScale(1, 0))
    rejected('nonpositive-lower-rate', lambda: clock.TickScale(1, 1, 1))
    rejected('float-elapsed-window', lambda: unit.elapsed_ticks(
        1, 2, bits=8, max_elapsed_ns=10.0))
    rejected('boolean-wrap-admission', lambda: unit.elapsed_ticks(
        1, 2, bits=8, max_elapsed_ns=10, allow_wrap=1))
    rejected('unknown-epoch', lambda: clock.TimeBound('device', '', 5))
    left = clock.TimeBound('device', 'capture', 1_000_000, 20)
    near = clock.TimeBound('device', 'capture', 1_000_010, 20)
    far = clock.TimeBound('device', 'capture', 1_000_100, 20)
    check('near-endpoints-remain-unresolved',
          clock.compare_points(left, near) == 'unresolved')
    check('separated-endpoints-proven-before',
          clock.compare_points(left, far) == 'before')
    check('reverse-order', clock.compare_points(far, left) == 'after')
    rejected('same-name-different-epoch', lambda: clock.compare_points(
        left, clock.TimeBound('device', 'other-capture', 1_000_100)))
    rejected('different-domain', lambda: clock.compare_points(
        left, clock.TimeBound('other-device', 'capture', 1_000_100)))

    # These bounds came from six real GCU calibration/held-out pairs. They test
    # arithmetic only; their physical provenance is separately retained.
    lower = Fraction(1745931721, 1786266450)
    upper = Fraction(1825923767, 1786266450)
    center, error = (lower + upper) / 2, (upper - lower) / 2
    calibrated = clock.TickScale(center.numerator, center.denominator,
                                 error.numerator, error.denominator)
    nominal, uncertainty = calibrated.offset(1000)
    check('calibrated-rational-encloses-lower-bound',
          nominal - uncertainty <= 1000 * lower)
    check('calibrated-rational-encloses-upper-bound',
          nominal + uncertainty >= 1000 * upper)
    args.output.write_text(json.dumps({
        'status': 'source_cpu_contract_passed', 'checks': checks,
        'count': len(checks), 'optimized_python': bool(sys.flags.optimize),
        'device_work': False, 'physical_clock_proof': False,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
