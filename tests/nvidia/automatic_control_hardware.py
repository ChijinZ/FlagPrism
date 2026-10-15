"""Real default control observations, including an inactive sampled program.

Run only on an assigned NVIDIA GPU using the installed matching compiler.
Every profiled application call executes once; baseline calls use fresh output.
"""
import json
from pathlib import Path
import sys
import time

import torch
import triton
import triton.language as tl
import flagtree.profiler as profiler
from automatic_hardware import validate_bundle


@triton.jit
def gated_affine(X, Y, Calls, N: tl.constexpr, B: tl.constexpr):
    program = tl.program_id(0)
    if program > 0:
        i = (program - 1) * B + tl.arange(0, B)
        x = tl.load(X + i, i < N, other=0)
        y = x * 0.75 + 0.125
        tl.store(Y + i, y, i < N)
        tl.atomic_add(Calls + program, 1)


@triton.jit
def odd_program_energy(X, Y, Calls, N: tl.constexpr, B: tl.constexpr):
    program = tl.program_id(0)
    if program % 2 != 0:
        i = (program // 2) * B + tl.arange(0, B)
        x = tl.load(X + i, i < N, other=0)
        energy = tl.sum(x * x, 0)
        tl.store(Y + program // 2, energy)
        tl.atomic_add(Calls + program, 1)


@triton.jit(do_not_specialize=['loops'])
def surrounded_loop(X, Y, Calls, N: tl.constexpr, loops, B: tl.constexpr):
    i = tl.arange(0, B)
    x = tl.load(X + i, i < N, other=0)
    v = x + 0.01
    v = v * x
    v = v + 0.02
    v = v * x
    v = v + 0.03
    v = v * x
    v = v + 0.04
    v = v * x
    for step in range(loops):
        v = v * 0.5
    v = v + 0.05
    v = v * x
    v = v + 0.06
    v = v * x
    v = v + 0.07
    v = v * x
    v = v + 0.08
    v = v * x
    tl.store(Y + i, v, i < N)
    tl.atomic_add(Calls, 1)


def loop_expected(x, loops):
    v = x
    for offset in (0.01, 0.02, 0.03, 0.04):
        v = (v + offset) * x
    for _ in range(loops):
        v = v * 0.5
    for offset in (0.05, 0.06, 0.07, 0.08):
        v = (v + offset) * x
    return v


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    summaries = []
    n, block, sentinel = 137, 128, -91.0
    x = torch.linspace(-0.9, 0.9, n, device='cuda')
    original = x.clone()
    for kernel, grid, size, expected, counts in ((gated_affine, 3, n,
                                                  x.cpu() * 0.75 + 0.125,
                                                  [0, 1, 1]),
                                                 (odd_program_energy, 4, 2,
                                                  torch.stack([
                                                      (x[:128].cpu()**2).sum(),
                                                      (x[128:].cpu()**2).sum()
                                                  ]), [0, 1, 0, 1])):

        def launch():
            y = torch.full((size + 7, ), sentinel, device='cuda')
            calls = torch.zeros(grid, dtype=torch.int32, device='cuda')
            compiled = kernel[(grid, )](x, y, calls, n, block, num_warps=4)
            return y, calls, compiled

        started = time.monotonic()
        baseline, baseline_calls, _ = launch()
        baseline_seconds = time.monotonic() - started
        torch.testing.assert_close(baseline[:size].cpu(), expected)
        assert baseline_calls.cpu().tolist() == counts
        base = output / kernel.__name__
        session = profiler.start(str(base), detail='auto')
        started = time.monotonic()
        y, calls, compiled = launch()
        compile_launch_seconds = time.monotonic() - started
        started = time.monotonic()
        profiler.finalize(session)
        export_seconds = time.monotonic() - started
        torch.testing.assert_close(y[:size].cpu(), expected)
        assert torch.equal(y[size:].cpu(), torch.full((7, ), sentinel))
        assert calls.cpu().tolist() == counts  # no hidden application replay
        assert torch.equal(x, original)
        records, capture = validate_bundle(base)
        fine = json.loads(
            (base / 'ai/fine_grained.json').read_text())['records']
        # All measured work belongs to selected program zero. Other programs'
        # tensor computations run normally but are never claimed as observed.
        assert {row['program'] for row in fine} == {0}, fine
        assert len({row['invocation_id'] for row in fine}) == 1
        operations = {row['operation'] for row in fine}
        assert 'tt.get_program_id' in operations
        assert any(op.startswith('arith.cmp') for op in operations)
        assert not {'tt.load', 'tt.store', 'tt.atomic_rmw'} & operations
        assert len({(loc.get('file'), loc.get('line'))
                    for row in fine
                    for loc in row['source_locations']}) >= 2
        plan = capture['automatic_plan']
        assert any(r['operation'] == 'scf.if' for r in plan['control_regions'])
        assert compile_launch_seconds <= min(300, max(120,
                                                      3 * baseline_seconds))
        assert export_seconds <= 60
        summaries.append(
            dict(kernel=kernel.__name__,
                 binary=compiled.hash,
                 call_counts=counts,
                 measured_operations=sorted(operations),
                 baseline_seconds=baseline_seconds,
                 compile_launch_seconds=compile_launch_seconds,
                 export_seconds=export_seconds))
    for loops in (1, 3, 7):
        size = n

        def launch_loop():
            y = torch.full((size + 7, ), sentinel, device='cuda')
            calls = torch.zeros(1, dtype=torch.int32, device='cuda')
            compiled = surrounded_loop[(1, )](x,
                                              y,
                                              calls,
                                              n,
                                              loops,
                                              256,
                                              num_warps=4)
            return y, calls, compiled

        started = time.monotonic()
        baseline, _, _ = launch_loop()
        baseline_seconds = time.monotonic() - started
        expected = loop_expected(x.cpu(), loops)
        torch.testing.assert_close(baseline[:size].cpu(), expected)
        base = output / f'surrounded-loop-{loops}'
        session = profiler.start(str(base), detail='auto')
        started = time.monotonic()
        y, calls, compiled = launch_loop()
        compile_launch_seconds = time.monotonic() - started
        started = time.monotonic()
        profiler.finalize(session)
        export_seconds = time.monotonic() - started
        assert compile_launch_seconds <= min(300, max(120,
                                                      3 * baseline_seconds))
        assert export_seconds <= 60
        torch.testing.assert_close(y[:size].cpu(), expected)
        assert torch.equal(y[size:].cpu(), torch.full((7, ), sentinel))
        assert calls.cpu().tolist() == [1]
        assert torch.equal(x, original)
        records, capture = validate_bundle(base)
        plan = capture['automatic_plan']
        loop_regions = [r for r in plan['control_regions'] if r['repeated']]
        assert loop_regions and all(
            r['coverage_status'] == 'direct_representative'
            for r in loop_regions)
        selected = {row['candidate_ordinal']: row for row in plan['inventory']}
        scopes = [
            selected[i]['scope_id'] for r in loop_regions
            for i in r['selected_candidates']
        ]
        visits = {
            site: sum(r['site'] == site for r in records)
            for site in scopes
        }
        assert visits and all(count == loops
                              for count in visits.values()), visits
        summaries.append(
            dict(kernel='surrounded_loop',
                 loops=loops,
                 binary=compiled.hash,
                 loop_scope_visits=visits,
                 baseline_seconds=baseline_seconds,
                 compile_launch_seconds=compile_launch_seconds,
                 export_seconds=export_seconds))
    (output / 'summary.json').write_text(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
