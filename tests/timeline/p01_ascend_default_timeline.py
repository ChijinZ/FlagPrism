"""Actual default Ascend raw collection on ordinary, unannotated kernels."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
from unittest.mock import patch

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler
from flagtree.profiler.timeline_runtime import retained_owner_statuses


@triton.jit
def recurrence(x, out, state, iterations, N: tl.constexpr):
    i = tl.program_id(0) * 256 + tl.arange(0, 256)
    mask = i < N
    value = tl.load(x + i, mask, 0)
    k = tl.load(iterations)
    for _ in range(k):
        value = value * 1.001 + 0.01
    tl.store(out + i, value, mask)
    old = tl.load(state + i, mask, 0)
    tl.store(state + i, old + 1, mask)


@triton.jit
def softmax(x, out, N: tl.constexpr, B: tl.constexpr):
    row = tl.program_id(0)
    i = tl.arange(0, B)
    values = tl.load(x + row * N + i, i < N, float('-inf'))
    numerator = tl.exp(values - tl.max(values, 0))
    result = numerator / tl.sum(numerator, 0)
    tl.store(out + row * N + i, result, i < N)


def inspect_capture(bundle):
    directory = bundle / 'timeline'
    index = json.loads((directory / 'index.json').read_text())
    results = []
    for row in index['captures']:
        capture = json.loads((directory / row['capture_file']).read_text())
        raw = (directory / capture['raw_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != capture['raw_sha256']:
            raise RuntimeError('Raw identity changed')
        guard_info = capture['readback_guard']
        guard = (directory / guard_info['file']).read_bytes()
        if guard != bytes([165]) * 128:
            raise RuntimeError('Actual guard was not durably retained')
        batch = json.loads((directory / capture['events_file']).read_text())
        if not batch['events'] or len(batch['sites']) < 2:
            raise RuntimeError('Default capture has no internal structure')
        for record in batch['records']:
            if struct.unpack_from('<Q', raw,
                                  record['offset'])[0] != record['tick']:
                raise RuntimeError('Canonical tick differs from raw field')
        actual = [o for o in batch['observers'] if o['retained_records']]
        if len(actual) < 2:
            raise RuntimeError('Actual first/last program did not both record')
        results.append(
            dict(invocation_id=row['invocation_id'],
                 binary_id=row['binary_id'],
                 intervals=len(batch['events']),
                 endpoint_references=len(batch['records']),
                 observed_programs=[o['program_coordinates'] for o in actual],
                 unobserved_actors=sum(
                     o['attributes']['ascend.writer_state'] == 'unobserved'
                     for o in batch['observers']),
                 occurrences=sorted(
                     Counter(e['site_id'] for e in batch['events']).values())))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    n = 1027
    cpu = torch.linspace(-0.5, 0.5, n + 7)
    x = cpu.npu()
    refs = {}
    for k in (3, 7):
        v = cpu[:n].clone()
        for _ in range(k):
            v = v * 1.001 + 0.01
        refs[k] = v
    baseline = []
    for k in (3, 7):
        out = torch.full_like(x, 1234)
        state = torch.zeros(n + 7, dtype=torch.int32, device=x.device)
        iterations = torch.tensor([k], dtype=torch.int32, device=x.device)
        kernel = recurrence[(5, )](x,
                                   out,
                                   state,
                                   iterations,
                                   n,
                                   enable_auto_blockify=False)
        torch.npu.synchronize()
        torch.testing.assert_close(out[:n].cpu(),
                                   refs[k],
                                   rtol=1e-5,
                                   atol=1e-6)
        baseline.append(kernel.hash)
    streams = [torch.npu.current_stream(), torch.npu.Stream()]
    session = profiler.start(str(a.output / 'recurrence'),
                             backend='cann',
                             detail='timeline')
    values = []
    try:
        for stream, k in zip(streams, (3, 7)):
            with torch.npu.stream(stream):
                out = torch.full_like(x, 1234)
                state = torch.zeros(n + 7, dtype=torch.int32, device=x.device)
                iterations = torch.tensor([k],
                                          dtype=torch.int32,
                                          device=x.device)
                with patch.object(
                        torch.npu,
                        'synchronize',
                        side_effect=RuntimeError(
                            'unexpected per-launch global synchronization')):
                    kernel = recurrence[(5, )](x,
                                               out,
                                               state,
                                               iterations,
                                               n,
                                               enable_auto_blockify=False)
                values.append((out, state, k, kernel.hash))
        # Finalization must complete and retain each original stream's owner.
    finally:
        profiler.finalize(session)
    for out, state, k, _ in values:
        torch.testing.assert_close(out[:n].cpu(),
                                   refs[k],
                                   rtol=1e-5,
                                   atol=1e-6)
        if not bool((state[:n].cpu() == 1).all()) or not bool(
            (state[n:].cpu() == 0).all()) or not bool(
                (out[n:].cpu() == 1234).all()):
            raise RuntimeError('State or mathematical tail changed')
    if not torch.equal(
            x.cpu(),
            cpu) or baseline[0] != baseline[1] or values[0][3] != values[1][3]:
        raise RuntimeError('Input or runtime-K binary invariant changed')
    matrix = torch.linspace(-2, 2, 3 * 257).reshape(3, 257)
    source = matrix.npu()
    out = torch.empty_like(source)
    softmax[(3, )](source, out, 257, 512, enable_auto_blockify=False)
    torch.npu.synchronize()
    torch.testing.assert_close(out.cpu(),
                               torch.softmax(matrix, dim=1),
                               rtol=2e-4,
                               atol=1e-6)
    session = profiler.start(str(a.output / 'softmax'),
                             backend='cann',
                             detail='timeline')
    try:
        softmax[(3, )](source, out, 257, 512, enable_auto_blockify=False)
    finally:
        profiler.finalize(session)
    torch.testing.assert_close(out.cpu(),
                               torch.softmax(matrix, dim=1),
                               rtol=2e-4,
                               atol=1e-6)
    if retained_owner_statuses():
        raise RuntimeError('Completed capture retained a device owner')
    result = dict(status='public_raw_default_math_passed_not_P01',
                  recurrence=inspect_capture(a.output / 'recurrence'),
                  softmax=inspect_capture(a.output / 'softmax'),
                  boundary_status='unverified',
                  clock_status='unverified')
    (a.output / 'result.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__': main()
