"""Ordinary reduction application with more inactive arms than the site budget."""
import hashlib
import json
import os
from pathlib import Path

import torch
import triton
import triton.language as tl


@triton.jit
def modular_reductions(X, Y, Calls, N: tl.constexpr, B: tl.constexpr):
    program = tl.program_id(0)
    selector = (program * 3) % 11
    if selector == 1:
        i = tl.arange(0, B)
        x = tl.load(X + 0 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.0625
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 0, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 2:
        i = tl.arange(0, B)
        x = tl.load(X + 1 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.125
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 1, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 3:
        i = tl.arange(0, B)
        x = tl.load(X + 2 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.1875
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 2, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 4:
        i = tl.arange(0, B)
        x = tl.load(X + 3 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.25
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 3, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 5:
        i = tl.arange(0, B)
        x = tl.load(X + 4 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.3125
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 4, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 6:
        i = tl.arange(0, B)
        x = tl.load(X + 5 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.375
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 5, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 7:
        i = tl.arange(0, B)
        x = tl.load(X + 6 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.4375
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 6, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 8:
        i = tl.arange(0, B)
        x = tl.load(X + 7 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.5
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 7, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 9:
        i = tl.arange(0, B)
        x = tl.load(X + 8 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.5625
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 8, energy)
        tl.atomic_add(Calls + program, 1)
    if selector == 10:
        i = tl.arange(0, B)
        x = tl.load(X + 9 * N + i, i < N, other=0)
        shifted = tl.abs(x) + 0.625
        energy = tl.sum(tl.where(i < N, shifted * shifted, 0), 0)
        tl.store(Y + 9, energy)
        tl.atomic_add(Calls + program, 1)


with Path(os.environ['R7_EFFECT']).open('a') as stream:
    stream.write('application-executed\n')
n = 37
x = torch.linspace(-2, 2, 10 * n, device='cuda')
original = x.clone()
y = torch.full((17, ), -113., device='cuda')
calls = torch.zeros(11, dtype=torch.int32, device='cuda')
compiled = modular_reductions[(11, )](x,
                                      y,
                                      calls,
                                      n,
                                      64,
                                      num_warps=4,
                                      num_stages=1)
expected = (
    (x.cpu().reshape(10, n).abs() +
     torch.arange(1, 11, dtype=torch.float32)[:, None] * 0.0625)**2).sum(1)
torch.testing.assert_close(y[:10].cpu(), expected)
assert torch.equal(x, original)
assert torch.equal(y[10:].cpu(), torch.full((7, ), -113.))
assert calls.cpu().tolist() == [0] + [1] * 10
result = dict(math_input_canary_pass=True,
              explicit_kernel_calls=1,
              per_program_side_effects=calls.cpu().tolist(),
              compiled_hash=compiled.hash,
              source_sha256=hashlib.sha256(
                  Path(__file__).read_bytes()).hexdigest())
Path(os.environ['R7_RESULT']).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
