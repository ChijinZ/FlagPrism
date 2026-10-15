"""Independent C1 developer loops: real branch recurrence and loop memory load.

No held-out mathematical source is used here. Kernels are ordinary Triton; the
outer runner uses only the public automatic session API. Run in booked Docker.
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
def alternating_recurrence(X, A, B, Y, State, N, steps, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    x = tl.load(X + offsets, offsets < N, 0)
    a = tl.load(A + offsets, offsets < N, 0)
    b = tl.load(B + offsets, offsets < N, 0)
    value = x * 0.5 + a * 0.25 - b * 0.125
    index = 0
    while index < steps:
        if index % 2 == 0:
            value = value * 0.5 + 0.25
        else:
            value = value * 0.25 - 0.125
        index += 1
    result = value + a * 0.5 - b * 0.25 + x * 0.125
    tl.store(Y + offsets, result, offsets < N)
    if tl.program_id(0) == 0:
        calls = tl.load(State)
        tl.store(State, calls + 1)


@triton.jit(do_not_specialize=['steps'])
def weighted_memory_loop(X, A, B, Y, State, N, steps, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    x = tl.load(X + offsets, offsets < N, 0)
    b = tl.load(B + offsets, offsets < N, 0)
    prefix = x * 0.5 + b * 0.25 + x * 0.125 - b * 0.0625
    accumulated = tl.full((BLOCK, ), 0, tl.float32)
    index = 0
    while index < steps:
        sample = tl.load(A + offsets, offsets < N, 0)
        weight = (index + 1).to(tl.float32) * 0.125
        accumulated = accumulated + sample * weight
        index += 1
    result = prefix + accumulated + b * 0.5 - x * 0.25
    tl.store(Y + offsets, result, offsets < N)
    if tl.program_id(0) == 0:
        calls = tl.load(State)
        tl.store(State, calls + 1)


def inspect_bundle(bundle):
    fine = json.loads((bundle / 'ai/fine_grained.json').read_text())
    raw = json.loads((bundle / 'ai/observations.json').read_text())
    plans = json.loads(
        (bundle / 'ai/observation_plan.json').read_text())['plans']
    assert len(plans) == 1 and len(raw['captures']) == 2
    plan = plans[0]['plan']
    assert plan['max_sites'] == 8 and plan['policy_version'] == 2
    assert len(plan['selected_sites']) <= 8 and len(plan['inventory']) > 8
    loop_regions = [
        row for row in plan['control_regions']
        if row['operation'] == 'scf.while'
    ]
    assert {row['regionIndex'] for row in loop_regions} == {0, 1}, loop_regions
    assert all(row['coverage_status'] == 'direct_representative'
               for row in loop_regions)
    records = fine['records']
    assert all(
        row['source_locations'] and row['operation']
        and row['native_event_ids'] and row['association_status'] == 'verified'
        and row['program'] == 0 and row['duration_ns'] is None
        and row['clock']['domain'] == 'enflame.sdk.global_timer'
        for row in records)
    visits = []
    for steps, capture in zip((2, 5), raw['captures']):
        assert capture['capture_status'] == 'decoded' and capture[
            'decode_error'] is None
        assert not capture['counter_saturated']
        payload = base64.b64decode(capture['raw_base64'])
        assert hashlib.sha256(payload).hexdigest() == capture['raw_sha256']
        written, cap, dropped, flags, stride, _, attempted, reserved = struct.unpack_from(
            '<8I', payload)
        assert written == attempted and cap == 256 and stride == 64 and dropped == flags == reserved == 0
        for index in range(written):
            assert struct.unpack_from(
                '<IIQQ', payload,
                32 + index * 64 + 40) == (0, index, index, 0x465044594e563031)
        selected = [
            row for row in records
            if row['capture_id'] == capture['capture_id']
        ]
        assert len(selected) == written
        counts = Counter(row['site'] for row in selected)
        by_region = []
        for region in loop_regions:
            direct = set(region['direct_sites']) & set(
                region['selected_sites'])
            assert direct
            expected = steps + 1 if region['regionIndex'] == 0 else steps
            assert all(counts[site] == expected
                       for site in direct), (steps, region, counts)
            by_region.append({
                'region': region['regionIndex'],
                'sites': sorted(direct),
                'visits': expected
            })
        visits.append({
            'steps': steps,
            'written': written,
            'attempted': attempted,
            'dropped': dropped,
            'site_counts': dict(counts),
            'regions': by_region
        })
    report = json.loads((bundle / 'report/report.json').read_text())
    for binary in report['binaries']:
        mode = binary['compiler_metadata']['instrumentation_mode']
        config = json.loads(mode.split('|config=', 1)[1])
        assert config['debug_automatic_plan_version'] == 2
        assert config['debug_control_flow_metadata_version'] == 1
    timing = json.loads((bundle / 'ai/export_timing.json').read_text())
    assert timing['complete_finalize_and_export'] and timing[
        'export_wall_s'] < 60
    assert (bundle / 'report/fine_grained.html').is_file()
    size = sum(path.stat().st_size for path in bundle.rglob('*')
               if path.is_file())
    assert size <= 64 * 1024 * 1024
    return {
        'visits': visits,
        'bytes': size,
        'export_wall_s': timing['export_wall_s'],
        'selected_sites': plan['selected_sites'],
        'control_regions': plan['control_regions']
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--size', type=int, default=97)
    parser.add_argument('--num-warps', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cpu = (torch.arange(args.size).remainder(32).float() - 16) / 32
    ac, bc = cpu * 0.5, cpu * 0.25
    x, a, b = [value.to('gcu') for value in (cpu, ac, bc)]
    inputs = [value.cpu().numpy().tobytes() for value in (x, a, b)]
    results = []
    for name, kernel in [('alternating', alternating_recurrence),
                         ('memory', weighted_memory_loop)]:
        state_storage = torch.full((3, ), 777, dtype=torch.int32, device='gcu')
        state = state_storage[1:2]
        state.zero_()
        bundle = args.output / name
        session = None if args.baseline_only else profiler.start(str(bundle),
                                                                 detail='auto')
        hashes, elapsed = [], []
        for steps in (2, 5):
            storage = torch.full((args.size + 2, ), 123.0, device='gcu')
            y = storage[1:-1]
            if name == 'alternating':
                expected = cpu * 0.5 + ac * 0.25 - bc * 0.125
                for index in range(steps):
                    expected = expected * 0.5 + 0.25 if index % 2 == 0 else expected * 0.25 - 0.125
                expected = expected + ac * 0.5 - bc * 0.25 + cpu * 0.125
            else:
                expected = cpu * 0.5 + bc * 0.25 + cpu * 0.125 - bc * 0.0625
                accumulated = torch.zeros_like(cpu)
                for index in range(steps):
                    accumulated = accumulated + ac * ((index + 1) * 0.125)
                expected = expected + accumulated + bc * 0.5 - cpu * 0.25
            started = time.monotonic()
            compiled = kernel[(triton.cdiv(args.size,
                                           128), )](x,
                                                    a,
                                                    b,
                                                    y,
                                                    state,
                                                    args.size,
                                                    steps,
                                                    128,
                                                    num_warps=args.num_warps)
            torch.gcu.synchronize()
            elapsed.append(time.monotonic() - started)
            hashes.append(compiled.hash)
            torch.testing.assert_close(y.cpu(), expected, rtol=0, atol=0)
            assert storage[0].cpu().item() == 123 and storage[-1].cpu().item(
            ) == 123
        assert len(set(hashes)) == 1, hashes
        if session is not None:
            profiler.finalize(session)
        assert state.cpu().item() == 2
        assert state_storage[0].cpu().item() == 777 and state_storage[-1].cpu(
        ).item() == 777
        assert inputs == [value.cpu().numpy().tobytes() for value in (x, a, b)]
        result = {
            'structure': name,
            'binary': hashes[0],
            'compile_launch_s': elapsed,
            'math_input_canary_no_replay': True
        }
        if session is not None:
            result.update(inspect_bundle(bundle))
        results.append(result)
    (args.output /
     'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2), flush=True)


if __name__ == '__main__':
    main()
