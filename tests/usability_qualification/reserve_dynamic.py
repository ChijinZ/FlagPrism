"""Q4 repair-generalization reserve. Freeze before any repaired-candidate exposure.

No profiler imports or expert parameters. Numerical checks run only in server Docker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import torch
if os.environ.get('FLAGTREE_BACKEND') == 'ascend':
    import torch_npu
elif os.environ.get('FLAGTREE_BACKEND') == 'enflame':
    import torch_gcu
import triton
import triton.language as tl

GUARD = 23
CANARY = 12345.0


@triton.jit
def coupled_logistic(X, Y, Out, Steps, N: tl.constexpr, B: tl.constexpr):
    offsets = tl.program_id(0) * B + tl.arange(0, B)
    valid = offsets < N
    a = tl.load(X + offsets, valid, 0)
    b = tl.load(Y + offsets, valid, 0)
    count = tl.load(Steps)
    k = 0
    while k < count:
        next_a = a * (1.0 - a) * 0.5 + b * 0.125
        b = b * 0.625 + a * 0.25 + 0.03125
        a = next_a
        k += 1
    previous = tl.load(Out + offsets, valid, 0)
    tl.store(Out + offsets, previous + a + 0.5 * b, valid)


@triton.jit
def neighbor_accumulation(X, Y, Out, Steps, N: tl.constexpr, B: tl.constexpr):
    offsets = tl.program_id(0) * B + tl.arange(0, B)
    valid = offsets < N
    value = tl.load(X + offsets, valid, 0)
    count = tl.load(Steps)
    k = 0
    while k < count:
        left = tl.load(X + (offsets + k + 1) % N, valid, 0)
        right = tl.load(Y + (offsets + N - k - 1) % N, valid, 0)
        value = value * 0.5 + left * 0.25 - right * 0.125
        k += 1
    previous = tl.load(Out + offsets, valid, 0)
    tl.store(Out + offsets, previous + value, valid)


def digest(tensor):
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def cpu_delta(case, inputs, count):
    # CPU-double expressions use full vectors, separate from GPU lane/mask/address logic.
    x, y = [value.double() for value in inputs]
    if case == 'coupled_logistic':
        a, b = x.clone(), y.clone()
        for _ in range(count):
            a, b = 0.5 * a * (1 - a) + y.new_tensor(0.125) * b, 0.625 * b + 0.25 * a + 0.03125
        return a + b / 2
    value = x.clone()
    for k in range(count):
        value = value / 2 + torch.roll(x, -(k + 1)) / 4 - torch.roll(y, k + 1) / 8
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=['coupled_logistic', 'neighbor_accumulation'], required=True)
    parser.add_argument('--backend', choices=['nvidia', 'enflame', 'ascend'], required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--shape-index', type=int, choices=[0, 1], required=True)
    parser.add_argument('--config-index', type=int, choices=[0, 1], required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--startup-ledger', required=True)
    args = parser.parse_args()
    with open(args.startup_ledger, 'a') as stream:
        stream.write(json.dumps({'pid': os.getpid(), 'case': args.case}) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    device = torch.device(args.device)
    runtime = getattr(torch, device.type)
    runtime.set_device(device)
    n, block = [512, 517][args.shape_index], [128, 256][args.config_index]
    indices = torch.arange(n, dtype=torch.float64, device='cpu')
    host = [(((indices * 13 + 3) % 97 - 48) / 128 + 0.25).float(),
            (((indices * 17 + 11) % 89 - 44) / 128 + 0.125).float()]
    inputs = [value.to(device) for value in host]
    input_hashes = [digest(value) for value in inputs]
    backing = torch.full((n + 2 * GUARD,), CANARY, dtype=torch.float32, device=device)
    output = backing[GUARD:-GUARD]
    output.fill_(0.375)
    seed_hash = digest(output)
    expected = torch.full((n,), 0.375, dtype=torch.float64, device='cpu')
    steps = torch.zeros((1,), dtype=torch.int32, device=device)
    calls = []
    grid = (triton.cdiv(n, block),)
    for count in [2, 5]:
        delta = cpu_delta(args.case, host, count)
        witness = float(delta.abs().max())
        assert witness > 0.01, 'inputs must expose duplicated mathematical execution'
        expected = expected + delta
        steps.copy_(torch.tensor([count], dtype=torch.int32, device=device))
        started = time.perf_counter()
        compiled = globals()[args.case][grid](*inputs, output, steps, n, block, num_warps=4)
        runtime.synchronize()
        elapsed = time.perf_counter() - started
        actual = output.cpu().double()
        torch.testing.assert_close(actual, expected, atol=3e-5, rtol=3e-5)
        assert [digest(value) for value in inputs] == input_hashes, 'input mutation'
        assert int(steps.cpu()[0]) == count, 'runtime-bound input mutation'
        assert bool((backing[:GUARD] == CANARY).all()) and bool((backing[-GUARD:] == CANARY).all()), 'output canary'
        calls.append({'call_index': len(calls), 'runtime_steps': count,
                      'compiled_kernel_hash': str(getattr(compiled, 'hash', '')),
                      'compile_launch_sync_wall_s': elapsed, 'max_abs_error': float((actual - expected).abs().max()),
                      'output_sha256': digest(output), 'non_idempotence_witness_max_abs': witness,
                      'atol': 3e-5, 'rtol': 3e-5, 'input_unchanged': True, 'canaries': True})
    assert calls[0]['compiled_kernel_hash'] and calls[0]['compiled_kernel_hash'] == calls[1]['compiled_kernel_hash'], 'runtime bounds recompiled'
    receipt = {'schema': 'flagprism-usability-workload-v1', 'revision': 'Q4-dynamic-reserve',
               'case': args.case, 'backend': args.backend, 'device': str(device),
               'shape_index': args.shape_index, 'config_index': args.config_index, 'shape': [n],
               'config': {'B': block, 'num_warps': 4}, 'grid': list(grid), 'input_sha256': input_hashes,
               'output_initial_sha256': seed_hash, 'calls': calls, 'requested_launches': 2,
               'sideeffect_protocol': 'per-element output consumes prior state; CPU oracle requires exactly one update per call',
               'torch_path': torch.__file__, 'triton_path': triton.__file__, 'pid': os.getpid()}
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
