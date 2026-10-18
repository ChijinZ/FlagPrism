"""Ordinary CLI application: one user kernel, no profiler annotations or API."""
import argparse
import json
import os
from pathlib import Path

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl


@triton.jit
def fused(x, y, out, state, N: tl.constexpr):
    i = tl.program_id(0) * 256 + tl.arange(0, 256)
    active = i < N
    a = tl.load(x + i, active, 0)
    b = tl.load(y + i, active, 0)
    value = (a + b) * 3 - a
    tl.store(out + i, value, active)
    old = tl.load(state + i, active, 0)
    tl.store(state + i, old + 1, active)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    n = 1027
    a = torch.arange(n + 7, dtype=torch.int32) % 17
    b = torch.arange(n + 7, dtype=torch.int32) % 11
    x, y = a.npu(), b.npu()
    out = torch.full_like(x, -1234)
    state = torch.zeros_like(x)
    kernel = fused[(5, )](x, y, out, state, n, enable_auto_blockify=False)
    torch.npu.synchronize(
    )  # Explicit application validation, not profiler policy.
    torch.testing.assert_close(out[:n].cpu(), ((a + b) * 3 - a)[:n],
                               rtol=0,
                               atol=0)
    if not bool((state[:n].cpu() == 1).all()) or not bool(
        (state[n:].cpu() == 0).all()):
        raise RuntimeError(
            'Application kernel was replayed or its tail changed')
    if not bool((out[n:].cpu() == -1234).all()) or not torch.equal(
            x.cpu(), a) or not torch.equal(y.cpu(), b):
        raise RuntimeError('Input or tail changed')
    (args.evidence / 'result.json').write_text(
        json.dumps(dict(status='pass',
                        user_kernel_calls=1,
                        binary_id=kernel.hash),
                   indent=2))


if __name__ == '__main__':
    main()
