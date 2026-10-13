def rows(X, W, B, Y, R: tl.constexpr, N: tl.constexpr,
         BLOCK: tl.constexpr, ROWS: tl.constexpr, OP: tl.constexpr):
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
        y = centered * tl.rsqrt(var[:, None] + 1.0e-5) * w[None, :] + b[None, :]
        tl.store(Y + r[:, None] * N + c[None, :], y, valid)
    else:
        x = tl.load(X + r[:, None] * N + c[None, :], valid, 0.0)
        y = tl.sum(x, 1)
        tl.store(Y + r, y, r < R)
