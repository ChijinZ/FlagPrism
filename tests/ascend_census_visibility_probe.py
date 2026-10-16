"""Public cube/vector census visibility diagnostic; no replay inference."""
import argparse
import json
import os
from pathlib import Path

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler


@triton.jit
def visibility_probe(a, b, bias, out, state, M: tl.constexpr, N: tl.constexpr,
                     K: tl.constexpr):
    p = tl.program_id(0)
    rows = p * 16 + tl.arange(0, 16)
    cols = tl.arange(0, 32)
    inner = tl.arange(0, 32)
    av = tl.load(a + rows[:, None] * K + inner[None, :],
                 (rows[:, None] < M) & (inner[None, :] < K), 0)
    bv = tl.load(b + inner[:, None] * N + cols[None, :],
                 (inner[:, None] < K) & (cols[None, :] < N), 0)
    cv = tl.load(bias + cols, cols < N, 0)
    v = tl.maximum(tl.dot(av, bv) + cv[None, :], 0.)
    v = tl.where(cols[None, :] < N, v, 0.)
    v = v / (1. + tl.sum(v, 1))[:, None]
    indices = rows[:, None] * N + cols[None, :]
    mask = (rows[:, None] < M) & (cols[None, :] < N)
    tl.store(out + indices, v, mask)
    previous = tl.load(state + indices, mask, 0)
    tl.store(state + indices, previous + 1, mask)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--baseline', action='store_true')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    m, n, k = 32, 32, 19
    ca = ((torch.arange(m * k).reshape(m, k) % 19) - 9).half() / 32
    cb = ((torch.arange(k * n).reshape(k, n) % 13) - 6).half() / 32
    cc = ((torch.arange(n) % 7) - 3).float() / 16
    expected = torch.relu(ca.float() @ cb.float() + cc)
    expected /= 1. + expected.sum(1, keepdim=True)
    a, b, bias = ca.npu(), cb.npu(), cc.npu()
    out = torch.empty((m, n), device='npu:4')
    state = torch.zeros((m, n), dtype=torch.int32, device='npu:4')
    target = args.output / 'capture'
    session = None if args.baseline else profiler.start(
        str(target), backend='cann', detail='auto')
    try:
        compiled = visibility_probe[(2, )](a,
                                           b,
                                           bias,
                                           out,
                                           state,
                                           m,
                                           n,
                                           k,
                                           enable_auto_blockify=False)
        torch.npu.synchronize()
    finally:
        if session is not None:
            profiler.finalize(session)
    torch.testing.assert_close(out.cpu(), expected, rtol=2e-3, atol=2e-4)
    actual = state.cpu()
    assert bool((actual == 1).all()), actual.tolist()
    result = dict(status='pass',
                  baseline=args.baseline,
                  shape=[m, n, k],
                  binary=compiled.hash,
                  state_elements=actual.numel(),
                  state_values=torch.unique(actual).tolist(),
                  pid=os.getpid())
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
