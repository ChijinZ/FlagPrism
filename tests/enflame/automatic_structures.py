"""Public automatic capture of ordinary call, branch and matrix structures."""
import argparse
import json
from pathlib import Path
import time

import torch
import torch_gcu  # noqa: F401
import triton
import triton.language as tl
import flagtree.profiler as profiler
from automatic_hardware import check


@triton.jit
def affine_value(value):
    return value * 0.5 + 0.25


@triton.jit(do_not_specialize=['positive'])
def branch_affine(X, Y, N, positive, B: tl.constexpr):
    offset = tl.program_id(0) * B + tl.arange(0, B)
    value = tl.load(X + offset, offset < N, other=0)
    if positive:
        result = affine_value(value)
    else:
        result = value * value - 0.125
    tl.store(Y + offset, result, offset < N)


@triton.jit
def matrix_product(A, B, C, N: tl.constexpr, K: tl.constexpr,
                   BK: tl.constexpr):
    row = tl.arange(0, 16)
    col = tl.arange(0, 16)
    reduction = tl.arange(0, BK)
    a = tl.load(A + row[:, None] * K + reduction[None, :], reduction[None, :]
                < K, 0)
    b = tl.load(B + reduction[:, None] * N + col[None, :],
                (reduction[:, None] < K) & (col[None, :] < N), 0)
    product = tl.dot(a, b)
    tl.store(C + row[:, None] * N + col[None, :], product, col[None, :] < N)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--size', type=int, default=137)
    parser.add_argument('--num-warps', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    branch_binaries = set()
    for positive in (0, 1):
        # Binary fractions keep both the fused device expression and the
        # unfused CPU oracle exact, so zero tolerance is meaningful.
        cpu = (torch.arange(args.size).remainder(32).float() - 16) / 32
        x = cpu.to('gcu')
        storage = torch.full((args.size + 2, ), 123.0, device='gcu')
        y = storage[1:-1]
        bundle = args.output / f'branch-{positive}'
        session = None if args.baseline_only else profiler.start(str(bundle),
                                                                 detail='auto')
        start = time.monotonic()
        kernel = branch_affine[(triton.cdiv(args.size,
                                            128), )](x,
                                                     y,
                                                     args.size,
                                                     positive,
                                                     128,
                                                     num_warps=args.num_warps)
        torch.gcu.synchronize()
        elapsed = time.monotonic() - start
        branch_binaries.add(kernel.hash)
        start = time.monotonic()
        if session is not None:
            profiler.finalize(session)
        exported = time.monotonic() - start
        expected = cpu * 0.5 + 0.25 if positive else cpu * cpu - 0.125
        torch.testing.assert_close(y.cpu(), expected, rtol=0, atol=0)
        torch.testing.assert_close(x.cpu(), cpu, rtol=0, atol=0)
        assert storage[0].cpu().item() == 123 and storage[-1].cpu().item(
        ) == 123
        result = {
            'structure': 'branch',
            'positive': positive,
            'binary': kernel.hash,
            'compile_launch_s': elapsed,
            'export_s': exported
        }
        if session is not None:
            result.update(check(bundle))
        results.append(result)
    assert len(branch_binaries) == 1, branch_binaries
    n, k = (13, 19) if args.size % 2 else (16, 32)
    ac = torch.linspace(-0.5, 0.5, 16 * k).reshape(16, k).half()
    bc = torch.linspace(-0.5, 0.5, k * n).reshape(k, n).half()
    a, b = ac.to('gcu'), bc.to('gcu')
    storage = torch.full((16 * n + 2, ), 123.0, device='gcu')
    c = storage[1:-1].reshape(16, n)
    bundle = args.output / 'matrix'
    session = None if args.baseline_only else profiler.start(str(bundle),
                                                             detail='auto')
    start = time.monotonic()
    kernel = matrix_product[(1, )](a,
                                   b,
                                   c,
                                   n,
                                   k,
                                   triton.next_power_of_2(k),
                                   num_warps=args.num_warps)
    torch.gcu.synchronize()
    elapsed = time.monotonic() - start
    start = time.monotonic()
    if session is not None:
        profiler.finalize(session)
    exported = time.monotonic() - start
    torch.testing.assert_close(c.cpu(),
                               ac.float() @ bc.float(),
                               rtol=1e-4,
                               atol=1e-5)
    torch.testing.assert_close(a.cpu(), ac, rtol=0, atol=0)
    torch.testing.assert_close(b.cpu(), bc, rtol=0, atol=0)
    assert storage[0].cpu().item() == 123 and storage[-1].cpu().item() == 123
    result = {
        'structure': 'matrix',
        'binary': kernel.hash,
        'compile_launch_s': elapsed,
        'export_s': exported
    }
    if session is not None:
        result.update(check(bundle))
    results.append(result)
    (args.output /
     'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2), flush=True)


if __name__ == '__main__':
    main()
