"""Ordinary user application for the public CLI integration test.

It has no profiler imports, annotations, extra pointer arguments or hidden replays.
"""
import argparse
import json
from pathlib import Path
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl


@triton.jit
def transform(x, out, n: tl.constexpr, block: tl.constexpr):
    i = tl.program_id(0) * block + tl.arange(0, block)
    a = tl.load(x + i, i < n, 0)
    v = (a + 0.75) * (a - 0.25)
    tl.store(out + i, v, i < n)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=int, default=4)
    parser.add_argument('--state-file', type=Path, required=True)
    args = parser.parse_args()
    previous = json.loads(args.state_file.read_text()) if args.state_file.exists() else {'application_executions': 0}
    previous['application_executions'] += 1
    args.state_file.write_text(json.dumps(previous))
    torch.npu.set_device(args.device)
    cpu = torch.arange(257, dtype=torch.float32) / 16
    x = cpu.to(f'npu:{args.device}')
    storage = torch.full((257 + 32,), -12345., device=f'npu:{args.device}')
    out = storage[16:-16]
    kernel = transform[(1,)](x, out, 257, 512)
    torch.npu.synchronize()
    torch.testing.assert_close(out.cpu(), (cpu + .75) * (cpu - .25))
    torch.testing.assert_close(x.cpu(), cpu, atol=0, rtol=0)
    guards = storage.cpu()
    assert torch.all(guards[:16] == -12345.) and torch.all(guards[-16:] == -12345.)
    previous.update(math='passed', input='unchanged', canaries='passed', binary=kernel.hash)
    args.state_file.write_text(json.dumps(previous, indent=2))
    print(json.dumps(previous))


if __name__ == '__main__':
    main()
