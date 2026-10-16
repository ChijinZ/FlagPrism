"""GCU development checks; ordinary kernels, public automatic session API.

All execution and CPU references belong inside the booked server Docker.
This is development data, separate from independent held-out qualification.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import torch
import torch_gcu  # noqa: F401
import triton
import triton.language as tl
import flagtree.profiler as profiler

# Also support direct execution of this hardware driver.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_census_assertions import read_view
from source_census_assertions import validate_bundle as validate_census_bundle


@triton.jit(do_not_specialize=['steps'])
def relax(X, Y, N, steps, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    value = tl.load(X + offsets, offsets < N, other=0)
    for _ in range(steps):
        value = value * 0.25 + 0.125
    tl.store(Y + offsets, value, offsets < N)


@triton.jit
def squared_shift(X, Y, N, BLOCK: tl.constexpr):
    offsets = tl.arange(0, BLOCK)
    value = tl.load(X + offsets, offsets < N, other=0)
    shifted = value + 0.5
    total = tl.sum(tl.where(offsets < N, shifted * shifted, 0), 0)
    tl.store(Y, total)


def check(bundle):
    raw, cells, summaries, fine = validate_census_bundle(bundle, 'enflame')
    assert len(raw['captures']) == 1
    plan = read_view(bundle, 'observation_plan.json', raw)
    assert plan['plans'] and all(row['plan']['max_sites'] == 8
                                 for row in plan['plans'])
    plans = {row['binary_id']: row['plan'] for row in plan['plans']}
    for row in raw['observations']:
        selected = set(plans[row['binary_id']]['selected_sites'])
        assert row['site'] in selected
        inventory = plans[row['binary_id']]['inventory']
        assert {item['opId']
                for item in inventory if item['selected']} == selected
    records = fine['records']
    assert len({row['site'] for row in records}) >= 2, records
    timing = json.loads((bundle / 'ai/export_timing.json').read_text())
    assert timing['complete_finalize_and_export'] and timing[
        'export_wall_s'] < 60
    size = sum(file.stat().st_size for file in bundle.rglob('*')
               if file.is_file())
    assert size <= 64 * 1024 * 1024, size
    # Counts aggregate real source visits; rows are not expanded into events.
    counts = Counter()
    for row in records:
        counts[row['site']] += row['count']
    return {
        'records': len(records),
        'sites': sorted({row['site']
                         for row in records}),
        'binary_ids': sorted({row['binary_id']
                              for row in records}),
        'bytes': size,
        'census': summaries,
        'site_counts': dict(counts),
        'observations': records
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--size', type=int, default=137)
    parser.add_argument('--block', type=int, default=128)
    parser.add_argument('--num-warps', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    x_cpu = torch.linspace(-0.75, 0.75, args.size)
    x = x_cpu.to('gcu')
    input_hash = hashlib.sha256(x.cpu().numpy().tobytes()).hexdigest()
    results = []
    binaries = set()
    for steps in (2, 5):
        storage = torch.full((x.numel() + 2, ), 123.0, device='gcu')
        y = storage[1:-1]
        expected = x_cpu.clone()
        for _ in range(steps):
            expected = expected * 0.25 + 0.125
        bundle = args.output / f'loop-{steps}'
        session = None if args.baseline_only else profiler.start(str(bundle),
                                                                 detail='auto')
        started = time.monotonic()
        kernel = relax[(triton.cdiv(x.numel(),
                                    args.block), )](x,
                                                    y,
                                                    x.numel(),
                                                    steps,
                                                    args.block,
                                                    num_warps=args.num_warps)
        torch.gcu.synchronize()
        compile_launch_s = time.monotonic() - started
        binaries.add(kernel.hash)
        export_start = time.monotonic()
        if session is not None:
            profiler.finalize(session)
        export_s = time.monotonic() - export_start
        torch.testing.assert_close(y.cpu(), expected, rtol=0, atol=0)
        assert storage[0].cpu().item() == 123 and storage[-1].cpu().item(
        ) == 123
        result = {
            'steps': steps,
            'binary': kernel.hash,
            'compile_launch_s': compile_launch_s,
            'export_s': export_s
        }
        if not args.baseline_only:
            result.update(check(bundle))
            assert export_s < 60
        results.append(result)
    assert len(binaries) == 1, binaries
    if not args.baseline_only:
        repeated = []
        for result in results:
            counts = result['site_counts']
            repeated.append({
                site
                for site, count in counts.items() if count == result['steps']
            })
        assert repeated[0] & repeated[1], repeated
    y = torch.empty((), device='gcu')
    session = None if args.baseline_only else profiler.start(
        str(args.output / 'reduction'), detail='auto')
    started = time.monotonic()
    kernel = squared_shift[(1, )](x,
                                  y,
                                  x.numel(),
                                  triton.next_power_of_2(x.numel()),
                                  num_warps=args.num_warps)
    torch.gcu.synchronize()
    compile_launch_s = time.monotonic() - started
    export_start = time.monotonic()
    if session is not None:
        profiler.finalize(session)
    export_s = time.monotonic() - export_start
    torch.testing.assert_close(y.cpu(), ((x_cpu + 0.5)**2).sum())
    assert input_hash == hashlib.sha256(x.cpu().numpy().tobytes()).hexdigest()
    reduction = {
        'structure': 'reduction',
        'binary': kernel.hash,
        'compile_launch_s': compile_launch_s,
        'export_s': export_s
    }
    if not args.baseline_only:
        reduction.update(check(args.output / 'reduction'))
        assert any(row['operation'] == 'tt.reduce'
                   for row in reduction['observations'])
    results.append(reduction)
    (args.output /
     'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2), flush=True)


if __name__ == '__main__':
    main()
