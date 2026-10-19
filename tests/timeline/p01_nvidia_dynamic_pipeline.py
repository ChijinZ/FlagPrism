"""Real runtime-K GEMM to inspect ordinary/profile pipeline preservation.

No scope, site, internal compiler API or custom allocator. This is a development
case, not an independent qualifier or a performance/overhead measurement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import torch
import triton
import triton.language as tl
from flagtree import profiler


def need(value, message):
    if not value:
        raise RuntimeError(message)


@triton.jit
def runtime_gemm(A, B, C, KInput, Calls, M: tl.constexpr, N: tl.constexpr,
                 STRIDE: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr,
                 BK: tl.constexpr):
    row = tl.program_id(0) * BM + tl.arange(0, BM)
    col = tl.program_id(1) * BN + tl.arange(0, BN)
    kk = tl.arange(0, BK)
    k = tl.load(KInput)
    acc = tl.full((BM, BN), 0, tl.float32)
    for tile in range(tl.cdiv(k, BK)):
        ix = tile * BK + kk
        av = tl.load(A + row[:, None] * STRIDE + ix[None, :],
                     (row[:, None] < M) & (ix[None, :] < k), 0)
        bv = tl.load(B + ix[:, None] * N + col[None, :],
                     (ix[:, None] < k) & (col[None, :] < N), 0)
        acc += tl.dot(av, bv)
    tl.store(C + row[:, None] * N + col[None, :], acc,
             (row[:, None] < M) & (col[None, :] < N))
    # Scalar atomic has one logical update per program; no non-atomic
    # multi-writer read/modify/write is used as a replay oracle.
    pid = tl.program_id(0) * tl.num_programs(1) + tl.program_id(1)
    tl.atomic_add(Calls + pid, 1, sem='relaxed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--site-budget', type=int)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability() == (12, 0), 'Wrong target')
    torch.manual_seed(32046)
    m, n, maximum = 64, 64, 224
    acpu = torch.randn((m, maximum), dtype=torch.float16)
    bcpu = torch.randn((maximum, n), dtype=torch.float16)
    a, b = acpu.cuda(), bcpu.cuda()
    cases, hashes = [], []
    for phase in ('ordinary', 'profile'):
        session = None
        if phase == 'profile':
            options = {} if args.site_budget is None else dict(
                timeline_max_sites=args.site_budget)
            session = profiler.start(str(args.output / 'profile'),
                                     detail='timeline',
                                     **options)
        try:
            for tiles in (3, 7):
                k = tiles * 32
                ki = torch.tensor([k], device='cuda', dtype=torch.int32)
                out = torch.full((m * n + 7, ), 1234., device='cuda')
                calls = torch.zeros((4, ), device='cuda', dtype=torch.int32)
                compiled = runtime_gemm[(2, 2)](a,
                                                b,
                                                out,
                                                ki,
                                                calls,
                                                m,
                                                n,
                                                maximum,
                                                32,
                                                32,
                                                32,
                                                num_warps=4,
                                                num_stages=3)
                observed = out[:m * n].cpu().reshape(m, n).double()
                reference = acpu[:, :k].double() @ bcpu[:k].double()
                need(torch.allclose(observed, reference, rtol=1e-2, atol=1e-2),
                     phase + ' GEMM numerical error')
                need(torch.equal(out[m * n:].cpu(), torch.full((7, ), 1234.)),
                     phase + ' output guard changed')
                need(calls.cpu().tolist() == [1] * 4,
                     phase + ' requested invocation count changed')
                need(
                    torch.equal(a.cpu(), acpu) and torch.equal(b.cpu(), bcpu),
                    phase + ' input changed')
                folder = args.output / (phase + '-' + str(tiles))
                folder.mkdir()
                artifacts = {}
                for name, value in compiled.asm.items():
                    if not isinstance(value, (str, bytes)):
                        continue
                    raw = value.encode() if isinstance(value, str) else value
                    path = folder / name
                    path.write_bytes(raw)
                    artifacts[name] = dict(
                        file=str(path),
                        bytes=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest())
                if phase == 'ordinary':
                    ptx = compiled.asm['ptx']
                    need(
                        'cp.async' in ptx and '%globaltimer' not in ptx,
                        'Ordinary case lacks async or is already instrumented')
                    hashes.append(compiled.hash)
                cases.append(
                    dict(phase=phase,
                         tiles=tiles,
                         k=k,
                         binary_hash=compiled.hash,
                         math=True,
                         calls=calls.cpu().tolist(),
                         artifacts=artifacts))
                (args.output / 'cases.json').write_text(
                    json.dumps(cases, indent=2))
        finally:
            if session is not None:
                profiler.finalize(session)
    need(
        len(set(hashes)) == 1,
        'Runtime K unexpectedly specialized ordinary binary')
    directory = args.output / 'profile/timeline'
    index = json.loads((directory / 'index.json').read_text())
    need(len(index['captures']) == 2, 'Wrong profile invocation count')
    summaries = []
    for row in index['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(directory / row['capture_file'])
        facts = json.loads((directory / capture['async_file']).read_text())
        batch = json.loads((directory / capture['events_file']).read_text())
        need(batch['complete'] and facts['groups'], 'Incomplete async capture')
        need(
            capture.get('counter_ns_status', {}).get('status')
            == 'counter_unit_only' and capture.get('counter_ns_exports'),
            'Default timeline did not export actual observer traces')
        summaries.append(
            dict(invocation_id=row['invocation_id'],
                 binary_id=row['binary_id'],
                 intervals=len(batch['events']),
                 groups=len(facts['groups']),
                 generations=facts['shared_view_generations'],
                 loads=facts['shared_view_loads']))
    need(
        len({r['binary_id']
             for r in summaries}) == 1,
        'Runtime K unexpectedly specialized profile binary')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'runtime_K_public_math_and_async_records_passed_schedule_not_yet_qualified',
            python=sys.executable,
            implementation='actual installed wheel; no source overlay',
            explicit_ordinary_calls=2,
            explicit_profile_calls=2,
            performance_measured=False,
            site_budget=args.site_budget,
            captures=summaries),
                   indent=2))


if __name__ == '__main__':
    main()
