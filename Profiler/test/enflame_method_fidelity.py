#!/usr/bin/env python3
"""Formal tail Softmax / T5 evidence; source math inherited from Study kernels.

All CPU references, compilation, timing and collection must run inside Docker.
Raw stream-event intervals include gaps; TOPSPTI kernel events are device-task
intervals. No raw SDK ticks are converted or aligned to either clock.
"""
import argparse, hashlib, json, random, statistics, time
from pathlib import Path
import torch
import torch_gcu  # noqa:F401
import triton
import flagtree.profiler as profiler
from flagtree.profiler import ObservationRequest
from fixtures.enflame_method import kernels

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--input-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--task',
               choices=('tail', 't5', 'tcu_workload', 'i64_oracle'),
               required=True)
p.add_argument('--work-items', type=int, default=4)
p.add_argument(
    '--sites',
    type=int,
    nargs='+',
    help='Actual static IDs from this source compiled tracked table')
p.add_argument('--sample-every', type=int, default=1)
p.add_argument('--capacity', type=int, default=256)
p.add_argument('--selected-program', type=int, default=0)
p.add_argument(
    '--enable-i64',
    action='store_true',
    help='Independent native codegen-flag ablation, no added observer')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
r, n = 127, 769
raw = [(a.input_dir / f'rows-{r}x{n}-{i}.bin').read_bytes() for i in range(3)]
cpu = [
    torch.frombuffer(
        bytearray(v),
        dtype=torch.float32).clone().reshape((r, n) if i == 0 else (n, ))
    for i, v in enumerate(raw)
]
x, w, b = [v.to('gcu') for v in cpu]
y = torch.empty_like(x)
ref = torch.softmax(cpu[0], dim=-1)
request = ObservationRequest(programs=(a.selected_program, ),
                             sites=tuple(a.sites) if a.sites else None,
                             max_events_per_instance=a.capacity,
                             sample_every=a.sample_every)


def launch(work_items):
    return kernels.rows[(r, )](x,
                               w,
                               b,
                               y,
                               r,
                               n,
                               triton.next_power_of_2(n),
                               1,
                               'softmax',
                               num_warps=work_items,
                               num_stages=1,
                               **({
                                   'enable_i64': True
                               } if a.enable_i64 else {}))


def check():
    actual = y.cpu()
    torch.testing.assert_close(actual, ref, rtol=.002, atol=.0005)
    return {
        'reference': 'PyTorch CPU float32',
        'rtol': .002,
        'atol': .0005,
        'max_abs_error': float((actual - ref).abs().max()),
        'passed': True
    }


def write(path, document):
    path.write_text(json.dumps(document, indent=2, default=str))


write(
    a.output / 'plan.json', {
        'task':
        a.task,
        'shape': [r, n],
        'grid': [r],
        'ROWS':
        1,
        'input_sha256': [hashlib.sha256(v).hexdigest() for v in raw],
        'request':
        request.as_dict() if hasattr(request, 'as_dict') else repr(request),
        'native_task_clock':
        'TOPSPTI, raw native collector durations',
        'stream_event_clock':
        'torch.gcu.Event; enclosing stream interval, includes stream gaps',
        'internal_clock':
        'enflame.sdk.global_timer raw46bit ticks; frequency/alignment unverified',
        'source':
        'inherited Study mathematical kernels; formal profiler/actual compiler, no text rewriting'
    })
if a.task == 'tcu_workload':
    for _ in range(2):
        launch(a.work_items)
    torch.gcu.synchronize()
    write(a.output / 'validation.json', check())
    raise SystemExit(0)


