"""Ordinary launch script: execute inside the booked server Docker only.

No profiler dependency. The same script and mathematical kernels serve both
the uninstrumented baseline and the documented default CLI.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import torch
import triton

import kernels


CASES = {
    "rational_blend": {"category": "pointwise", "shapes": [[512], [517]]},
    "reflected_contrast": {"category": "pointwise", "shapes": [[512], [517]]},
    "weighted_covariance": {"category": "reduction", "shapes": [[8, 128], [7, 131]]},
    "absolute_deviation": {"category": "reduction", "shapes": [[8, 128], [7, 131]]},
    "squared_distance": {"category": "matrix", "shapes": [[64, 64, 64], [35, 37, 45]]},
    "gated_product": {"category": "matrix", "shapes": [[64, 64, 64], [35, 37, 45]]},
    "runtime_recurrence": {"category": "runtime_loop", "shapes": [[512], [517]]},
}
GUARD = 64
CANARY = -12345.0


def digest(tensor):
    return hashlib.sha256(tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def data(shape, phase=0, dtype=torch.float32):
    # Independent, deterministic CPU input generation, executed on server only.
    count = 1
    for n in shape:
        count *= n
    values = torch.arange(count, dtype=torch.float64)
    return (((values * 17 + phase * 13) % 97 - 48) / 32).reshape(shape).to(dtype)


def oracle(case, inputs, shape, steps=None):
    # Double CPU arithmetic; no Triton code, GPU operation, or profiler data.
    x = [v.cpu().double() for v in inputs]
    if case == "rational_blend":
        q = (x[0] - x[1]) / (1 + x[0].abs() + x[1].abs())
        return torch.where(x[0] > x[1], q.square() + x[1], q - x[0])
    if case == "reflected_contrast":
        left = torch.cat((x[0][:1], x[0][:-1]))
        right = torch.cat((x[0][1:], x[0][-1:]))
        return (2 * x[0] - left - right) * x[1].flip(0)
    if case == "weighted_covariance":
        wsum = x[2].sum(1)
        mx = (x[2] * x[0]).sum(1) / wsum
        my = (x[2] * x[1]).sum(1) / wsum
        return (x[2] * (x[0] - mx[:, None]) * (x[1] - my[:, None])).sum(1) / wsum
    if case == "absolute_deviation":
        return (x[0] - x[0].mean(1, keepdim=True)).abs().mean(1)
    if case == "squared_distance":
        # Direct pairwise differences, independent of dot/norm implementation.
        return (x[0][:, None, :] - x[1][None, :, :]).square().sum(2)
    if case == "gated_product":
        return x[2] + (x[0] @ x[1]).clamp_min(0) * x[3][None, :]
    if case == "runtime_recurrence":
        return 0.5 + (x[0] - 0.5) * (0.75 ** steps)
    raise ValueError(case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--shape-index", type=int, choices=[0, 1], required=True)
    parser.add_argument("--config-index", type=int, choices=[0, 1], required=True)
    parser.add_argument("--backend", choices=["nvidia", "enflame", "ascend"], required=True)
    parser.add_argument("--device", help="explicit device, e.g. npu:4; recorded verbatim")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--startup-ledger", required=True)
    args = parser.parse_args()
    # Durable process side effect catches rerunning the entire launch script.
    with open(args.startup_ledger, "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "case": args.case}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if args.backend == "ascend":
        import torch_npu  # noqa: F401
        default_device = "npu:4"
    elif args.backend == "enflame":
        import torch_gcu  # noqa: F401
        default_device = "gcu:0"
    else:
        default_device = "cuda:0"
    device = torch.device(args.device or default_device)
    torch_module = getattr(torch, device.type)
    torch_module.set_device(device)
    case = args.case
    category = CASES[case]["category"]
    shape = CASES[case]["shapes"][args.shape_index]
    ci = args.config_index
    if category in ("pointwise", "runtime_loop"):
        n = shape[0]
        host = [data(shape, 1)]
        if category == "pointwise":
            host.append(data(shape, 3))
        block = [128, 256][ci]
        config = {"B": block, "num_warps": 4}
        grid = (triton.cdiv(n, block),)
        output_shape = shape
        positional = (n, block)
    elif category == "reduction":
        r, c = shape
        host = [data(shape, 1)]
        if case == "weighted_covariance":
            host.extend([data(shape, 3), data(shape, 5).abs() + 0.25])
        block = triton.next_power_of_2(c) * [1, 2][ci]
        config = {"B": block, "num_warps": 4}
        grid = (r,)
        output_shape = [r]
        positional = (r, c, block)
    else:
        m, n, k = shape
        a = data([m, k], 1, torch.float16)
        if case == "squared_distance":
            b = data([n, k], 3, torch.float16)
            host = [a, b, a.float().square().sum(1), b.float().square().sum(1)]
        else:
            b = data([k, n], 3, torch.float16)
            host = [a, b, data([m, n], 5), data([n], 7)]
        bm, bn, bk = (32, 32, [32, 64][ci])
        config = {"BM": bm, "BN": bn, "BK": bk, "num_warps": 4}
        grid = (triton.cdiv(m, bm) * triton.cdiv(n, bn),)
        output_shape = [m, n]
        positional = (m, n, k, bm, bn, bk)
    tensors = [v.to(device) for v in host]
    before = [digest(v) for v in tensors]
    size = 1
    for n in output_shape:
        size *= n
    backing = torch.full((size + 2 * GUARD,), CANARY, dtype=torch.float32, device=device)
    output = backing[GUARD:GUARD + size].view(output_shape)
    state_backing = torch.full((grid[0] + 2 * GUARD,), -937, dtype=torch.int32, device=device)
    state = state_backing[GUARD:GUARD + grid[0]]
    state.zero_()
    steps_tensor = torch.tensor([0], dtype=torch.int32, device=device)
    step_values = [2, 5] if case == "runtime_recurrence" else [None]
    results = []
    for call_index, steps in enumerate(step_values):
        output.fill_(float("nan"))
        started = time.perf_counter()
        if steps is not None:
            steps_tensor.fill_(steps)
            compiled = kernels.runtime_recurrence[grid](
                tensors[0], output, steps_tensor, state, *positional, num_warps=4)
        else:
            compiled = getattr(kernels, case)[grid](
                *tensors, output, state, *positional, num_warps=4)
        torch_module.synchronize()
        launch_wall_s = time.perf_counter() - started
        expected = oracle(case, host, shape, steps)
        actual = output.cpu().double()
        atol, rtol = (0.003, 0.003) if category == "matrix" else (0.00003, 0.00003)
        torch.testing.assert_close(actual, expected, atol=atol, rtol=rtol)
        assert before == [digest(v) for v in tensors], "input mutation"
        assert bool((backing[:GUARD] == CANARY).all().item())
        assert bool((backing[-GUARD:] == CANARY).all().item())
        assert bool((state_backing[:GUARD] == -937).all().item())
        assert bool((state_backing[-GUARD:] == -937).all().item())
        assert bool((state == call_index + 1).all().item()), "hidden device replay or missed program"
        # Public Triton CompiledKernel identity is supplemental evidence; the
        # public profiler report must independently bind calls to real binaries.
        identity = getattr(compiled, "hash", None)
        results.append({"call_index": call_index, "runtime_steps": steps,
                        "compile_launch_sync_wall_s": launch_wall_s,
                        "compiled_kernel_hash": str(identity) if identity else None,
                        "output_sha256": digest(output),
                        "max_abs_error": float((actual - expected).abs().max()),
                        "atol": atol, "rtol": rtol,
                        "input_unchanged": True, "canaries": True,
                        "program_state_counts": state.cpu().tolist()})
    if case == "runtime_recurrence":
        ids = [r["compiled_kernel_hash"] for r in results]
        assert all(ids) and ids[0] == ids[1], "runtime steps recompiled or binary identity unavailable"
    receipt = {"schema": "flagprism-usability-workload-v1", "case": case,
               "backend": args.backend, "device": str(device), "shape": shape,
               "shape_index": args.shape_index, "config_index": ci,
               "config": config, "grid": list(grid), "calls": results,
               "input_sha256": before, "torch_path": torch.__file__,
               "triton_path": triton.__file__, "pid": os.getpid()}
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
