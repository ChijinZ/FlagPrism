"""GCU development checks; ordinary kernels, public automatic session API.

All execution and CPU references belong inside the booked server Docker.
This is development data, separate from independent held-out qualification.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import time

import torch
import torch_gcu  # noqa: F401
import triton
import triton.language as tl
import flagtree.profiler as profiler


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
    fine = json.loads((bundle / 'ai/fine_grained.json').read_text())
    records = fine['records']
    assert len({row['site'] for row in records}) >= 2, records
    assert all(row['association_status'] == 'verified' and row['invocation_id']
               and row['binary_id'] and row['source_locations']
               and row['operation'] and row['program'] == 0
               for row in records), records
    assert all(row['clock']['domain'] == 'enflame.sdk.global_timer'
               and row['duration_ns'] is None for row in records), records
    plan = json.loads((bundle / 'ai/observation_plan.json').read_text())
    assert plan['plans'], plan
    assert all(row['plan']['max_sites'] == 8 for row in plan['plans'])
    assert (bundle / 'report/fine_grained.html').is_file()
    timing = json.loads((bundle / 'ai/export_timing.json').read_text())
    assert timing['complete_finalize_and_export'] and timing[
        'export_wall_s'] < 60, timing
    raw = json.loads((bundle / 'ai/observations.json').read_text())
    assert len(raw['captures']) == 1
    capture = raw['captures'][0]
    assert capture['capture_status'] == 'decoded' and capture[
        'decode_error'] is None
    payload = base64.b64decode(capture['raw_base64'])
    assert hashlib.sha256(payload).hexdigest() == capture['raw_sha256']
    header = struct.unpack_from('<8I', payload)
    committed, capacity, dropped, flags, stride, _, attempted, reserved = header
    assert stride == 64 and capacity == 256 and dropped == flags == reserved == 0, header
    assert attempted == committed == len(records), (header, len(records))
    assert not capture['counter_saturated']
    for index, record in enumerate(raw['observations']):
        # The final 24 bytes are actor/sequence, pre-sampling ordinal and
        # publication tag.  Inspect actual device bytes independently of JSON.
        actor, sequence, ordinal, commit = struct.unpack_from(
            '<IIQQ', payload, 32 + index * 64 + 40)
        assert (actor, sequence, ordinal, commit) == (0, index, index,
                                                      0x465044594e563031)
        assert record['sequence'] == sequence and record[
            'attempted_ordinal'] == ordinal
    selected = set(plan['plans'][0]['plan']['selected_sites'])
    assert {row['site'] for row in records} <= selected
    inventory = plan['plans'][0]['plan']['inventory']
    assert {row['opId'] for row in inventory if row['selected']} == selected
    size = sum(file.stat().st_size for file in bundle.rglob('*')
               if file.is_file())
    assert size <= 64 * 1024 * 1024, size
    return {
        'records': len(records),
        'sites': sorted({row['site']
                         for row in records}),
        'binary_ids': sorted({row['binary_id']
                              for row in records}),
        'bytes': size,
        'attempted': attempted,
        'committed': committed,
        'dropped': dropped,
        'sampled_out': 0,
        'site_counts': dict(Counter(row['site'] for row in records)),
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
