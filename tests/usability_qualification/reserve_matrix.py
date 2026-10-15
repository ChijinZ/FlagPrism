"""Independent pre-profile matrix reserves with per-element stateful outputs.

Original Q0 kernels/results remain unchanged. No scalar read-modify-write probe.
Each requested launch consumes the prior output; hidden replay changes its math.
Same mathematical source, inputs, tolerance and startup script on every backend.
"""
import argparse
import json
import os
from pathlib import Path
import time

import torch

if os.environ.get('FLAGTREE_BACKEND') == 'ascend':
    import torch_npu  # noqa: F401
elif os.environ.get('FLAGTREE_BACKEND') == 'enflame':
    import torch_gcu  # noqa: F401

import triton
import triton.language as tl

from workload import CANARY, GUARD, data, digest


@triton.jit
def symmetric_cross(A, Bptr, Out, M: tl.constexpr, K: tl.constexpr,
                    BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
    p = tl.program_id(0)
    columns: tl.constexpr = triton.cdiv(M, BN)
    ii = p // columns * BM + tl.arange(0, BM)
    jj = p % columns * BN + tl.arange(0, BN)
    rr = tl.arange(0, BK)
    left = tl.full((BM, BN), 0, tl.float32)
    right = tl.full((BM, BN), 0, tl.float32)
    for tile in range(triton.cdiv(K, BK)):
        kk = tile * BK + rr
        a = tl.load(A + ii[:, None] * K + kk[None, :],
                    (ii[:, None] < M) & (kk[None, :] < K), 0)
        b = tl.load(Bptr + jj[None, :] * K + kk[:, None],
                    (jj[None, :] < M) & (kk[:, None] < K), 0)
        c = tl.load(Bptr + ii[:, None] * K + kk[None, :],
                    (ii[:, None] < M) & (kk[None, :] < K), 0)
        d = tl.load(A + jj[None, :] * K + kk[:, None],
                    (jj[None, :] < M) & (kk[:, None] < K), 0)
        left += tl.dot(a, b)  # QUAL_ANCHOR symmetric_left_dot
        right += tl.dot(c, d)  # QUAL_ANCHOR symmetric_right_dot
    valid = (ii[:, None] < M) & (jj[None, :] < M)
    offset = ii[:, None] * M + jj[None, :]
    previous = tl.load(Out + offset, valid, 0)
    tl.store(Out + offset, previous + left + right, valid)  # QUAL_ANCHOR symmetric_update


@triton.jit
def bilinear_difference(A, Bptr, Cptr, D, Out,
                        M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                        BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
    p = tl.program_id(0)
    columns: tl.constexpr = triton.cdiv(N, BN)
    ii = p // columns * BM + tl.arange(0, BM)
    jj = p % columns * BN + tl.arange(0, BN)
    rr = tl.arange(0, BK)
    positive = tl.full((BM, BN), 0, tl.float32)
    negative = tl.full((BM, BN), 0, tl.float32)
    for tile in range(triton.cdiv(K, BK)):
        kk = tile * BK + rr
        a = tl.load(A + ii[:, None] * K + kk[None, :],
                    (ii[:, None] < M) & (kk[None, :] < K), 0)
        b = tl.load(Bptr + kk[:, None] * N + jj[None, :],
                    (kk[:, None] < K) & (jj[None, :] < N), 0)
        c = tl.load(Cptr + ii[:, None] * K + kk[None, :],
                    (ii[:, None] < M) & (kk[None, :] < K), 0)
        d = tl.load(D + kk[:, None] * N + jj[None, :],
                    (kk[:, None] < K) & (jj[None, :] < N), 0)
        positive += tl.dot(a, b)  # QUAL_ANCHOR bilinear_positive_dot
        negative += tl.dot(c, d)  # QUAL_ANCHOR bilinear_negative_dot
    valid = (ii[:, None] < M) & (jj[None, :] < N)
    offset = ii[:, None] * N + jj[None, :]
    previous = tl.load(Out + offset, valid, 0)
    tl.store(Out + offset, previous + positive - negative, valid)  # QUAL_ANCHOR bilinear_update


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--case', choices=['symmetric_cross', 'bilinear_difference'], required=True)
    p.add_argument('--shape-index', type=int, choices=[0, 1], required=True)
    p.add_argument('--config-index', type=int, choices=[0, 1], required=True)
    p.add_argument('--backend', choices=['nvidia', 'enflame', 'ascend'], required=True)
    p.add_argument('--device', required=True)
    p.add_argument('--receipt', required=True)
    p.add_argument('--startup-ledger', required=True)
    args = p.parse_args()
    with open(args.startup_ledger, 'a') as stream:
        stream.write(json.dumps({'pid': os.getpid(), 'case': args.case}) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    device = torch.device(args.device)
    runtime = getattr(torch, device.type)
    runtime.set_device(device)
    bk = [32, 64][args.config_index]
    bm, bn = 32, 32
    if args.case == 'symmetric_cross':
        m, k = [[64, 64], [35, 45]][args.shape_index]
        n = m
        shape = [m, k]
        host = [data([m, k], 2, torch.float16), data([m, k], 7, torch.float16)]
        launch_dimensions = (m, k, bm, bn, bk)
    else:
        m, n, k = [[64, 64, 64], [35, 37, 45]][args.shape_index]
        shape = [m, n, k]
        host = [data([m, k], 1, torch.float16), data([k, n], 4, torch.float16),
                data([m, k], 8, torch.float16), data([k, n], 11, torch.float16)]
        launch_dimensions = (m, n, k, bm, bn, bk)
    inputs = [x.to(device) for x in host]
    before = [digest(x) for x in inputs]
    backing = torch.full((m * n + 2 * GUARD,), CANARY, dtype=torch.float32, device=device)
    output = backing[GUARD:-GUARD].view(m, n)
    seed = 0.375
    output.fill_(seed)
    initial_output_hash = digest(output)
    # Independent CPU-double mathematical reference, never device operations.
    cpu = [x.cpu().double() for x in host]
    if args.case == 'symmetric_cross':
        cross = cpu[0] @ cpu[1].T
        delta = cross + cross.T
    else:
        delta = cpu[0] @ cpu[1] - cpu[2] @ cpu[3]
    expected = seed + delta
    witness = float(delta.abs().max())
    assert witness > 0.01, 'input must distinguish one launch from hidden replay'
    grid = (triton.cdiv(m, bm) * triton.cdiv(n, bn),)
    started = time.perf_counter()
    compiled = globals()[args.case][grid](*inputs, output, *launch_dimensions, num_warps=4)
    runtime.synchronize()
    elapsed = time.perf_counter() - started
    actual = output.cpu().double()
    atol, rtol = 0.003, 0.003
    torch.testing.assert_close(actual, expected, atol=atol, rtol=rtol)
    assert before == [digest(x) for x in inputs], 'input mutation'
    assert bool((backing[:GUARD] == CANARY).all()) and bool((backing[-GUARD:] == CANARY).all())
    receipt = {'schema': 'flagprism-usability-workload-v1', 'case': args.case,
               'backend': args.backend, 'device': str(device), 'shape': shape,
               'shape_index': args.shape_index, 'config_index': args.config_index,
               'grid': list(grid), 'config': {'BM': bm, 'BN': bn, 'BK': bk, 'num_warps': 4},
               'input_sha256': before, 'output_initial_sha256': initial_output_hash,
               'non_idempotence_witness_max_abs': witness, 'requested_launches': 1,
               'sideeffect_protocol': 'per-element output consumes prior state; original CPU oracle requires exactly one update',
               'calls': [{'call_index': 0, 'runtime_steps': None,
                          'compiled_kernel_hash': str(getattr(compiled, 'hash', '')),
                          'compile_launch_sync_wall_s': elapsed, 'output_sha256': digest(output),
                          'max_abs_error': float((actual - expected).abs().max()),
                          'atol': atol, 'rtol': rtol, 'input_unchanged': True, 'canaries': True}]}
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
