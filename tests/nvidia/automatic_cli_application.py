"""An ordinary user script: no profiling API or annotations in its kernel."""
import os
from pathlib import Path
import torch
import triton
import triton.language as tl


@triton.jit(do_not_specialize=['repetitions'])
def recurrence(X, Y, N, repetitions, B: tl.constexpr):
    index = tl.arange(0, B)
    x = tl.load(X + index, index < N, other=0)
    for iteration in range(repetitions):
        x = x * 0.75 + 0.125
    tl.store(Y + index, x, index < N)


# An observable host-side effect detects hidden application replay.
side_effect = Path(os.environ['FLAGPRISM_DEVELOPMENT_SIDE_EFFECT'])
with side_effect.open('a') as output:
    output.write('application-executed\n')
x = torch.linspace(-1, 1, 137, device='cuda')
original = x.clone()
y = torch.full((144, ), -123., device='cuda')
for repetitions in (3, 7):
    expected = x.cpu()
    for _ in range(repetitions):
        expected = expected * 0.75 + 0.125
    recurrence[(1, )](x, y, 137, repetitions, 256, num_warps=4, num_stages=1)
    torch.testing.assert_close(y[:137].cpu(), expected)
    assert torch.equal(y[137:].cpu(), torch.full((7, ), -123.))
assert torch.equal(x, original)
