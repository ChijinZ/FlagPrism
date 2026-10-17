"""Ordinary unannotated math; usable as a standalone CLI target or API workload."""
import argparse
from pathlib import Path
import torch
import triton
import triton.language as tl


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


@triton.jit
def recurrence(X, Y, Counter, K, N, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    lane = tl.arange(0, BLOCK)
    index = pid * BLOCK + lane
    value = tl.load(X + index, index < N, 0)
    k = tl.load(K)
    for _ in range(k):
        value = value * 0.75 + 0.125
    tl.store(Y + index, value, index < N)
    prior = tl.load(Counter + pid + lane, lane == 0, 0)
    tl.store(Counter + pid + lane, prior + 1, lane == 0)


@triton.jit
def gemm(A, B, C, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
         BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
    r = tl.program_id(0) * BM + tl.arange(0, BM)
    c = tl.program_id(1) * BN + tl.arange(0, BN)
    kk = tl.arange(0, BK)
    accum = tl.full((BM, BN), 0, tl.float32)
    for tile in range(tl.cdiv(K, BK)):
        ks = tile * BK + kk
        av = tl.load(A + r[:, None] * K + ks[None, :],
                     (r[:, None] < M) & (ks[None, :] < K), 0)
        bv = tl.load(B + ks[:, None] * N + c[None, :],
                     (ks[:, None] < K) & (c[None, :] < N), 0)
        accum += tl.dot(av, bv)
    tl.store(C + r[:, None] * N + c[None, :], accum,
             (r[:, None] < M) & (c[None, :] < N))


def run(evidence, *, include_zero=True):
    evidence = Path(evidence)
    evidence.mkdir(exist_ok=False)
    (evidence/'host-once.txt').write_text('one explicit workload execution\n')
    torch.manual_seed(9217)
    streams = [torch.cuda.Stream(), torch.cuda.Stream()]
    cases = []
    for index, k in enumerate((3, 7, 11)):
        grid, n = (3, 189) if index % 2 == 0 else (5, 317)
        cpu = torch.rand(320)
        x = cpu.cuda()
        y = torch.full((328,), -17.25, device='cuda')
        state = torch.zeros(5, device='cuda', dtype=torch.int32)
        kd = torch.tensor(k, device='cuda', dtype=torch.int32)
        reference = cpu[:n].clone()
        for _ in range(k):
            reference = reference * 0.75 + 0.125
        cases.append((x, y, state, kd, n, grid, reference, cpu))
    ready = torch.cuda.Event()
    ready.record(torch.cuda.current_stream())
    for stream in streams:
        stream.wait_event(ready)
    for index, (x, y, state, kd, n, grid, _, _) in enumerate(cases):
        with torch.cuda.stream(streams[index % 2]):
            recurrence[(grid,)](x, y, state, kd, n, 64, num_warps=4)
    for x, y, state, kd, n, grid, reference, cpu in cases:
        require(torch.allclose(y[:n].cpu(), reference, rtol=2e-6, atol=2e-6), 'Recurrence math')
        require(torch.equal(y[n:].cpu(), torch.full((328-n,), -17.25)), 'Tail canary')
        require(state.cpu().tolist() == [1]*grid+[0]*(5-grid), 'Program side effect/replay')
        require(torch.equal(x.cpu(), cpu), 'Input changed')
    # Legal zero-grid launch: no device work, owner or synthetic event.
    if include_zero:
        x, y, state, kd, n, grid, _, _ = cases[-1]
        recurrence[(0,)](x, y, state, kd, n, 64, num_warps=4)
        require(state.cpu().tolist() == [1]*grid+[0]*(5-grid), 'Zero-grid launch changed state')
    a_cpu = torch.randn(48, 96, dtype=torch.float16)
    b_cpu = torch.randn(96, 56, dtype=torch.float16)
    a, b = a_cpu.cuda(), b_cpu.cuda()
    c = torch.empty((48, 56), device='cuda', dtype=torch.float32)
    gemm[(2, 2)](a, b, c, 48, 56, 96, 32, 32, 32, num_warps=4, num_stages=3)
    require(torch.allclose(c.cpu().double(), a_cpu.double()@b_cpu.double(),
                          rtol=1e-2, atol=1e-2), 'GEMM math')
    require(torch.equal(a.cpu(), a_cpu) and torch.equal(b.cpu(), b_cpu), 'GEMM inputs changed')
    (evidence/'math-passed.txt').write_text('3 recurrence + 1 GEMM; original outputs/input/tail/side effects passed\n')


def run_overflow(evidence):
    """Actual math with more timestamps than the default bounded ring retains."""
    evidence = Path(evidence)
    evidence.mkdir(exist_ok=False)
    (evidence/'host-once.txt').write_text('one explicit overflow workload\n')
    cpu = torch.rand(256)
    x = cpu.cuda()
    y = torch.full((197,), -17.25, device='cuda')
    counter = torch.zeros(3, dtype=torch.int32, device='cuda')
    k = torch.tensor(1021, dtype=torch.int32, device='cuda')
    reference = cpu[:189].clone()
    for _ in range(1021):
        reference = reference * 0.75 + 0.125
    recurrence[(3,)](x, y, counter, k, 189, 64, num_warps=4)
    require(torch.allclose(y[:189].cpu(), reference, rtol=2e-6, atol=2e-6), 'Overflow math')
    require(torch.equal(y[189:].cpu(), torch.full((8,), -17.25)), 'Overflow tail')
    require(counter.cpu().tolist() == [1,1,1], 'Overflow workload replay')
    require(torch.equal(x.cpu(), cpu), 'Overflow input changed')
    (evidence/'math-passed.txt').write_text('original math, tail, input and side effects passed\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--skip-zero', action='store_true')
    parsed = parser.parse_args()
    run(parsed.evidence, include_zero=not parsed.skip_zero)
