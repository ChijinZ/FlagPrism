"""Compiler capability probe, not an ordinary-program acceptance workload.

The side-effect-only empty comment consumes compiler-provided source coordinates
and extents. Its presence/operands must survive SDK lowering before a census
producer may use them. No timing or count is inferred from this probe.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler  # noqa: F401; registers the public compiler driver


@triton.jit
def anchor_probe(x, out, width: tl.constexpr):
    px = tl.program_id(0)
    py = tl.program_id(1)
    pz = tl.program_id(2)
    nx = tl.num_programs(0)
    ny = tl.num_programs(1)
    nz = tl.num_programs(2)
    tl.inline_asm_elementwise(
        asm='/* flagprism.source_program_axes.v1 */',
        constraints='=r,r,r,r,r,r,r', args=[px, py, pz, nx, ny, nz],
        dtype=tl.int32, is_pure=False, pack=1)
    linear = (px * ny + py) * nz + pz
    offset = linear * width + tl.arange(0, width)
    tl.store(out + offset, tl.load(x + offset) * 2.0 + 0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--grid', type=int, nargs=3, default=(2, 3, 2))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    n = args.grid[0] * args.grid[1] * args.grid[2] * 16
    cpu = torch.arange(n, dtype=torch.float32) / 32
    x = cpu.to('npu:4')
    out = torch.empty_like(x)
    result = dict(pid=os.getpid(), grid=args.grid,
                  capability_probe=True, status='started',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  triton_path=triton.__file__, profiler_path=profiler.__file__)
    try:
        kernel = anchor_probe[tuple(args.grid)](x, out, 16)
        torch.npu.synchronize()
        torch.testing.assert_close(out.cpu(), cpu * 2 + 0.5, atol=0, rtol=0)
        torch.testing.assert_close(x.cpu(), cpu, atol=0, rtol=0)
        result.update(status='passed', binary_hash=kernel.hash)
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (args.output / 'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
        print('FLAGPRISM_SOURCE_PROGRAM_ANCHOR_PROBE', json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
