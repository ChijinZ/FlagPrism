"""Public auto-mode development oracle. Run in the Ascend Docker on one device.

The kernels contain no profiler calls or extra formals. These are development
programs; they are not independent acceptance holdouts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler

# Also support direct execution of this hardware driver.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_census_assertions import validate_bundle as validate_census_bundle


@triton.jit
def fused(x, y, out, n: tl.constexpr, b: tl.constexpr):
    i = tl.program_id(0) * b + tl.arange(0, b)
    a = tl.load(x + i, i < n, 0)
    v = tl.load(y + i, i < n, 0)
    z = (a * 0.5 + v) * (v - 2.0)
    tl.store(out + i, z, i < n)


@triton.jit
def dynamic(x, y, out, iterations, n: tl.constexpr, b: tl.constexpr):
    i = tl.program_id(0) * b + tl.arange(0, b)
    a = tl.load(x + i, i < n, 0)
    v = tl.load(y + i, i < n, 0)
    for step in range(iterations):
        a = a + v
    tl.store(out + i, a, i < n)


@triton.jit
def reduced(x, out, n: tl.constexpr, b: tl.constexpr):
    i = tl.arange(0, b)
    a = tl.load(x + i, i < n, 0)
    z = tl.sum(a * a, 0)
    tl.store(out, z)


@triton.jit
def matrix(a, b, out, m: tl.constexpr, n: tl.constexpr, k: tl.constexpr):
    rows = tl.arange(0, 32)
    cols = tl.arange(0, 32)
    inner = tl.arange(0, 32)
    left = tl.load(a + rows[:, None] * k + inner[None, :],
                   (rows[:, None] < m) & (inner[None, :] < k), 0)
    right = tl.load(b + inner[:, None] * n + cols[None, :],
                    (inner[:, None] < k) & (cols[None, :] < n), 0)
    product = tl.dot(left, right)
    tl.store(out + rows[:, None] * n + cols[None, :], product,
             (rows[:, None] < m) & (cols[None, :] < n))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', type=int, default=4)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(args.device)
    device = f'npu:{args.device}'
    n, b = 257, 512
    cpu_a = torch.arange(32 * 32,
                         dtype=torch.float32).reshape(32, 32).div(1024).half()
    cpu_b = torch.arange(32 * 32, dtype=torch.float32).reshape(
        32, 32).remainder(17).div(32).half()
    ma, mb = cpu_a.to(device), cpu_b.to(device)
    cpu_x = torch.arange(n, dtype=torch.float32) / 32
    cpu_y = torch.full((n, ), 0.25)
    x, y = cpu_x.to(device), cpu_y.to(device)
    storage = torch.full((n + 32, ), -12345., device=device)
    out = storage[16:-16]
    result = {'pid': os.getpid(), 'status': 'running', 'kernels': []}
    for kind, iterations in [('fused', None), ('dynamic', 2), ('dynamic', 5),
                             ('reduced', None), ('matrix', None)]:
        if kind == 'matrix':
            storage = torch.full((32 * 32 + 32, ), -12345., device=device)
            out = storage[16:-16]
        label = kind + (str(iterations) if iterations else '')
        capture = args.output / label
        start = time.monotonic()
        session = None if args.baseline else profiler.start(
            str(capture), backend='cann', detail='auto')
        compile_start = time.monotonic()
        try:
            if kind == 'fused':
                compiled = fused[(1, )](x, y, out, n, b)
                expected = (cpu_x * .5 + cpu_y) * (cpu_y - 2)
            elif kind == 'dynamic':
                compiled = dynamic[(1, )](x, y, out, iterations, n, b)
                expected = cpu_x + cpu_y * iterations
            elif kind == 'matrix':
                compiled = matrix[(1, )](ma, mb, out, 32, 32, 32)
                expected = (cpu_a.float() @ cpu_b.float()).reshape(-1)
            else:
                compiled = reduced[(1, )](x, out, n, b)
                expected = (cpu_x * cpu_x).sum().reshape(1)
            torch.npu.synchronize()
            compile_launch_s = time.monotonic() - compile_start
        finally:
            export_start = time.monotonic()
            if session is not None:
                profiler.finalize(session)
            export_s = time.monotonic() - export_start
        actual = out[:1] if kind == 'reduced' else out
        torch.testing.assert_close(actual.cpu(), expected)
        guards = storage.cpu()
        assert torch.all(guards[:16] == -12345.) and torch.all(
            guards[-16:] == -12345.)
        torch.testing.assert_close(x.cpu(), cpu_x, atol=0, rtol=0)
        torch.testing.assert_close(y.cpu(), cpu_y, atol=0, rtol=0)
        torch.testing.assert_close(ma.cpu(), cpu_a, atol=0, rtol=0)
        torch.testing.assert_close(mb.cpu(), cpu_b, atol=0, rtol=0)
        observation_summary = None
        if not args.baseline:
            payload, cells, summaries, fine = validate_census_bundle(
                capture, 'ascend')
            events = payload['observations']
            operations = [e for e in events if e['site_role'] == 'primary']
            assert len({(e['actor']['id'], e['site']) for e in events}) >= 2
            positions = {(loc['file'], loc['line'])
                         for row in fine['records']
                         for loc in row['source_locations']}
            assert len(
                positions
            ) >= 2, 'automatic operations lack distinct source regions'
            visits = {
                (e['actor']['id'], e['site']): e['count']
                for e in operations
            }
            # Census retains exact source-control counts, without checkpoint
            # ordering or an interval condition-header occurrence stream.
            if kind == 'dynamic':
                assert iterations in visits.values(
                ), 'runtime operation counts missing'
            observation_summary = {
                'normalized_rows': len(events),
                'source_positions': sorted(positions),
                'operation_visits': {
                    str(k): v
                    for k, v in visits.items()
                },
                'census': summaries,
                'exact': True
            }
        result['kernels'].append({
            'kind':
            kind,
            'iterations':
            iterations,
            'observations':
            observation_summary,
            'binary':
            compiled.hash,
            'compile_launch_s':
            compile_launch_s,
            'export_s':
            export_s,
            'bundle_bytes':
            sum(p.stat().st_size for p in capture.rglob('*') if p.is_file()),
            'elapsed_s':
            time.monotonic() - start,
            'capture':
            str(capture),
            'math':
            'passed',
            'canaries':
            'passed'
        })
        (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    loops = [k for k in result['kernels'] if k['kind'] == 'dynamic']
    assert len({k['binary']
                for k in loops}) == 1, 'runtime iteration argument recompiled'
    result['status'] = 'PASS'
    result['source_sha256'] = hashlib.sha256(
        Path(__file__).read_bytes()).hexdigest()
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
