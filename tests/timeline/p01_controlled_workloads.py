"""Real work and tiling interventions; timings describe instrumented execution.

Each profile session executes exactly one original mathematical kernel. C1
changes runtime loop work without specializing the executable. C2 changes the
reduction tile while keeping the input, mathematical result and work fixed.
This runner does not assert that a variant is faster, or call issue time busy.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch


def create_kernels():
    global triton, tl
    import triton
    import triton.language as tl

    @triton.jit
    def recurrence(X, Y, State, Steps, N: tl.constexpr, BLOCK: tl.constexpr):
        offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
        mask = offsets < N
        value = tl.load(X + offsets, mask, 0)
        steps = tl.load(Steps)
        for _ in range(steps):
            value = value * 0.75 + 0.125
        tl.store(Y + offsets, value, mask)
        prior = tl.load(State + offsets, mask, 0)
        tl.store(State + offsets, prior + 1, mask)

    @triton.jit
    def product(A, B, C, State, M: tl.constexpr, N: tl.constexpr,
                K: tl.constexpr, BK: tl.constexpr):
        rows = tl.program_id(0) * 32 + tl.arange(0, 32)
        cols = tl.program_id(1) * 32 + tl.arange(0, 32)
        inner = tl.arange(0, BK)
        result = tl.full((32, 32), 0, tl.float32)
        for tile in range(tl.cdiv(K, BK)):
            kk = tile * BK + inner
            left = tl.load(A + rows[:, None] * K + kk[None, :],
                           (rows[:, None] < M) & (kk[None, :] < K), 0)
            right = tl.load(B + kk[:, None] * N + cols[None, :],
                            (kk[:, None] < K) & (cols[None, :] < N), 0)
            result += tl.dot(left, right)
        offsets = rows[:, None] * N + cols[None, :]
        mask = (rows[:, None] < M) & (cols[None, :] < N)
        tl.store(C + offsets, result, mask)
        prior = tl.load(State + offsets, mask, 0)
        tl.store(State + offsets, prior + 1, mask)

    return recurrence, product


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def inspect(bundle):
    root = bundle / 'timeline'
    index = json.loads((root / 'index.json').read_text())
    need(len(index['captures']) == 1, 'Expected exactly one captured call')
    from flagtree.profiler.timeline_capture_store import load_capture_file
    capture = load_capture_file(root / index['captures'][0]['capture_file'])
    batch = json.loads((root / capture['events_file']).read_text())
    from flagtree.profiler.timeline_events import validate_raw_batch
    validate_raw_batch(batch)
    count_fields = (('written_records', 'retained_records',
                     'overwritten_records') if batch['schema_version'] == 1
                    else ('attempted_records', 'committed_records',
                          'retained_records', 'dropped_records',
                          'filtered_records', 'overwritten_records'))
    # Unobserved reserved slots remain unknown; they are not evidence that an
    # observed writer lost data. Never accept loss from an arrived writer.
    observed = []
    unobserved = []
    for observer in batch['observers']:
        empty_unknown = (observer['physical_identity'] is None
                         and not observer['complete']
                         and all(observer[key] == 0 for key in count_fields)
                         and not observer['saturated']
                         and not any(e['observer_id'] == observer['id']
                                     for e in batch['events']))
        if empty_unknown:
            unobserved.append(observer['id'])
            continue
        need(
            observer['complete'] and not observer['saturated']
            and observer['overwritten_records'] == 0,
            'Controlled case lost records from an observed writer')
        observed.append(observer['id'])
    need(observed, 'Controlled case has no observed writers')
    positive = sum(e['end_tick'] > e['start_tick'] for e in batch['events']
                   if e['kind'] == 'interval')
    need(positive >= 2, 'Controlled case has no positive internal structure')
    exports = capture.get('counter_ns_exports', [])
    need(exports, 'Controlled case has no measured counter-unit timeline')
    scopes = []
    for row in exports:
        view = json.loads((root / row['view_file']).read_text())
        durations = {}
        for event in view['events']:
            if event['kind'] == 'interval':
                durations.setdefault(event['site_id'],
                                     []).append(event['end_ns'] -
                                                event['start_ns'])
        scopes.append(
            dict(observer_id=row['observer_id'],
                 program_coordinates=row['program_coordinates'],
                 clock_status=row['clock_status'],
                 site_durations_ns=durations))
    return dict(binary_id=capture['owner']['binary_id'],
                batch_complete=batch['complete'],
                observed_writers=observed,
                unobserved_reserved_slots=unobserved,
                positive_intervals=positive,
                sites=batch['sites'],
                site_occurrences=dict(
                    Counter(e['site_id'] for e in batch['events'])),
                scopes=scopes,
                dependency_exports=capture.get('observed_dependency_exports',
                                               []),
                bundle=str(bundle),
                bundle_bytes=sum(f.stat().st_size for f in bundle.rglob('*')
                                 if f.is_file()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',
                        choices=['nvidia', 'ascend', 'enflame'],
                        required=True)
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--case', choices=['C1', 'C2'], required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--ordinary-repetitions', type=int, default=1)
    parser.add_argument('--timeline-max-sites', type=int, default=8)
    parser.add_argument('--variant',
                        type=int,
                        help='Run one existing work/tiling variant only')
    parser.add_argument(
        '--measure-device-span',
        action='store_true',
        help='Record SDK event span including host submission gaps')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(2 <= args.repetitions <= 5, 'Use two to five finite repetitions')
    need(1 <= args.ordinary_repetitions <= 5,
         'Use one to five finite ordinary repetitions')
    need(1 <= args.timeline_max_sites <= 128, 'Invalid observation budget')
    need(not args.measure_device_span or args.backend != 'nvidia',
         'NVIDIA performance measurements remain deferred')
    variants = [3, 7, 11] if args.case == 'C1' else [32, 64]
    if args.variant is not None:
        need(args.variant in variants, 'Unknown existing controlled variant')
        variants = [args.variant]
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
    recurrence, product = create_kernels()
    from flagtree import profiler
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for variant in variants:
        for repetition in range(-args.ordinary_repetitions, args.repetitions):
            label = (
                'ordinary' if args.ordinary_repetitions == 1 else 'ordinary' +
                str(repetition)) if repetition < 0 else str(repetition)
            folder = args.output / (str(variant) + '-' + label)
            folder.mkdir()
            if args.case == 'C1':
                cpu = torch.linspace(-2, 2, 257, device='cpu')
                x = cpu.to(device)
                y = torch.full((261, ), -17.25, device=device)
                state = torch.zeros(257, dtype=torch.int32, device=device)
                steps = torch.tensor([variant],
                                     dtype=torch.int32,
                                     device=device)
                launch = lambda: recurrence[
                    (3, )](x, y, state, steps, 257, 128, num_warps=4)
                reference = cpu.clone()
                for _ in range(variant):
                    reference = reference * 0.75 + 0.125
                inputs = [(x, cpu),
                          (steps,
                           torch.tensor([variant],
                                        dtype=torch.int32,
                                        device='cpu'))]
            else:
                left = torch.linspace(-0.5, 0.5, 64 * 192,
                                      device='cpu').reshape(64, 192).half()
                right = torch.linspace(0.5, -0.25, 192 * 64,
                                       device='cpu').reshape(192, 64).half()
                x, b = left.to(device), right.to(device)
                y = torch.full((4100, ), -17.25, device=device)
                state = torch.zeros(4096, dtype=torch.int32, device=device)
                launch = lambda: product[(2, 2)](x,
                                                 b,
                                                 y,
                                                 state,
                                                 64,
                                                 64,
                                                 192,
                                                 variant,
                                                 num_warps=4,
                                                 num_stages=1)
                reference = (left.float() @ right.float()).reshape(-1)
                inputs = [(x, left), (b, right)]
            event_backend = (
                torch.npu if args.backend == 'ascend' else
                torch.gcu if args.backend == 'enflame' else torch.cuda)
            start_event = end_event = None
            if args.measure_device_span:
                need(args.backend != 'nvidia',
                     'NVIDIA performance measurements remain deferred')
                event_backend.synchronize()
                start_event = event_backend.Event(enable_timing=True)
                end_event = event_backend.Event(enable_timing=True)
            session = profiler.start(str(folder / 'capture'),
                                     detail='timeline',
                                     timeline_max_sites=args.timeline_max_sites
                                     ) if repetition >= 0 else None
            request_start = time.perf_counter_ns()
            try:
                if start_event is not None:
                    start_event.record()
                compiled = launch()
                if end_event is not None:
                    end_event.record()
            finally:
                if session is not None:
                    profiler.finalize(session)
            request_elapsed = time.perf_counter_ns() - request_start
            device_span = None
            if end_event is not None:
                end_event.synchronize()
                device_span = start_event.elapsed_time(end_event)
                need(device_span >= 0, 'SDK reported a negative stream span')
            observed = y[:reference.numel()].cpu()
            tolerance = 2e-6 if args.case == 'C1' else 2e-3
            need(
                torch.allclose(observed,
                               reference,
                               rtol=tolerance,
                               atol=tolerance), 'Mathematical result changed')
            need(
                torch.equal(y[reference.numel():].cpu(),
                            torch.full((4, ), -17.25)), 'Output tail changed')
            need(
                all(
                    torch.equal(value.cpu(), original)
                    for value, original in inputs), 'Input changed')
            need(torch.equal(state.cpu(), torch.ones_like(state.cpu())),
                 'Original mathematical call replayed or missed')
            row = dict(variant=variant,
                       repetition=repetition,
                       math_passed=True,
                       original_calls=1,
                       requested_max_sites=args.timeline_max_sites,
                       host_request_elapsed_ns=request_elapsed,
                       device_stream_span_ms=device_span,
                       stream_span_includes_host_submission_gaps=True)
            if repetition < 0:
                row['binary_id'] = compiled.hash
                for kind, value in compiled.asm.items():
                    if isinstance(value, (str, bytes)):
                        (folder /
                         ('ordinary.' + kind)).write_bytes(value.encode(
                         ) if isinstance(value, str) else value)
            else:
                row.update(inspect(folder / 'capture'))
            rows.append(row)
            (args.output /
             'calls.json').write_text(json.dumps(rows, indent=2) + '\n')
    if args.case == 'C1':
        need(
            len({r['binary_id']
                 for r in rows if r['repetition'] >= 0}) == 1,
            'Runtime work specialized the instrumented executable')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'controlled_real_math_and_internal_timestamps_collected_pending_interpretation',
            backend=args.backend,
            case=args.case,
            requested_max_sites=args.timeline_max_sites,
            rows=rows,
            limits=[
                'Instrumented execution only; no uninstrumented speedup or overhead claim.',
                'No cross-observer alignment, physical overlap or engine busy inferred.',
                'SDK stream spans include host submission/compilation gaps; cold spans are not kernel overhead.'
            ]),
                   indent=2) + '\n')


if __name__ == '__main__':
    main()