def capture(mode, output, work_items, count, measure):
    session = None
    if mode != 'off':
        session = profiler.start(
            str(output / 'bundle'),
            backend='enflame',
            hook='instrumentation' if mode == 'selected_detail' else 'triton',
            **({
                'observation_request': request
            } if mode == 'selected_detail' else {}))
    compile_start = time.perf_counter_ns()
    compiled = kernels.rows.warmup(x,
                                   w,
                                   b,
                                   y,
                                   r,
                                   n,
                                   triton.next_power_of_2(n),
                                   1,
                                   'softmax',
                                   grid=(r, ),
                                   num_warps=work_items,
                                   num_stages=1,
                                   **({
                                       'enable_i64': True
                                   } if a.enable_i64 else {}))
    compile_ns = time.perf_counter_ns() - compile_start
    samples = []
    event_error = None
    for index in range(count):
        torch.gcu.synchronize()
        try:
            begin = torch.gcu.Event(enable_timing=True)
            end = torch.gcu.Event(enable_timing=True)
            begin.record()
        except Exception as exc:
            begin = end = None
            event_error = repr(exc)
        before = time.perf_counter_ns()
        compiled = launch(work_items)
        submitted = time.perf_counter_ns()
        if end is not None: end.record()
        torch.gcu.synchronize()
        synced = time.perf_counter_ns()
        try:
            interval = begin.elapsed_time(
                end) * 1.e6 if begin is not None else None
        except Exception as exc:
            interval = None
            event_error = repr(exc)
        samples.append({
            'sample': index,
            'host_submit_ns': submitted - before,
            'host_submit_and_sync_ns': synced - before,
            'device_stream_interval_ns': interval
        })
    finalize_start = time.perf_counter_ns()
    if session is not None: profiler.finalize(session)
    finalize_ns = time.perf_counter_ns() - finalize_start
    output.mkdir(parents=True, exist_ok=True)
    validation = check()
    metadata = compiled.metadata._asdict()
    metadata.pop('target', None)
    write(output / 'compiled-metadata.json', metadata)
    ir = output / 'asm'
    ir.mkdir()
    for key, value in compiled.asm.items():
        if isinstance(value, (str, bytes)):
            (ir / key
             ).write_bytes(value.encode() if isinstance(value, str) else value)
    tasks = []
    if session is not None:
        tasks = [
            json.loads(line)
            for line in (output /
                         'bundle/ai/events.jsonl').read_text().splitlines()
            if json.loads(line).get('kind') == 'kernel'
        ]
        if len(tasks) != count:
            raise RuntimeError(
                f'Expected {count} actual kernel records, got {len(tasks)}')
    if mode == 'selected_detail':
        observations = json.loads(
            (output / 'bundle/ai/observations.json').read_text())
        events = observations['observations']
        if len(observations['captures']) != count:
            raise RuntimeError(
                'Dynamic capture count differs from launched kernels')
        if a.selected_program < r:
            if not events or any(e['association_status'] != 'verified'
                                 for e in events):
                raise RuntimeError('Dynamic invocation association missing')
        else:
            if events or any(
                    c['header']['write_idx'] or c['header']['reserved0']
                    for c in observations['captures']):
                raise RuntimeError('Absent selected program produced records')
        if any(e['duration_ns'] is not None for e in events):
            raise RuntimeError('Unverified tick conversion')
        if any(c['header']['overflow_count']
               for c in observations['captures']):
            raise RuntimeError('Unexpected default selected capacity overflow')
    doc = {
        'mode':
        mode,
        'work_items':
        work_items,
        'measured':
        measure,
        'compile_or_cache_lookup_ns':
        compile_ns,
        'compile_scope':
        'public JIT warmup, no launch; may hit compiler cache',
        'samples':
        samples,
        'native_task_events':
        tasks,
        'native_task_durations_us': [e['duration_us'] for e in tasks],
        'off_task_duration_status':
        'unobserved; stream events are not isolated kernel durations'
        if mode == 'off' else 'actual TOPSPTI kernel activity',
        'event_error':
        event_error,
        'finalize_and_export_ns':
        finalize_ns,
        'validation':
        validation,
        'binary_id':
        compiled.hash,
        'compiler_metadata':
        metadata
    }
    write(output / 'result.json', doc)
    print(mode, work_items, count, 'passed', flush=True)
    return doc


if a.task == 'i64_oracle':
    for enabled in (False, True):
        a.enable_i64 = enabled
        capture('native', a.output / f'warmup-i64-{enabled}', a.work_items, 5,
                False)
    results = []
    for batch in range(3):
        flags = [False, True]
        random.Random(20261014 + batch).shuffle(flags)
        for enabled in flags:
            a.enable_i64 = enabled
            doc = capture('native', a.output / f'b{batch}-i64-{enabled}',
                          a.work_items, 30, True)
            if '_ZN4tops12global_timerEv' in (a.output /
                                              f'b{batch}-i64-{enabled}' /
                                              'asm/llir').read_text():
                raise RuntimeError('Observer leaked into native i64 oracle')
            results.append({
                'batch':
                batch,
                'enable_i64':
                enabled,
                'actual_enable_i64':
                doc['compiler_metadata']['enable_i64'],
                'binary_id':
                doc['binary_id'],
                'native_task_median_us':
                statistics.median(doc['native_task_durations_us']),
                'validation':
                doc['validation']
            })
            write(a.output / 'batch-summary.json', results)
elif a.task == 'tail':
    for work_items in (4, 1):
        capture('selected_detail', a.output / f'w{work_items}', work_items, 3,
                True)
else:
    work_items = a.work_items
    for mode in ('off', 'native', 'selected_detail'):
        capture(mode, a.output / f'warmup-{mode}', work_items, 5, False)
    results = []
    for batch in range(3):
        modes = ['off', 'native', 'selected_detail']
        random.Random(20261014 + batch).shuffle(modes)
        for mode in modes:
            doc = capture(mode, a.output / f'b{batch}-{mode}', work_items, 30,
                          True)
            results.append({
                'batch':
                batch,
                'mode':
                mode,
                'binary_id':
                doc['binary_id'],
                'host_submit_median_ns':
                statistics.median(s['host_submit_ns'] for s in doc['samples']),
                'stream_interval_median_ns':
                statistics.median(
                    s['device_stream_interval_ns'] for s in doc['samples']
                    if s['device_stream_interval_ns'] is not None) if any(
                        s['device_stream_interval_ns'] is not None
                        for s in doc['samples']) else None,
                'native_task_median_us':
                statistics.median(doc['native_task_durations_us'])
                if doc['native_task_durations_us'] else None
            })
            write(a.output / 'batch-summary.json', results)
write(a.output / 'complete.json', {'passed': True, 'task': a.task})
