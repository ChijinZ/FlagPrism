"""Ordinary side-effecting application for the public GCU CLI, no profiler API."""
import json
from pathlib import Path
import sys

import torch
import torch_gcu  # noqa: F401
import triton
import triton.language as tl


@triton.jit
def accumulate(X, Y, N, B: tl.constexpr):
    offset = tl.program_id(0) * B + tl.arange(0, B)
    x = tl.load(X + offset, offset < N, 0)
    previous = tl.load(Y + offset, offset < N, 0)
    tl.store(Y + offset, previous + x * 0.5, offset < N)


cpu = (torch.arange(137).remainder(32).float() - 16) / 32
x = cpu.to('gcu')
storage = torch.full((139, ), 123.0, device='gcu')
y = storage[1:-1]
y.zero_()
binaries = []
for _ in range(2):
    kernel = accumulate[(2, )](x, y, 137, 128, num_warps=4)
    binaries.append(kernel.hash)
torch.gcu.synchronize()
torch.testing.assert_close(y.cpu(), cpu, rtol=0, atol=0)
torch.testing.assert_close(x.cpu(), cpu, rtol=0, atol=0)
assert storage[0].cpu().item() == 123 and storage[-1].cpu().item() == 123
assert len(set(binaries)) == 1
Path(sys.argv[1]).write_text(
    json.dumps({
        'requested_launches': 2,
        'binaries': binaries,
        'math_input_canary_and_no_replay': True
    }) + '\n')
print(
    'mathematics, input, canary and exactly two accumulating launches passed',
    flush=True)
