"""Discover the installed SDK timer scale with real unannotated math.

Uses the existing advanced automatic interval path, not the future default
timeline API. A successful probe alone does not satisfy P01 or async acceptance.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import time


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'started.json').write_text(json.dumps({
        'pid': os.getpid(), 'pgid': os.getpgid(0),
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'clock discovery, not full timeline qualification',
    }, indent=2))

    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler

    @triton.jit(do_not_specialize=['steps'])
    def recurrence(X, Y, State, N, steps, BLOCK: tl.constexpr):
        offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
        value = tl.load(X + offsets, offsets < N, 0)
        for _ in range(steps):
            value = value * 0.75 + 0.125
        tl.store(Y + offsets, value, offsets < N)
        if tl.program_id(0) == 0:
            old = tl.load(State)
            tl.store(State, old + 1)

    torch.gcu.set_device(0)
    torch.manual_seed(1729)
    x_cpu = torch.rand(129, dtype=torch.float32)
    x = x_cpu.to('gcu')
    y = torch.empty_like(x)
    state = torch.zeros((), device='gcu', dtype=torch.int32)

    # Register an ordinary baseline before asking the profiler for any records.
    ordinary = recurrence[(2,)](x, y, state, 129, 7, 128, num_warps=4)
    torch.gcu.synchronize()
    reference = x_cpu.clone()
    for _ in range(7):
        reference = reference * 0.75 + 0.125
    require(torch.allclose(y.cpu(), reference, rtol=2e-6, atol=2e-6),
            'Ordinary recurrence baseline is invalid')
    require(state.cpu().item() == 1, 'Ordinary baseline call count changed')
    baseline_hashes = {}
    for name, value in ordinary.asm.items():
        if isinstance(value, str):
            raw = value.encode()
        elif isinstance(value, bytes):
            raw = value
        else:
            continue
        path = args.output / ('ordinary.' + name)
        path.write_bytes(raw)
        baseline_hashes[path.name] = hashlib.sha256(raw).hexdigest()

    rows = []
    for index in range(6):
        if index:
            time.sleep(0.25)
        state.zero_()
        request = profiler.ObservationRequest(
            semantics=('source_control_interval',), programs=(0,),
            automatic=True, max_sites=2, max_events_per_instance=32)
        bundle = args.output / f'capture-{index}'
        sid = profiler.start(str(bundle), backend='enflame',
                             hook='instrumentation', observation_request=request)
        try:
            torch.gcu.synchronize()
            before = time.monotonic_ns()
            recurrence[(2,)](x, y, state, 129, 7, 128, num_warps=4)
            torch.gcu.synchronize()
            after = time.monotonic_ns()
        finally:
            profiler.finalize(sid)
        require(torch.allclose(y.cpu(), reference, rtol=2e-6, atol=2e-6),
                'Instrumented recurrence math failed')
        require(torch.equal(x.cpu(), x_cpu), 'Profiler changed an input')
        require(state.cpu().item() == 1, 'Profiler repeated or missed the kernel')
        document = json.loads((bundle / 'ai/observations.json').read_text())
        events = document.get('observations', [])
        timed = [event for event in events
                 if event.get('start_tick') is not None
                 and event.get('end_tick') is not None]
        require(timed, 'The legacy producer supplied no actual timer intervals')
        require(all(event['end_tick'] >= event['start_tick'] for event in timed),
                'Decreasing clock: do not guess a wrap')
        start = min(event['start_tick'] for event in timed)
        row = {'capture': index, 'purpose': 'discovery' if index == 0 else
               'calibration' if index < 4 else 'held-out-validation',
               'host_before_ns': before, 'host_after_ns': after,
               'raw_start_tick': start, 'timed_events': len(timed),
               'clock_declarations': [event.get('clock') for event in timed],
               'observations_sha256': hashlib.sha256(
                   (bundle / 'ai/observations.json').read_bytes()).hexdigest()}
        rows.append(row)
        (args.output / 'clock-calls.json').write_text(json.dumps(rows, indent=2))

    # Calibration produces bounds rather than guessing a convenient integer.
    # Leave the scale unverified until independent held-out evidence and actual
    # getter/target facts have been reviewed by the backend implementation.
    bounds = []
    for a in rows[1:4]:
        for b in rows[4:]:
            delta = b['raw_start_tick'] - a['raw_start_tick']
            lower = b['host_before_ns'] - a['host_after_ns']
            upper = b['host_after_ns'] - a['host_before_ns']
            require(delta > 0 and lower > 0, 'Clock anchors are not separable')
            lo, hi = Fraction(lower, delta), Fraction(upper, delta)
            bounds.append({'tick_delta': delta,
                           'period_lower_ns': [lo.numerator, lo.denominator],
                           'period_upper_ns': [hi.numerator, hi.denominator]})
    (args.output / 'primitive-result.json').write_text(json.dumps({
        'status': 'clock_bounds_collected_not_timeline_acceptance',
        'ordinary_calls': 1, 'profiled_calls': 6,
        'baseline_artifact_sha256': baseline_hashes,
        'heldout_period_bounds': bounds,
        'limits': ['not the new default timeline interface',
                   'no certified fixed frequency or shared epoch yet',
                   'no dynamic async logger or Perfetto acceptance yet'],
    }, indent=2))


if __name__ == '__main__':
    main()
