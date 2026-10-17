"""Ordinary GCU launch script for the public profiler CLI; no profiler scopes."""
import argparse
import json
from pathlib import Path

import torch
import torch_gcu  # noqa: F401
import triton
import triton.language as tl


@triton.jit(do_not_specialize=['steps'])
def recurrence(X, Y, State, N, steps, BLOCK: tl.constexpr):
    pid = tl.program_id(0)+tl.program_id(1)*tl.num_programs(0)
    lanes = tl.arange(0, BLOCK)
    offsets = pid*BLOCK+lanes
    value = tl.load(X+offsets, offsets<N, 0)
    for _ in range(steps):
        value = value*0.75+0.125
    tl.store(Y+offsets, value, offsets<N)
    previous = tl.load(State+pid+lanes, lanes==0, 0)
    tl.store(State+pid+lanes, previous+1, lanes==0)


def make_inputs(grid, steps):
    total = grid[0]*grid[1]
    n = 128*total-5
    cpu = torch.linspace(-2, 2, n)
    return dict(grid=grid, steps=steps, n=n, cpu=cpu, x=cpu.to('gcu'),
        y=torch.full((n+4,), -17.25, device='gcu'),
        state=torch.zeros(total, device='gcu', dtype=torch.int32))


def launch(row):
    return recurrence[row['grid']](row['x'], row['y'], row['state'], row['n'],
                                   row['steps'], 128, num_warps=4)


def verify(row):
    reference = row['cpu'].clone()
    for _ in range(row['steps']):
        reference = reference*0.75+0.125
    if not torch.allclose(row['y'][:row['n']].cpu(), reference, rtol=2e-6, atol=2e-6):
        raise RuntimeError('Ordinary recurrence output changed')
    if not torch.equal(row['x'].cpu(), row['cpu']):
        raise RuntimeError('Ordinary input changed')
    if not torch.equal(row['y'][row['n']:].cpu(), torch.full((4,), -17.25)):
        raise RuntimeError('Ordinary tail canary changed')
    if row['state'].cpu().tolist()!=[1]*(row['grid'][0]*row['grid'][1]):
        raise RuntimeError('Ordinary side effects replayed or lost')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(exist_ok=False)
    torch.gcu.set_device(0)
    rows = [make_inputs(grid, steps) for grid, steps in [((3, 2), 3), ((2, 2), 7), ((1, 1), 11)]]
    for row in rows:
        launch(row)
    for row in rows:
        verify(row)
    (args.evidence/'math.json').write_text(json.dumps(dict(math_calls=3,
        cases=[dict(grid=row['grid'], steps=row['steps'], input_unchanged=True,
                    tail_canary=True, program_side_effects=row['state'].cpu().tolist())
               for row in rows]), indent=2)+'\n')


if __name__ == '__main__':
    main()
