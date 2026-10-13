"""Identical source workloads; backend lowering and execution are the study variables."""
import triton
import triton.language as tl

@triton.jit
def matmul_unrolled(A, B, Bias, C, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
           BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr, FUSED: tl.constexpr, UNROLL: tl.constexpr):
    m = tl.program_id(0) * BM + tl.arange(0, BM)
    n = tl.program_id(1) * BN + tl.arange(0, BN)
    k = tl.arange(0, BK)
    acc = tl.full((BM, BN), 0, tl.float32)
    for base in tl.range(0, tl.cdiv(K, BK), loop_unroll_factor=UNROLL):
        kk = base * BK + k
        a = tl.load(A + m[:, None] * K + kk[None, :], (m[:, None] < M) & (kk[None, :] < K), 0)
        b = tl.load(B + kk[:, None] * N + n[None, :], (kk[:, None] < K) & (n[None, :] < N), 0)
        acc += tl.dot(a, b)
    if FUSED:
        bias = tl.load(Bias + n, n < N, 0)
        z = acc + bias[None, :]
        u = 0.7978845608028654 * (z + 0.044715 * z * z * z)
        tanh_u = 2.0 / (1.0 + tl.exp(-2.0 * u)) - 1.0
        acc = 0.5 * z * (1.0 + tanh_u)
    tl.store(C + m[:, None] * N + n[None, :], acc, (m[:, None] < M) & (n[None, :] < N))

