"""One public timeline session, ten real calls and two interleaved binaries.

Uses the existing recurrence mathematics. Single-program specializations keep
the complete session within its normal physical recording budget. Readback is
explicit test behavior, not a claim of ten concurrently pending launches.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',
                   choices=['nvidia', 'enflame', 'ascend'],
                   required=True)
    p.add_argument('--device', type=int, default=0)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
    import torch
    if args.backend == 'ascend':
        import torch_npu  # noqa: F401
        torch.npu.set_device(args.device)
        device = 'npu:' + str(args.device)
    elif args.backend == 'enflame':
        import torch_gcu  # noqa: F401
        torch.gcu.set_device(args.device)
        device = 'gcu:' + str(args.device)
    else:
        torch.cuda.set_device(args.device)
        device = 'cuda:' + str(args.device)
    name = 'timeline_e01_existing_workloads'
    spec = importlib.util.spec_from_file_location(
        name,
        Path(__file__).with_name('p01_controlled_workloads.py'))
    workloads = importlib.util.module_from_spec(spec)
    sys.modules[name] = workloads
    spec.loader.exec_module(workloads)
    recurrence, _ = workloads.create_kernels()
    from flagtree import profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    from flagtree.profiler.timeline_capture_store import load_capture
    (args.output / 'host-once.txt').write_text('one explicit E01 workload\n')
    rows = []
    session = profiler.start(str(args.output / 'capture'), detail='timeline')
    try:
        for call in range(10):
            n, block = (113, 128) if call % 2 == 0 else (117, 256)
            iterations = 31 if call % 3 == 0 else 47
            cpu = torch.linspace(-2 + call / 16., 2 + call / 16., n)
            x = cpu.to(device)
            y = torch.full((n + 7, ), -17.25, device=device)
            state = torch.zeros(n + 7, dtype=torch.int32, device=device)
            steps_cpu = torch.tensor([iterations], dtype=torch.int32)
            steps = steps_cpu.to(device)
            input_sha = hashlib.sha256(cpu.numpy().tobytes()).hexdigest()
            compiled = recurrence[(1, )](x,
                                         y,
                                         state,
                                         steps,
                                         n,
                                         block,
                                         num_warps=4)
            reference = cpu.double()
            for _ in range(iterations):
                reference = reference * .75 + .125
            observed = y.cpu()
            need(
                torch.allclose(observed[:n].double(),
                               reference,
                               rtol=1e-5,
                               atol=1e-6), 'Recurrence math changed')
            need(bool((observed[n:] == -17.25).all()), 'Output tail changed')
            states = state.cpu()
            need(
                bool((states[:n] == 1).all()) and bool(
                    (states[n:] == 0).all()),
                'State indicates replay or invalid tail writer')
            need(
                torch.equal(x.cpu(), cpu)
                and torch.equal(steps.cpu(), steps_cpu), 'Input changed')
            rows.append(
                dict(call=call,
                     n=n,
                     block=block,
                     iterations=iterations,
                     binary_id=compiled.hash,
                     input_sha256=input_sha,
                     math=True,
                     input=True,
                     tail=True,
                     exactly_once=True))
            (args.output / 'calls.json').write_text(json.dumps(rows, indent=2))
    finally:
        profiler.finalize(session)
    root = args.output / 'capture/timeline'
    index = json.loads((root / 'index.json').read_text())
    need(len(index['captures']) == 10, 'Expected ten captures in this session')
    need(
        not index['pending_decode'] and not index['retained_owners']
        and not index['failures'], 'Session left failures or owners')
    need(
        len({r['binary_id']
             for r in rows}) == 2, 'Expected exactly two real specializations')
    captures = []
    for row, entry in zip(rows, index['captures']):
        capture = load_capture(root, entry['capture_file'])
        need(capture['owner']['binary_id'] == row['binary_id'],
             'Capture crossed binary boundary')
        raw = root / capture['raw_file']
        need(
            hashlib.sha256(
                raw.read_bytes()).hexdigest() == capture['raw_sha256'],
            'Raw changed')
        batch = validate_raw_batch(
            json.loads((root / capture['events_file']).read_text()))
        need(batch['complete'], 'Incomplete raw capture')
        intervals = [
            e for e in batch['events']
            if e['kind'] == 'interval' and e['end_tick'] > e['start_tick']
        ]
        need(
            len(intervals) >= 2 and len({e['site_id']
                                         for e in intervals}) >= 2,
            'Missing detailed positive internal intervals')
        need(capture.get('counter_ns_exports'),
             'Missing measured counter-unit exports')
        captures.append(
            dict(invocation_id=entry['invocation_id'],
                 binary_id=entry['binary_id'],
                 capture_id=capture['owner']['capture_id'],
                 raw_sha256=capture['raw_sha256'],
                 raw_bytes=raw.stat().st_size,
                 positive_intervals=len(intervals),
                 site_occurrences=dict(Counter(e['site_id']
                                               for e in intervals)),
                 counter_exports=len(capture['counter_ns_exports'])))
    need(
        len({r['capture_id']
             for r in captures}) == 1, 'Calls belong to different sessions')
    need(
        len({r['invocation_id']
             for r in captures}) == 10, 'Repeated invocation identity')
    size = sum(p.stat().st_size for p in (args.output / 'capture').rglob('*')
               if p.is_file())
    need(size <= 64 * 1024 * 1024, 'Complete bundle exceeds 64MiB')
    result = dict(
        status='real_one_session_ten_interleaved_specializations_passed',
        backend=args.backend,
        calls=rows,
        captures=captures,
        bundle_bytes=size,
        hidden_replay=False,
        performance_measured=False,
        concurrent_pending_claim=False)
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
