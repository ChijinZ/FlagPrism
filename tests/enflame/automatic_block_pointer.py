"""Ordinary block-pointer structures exercising public GCU automatic capture.

Run baseline first; numerical references execute only in the remote Docker.
"""
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
def block_affine(X, Y, N: tl.constexpr, B: tl.constexpr):
    block = tl.program_id(0) * B
    xp = tl.make_block_ptr(X, (N, ), (1, ), (block, ), (B, ), (0, ))
    yp = tl.make_block_ptr(Y, (N, ), (1, ), (block, ), (B, ), (0, ))
    value = tl.load(xp, boundary_check=(0, ), padding_option='zero')
    tl.store(yp, value * 0.5 + 0.25, boundary_check=(0, ))


@triton.jit
def block_row_energy(X, Y, M: tl.constexpr, N: tl.constexpr, B: tl.constexpr):
    row = tl.program_id(0)
    xp = tl.make_block_ptr(X, (M, N), (N, 1), (row, 0), (1, B), (1, 0))
    value = tl.load(xp, boundary_check=(0, 1), padding_option='zero')
    energy = tl.sum(value * value, 1)
    tl.store(Y + row + tl.arange(0, 1), energy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--size', type=int, default=137)
    parser.add_argument('--num-warps', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for name in ('affine', 'row_energy'):
        cpu = torch.linspace(-0.75, 0.75, 2 * args.size).reshape(2, args.size)
        x = cpu.to('gcu')
        count = cpu.numel() if name == 'affine' else 2
        storage = torch.full((count + 2, ), 123.0, device='gcu')
        y = storage[1:-1]
        bundle = args.output / name
        session = None if args.baseline_only else profiler.start(str(bundle),
                                                                 detail='auto')
        start = time.monotonic()
        if name == 'affine':
            kernel = block_affine[(triton.cdiv(cpu.numel(), 128), )](
                x, y, cpu.numel(), 128, num_warps=args.num_warps)
            expected = cpu.flatten() * 0.5 + 0.25
        else:
            kernel = block_row_energy[(2, )](x,
                                             y,
                                             2,
                                             args.size,
                                             triton.next_power_of_2(args.size),
                                             num_warps=args.num_warps)
            expected = (cpu * cpu).sum(1)
        torch.gcu.synchronize()
        elapsed = time.monotonic() - start
        start = time.monotonic()
        if session is not None:
            profiler.finalize(session)
        exported = time.monotonic() - start
        torch.testing.assert_close(y.cpu(), expected)
        torch.testing.assert_close(x.cpu(), cpu, rtol=0, atol=0)
        assert storage[0].cpu().item() == 123 and storage[-1].cpu().item(
        ) == 123
        result = {
            'structure': name,
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
