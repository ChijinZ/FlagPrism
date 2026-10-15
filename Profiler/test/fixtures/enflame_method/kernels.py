"""Identical source workloads; backend lowering and execution are the study variables."""
import triton
import triton.language as tl


@triton.jit
def matmul(A, B, Bias, C, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
           BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr,
           FUSED: tl.constexpr):
    m = tl.program_id(0) * BM + tl.arange(0, BM)
    n = tl.program_id(1) * BN + tl.arange(0, BN)
    k = tl.arange(0, BK)
    acc = tl.full((BM, BN), 0, tl.float32)
    for base in range(tl.cdiv(K, BK)):
        kk = base * BK + k
        a = tl.load(A + m[:, None] * K + kk[None, :],
                    (m[:, None] < M) & (kk[None, :] < K), 0)
        b = tl.load(B + kk[:, None] * N + n[None, :],
                    (kk[:, None] < K) & (n[None, :] < N), 0)
        acc += tl.dot(a, b)
    if FUSED:
        bias = tl.load(Bias + n, n < N, 0)
        z = acc + bias[None, :]
        u = 0.7978845608028654 * (z + 0.044715 * z * z * z)
        tanh_u = 2.0 / (1.0 + tl.exp(-2.0 * u)) - 1.0
        acc = 0.5 * z * (1.0 + tanh_u)
    tl.store(C + m[:, None] * N + n[None, :], acc,
             (m[:, None] < M) & (n[None, :] < N))


@triton.jit
def rows(X, W, B, Y, R: tl.constexpr, N: tl.constexpr, BLOCK: tl.constexpr,
         ROWS: tl.constexpr, OP: tl.constexpr):
    r = tl.program_id(0) * ROWS + tl.arange(0, ROWS)
    c = tl.arange(0, BLOCK)
    valid = (r[:, None] < R) & (c[None, :] < N)
    if OP == 'softmax':
        x = tl.load(X + r[:, None] * N + c[None, :], valid, float('-inf'))
        e = tl.exp(x - tl.max(x, 1)[:, None])
        y = e / tl.sum(e, 1)[:, None]
        tl.store(Y + r[:, None] * N + c[None, :], y, valid)
    elif OP == 'layernorm':
        x = tl.load(X + r[:, None] * N + c[None, :], valid, 0.0)
        mean = tl.sum(x, 1) / N
        centered = tl.where(c[None, :] < N, x - mean[:, None], 0.0)
        var = tl.sum(centered * centered, 1) / N
        w = tl.load(W + c, c < N, 0.0)
        b = tl.load(B + c, c < N, 0.0)
        y = centered * tl.rsqrt(var[:, None] +
                                1.0e-5) * w[None, :] + b[None, :]
        tl.store(Y + r[:, None] * N + c[None, :], y, valid)
    else:
        x = tl.load(X + r[:, None] * N + c[None, :], valid, 0.0)
        y = tl.sum(x, 1)
        tl.store(Y + r, y, r < R)


@triton.jit
def transpose(X, Y, M: tl.constexpr, N: tl.constexpr, BM: tl.constexpr,
              BN: tl.constexpr):
    m = tl.program_id(0) * BM + tl.arange(0, BM)
    n = tl.program_id(1) * BN + tl.arange(0, BN)
    mask = (m[:, None] < M) & (n[None, :] < N)
    x = tl.load(X + m[:, None] * N + n[None, :], mask, 0.0)
    tl.store(Y + n[None, :] * M + m[:, None], x, mask)
