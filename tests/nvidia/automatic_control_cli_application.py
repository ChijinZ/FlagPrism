"""Ordinary single-launch application for the default inactive-program CLI test."""
import json
import os
from pathlib import Path

import torch
import triton
import triton.language as tl


@triton.jit
def active_neighbors(X, Y, Calls, N: tl.constexpr, B: tl.constexpr):
    program = tl.program_id(0)
    if program > 0:
        i = (program - 1) * B + tl.arange(0, B)
        x = tl.load(X + i, i < N, other=0)
        value = x * x + 0.25
        tl.store(Y + i, value, i < N)
        tl.atomic_add(Calls + program, 1)


side_effect = Path(os.environ['FLAGPRISM_DEVELOPMENT_SIDE_EFFECT'])
with side_effect.open('a') as stream:
    stream.write('application-executed\n')
x = torch.linspace(-1, 1, 123, device='cuda')
original = x.clone()
y = torch.full((130, ), -127., device='cuda')
calls = torch.zeros(3, dtype=torch.int32, device='cuda')
active_neighbors[(3, )](x, y, calls, 123, 64, num_warps=4, num_stages=1)
torch.testing.assert_close(y[:123].cpu(), x.cpu() * x.cpu() + 0.25)
assert torch.equal(y[123:].cpu(), torch.full((7, ), -127.))
assert torch.equal(x, original)
assert calls.cpu().tolist() == [0, 1, 1]
print(
    json.dumps(
        dict(math='passed',
             input='unchanged',
             canary='passed',
             actual_kernel_calls=1,
             per_program_side_effects=[0, 1, 1])))
