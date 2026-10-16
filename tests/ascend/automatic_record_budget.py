"""Development evidence for bounded default automatic census storage.

Two ordinary programs intentionally exercise different compiler-generated loops.
This is an engineering regression, not an independent acceptance holdout.
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

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_census_assertions import validate_bundle as validate_census_bundle


@triton.jit
def recurrence(x, y, out, launches, rounds, n: tl.constexpr, b: tl.constexpr):
    i = tl.arange(0, b)
    a = tl.load(x + i, i < n, 0)
    delta = tl.load(y + i, i < n, 0)
    step = 0
    while step < rounds:
        a = a * 0.5 + delta
        step += 1
    tl.store(out + i, a, i < n)
    tl.store(launches, tl.load(launches) + 1)


@triton.jit
def nested_memory(x, y, out, launches, rounds, n: tl.constexpr,
                  b: tl.constexpr):
    i = tl.arange(0, b)
    a = tl.load(x + i, i < n, 0)
    for outer in range(rounds):
        for inner in range(2):
            delta = tl.load(y + i, i < n, 0)
            a = a + delta * (inner + 1)
        tl.store(out + i, a, i < n)
    tl.store(launches, tl.load(launches) + 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--device', type=int, default=4)
    p.add_argument('--expect-loss', action='store_true')
    p.add_argument('--rounds', type=int, nargs='+', default=[64, 128])
    args = p.parse_args()
    if args.expect_loss:
        p.error(
            "--expect-loss describes the historical checkpoint ring; default census asserts exact counters instead"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(args.device)
    device = f'npu:{args.device}'
    n, b = 257, 512
    cx = torch.arange(n, dtype=torch.float32) / 32
    cy = torch.full((n, ), .25)
    x, y = cx.to(device), cy.to(device)
    rows = []
    for kind, fn in [('recurrence', recurrence),
                     ('nested_memory', nested_memory)]:
        for rounds in args.rounds:
            storage = torch.full((n + 32, ), -12345., device=device)
            out = storage[16:-16]
            launches = torch.zeros((), dtype=torch.int32, device=device)
            target = args.output / f'{kind}-{rounds}'
            start = time.monotonic()
            session = profiler.start(str(target),
                                     backend='cann',
                                     detail='auto')
            try:
                compile_start = time.monotonic()
                compiled = fn[(1, )](x, y, out, launches, rounds, n, b)
                torch.npu.synchronize()
                compile_launch_s = time.monotonic() - compile_start
            finally:
                export_start = time.monotonic()
                profiler.finalize(session)
                export_s = time.monotonic() - export_start
            expected = cx.clone()
            for _ in range(rounds):
                expected = expected * .5 + cy if kind == 'recurrence' else expected + cy * 3
            torch.testing.assert_close(out.cpu(), expected)
            torch.testing.assert_close(x.cpu(), cx, rtol=0, atol=0)
            torch.testing.assert_close(y.cpu(), cy, rtol=0, atol=0)
            assert launches.item(
            ) == 1, 'instrumentation replayed the user kernel'
            guards = storage.cpu()
            assert (guards[:16] == -12345.).all() and (guards[-16:]
                                                       == -12345.).all()
            payload, cells, summaries, fine = validate_census_bundle(
                target, 'ascend')
            events = payload['observations']
            assert events
            positions = {(loc['file'], loc['line'])
                         for row in fine['records']
                         for loc in row['source_locations']}
            assert len(positions) >= 2
            # Storage is bounded by physical actor/site cells rather than loop
            # event capacity; repeated visits remain actual integer counts.
            primary = [e for e in events if e['site_role'] == 'primary']
            assert any(e['count'] in (rounds, 2 * rounds) for e in primary)
            bundle_bytes = sum(f.stat().st_size for f in target.rglob('*')
                               if f.is_file())
            row = dict(kind=kind,
                       rounds=rounds,
                       pid=os.getpid(),
                       binary=compiled.hash,
                       compile_launch_s=compile_launch_s,
                       export_s=export_s,
                       elapsed_s=time.monotonic() - start,
                       bundle_bytes=bundle_bytes,
                       census=summaries,
                       normalized_rows=len(events),
                       exact=True,
                       source_positions=sorted(positions),
                       source_visit_counts={
                           str((e['actor']['id'], e['site'])): e['count']
                           for e in events
                       },
                       math='passed',
                       inputs='unchanged',
                       canaries='passed',
                       actual_launches=launches.item())
            rows.append(row)
            result = dict(pid=os.getpid(),
                          source_sha256=hashlib.sha256(
                              Path(__file__).read_bytes()).hexdigest(),
                          cases=rows)
            (args.output / 'result.json').write_text(
                json.dumps(result, indent=2))
            assert bundle_bytes <= 64 * 1024**2 and export_s <= 60
    for kind in ('recurrence', 'nested_memory'):
        assert len({r['binary'] for r in rows if r['kind'] == kind}) == 1
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
