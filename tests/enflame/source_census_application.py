"""Ordinary runtime-gated vector accumulations; no internal annotations."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
import torch_gcu
import triton
import triton.language as tl


@triton.jit(do_not_specialize=['Steps', 'ActiveProgram'])
def weighted_visits(X, Y, N: tl.constexpr, Steps, ActiveProgram,
                    B: tl.constexpr):
    program = tl.program_id(0)
    if program == ActiveProgram:
        for step in range(Steps):
            offset = program * B + tl.arange(0, B)
            x = tl.load(X + offset, offset < N, other=0)
            previous = tl.load(Y + offset, offset < N, other=0)
            updated = previous + x * 0.25 + 0.03125
            tl.store(Y + offset, updated, offset < N)


@triton.jit(do_not_specialize=['Steps'])
def cubic_visits(X, Y, Activation, N: tl.constexpr, Steps, B: tl.constexpr):
    program = tl.program_id(0)
    active = tl.load(Activation + program)
    if active != 0:
        iteration = 0
        while iteration < Steps:
            offset = program * B + tl.arange(0, B)
            x = tl.load(X + offset, offset < N, other=0)
            previous = tl.load(Y + offset, offset < N, other=0)
            contribution = x * x * x * 0.125 + (program + 1) * 0.015625
            tl.store(Y + offset, previous + contribution, offset < N)
            iteration += 1


def digest(tensor):
    return hashlib.sha256(tensor.contiguous().numpy().tobytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    parser.add_argument('--all-false', action='store_true')
    parser.add_argument('--shift-active', action='store_true')
    parser.add_argument('--witness', action='store_true')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.gcu.set_device(0)
    n, block, programs = 717, 64, 13
    host_x = ((torch.arange(n + 8, dtype=torch.float32) % 17) - 8) / 16
    initial = torch.full((n + 8, ), -113., dtype=torch.float32)
    host_activation = torch.zeros(programs, dtype=torch.int32)
    weighted_active = 12 if args.all_false else (9 if args.shift_active else 7)
    cubic_active = [12] if args.all_false else (
        [9, 11] if args.shift_active else [7, 11])
    host_activation[cubic_active] = 1
    x = host_x.to('gcu')
    y = initial.to('gcu')
    activation = host_activation.to('gcu')
    rows = []
    for name, kernel, steps_list, active in [
        ('weighted', weighted_visits, [2, 5], [weighted_active]),
        ('cubic', cubic_visits, [3, 6], cubic_active)
    ]:
        binaries = []
        for steps in steps_list:
            y.copy_(initial.to('gcu'))
            expected = initial.clone()
            repeats = 2 if args.witness else 1
            for repeat in range(repeats):
                if name == 'weighted':
                    compiled = kernel[(programs, )](x,
                                                    y,
                                                    n,
                                                    steps,
                                                    weighted_active,
                                                    block,
                                                    num_warps=4)
                else:
                    compiled = kernel[(programs, )](x,
                                                    y,
                                                    activation,
                                                    n,
                                                    steps,
                                                    block,
                                                    num_warps=4)
                for program in active:
                    lo, hi = program * block, min(n, (program + 1) * block)
                    if lo >= hi:
                        continue
                    values = host_x[lo:hi]
                    for iteration in range(steps):
                        if name == 'weighted':
                            expected[lo:hi] = expected[
                                lo:hi] + values * 0.25 + 0.03125
                        else:
                            contribution = values * values * values * 0.125 + (
                                program + 1) * 0.015625
                            expected[lo:hi] = expected[lo:hi] + contribution
            torch.gcu.synchronize()
            actual = y.cpu()
            torch.testing.assert_close(actual, expected, rtol=1e-6, atol=1e-5)
            assert torch.equal(actual[n:], initial[n:])
            assert torch.equal(x.cpu(), host_x)
            assert torch.equal(activation.cpu(), host_activation)
            binaries.append(compiled.hash)
            rows.append({
                'kernel': name,
                'steps': steps,
                'active_programs': active,
                'binary': compiled.hash,
                'explicit_calls': repeats,
                'input_sha256': digest(host_x),
                'activation_sha256': digest(host_activation),
                'output_sha256': digest(actual),
                'expected_sha256': digest(expected),
                'math_input_canary_pass': True
            })
        assert len(
            set(binaries)) == 1, 'runtime trip count changed compiled binary'
    (output / 'result.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))
    print('application-executed explicit_calls=' +
          str(sum(r['explicit_calls'] for r in rows)))


if __name__ == '__main__':
    main()
