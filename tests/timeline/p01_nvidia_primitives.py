"""Real math / timer / ordinary async-lowering discovery for P01.

This is a mechanism probe, not FlagPrism's automatic timeline interface and not
a passing P01 verdict. Inline timestamps are deliberately confined to the clock
probe; ordinary GEMM has no profiling annotations. Run only in the booked Docker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    stat = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
    write_json(args.output / 'started.json', {
        'pid': os.getpid(), 'pgid': os.getpgid(0),
        'startticks': int(stat[19]), 'argv': sys.argv,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'primitive evidence only; not automatic profiling acceptance',
    })

    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def clock_math(X, Y, T, State, K, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        lane = tl.arange(0, BLOCK)
        x = tl.load(X + pid * BLOCK + lane)
        begin, value = tl.inline_asm_elementwise(
            'mov.u64 $0, %globaltimer; mov.f32 $1, $2;',
            constraints='=l,=f,f', args=[x],
            dtype=(tl.uint64, tl.float32), is_pure=False, pack=1)
        k = tl.load(K)
        for _ in range(k):
            value = value * 0.75 + 0.125
        end, value = tl.inline_asm_elementwise(
            'mov.f32 $1, $2; mov.u64 $0, %globaltimer;',
            constraints='=l,=f,f', args=[value],
            dtype=(tl.uint64, tl.float32), is_pure=False, pack=1)
        tl.store(Y + pid * BLOCK + lane, value)
        tl.store(T + pid * 2 + lane * 2, begin, lane == 0)
        tl.store(T + pid * 2 + lane * 2 + 1, end, lane == 0)
        tl.store(State + pid + lane, 1, lane == 0)

    @triton.jit
    def ordinary_gemm(A, B, C, M: tl.constexpr, N: tl.constexpr,
                      K: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr,
                      BK: tl.constexpr):
        rows = tl.program_id(0) * BM + tl.arange(0, BM)
        cols = tl.program_id(1) * BN + tl.arange(0, BN)
        ks = tl.arange(0, BK)
        acc = tl.full((BM, BN), 0, tl.float32)
        for tile in range(tl.cdiv(K, BK)):
            kval = tile * BK + ks
            a = tl.load(A + rows[:, None] * K + kval[None, :],
                        (rows[:, None] < M) & (kval[None, :] < K), 0)
            b = tl.load(B + kval[:, None] * N + cols[None, :],
                        (kval[:, None] < K) & (cols[None, :] < N), 0)
            acc += tl.dot(a, b)
        tl.store(C + rows[:, None] * N + cols[None, :], acc,
                 (rows[:, None] < M) & (cols[None, :] < N))

    torch.cuda.set_device(0)
    require(torch.cuda.get_device_capability(0) == (12, 0),
            'This discovery registration is for the booked cuda:120 target')
    torch.manual_seed(1729)
    x_cpu = torch.rand(128, dtype=torch.float32)
    x = x_cpu.cuda()
    y = torch.empty_like(x)
    stamps = torch.empty((2, 2), device='cuda', dtype=torch.int64)
    state = torch.zeros(2, device='cuda', dtype=torch.int32)
    k_device = torch.empty((), device='cuda', dtype=torch.int32)
    calls = []
    clock_objects = []

    def run_clock(k, purpose):
        k_device.fill_(k)
        state.zero_()
        torch.cuda.synchronize()
        lo = time.monotonic_ns()
        compiled = clock_math[(2,)](x, y, stamps, state, k_device, 64,
                                    num_warps=4)
        torch.cuda.synchronize()
        hi = time.monotonic_ns()
        ticks = stamps.cpu().tolist()
        expected = x_cpu.clone()
        for _ in range(k):
            expected = expected * 0.75 + 0.125
        require(torch.allclose(y.cpu(), expected, rtol=2e-6, atol=2e-6),
                'Clock probe changed the registered mathematical result')
        require(torch.equal(x.cpu(), x_cpu), 'Input was modified')
        require(state.cpu().tolist() == [1, 1], 'Missing actual program work')
        require(all(0 < a < b for a, b in ticks), 'Nonpositive device interval')
        row = {'purpose': purpose, 'runtime_k': k,
               'host_before_ns': lo, 'host_after_ns': hi,
               'raw_uint64_ticks': ticks, 'state': [1, 1]}
        calls.append(row)
        write_json(args.output / 'clock-calls.json', calls)
        clock_objects.append(compiled)

    # Explicit discovery calls, never implicit warmup/replay of a user request.
    for k in (3, 7, 11):
        run_clock(k, 'math-and-runtime-loop-discovery')
    for i in range(6):
        time.sleep(0.04)
        run_clock(7, 'independent-clock-calibration')
    for i in range(4):
        time.sleep(0.06)
        run_clock(3 if i % 2 else 11, 'held-out-clock-validation')

    # Test the independently documented 1ns candidate against host brackets.
    # Never fit a profiled kernel's endpoints or stretch its duration.
    anchors = [r for r in calls if r['purpose'].startswith('independent')]
    heldout = [r for r in calls if r['purpose'].startswith('held-out')]
    bounds = []
    for a in anchors:
        for b in heldout:
            dtick = b['raw_uint64_ticks'][0][0] - a['raw_uint64_ticks'][0][0]
            lower = b['host_before_ns'] - a['host_after_ns']
            upper = b['host_after_ns'] - a['host_before_ns']
            require(dtick > 0 and lower > 0, 'Invalid clock comparison window')
            require(lower <= dtick <= upper,
                    '1ns globaltimer candidate is outside held-out host bounds')
            bounds.append({'tick_delta': dtick, 'host_delta_lower_ns': lower,
                           'host_delta_upper_ns': upper,
                           'candidate_tick_ns_numerator': 1,
                           'candidate_tick_ns_denominator': 1})

    m, n, k = 48, 56, 96
    a_cpu = torch.randn((m, k), dtype=torch.float16)
    b_cpu = torch.randn((k, n), dtype=torch.float16)
    a, b = a_cpu.cuda(), b_cpu.cuda()
    c = torch.empty((m, n), device='cuda', dtype=torch.float32)
    expected = a_cpu.float() @ b_cpu.float()
    objects = {}
    for stages in (2, 3):
        compiled = ordinary_gemm[(triton.cdiv(m, 32), triton.cdiv(n, 32))](
            a, b, c, m, n, k, 32, 32, 32, num_warps=4,
            num_stages=stages)
        torch.cuda.synchronize()
        require(torch.allclose(c.cpu(), expected, rtol=1e-3, atol=2e-3),
                'Ordinary GEMM math failed before profiling')
        require(torch.equal(a.cpu(), a_cpu) and torch.equal(b.cpu(), b_cpu),
                'Ordinary GEMM modified an input')
        objects[f'ordinary-gemm-stages{stages}'] = compiled
    objects['clock-math'] = clock_objects[-1]
    artifact_rows = []
    for name, compiled in objects.items():
        for kind, value in compiled.asm.items():
            if isinstance(value, str):
                raw = value.encode()
            elif isinstance(value, bytes):
                raw = value
            else:
                continue
            path = args.output / f'{name}.{kind}'
            path.write_bytes(raw)
            artifact_rows.append({'path': path.name, 'bytes': len(raw),
                                  'sha256': hashlib.sha256(raw).hexdigest()})
    write_json(args.output / 'primitive-result.json', {
        'status': 'primitive_checks_passed_not_timeline_acceptance',
        'device': torch.cuda.get_device_name(0), 'capability': [12, 0],
        'torch': torch.__version__, 'triton': triton.__version__,
        'clock_math_calls': len(calls), 'ordinary_gemm_calls': 2,
        'heldout_clock_constraints': bounds, 'artifacts': artifact_rows,
        'limits': ['not automatic FlagPrism profiling',
                   'not proof of async instrumentation or dependencies',
                   'host brackets validate clock scale, not profiling overhead',
                   'inspect actual generated objects before capability claims'],
    })


if __name__ == '__main__':
    main()
