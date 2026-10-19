"""Actual default vector/mixed participant coverage, using existing C1/C2 math.

One ordinary and one profiled invocation per case. No performance claim or
application instrumentation; original raw topology words are checked directly.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
from flagtree import profiler


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def inspect(bundle, expected_count):
    root = bundle / 'timeline'
    index = json.loads((root / 'index.json').read_text())
    need(
        len(index['captures']) == 1,
        'Expected exactly one profiled invocation')
    capture = json.loads(
        (root / index['captures'][0]['capture_file']).read_text())
    raw = (root / capture['raw_file']).read_bytes()
    need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Raw changed')
    guard = capture['readback_guard']
    need((root / guard['file']).read_bytes() == bytes([165]) * 128,
         'Physical allocation guard changed')
    batch = json.loads((root / capture['events_file']).read_text())
    need(batch['complete'], 'Actual default capture is incomplete')
    sites = {s['id']: s for s in batch['sites']}
    positive_source_sites = {
        e['site_id']
        for e in batch['events'] if e['end_tick'] > e['start_tick']
        and 'ascend.native_operation' not in sites[e['site_id']]['attributes']
    }
    need(
        len(positive_source_sites) >= 2,
        'Fewer than two actual positive source fragment sites')
    need(capture.get('counter_ns_exports'), 'Missing actual counter-ns trace')
    layout = capture['owner']['layout']
    stride = layout['scratch_size']
    expected_slots = [1] if expected_count == 1 else [0, 1, 2]
    need(
        len(batch['observers']) == len(layout['programs']) *
        len(expected_slots), 'Canonical participant denominator differs')
    headers = []
    for physical_slot, program in enumerate(layout['programs']):
        for actor in range(3):
            base = (physical_slot * 3 + actor) * stride
            segment = raw[base:base + stride]
            if actor not in expected_slots:
                need(not any(segment), 'Unselected raw segment is not zero')
                continue
            header = struct.unpack_from('<8Q', raw, base)
            count = header[7] >> 8
            need(count == (1 if actor == 0 else expected_count),
                 'Device subblock count differs from expected execution mode')
            need(
                header[4] == program and header[5] == actor and header[7] & 1
                and not header[7] & ~0x307,
                'Actual publisher identity or flags differ')
            headers.append(
                dict(program=program,
                     actor=actor,
                     count=count,
                     flags=header[7],
                     offset=base))
    for record in batch['records']:
        need(
            struct.unpack_from('<Q', raw,
                               record['offset'])[0] == record['tick'],
            'Canonical timestamp is not its actual raw word')
    return dict(invocation_id=index['captures'][0]['invocation_id'],
                binary_id=capture['owner']['binary_id'],
                raw_sha256=capture['raw_sha256'],
                headers=headers,
                observers=len(batch['observers']),
                events=len(batch['events']),
                positive_source_sites=sorted(positive_source_sites),
                complete=batch['complete'],
                ns_exports=capture['counter_ns_exports'],
                bundle=str(bundle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    spec = importlib.util.spec_from_file_location(
        'participation_existing_C1_C2',
        Path(__file__).with_name('p01_controlled_workloads.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    recurrence, product = module.create_kernels()
    results = []
    for case in ('vector', 'mixed'):
        folder = args.output / case
        folder.mkdir()
        for profiled in (False, True):
            if case == 'vector':
                cpu = torch.linspace(-2, 2, 257)
                x = cpu.npu()
                y = torch.full((261, ), -17.25, device='npu:4')
                state = torch.zeros(257, dtype=torch.int32, device='npu:4')
                steps_cpu = torch.tensor([3], dtype=torch.int32)
                steps = steps_cpu.npu()
                launch = lambda: recurrence[
                    (3, )](x, y, state, steps, 257, 128, num_warps=4)
                reference = cpu.clone()
                for _ in range(3):
                    reference = reference * 0.75 + 0.125
                inputs = [(x, cpu), (steps, steps_cpu)]
                tolerance = 2e-6
            else:
                left = torch.linspace(-0.5, 0.5, 64 * 192).reshape(64,
                                                                   192).half()
                right = torch.linspace(0.5, -0.25,
                                       192 * 64).reshape(192, 64).half()
                x, b = left.npu(), right.npu()
                y = torch.full((4100, ), -17.25, device='npu:4')
                state = torch.zeros(4096, dtype=torch.int32, device='npu:4')
                launch = lambda: product[(2, 2)](
                    x, b, y, state, 64, 64, 192, 32, num_warps=4, num_stages=1)
                reference = (left.float() @ right.float()).reshape(-1)
                inputs = [(x, left), (b, right)]
                tolerance = 2e-3
            bundle = folder / 'capture'
            session = profiler.start(str(bundle),
                                     detail='timeline') if profiled else None
            try:
                kernel = launch()
            finally:
                if session is not None:
                    profiler.finalize(session)
            torch.npu.synchronize()
            need(
                torch.allclose(y[:reference.numel()].cpu(),
                               reference,
                               rtol=tolerance,
                               atol=tolerance), 'Math changed')
            need(
                torch.equal(y[reference.numel():].cpu(),
                            torch.full((4, ), -17.25)), 'Output tail changed')
            need(torch.equal(state.cpu(), torch.ones_like(state.cpu())),
                 'Original mathematical invocation replayed or missed')
            need(
                all(
                    torch.equal(value.cpu(), before)
                    for value, before in inputs), 'Application input changed')
            row = dict(case=case,
                       profiled=profiled,
                       binary_id=kernel.hash,
                       math_passed=True,
                       original_calls=1)
            if profiled:
                row['capture'] = inspect(bundle, 1 if case == 'vector' else 2)
            results.append(row)
            (args.output / 'progress.json').write_text(
                json.dumps(results, indent=2))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='actual_vector_and_mixed_runtime_participation_passed',
            calls=results,
            performance_measured=False),
                   indent=2))


if __name__ == '__main__':
    main()
