"""Real default API, repeated specializations/streams and warm-session captures.

Development raw gate only. This does not waive final-machine clock, Perfetto,
async or independent qualifier requirements.
"""
import argparse
import hashlib
import json
from pathlib import Path
import torch
import triton
import triton.language as tl
from flagtree import profiler


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


@triton.jit
def nonlinear(X, Y, Calls, N: tl.constexpr, B: tl.constexpr):
    pid = tl.program_id(0)
    offset = pid * B + tl.arange(0, B)
    value = tl.load(X + offset, offset < N, 0.0)
    result = tl.exp(-value * value) * 0.75 + value * 0.125
    tl.store(Y + offset, result, offset < N)
    tl.atomic_add(Calls + pid, 1, sem='relaxed')


@triton.jit
def row_softmax(X, Y, N: tl.constexpr, B: tl.constexpr):
    row = tl.program_id(0)
    offset = tl.arange(0, B)
    value = tl.load(X + row * N + offset, offset < N, -float('inf'))
    exp = tl.exp(value - tl.max(value, 0))
    result = exp / tl.sum(exp, 0)
    tl.store(Y + row * N + offset, result, offset < N)


def inspect(folder, expected):
    timeline = folder / 'timeline'
    index = json.loads((timeline / 'index.json').read_text())
    need(
        len(index['captures']) == expected,
        'Requested/captured invocation count differs')
    need(
        not index['pending_decode'] and not index['retained_owners']
        and not index['failures'], 'Finalization left failures or owners')
    need((timeline / 'compiler-attempts/index.json').is_file(),
         'Compiler receipts not retained in final bundle')
    need(
        sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        <= 64 * 1024 * 1024, 'Default bundle exceeded 64MiB budget')
    summaries = []
    for row in index['captures']:
        capture = json.loads((timeline / row['capture_file']).read_text())
        need(
            capture.get('counter_ns_status',
                        {}).get('status') == 'counter_unit_only'
            and len(capture.get('counter_ns_exports', [])) == 8,
            'Default late capture lacks its actual machine-validated counter-ns views'
        )
        need(
            capture['record_backend'] == 'nvidia-late-1'
            and capture['capture_status'] == 'raw_complete',
            'Default API did not produce complete late raw')
        raw = (timeline / capture['raw_file']).read_bytes()
        need(
            hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
            'Raw changed after bundle save')
        guard = capture['readback_guard']
        need((timeline / guard['file']).read_bytes() == bytes([165]) * 128,
             'Device record guard changed')
        from flagtree.profiler.timeline_decoded_reports import read_decoded_report
        decoded = read_decoded_report(timeline, capture)
        need(decoded['complete'],
             'Raw decoder did not verify complete capture')
        need(capture['owner']['layout']['storage_version'] == 'nvidia-late-1',
             'Wrong record layout')
        plan = capture['owner']['plan']
        need(
            plan['actors'] == 4 and not plan['dependency_footprint_complete'],
            'Non-async default should select four actual threads without collective qualification'
        )
        events = [
            e for program in decoded['programs']
            for actor in program['observers'] for e in actor['events']
        ]
        need(any(e['end_tick'] > e['begin_tick'] for e in events),
             'No positive measured internal bracket')
        need(
            len({
                member.get('line')
                for site in plan['sites']
                for member in site.get('members', []) if member.get('line')
            }) >= 2, 'Missing multiple native source locations')
        need(capture['owner']['submission_outcome'] == 'returned',
             'Launch was not submitted exactly once')
        summaries.append(
            dict(invocation=row['invocation_id'],
                 binary=row['binary_id'],
                 raw_bytes=len(raw),
                 events=len(events),
                 stream=capture['owner']['stream'],
                 programs=capture['owner']['layout']['programs']))
    return summaries


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability() == (12, 0), 'Wrong target')
    torch.manual_seed(36050)
    (a.output / 'host-once.txt').write_text('one explicit test workload\n')
    streams = [torch.cuda.Stream(), torch.cuda.Stream()]
    freezes, math_results = [], []
    for phase in ('ordinary', 'profile', 'warm_session'):
        count = 10 if phase != 'warm_session' else 2
        session = None
        if phase != 'ordinary':
            session = profiler.start(str(a.output / phase), detail='timeline')
        try:
            for i in range(count):
                n, block, warps = (1003, 512, 4) if i % 2 == 0 else (513, 256,
                                                                     8)
                grid = triton.cdiv(n, block)
                cpu = torch.randn(n, dtype=torch.float32)
                reference = torch.exp(
                    -cpu.double() * cpu.double()) * 0.75 + cpu.double() * 0.125
                with torch.cuda.stream(streams[i % 2]):
                    x = cpu.cuda()
                    y = torch.full((n + 7, ), 1234., device='cuda')
                    calls = torch.zeros(grid + 1,
                                        dtype=torch.int32,
                                        device='cuda')
                    freezes.append(
                        dict(phase=phase,
                             index=i,
                             N=n,
                             block=block,
                             warps=warps,
                             rtol=1e-5,
                             atol=1e-6,
                             input_sha256=hashlib.sha256(
                                 cpu.numpy().tobytes()).hexdigest()))
                    (a.output / 'frozen-inputs.json').write_text(
                        json.dumps(freezes, indent=2))
                    nonlinear[(grid, )](x, y, calls, n, block, num_warps=warps)
                    # Local readback proves completion before the next admission;
                    # product itself must not insert a device-wide barrier.
                    observed = y[:n].cpu().double()
                    need(
                        torch.allclose(observed,
                                       reference,
                                       rtol=1e-5,
                                       atol=1e-6), 'Original nonlinear math')
                    need(torch.equal(y[n:].cpu(), torch.full((7, ), 1234.)),
                         'Output tail changed')
                    need(calls.cpu().tolist() == [1] * grid + [0],
                         'Hidden replay or missed program')
                    need(torch.equal(x.cpu(), cpu), 'Input changed')
                    math_results.append(
                        dict(phase=phase,
                             index=i,
                             math=True,
                             guard=True,
                             input=True,
                             explicit_launches=1))
            if phase == 'profile':
                n = 769
                cpu = torch.randn(3, n)
                reference = torch.softmax(cpu.double(), 1)
                x = cpu.cuda()
                y = torch.full((3 * n + 7, ), 1234., device='cuda')
                row_softmax[(3, )](x, y, n, 1024, num_warps=8)
                need(
                    torch.allclose(y[:3 * n].cpu().reshape(3, n).double(),
                                   reference,
                                   rtol=1e-5,
                                   atol=1e-6), 'Original Softmax math')
                need(torch.equal(y[3 * n:].cpu(), torch.full((7, ), 1234.)),
                     'Softmax tail changed')
                need(torch.equal(x.cpu(), cpu), 'Softmax input changed')
                math_results.append(
                    dict(phase=phase,
                         case='softmax',
                         math=True,
                         guard=True,
                         input=True,
                         explicit_launches=1))
        finally:
            if session is not None:
                profiler.finalize(session)
    captures = inspect(a.output / 'profile', 11)
    warm = inspect(a.output / 'warm_session', 2)
    need(
        len({r['binary']
             for r in captures}) == 3,
        'Specializations or kernel binaries were mixed')
    need(
        len({r['stream']
             for r in captures}) >= 2, 'Two real streams were not captured')
    need(
        set(r['binary']
            for r in warm).issubset({r['binary']
                                     for r in captures}),
        'Warm session unexpectedly changed binary identity')
    from flagtree.profiler.timeline_runtime import retained_owner_statuses
    need(not retained_owner_statuses(),
         'Owned device buffers leaked after finalization')
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'default_late_raw_api_real_math_multicall_streams_warm_session_passed_not_full_timeline',
            mathematical_calls=math_results,
            captures=captures,
            warm_captures=warm,
            perfetto_qualified=False,
            clock_comparison_qualified=False),
                   indent=2))


if __name__ == '__main__':
    main()
