"""Development evidence for bounded late-LLVM automatic checkpoint budgets.

Two ordinary programs intentionally exercise different compiler-generated loops.
This is an engineering regression, not an independent acceptance holdout.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import time

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler


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
            payload = json.loads((target / 'ai/observations.json').read_text())
            events = payload['observations']
            assert events and all(e['association_status'] == 'verified'
                                  for e in events)
            positions = {(e['compiler_site']['source_file'],
                          e['compiler_site']['line'])
                         for e in events}
            assert len(positions) >= 2
            captures = payload['captures']
            dropped = sum(c['dropped'] for c in captures)
            raw_headers = []
            capacity = compiled.metadata.flagprism_ascend_trace_capacity
            for capture in captures:
                raw = base64.b64decode(capture['raw_base64'])
                assert hashlib.sha256(raw).hexdigest() == capture['raw_sha256']
                for actor in range(3):
                    version, committed, attempted, lost = struct.unpack_from(
                        '<4Q', raw, actor * (32 + capacity * 64))
                    assert version in (0, 1) and committed <= capacity
                    assert attempted == committed + lost
                    decoded = capture['actors'][actor]
                    assert (committed, attempted,
                            lost) == tuple(decoded[k]
                                           for k in ('committed', 'attempted',
                                                     'dropped'))
                    raw_headers.append(
                        dict(actor=actor,
                             version=version,
                             committed=committed,
                             attempted=attempted,
                             dropped=lost))
            assert sum(h['committed'] for h in raw_headers) == len(events)
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
                       raw_headers=raw_headers,
                       capacity=capacity,
                       event_count=len(events),
                       dropped=dropped,
                       source_positions=sorted(positions),
                       frequencies={
                           str(k): v
                           for k, v in Counter(
                               (e['actor_slot'], e['site'], e['semantic'])
                               for e in events).items()
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
            if not args.expect_loss:
                assert dropped == 0, f'{kind}: default capacity lost {dropped} records'
    if args.expect_loss:
        assert any(
            r['dropped']
            for r in rows), 'did not reproduce the original default loss'
    for kind in ('recurrence', 'nested_memory'):
        assert len({r['binary'] for r in rows if r['kind'] == kind}) == 1
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
