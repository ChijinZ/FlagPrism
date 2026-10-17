"""Dedicated clock check: real recurrence inside device-queued event brackets.

This development primitive is not an ordinary-operator qualification, application
profiling, performance/overhead certification, or proof of cross-SM epochs. The
1 ns/tick hypothesis and gate are fixed before acquisition; no endpoint fitting.
Final machine ordering must be inspected separately before clock qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def require(value, message):
    if not value:
        raise RuntimeError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    registration = {
        'target': 'cuda:120', 'device': 0, 'programs': 1, 'block': 128,
        'runtime_k': [4096, 16384, 65536], 'repetitions': 3,
        'requested_math_launches': 9, 'explicit_compile_only': True,
        'bracket': 'explicit_calibration_graph_external_event_nodes',
        'capture_must_execute_no_math': True,
        'candidate_period_numerator_ns': 1, 'candidate_period_denominator': 1,
        'event_minus_internal_allowance_ns': 10000,
        'event_relative_allowance_numerator': 2,
        'event_relative_allowance_denominator': 100,
        'rtol': 2e-6, 'atol': 2e-6,
        'scope': 'scale consistency only, not a frequency/epoch certificate',
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    write_json(args.output / 'registration.json', registration)
    stat = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
    write_json(args.output / 'started.json', {
        'pid': os.getpid(), 'pgid': os.getpgid(0),
        'startticks': int(stat[19]), 'argv': sys.argv,
    })
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def clock_math(X, Y, T, State, K, BLOCK: tl.constexpr):
        index = tl.arange(0, BLOCK)
        value = tl.load(X + index)
        k = tl.load(K)
        begin = tl.inline_asm_elementwise(
            'mov.u64 $0, %globaltimer;', constraints='=l', args=[],
            dtype=tl.uint64, is_pure=False, pack=1)
        end = tl.full((), 0, tl.uint64)
        # The start controls the math path; the end consumes its actual result.
        # These dependencies are deliberate but still require final-ISA audit.
        if begin != 0:
            for _ in range(k):
                value = value * 0.75 + 0.125
            checksum = tl.sum(value, 0)
            if checksum > 0:
                end = tl.inline_asm_elementwise(
                    'mov.u64 $0, %globaltimer;', constraints='=l', args=[],
                    dtype=tl.uint64, is_pure=False, pack=1)
        tl.store(Y + index, value)
        tl.store(T, begin)
        tl.store(T + 1, end)
        # One scalar writer. Increment, rather than assign, detects replay.
        old = tl.load(State)
        tl.store(State, old + 1)

    torch.cuda.set_device(0)
    require(torch.cuda.get_device_capability(0) == (12, 0),
            'Registered target differs from the actual device')
    torch.manual_seed(8617)
    x_cpu = torch.rand(128, dtype=torch.float32) + 0.25
    x = x_cpu.cuda()
    y = torch.full((130,), -911.0, device='cuda', dtype=torch.float32)
    stamps = torch.zeros(2, device='cuda', dtype=torch.int64)
    state = torch.zeros((), device='cuda', dtype=torch.int32)
    k_device = torch.full((), 4096, device='cuda', dtype=torch.int32)
    # Compile/load explicitly; no warmup kernel or hidden extra math launch.
    compiled = clock_math.warmup(x, y, stamps, state, k_device, BLOCK=128,
                                grid=(1,), num_warps=4)
    compiled._init_handles()
    artifacts = []
    for kind, data in compiled.asm.items():
        if isinstance(data, str):
            data = data.encode()
        if not isinstance(data, bytes):
            continue
        target = args.output / ('clock-math.' + kind)
        target.write_bytes(data)
        artifacts.append({'path': target.name, 'bytes': len(data),
                          'sha256': hashlib.sha256(data).hexdigest()})
    write_json(args.output / 'compiled-artifacts.json', artifacts)
    before = torch.cuda.Event(enable_timing=True, external=True)
    after = torch.cuda.Event(enable_timing=True, external=True)
    graph = torch.cuda.CUDAGraph()
    capture_stream = torch.cuda.Stream()
    torch.cuda.synchronize()
    with torch.cuda.graph(graph, stream=capture_stream):
        before.record()
        captured = clock_math[(1,)](x, y, stamps, state, k_device,
                                   BLOCK=128, num_warps=4)
        after.record()
    torch.cuda.synchronize()
    require(captured is compiled, 'Capture changed the compiled object')
    require(state.item() == 0, 'Graph capture unexpectedly executed math')
    write_json(args.output / 'capture.json', {
        'math_executions_after_capture': state.item(),
        'external_event_nodes': True, 'application_replay': False,
        'purpose': 'dedicated clock primitive, not public graph support',
    })
    calls = []
    for k in registration['runtime_k']:
        for repetition in range(3):
            k_device.fill_(k)
            torch.cuda.synchronize()
            lo = time.monotonic_ns()
            # One explicit graph launch contains one real mathematical kernel.
            # Device event nodes eliminate host enqueue gaps from the bracket.
            graph.replay()
            after.synchronize()
            hi = time.monotonic_ns()
            raw = stamps.cpu().tolist()
            observed = y.cpu()
            expected = 0.5 + (0.75 ** k) * (x_cpu - 0.5)
            elapsed_ms = before.elapsed_time(after)
            event_ns = round(elapsed_ms * 1000000)
            ticks = raw[1] - raw[0]
            allowance = max(10000, (event_ns * 2 + 99) // 100)
            row = {'runtime_k': k, 'repetition': repetition,
                   'raw_start_tick': raw[0], 'raw_end_tick': raw[1],
                   'tick_delta': ticks, 'event_elapsed_ms': elapsed_ms,
                   'event_elapsed_ns_rounded': event_ns,
                   'candidate_internal_ns': ticks,
                   'event_allowance_ns': allowance,
                   'host_before_ns': lo, 'host_after_ns': hi,
                   'binary_sha256': hashlib.sha256(compiled.asm['cubin']).hexdigest(),
                   'state': state.item()}
            calls.append(row)
            write_json(args.output / 'calls.json', calls)
            require(torch.allclose(observed[:128], expected, rtol=2e-6, atol=2e-6),
                    'Real recurrence disagrees with the frozen CPU oracle')
            require(torch.equal(x.cpu(), x_cpu), 'Input changed')
            require(observed[128:].tolist() == [-911.0, -911.0], 'Output tail changed')
            require(state.item() == len(calls), 'Requested launch count changed')
            require(0 < raw[0] < raw[1], 'Nonpositive timer interval')
            require(event_ns > 0 and ticks <= hi - lo,
                    'Candidate duration exceeds independent host bound')
            require(abs(event_ns - ticks) <= allowance,
                    '1ns hypothesis is inconsistent with CUDA Event bracket')
    write_json(args.output / 'result.json', {
        'status': 'clock_scale_consistency_passed_not_certified',
        'registration': registration, 'calls': calls, 'artifacts': artifacts,
        'device': torch.cuda.get_device_name(0), 'torch': torch.__version__,
        'triton': triton.__version__, 'cuda_runtime': torch.version.cuda,
        'limits': ['not automatic profiling qualification',
                   'device bracket includes kernel prologue/epilogue and event-node gap',
                   'coarse consistency gate is not a fine-grained error bound',
                   'no cross-SM epoch or clock-drift proof',
                   'inspect actual SASS dependencies before boundary claims'],
    })


if __name__ == '__main__':
    main()
