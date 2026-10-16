"""Ordinary multidimensional launch geometry regression for source census.

No tracing arguments, annotations, warm-up under observation, or instrumentation
calls occur in either kernel. Run baseline before default in the Ascend Docker.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler


@triton.jit
def row_increment(x, counts, out, width: tl.constexpr):
    row = tl.program_id(0) + tl.num_programs(0) * (tl.program_id(1) + tl.num_programs(1) * tl.program_id(2))
    lane = tl.arange(0, width)
    value = tl.load(x + row * width + lane)
    count = tl.load(counts + row)
    for step in range(count):
        value = value + 0.25
    tl.store(out + row * width + lane, value)


@triton.jit
def row_energy(x, counts, out, width: tl.constexpr):
    row = tl.program_id(0) + tl.num_programs(0) * (tl.program_id(1) + tl.num_programs(1) * tl.program_id(2))
    lane = tl.arange(0, width)
    value = tl.load(x + row * width + lane)
    count = tl.load(counts + row)
    result = tl.full((), 0.0, tl.float32)
    for step in range(count):
        result += tl.sum(value * value + step * 0.125, 0)
    tl.store(out + row, result)


def digest_tensor(tensor):
    return hashlib.sha256(tensor.cpu().numpy().tobytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('baseline', 'default'), required=True)
    parser.add_argument('--grid', type=int, nargs=3, required=True)
    args = parser.parse_args()
    if any(dimension <= 0 for dimension in args.grid):
        raise ValueError('grid dimensions must be positive')
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    width, rows = 32, math.prod(args.grid)
    cpu = (torch.arange(rows * width, dtype=torch.float32).reshape(rows, width) - 48) / 32
    x = cpu.to('npu:4')
    counts = torch.empty(rows, dtype=torch.int32, device='npu:4')
    receipt = dict(pid=os.getpid(), phase=args.phase, device=4,
                   triton_file=triton.__file__, profiler_file=profiler.__file__,
                   source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   grid=args.grid, width=width, input_sha256=digest_tensor(x), runs=[])
    receipt_path = args.output / 'receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2))
    for name, kernel in (('row_increment', row_increment), ('row_energy', row_energy)):
        hashes = []
        for iterations in (2, 5):
            cpu_counts = torch.tensor([0] + [iterations] * (rows - 1), dtype=torch.int32)
            counts.copy_(cpu_counts)
            size = rows * width if name == 'row_increment' else rows
            storage = torch.full((size + 32,), -12345.0, device='npu:4')
            output = storage[16:-16]
            label = f'{name}-{iterations}'
            session = None
            row = dict(kernel=name, iterations=iterations, counts=cpu_counts.tolist(),
                       status='running', capture=str(args.output / label))
            receipt['runs'].append(row)
            receipt_path.write_text(json.dumps(receipt, indent=2))
            started = time.monotonic()
            try:
                if args.phase == 'default':
                    session = profiler.start(str(args.output / label), backend='cann', detail='auto')
                compiled = kernel[tuple(args.grid)](x, counts, output, width)
                torch.npu.synchronize()
                row['binary_hash'] = compiled.hash
                hashes.append(compiled.hash)
                if name == 'row_increment':
                    expected = cpu + cpu_counts[:, None] * 0.25
                else:
                    n = cpu_counts.float()
                    expected = (cpu * cpu).sum(1) * n + width * 0.125 * n * (n - 1) / 2
                torch.testing.assert_close(output.cpu().reshape(expected.shape), expected,
                                           atol=1e-5, rtol=1e-5)
                torch.testing.assert_close(x.cpu(), cpu, atol=0, rtol=0)
                torch.testing.assert_close(counts.cpu(), cpu_counts, atol=0, rtol=0)
                guards = storage.cpu()
                assert torch.all(guards[:16] == -12345.0)
                assert torch.all(guards[-16:] == -12345.0)
                row.update(status='passed', output_sha256=digest_tensor(output))
            except BaseException as error:
                row.update(status='failed', error_type=type(error).__name__, error=str(error))
                raise
            finally:
                try:
                    if session is not None:
                        profiler.finalize(session)
                finally:
                    row['elapsed_seconds'] = time.monotonic() - started
                    receipt_path.write_text(json.dumps(receipt, indent=2))
        if len(set(hashes)) != 1:
            raise RuntimeError('runtime count change unexpectedly changed compiled binary')
    receipt['status'] = 'passed'
    receipt_path.write_text(json.dumps(receipt, indent=2))
    print('FLAGPRISM_R10_ACTIVE_PROGRAM_RESULT', json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
