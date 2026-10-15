"""Source discovery across ordinary JIT helper calls, through public auto API."""
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
def affine_inside(value):
    return value * 0.5 + 0.25


@triton.jit
def square_inside(value):
    shifted = value + 0.5
    return shifted * shifted


@triton.jit
def helper_map(X, Y, N, B: tl.constexpr):
    index = tl.program_id(0) * B + tl.arange(0, B)
    value = tl.load(X + index, index < N, 0)
    result = affine_inside(value)
    tl.store(Y + index, result, index < N)


@triton.jit
def helper_reduce(X, Y, N, B: tl.constexpr):
    index = tl.arange(0, B)
    value = tl.load(X + index, index < N, 0)
    squared = square_inside(value)
    total = tl.sum(tl.where(index < N, squared, 0), 0)
    tl.store(Y, total)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline-only', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cpu = (torch.arange(137).remainder(32).float() - 16) / 32
    x = cpu.to('gcu')
    results = []
    source_lines = Path(__file__).read_text().splitlines()
    helper_lines = {
        'map': {
            index + 1
            for index, text in enumerate(source_lines)
            if text.strip() == 'return value * 0.5 + 0.25'
        },
        'reduce': {
            index + 1
            for index, text in enumerate(source_lines)
            if text.strip() in ('shifted = value + 0.5',
                                'return shifted * shifted')
        },
    }
    for kind in ('map', 'reduce'):
        count = 137 if kind == 'map' else 1
        storage = torch.full((count + 2, ), 123.0, device='gcu')
        y = storage[1:-1]
        bundle = args.output / kind
        session = None if args.baseline_only else profiler.start(str(bundle),
                                                                 detail='auto')
        start = time.monotonic()
        if kind == 'map':
            kernel = helper_map[(2, )](x, y, 137, 128, num_warps=4)
            expected = cpu * 0.5 + 0.25
        else:
            kernel = helper_reduce[(1, )](x, y, 137, 256, num_warps=4)
            expected = ((cpu + 0.5)**2).sum().reshape(1)
        torch.gcu.synchronize()
        elapsed = time.monotonic() - start
        start = time.monotonic()
        if session is not None:
            profiler.finalize(session)
        exported = time.monotonic() - start
        torch.testing.assert_close(y.cpu(), expected, rtol=0, atol=0)
        torch.testing.assert_close(x.cpu(), cpu, rtol=0, atol=0)
        assert storage[0].cpu().item() == 123 and storage[-1].cpu().item(
        ) == 123
        result = {
            'structure': kind,
            'binary': kernel.hash,
            'compile_launch_s': elapsed,
            'export_s': exported
        }
        if session is not None:
            result.update(check(bundle))
            plan = json.loads(
                (bundle /
                 'ai/observation_plan.json').read_text())['plans'][0]['plan']
            inventory = json.dumps(plan['inventory'])
            # Inventory must retain real helper source positions after inlining.
            assert any(f':{line}:' in inventory
                       for line in helper_lines[kind]), inventory
        results.append(result)
    (args.output /
     'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2), flush=True)


if __name__ == '__main__':
    main()
