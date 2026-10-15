"""Held-out ordinary user kernels. No profiler imports, scopes, or site IDs.

QUAL_ANCHOR comments define source regions, never product selection hints.
Backend differences are launch parameters only; mathematical code is shared.
"""
import triton
import triton.language as tl


@triton.jit
def rational_blend(X, Y, Out, State, N: tl.constexpr, B: tl.constexpr):
    p = tl.program_id(0)
    i = p * B + tl.arange(0, B)
    x = tl.load(X + i, i < N, 0)  # QUAL_ANCHOR blend_load
    y = tl.load(Y + i, i < N, 0)
    q = (x - y) / (1.0 + tl.abs(x) + tl.abs(y))
    z = tl.where(x > y, q * q + y, q - x)  # QUAL_ANCHOR blend_select
    tl.store(Out + i, z, i < N)  # QUAL_ANCHOR blend_store
    s = tl.load(State + p)
    tl.store(State + p, s + 1)


@triton.jit
def reflected_contrast(X, Y, Out, State, N: tl.constexpr, B: tl.constexpr):
    p = tl.program_id(0)
    i = p * B + tl.arange(0, B)
    x = tl.load(X + i, i < N, 0)  # QUAL_ANCHOR contrast_center
    left = tl.load(X + tl.maximum(i - 1, 0), i < N, 0)
    right = tl.load(X + tl.minimum(i + 1, N - 1), i < N, 0)
    mirror = tl.load(Y + (N - 1 - i), i < N, 0)
    z = (2.0 * x - left - right) * mirror  # QUAL_ANCHOR contrast_stencil
    tl.store(Out + i, z, i < N)  # QUAL_ANCHOR contrast_store
    s = tl.load(State + p)
    tl.store(State + p, s + 1)


@triton.jit
def weighted_covariance(X, Y, W, Out, State, R: tl.constexpr,
                        C: tl.constexpr, B: tl.constexpr):
    row = tl.program_id(0)
    j = tl.arange(0, B)
    x = tl.load(X + row * C + j, j < C, 0)  # QUAL_ANCHOR covariance_load
    y = tl.load(Y + row * C + j, j < C, 0)
    w = tl.load(W + row * C + j, j < C, 0)
    sw = tl.sum(w, 0)
    mx = tl.sum(w * x, 0) / sw
    my = tl.sum(w * y, 0) / sw  # QUAL_ANCHOR covariance_means
    cov = tl.sum(w * (x - mx) * (y - my), 0) / sw
    tl.store(Out + row, cov)  # QUAL_ANCHOR covariance_store
    s = tl.load(State + row)
    tl.store(State + row, s + 1)


@triton.jit
def absolute_deviation(X, Out, State, R: tl.constexpr,
                       C: tl.constexpr, B: tl.constexpr):
    row = tl.program_id(0)
    j = tl.arange(0, B)
    x = tl.load(X + row * C + j, j < C, 0)  # QUAL_ANCHOR deviation_load
    mean = tl.sum(x, 0) / C  # QUAL_ANCHOR deviation_mean
    distance = tl.where(j < C, tl.abs(x - mean), 0)
    deviation = tl.sum(distance, 0) / C
    tl.store(Out + row, deviation)  # QUAL_ANCHOR deviation_store
    s = tl.load(State + row)
    tl.store(State + row, s + 1)


@triton.jit
def squared_distance(A, Bptr, Anorm, Bnorm, Out, State,
                     M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                     BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
    p = tl.program_id(0)
    cols: tl.constexpr = triton.cdiv(N, BN)
    mi = (p // cols) * BM + tl.arange(0, BM)
    ni = (p % cols) * BN + tl.arange(0, BN)
    ki = tl.arange(0, BK)
    acc = tl.full((BM, BN), 0, tl.float32)
    for start in range(triton.cdiv(K, BK)):
        kk = start * BK + ki
        a = tl.load(A + mi[:, None] * K + kk[None, :],
                    (mi[:, None] < M) & (kk[None, :] < K), 0)
        b = tl.load(Bptr + ni[None, :] * K + kk[:, None],
                    (ni[None, :] < N) & (kk[:, None] < K), 0)
        acc += tl.dot(a, b)  # QUAL_ANCHOR distance_dot
    aa = tl.load(Anorm + mi, mi < M, 0)
    bb = tl.load(Bnorm + ni, ni < N, 0)
    value = tl.maximum(aa[:, None] + bb[None, :] - 2 * acc, 0)
    tl.store(Out + mi[:, None] * N + ni[None, :], value,
             (mi[:, None] < M) & (ni[None, :] < N))  # QUAL_ANCHOR distance_store
    s = tl.load(State + p)
    tl.store(State + p, s + 1)


@triton.jit
def gated_product(A, Bptr, Residual, Gate, Out, State,
                  M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                  BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
    p = tl.program_id(0)
    cols: tl.constexpr = triton.cdiv(N, BN)
    mi = (p // cols) * BM + tl.arange(0, BM)
    ni = (p % cols) * BN + tl.arange(0, BN)
    ki = tl.arange(0, BK)
    acc = tl.full((BM, BN), 0, tl.float32)
    for start in range(triton.cdiv(K, BK)):
        kk = start * BK + ki
        a = tl.load(A + mi[:, None] * K + kk[None, :],
                    (mi[:, None] < M) & (kk[None, :] < K), 0)
        b = tl.load(Bptr + kk[:, None] * N + ni[None, :],
                    (kk[:, None] < K) & (ni[None, :] < N), 0)
        acc += tl.dot(a, b)  # QUAL_ANCHOR gated_dot
    offset = mi[:, None] * N + ni[None, :]
    valid = (mi[:, None] < M) & (ni[None, :] < N)
    residual = tl.load(Residual + offset, valid, 0)
    gate = tl.load(Gate + ni, ni < N, 0)
    value = residual + tl.maximum(acc, 0) * gate[None, :]  # QUAL_ANCHOR gated_fusion
    tl.store(Out + offset, value, valid)  # QUAL_ANCHOR gated_store
    s = tl.load(State + p)
    tl.store(State + p, s + 1)


@triton.jit
def runtime_recurrence(X, Out, Steps, State, N: tl.constexpr, B: tl.constexpr):
    p = tl.program_id(0)
    i = p * B + tl.arange(0, B)
    value = tl.load(X + i, i < N, 0)
    steps = tl.load(Steps)
    iteration = 0
    while iteration < steps:
        value = value * 0.75 + 0.125  # QUAL_ANCHOR recurrence_body
        iteration += 1
    tl.store(Out + i, value, i < N)  # QUAL_ANCHOR recurrence_store
    s = tl.load(State + p)
    tl.store(State + p, s + 1)
