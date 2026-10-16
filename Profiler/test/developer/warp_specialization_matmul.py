"""Ordinary TMA matmul body from pinned tutorial09; no autotuning or profiler APIs."""
import triton
import triton.language as tl


@triton.jit
def matmul_kernel_tma(a_desc, b_desc, c_desc, M, N, K,
                      BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr,
                      BLOCK_SIZE_K: tl.constexpr, GROUP_SIZE_M: tl.constexpr,
                      FP8_OUTPUT: tl.constexpr, WARP_SPECIALIZE: tl.constexpr):
    dtype = tl.float8e4nv if FP8_OUTPUT else tl.float16
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    k_tiles = tl.cdiv(K, BLOCK_SIZE_K)
    offs_am = pid_m * BLOCK_SIZE_M
    offs_bn = pid_n * BLOCK_SIZE_N
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in tl.range(k_tiles, warp_specialize=WARP_SPECIALIZE):
        offs_k = k * BLOCK_SIZE_K
        a = a_desc.load([offs_am, offs_k])
        b = b_desc.load([offs_bn, offs_k])
        accumulator = tl.dot(a, b.T, accumulator)
    c = accumulator.to(dtype)
    offs_cm = pid_m * BLOCK_SIZE_M
    offs_cn = pid_n * BLOCK_SIZE_N
    c_desc.store([offs_cm, offs_cn], c)
