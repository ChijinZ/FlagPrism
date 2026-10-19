"""Affected real-device resume and GCU allocation-guard regressions.

Uses the existing C1 math, without timing/performance claims. Fault injection
writes one byte inside this invocation's owned prefix, after its completion.
"""
import argparse
import ctypes
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',
                        choices=['nvidia', 'ascend', 'enflame'],
                        required=True)
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--guard-only', action='store_true')
    args = parser.parse_args()
    need(not args.guard_only or args.backend == 'enflame',
         'Guard-only is a GCU regression')
    if args.backend == 'ascend':
        import torch_npu  # noqa: F401
        api, device = torch.npu, 'npu:' + str(args.device)
    elif args.backend == 'enflame':
        import torch_gcu  # noqa: F401
        api, device = torch.gcu, 'gcu:' + str(args.device)
    else:
        api, device = torch.cuda, 'cuda:' + str(args.device)
    api.set_device(args.device)
    path = Path(__file__).with_name('p01_controlled_workloads.py')
    spec = importlib.util.spec_from_file_location('review_existing_C1', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    recurrence, _ = module.create_kernels()
    from flagtree import profiler
    args.output.mkdir(parents=True, exist_ok=False)
    cpu = torch.linspace(-2, 2, 257, device='cpu')
    x = cpu.to(device)
    steps = torch.tensor([3], dtype=torch.int32, device=device)
    reference = cpu.clone()
    for _ in range(3):
        reference = reference * 0.75 + 0.125
    mathematical_calls = []

    def launch():
        y = torch.full((261, ), -17.25, device=device)
        state = torch.zeros(257, dtype=torch.int32, device=device)
        compiled = recurrence[(3, )](x, y, state, steps, 257, 128, num_warps=4)
        need(torch.allclose(y[:257].cpu(), reference, rtol=2e-6, atol=2e-6),
             'C1 mathematical mismatch')
        need(bool((y[257:].cpu() == -17.25).all()), 'C1 output tail changed')
        need(bool((state.cpu() == 1).all()), 'C1 executed other than once')
        need(torch.equal(x.cpu(), cpu), 'C1 input changed')
        mathematical_calls.append(compiled.hash)
        return compiled.hash

    result = dict(backend=args.backend, performance_measured=False)
    if not args.guard_only:
        output = args.output / 'resume'
        session = profiler.start(str(output), detail='timeline')
        try:
            first = launch()
            profiler.deactivate()
            ordinary = launch()
            profiler.activate()
            resumed = launch()
        finally:
            profiler.finalize(session)
        need(first == resumed,
             'Resume must exercise the existing profiled executable')
        root = output / 'timeline'
        index = json.loads((root / 'index.json').read_text())
        need(
            len(index['captures']) == 2,
            'Expected first/resumed captures, not paused call')
        summaries = []
        for row in index['captures']:
            from flagtree.profiler.timeline_capture_store import load_capture_file
            capture = load_capture_file(root / row['capture_file'])
            need(capture['owner']['binary_id'] == first,
                 'Resume capture binary mismatch')
            need(capture.get('counter_ns_exports'),
                 'Resume capture lacks measured ns exports')
            batch = json.loads((root / capture['events_file']).read_text())
            positive = sum(
                e['kind'] == 'interval' and e['end_tick'] > e['start_tick']
                for e in batch['events'])
            need(positive > 0,
                 'Resume capture lacks positive internal intervals')
            if args.backend == 'enflame':
                guard = capture['readback_guard']
                need((root / guard['file']).read_bytes() == bytes([165]) * 128,
                     'Native physical GCU guards not intact')
            summaries.append(
                dict(invocation_id=row['invocation_id'],
                     positive_intervals=positive,
                     ns_exports=len(capture['counter_ns_exports'])))
        result = dict(status='real_device_resume_passed',
                      backend=args.backend,
                      first_binary=first,
                      ordinary_binary=ordinary,
                      resumed_binary=resumed,
                      captured=summaries,
                      mathematical_calls=len(mathematical_calls),
                      performance_measured=False)
    if args.backend == 'enflame':
        from flagtree.profiler.timeline_enflame import EnflameTimelineTransport
        loaded = sorted({
            line.split()[-1]
            for line in Path('/proc/self/maps').read_text().splitlines()
            if 'libtopsrt.so' in line and line.split()[-1].startswith('/')
        })
        need(len(loaded) == 1, 'Expected one actually loaded TOPS runtime')
        sdk = ctypes.CDLL(loaded[0])
        sdk.topsMemsetAsync.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p
        ]
        sdk.topsMemsetAsync.restype = ctypes.c_int
        sdk.topsStreamSynchronize.argtypes = [ctypes.c_void_p]
        sdk.topsStreamSynchronize.restype = ctypes.c_int
        read_raw = EnflameTimelineTransport.read_raw
        injections = []

        def corrupt_owned_prefix(transport, owner):
            pointer = int(owner['resource']['handle'].hidden_arg_value)
            stream = ctypes.c_void_p(owner['stream'])
            need(
                sdk.topsMemsetAsync(ctypes.c_void_p(pointer - 1), 0, 1,
                                    stream) == 0,
                'TOPS owned-prefix fault injection failed')
            need(
                sdk.topsStreamSynchronize(stream) == 0,
                'TOPS fault injection did not complete')
            readback = read_raw(transport, owner)
            need(
                readback.guard == bytes([165]) * 63 + bytes([0]) +
                bytes([165]) * 64,
                'Native readback missed actual device prefix corruption')
            injections.append(owner['invocation_id'])
            return readback

        bad = args.output / 'bad-guard'
        session = profiler.start(str(bad), detail='timeline')
        profile_module = importlib.import_module('flagtree.profiler.profile')
        retained_timeline = Path(profile_module._active_sessions[session]
                                 ['name']).with_suffix('.timeline')
        error = None
        with patch.object(EnflameTimelineTransport, 'read_raw',
                          corrupt_owned_prefix):
            try:
                launch()
            finally:
                try:
                    profiler.finalize(session)
                except (ValueError, RuntimeError) as caught:
                    error = str(caught)
        need(len(injections) == 1, 'Expected one real-device guard injection')
        need(error and 'integrity' in error.lower(),
             'Corrupted guard must reject decoding')
        originals = list((retained_timeline / 'captures').glob('*.input.json'))
        need(len(originals) == 1, 'Bad guard original was not retained')
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(originals[0])
        need(capture['owner']['readback_integrity']['status'] == 'invalid',
             'Bad guard was not classified invalid')
        need((retained_timeline / capture['raw_file']).is_file(),
             'Bad guard raw was lost')
        need(not capture.get('counter_ns_exports'),
             'Corrupt raw must not produce a qualified trace')
        need(
            not list(
                retained_timeline.glob('derived/counter-ns/*/complete.json')),
            'Corrupt raw produced a derived timeline')
        recovery = args.output / 'after-bad-guard'
        session = profiler.start(str(recovery), detail='timeline')
        try:
            launch()
        finally:
            profiler.finalize(session)
        recovered = json.loads((recovery / 'timeline/index.json').read_text())
        need(
            len(recovered['captures']) == 1,
            'New session failed after guard rejection')
        result.update(
            status=('real_device_guard_rejection_and_recovery_passed'
                    if args.guard_only else
                    'real_device_resume_guard_rejection_and_recovery_passed'),
            native_guard_bytes=128,
            actual_sdk_prefix_corruptions=len(injections),
            corruption_error=error,
            raw_preserved=True,
            mathematical_calls=len(mathematical_calls))
    (args.output /
     'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
