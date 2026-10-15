"""Pre-profile reserve, independent compact-support window mathematics.

Added after an original GCU baseline timeout, before any candidate profiling.
Original failing combinations remain in the frozen matrix. This reserve is not
counted as eligible until its own ordinary baseline runs in server Docker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import torch
import triton
import triton.language as tl

from workload import data, digest, GUARD, CANARY


@triton.jit
def cubic_window(X, Y, Out, State, N: tl.constexpr, B: tl.constexpr):
    p = tl.program_id(0)
    i = p * B + tl.arange(0, B)
    x = tl.load(X + i, i < N, 0)  # QUAL_ANCHOR window_load
    y = tl.load(Y + i, i < N, 0)
    support = tl.maximum(1.0 - x * x, 0.0)
    result = support * support * support * y  # QUAL_ANCHOR window_polynomial
    tl.store(Out + i, result, i < N)  # QUAL_ANCHOR window_store
    old = tl.load(State + p)
    tl.store(State + p, old + 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shape-index", type=int, choices=[0, 1], required=True)
    p.add_argument("--config-index", type=int, choices=[0, 1], required=True)
    p.add_argument("--backend", choices=["enflame", "ascend", "nvidia"], required=True)
    p.add_argument("--device", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--startup-ledger", required=True)
    args = p.parse_args()
    with open(args.startup_ledger, "a") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "case": "cubic_window"}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if args.backend == "enflame":
        import torch_gcu  # noqa: F401
    elif args.backend == "ascend":
        import torch_npu  # noqa: F401
    device = torch.device(args.device)
    runtime = getattr(torch, device.type)
    runtime.set_device(device)
    n, block = [512, 517][args.shape_index], [128, 256][args.config_index]
    host = [data([n], 2), data([n], 6)]
    inputs = [x.to(device) for x in host]
    before = [digest(x) for x in inputs]
    guard = torch.full((n + 2 * GUARD,), CANARY, device=device)
    out = guard[GUARD:-GUARD]
    out.fill_(float("nan"))
    programs = triton.cdiv(n, block)
    state_guard = torch.full((programs + 2 * GUARD,), -937, dtype=torch.int32, device=device)
    state = state_guard[GUARD:-GUARD]
    state.zero_()
    started = time.perf_counter()
    binary = cubic_window[(programs,)](*inputs, out, state, n, block, num_warps=4)
    runtime.synchronize()
    elapsed = time.perf_counter() - started
    # CPU reference computes the defining piecewise function in double precision.
    x, y = [v.double().cpu() for v in host]
    expected = torch.where(x.abs() < 1, (1 - x.square()).pow(3) * y, 0)
    actual = out.cpu().double()
    torch.testing.assert_close(actual, expected, atol=0.00003, rtol=0.00003)
    assert before == [digest(x) for x in inputs]
    assert bool((guard[:GUARD] == CANARY).all()) and bool((guard[-GUARD:] == CANARY).all())
    assert bool((state_guard[:GUARD] == -937).all()) and bool((state_guard[-GUARD:] == -937).all())
    assert bool((state == 1).all()), "hidden replay or missed program"
    result = {"schema": "flagprism-usability-workload-v1", "case": "cubic_window",
              "backend": args.backend, "device": str(device), "shape": [n],
              "shape_index": args.shape_index, "config_index": args.config_index,
              "config": {"B": block, "num_warps": 4}, "grid": [programs],
              "input_sha256": before, "pid": os.getpid(),
              "calls": [{"call_index": 0, "runtime_steps": None,
                         "compiled_kernel_hash": str(getattr(binary, "hash", "")),
                         "compile_launch_sync_wall_s": elapsed,
                         "output_sha256": digest(out), "input_unchanged": True,
                         "canaries": True, "atol": 0.00003, "rtol": 0.00003,
                         "max_abs_error": float((actual - expected).abs().max()),
                         "program_state_counts": state.cpu().tolist()}]}
    Path(args.receipt).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
