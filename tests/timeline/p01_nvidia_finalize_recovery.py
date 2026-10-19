"""Real public capture/decode fault recovery; no ns/Perfetto or overhead claim."""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import time


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    import torch
    import flagtree.profiler as profiler
    from flagtree.profiler.hooks.instrumentation import InstrumentationHook
    from flagtree.profiler.timeline_events import validate_raw_batch
    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability() == (12, 0), 'Wrong actual target')
    target = Path(__file__).with_name('ordinary_timeline_workload.py')
    spec = importlib.util.spec_from_file_location('ordinary_timeline_workload',
                                                  target)
    workload = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = workload
    spec.loader.exec_module(workload)
    profile = importlib.import_module('flagtree.profiler.profile')
    base = args.output / 'fault-capture'
    session = profiler.start(str(base), detail='timeline')
    state = profile._active_sessions[session]
    hook = state['timeline_hook']
    raw_base = state['name']
    actions = []
    for name in ('read_raw', 'release'):
        original = getattr(hook.timeline_pool.transport, name)

        def wrap(owner, *, name=name, original=original):
            result = original(owner)
            actions.append(
                dict(action=name,
                     invocation_id=owner['invocation_id'],
                     monotonic_ns=time.monotonic_ns()))
            return result

        setattr(hook.timeline_pool.transport, name, wrap)
    original_decode = hook._decode_timeline_original
    injected = []

    def decode(identity, directory, deadline):
        need(
            not hook.timeline_pool.invocation_ids
            and hook.timeline_pool.pending_bytes == 0,
            'Derived work ran before device owners were safely released')
        need(
            len([a for a in actions if a['action'] == 'read_raw']) == 4
            and len([a for a in actions if a['action'] == 'release']) == 4,
            'Expected four real completed owners before decoding')
        if not injected:
            injected.append(identity)
            raise ValueError('injected first real capture decoder failure')
        return original_decode(identity, directory, deadline)

    hook._decode_timeline_original = decode
    workload.run(args.output / 'fault-math')
    try:
        profiler.finalize(session)
    except RuntimeError as error:
        need('injected first real capture decoder failure' in str(error),
             'Wrong failure')
        (args.output /
         'first-finalize-error.txt').write_text(str(error) + '\n')
    else:
        raise RuntimeError('Injected decoder failure was swallowed')
    need(
        session not in profile._active_sessions
        and not InstrumentationHook.active_count,
        'Native session or instrumentation remained active')
    directory = Path(raw_base).with_suffix('.timeline')
    first_index = json.loads((directory / 'index.json').read_text())
    need(
        len(first_index['captures']) == 3
        and first_index['pending_decode'] == injected,
        'Other real captures were not recovered despite first decoder failure')
    need(
        not first_index['retained_owners']
        and not hook.timeline_pool.invocation_ids,
        'Completed persisted captures kept device resources')
    originals = {
        str(p.relative_to(directory)):
        hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.glob('captures/*')
        if p.suffix == '.raw' or p.name.endswith('.input.json')
    }
    need(len(originals) == 8, 'Not all four real originals were durably saved')
    actions_before = list(actions)
    first_attempt_sha = hashlib.sha256(
        (directory / 'attempts/flush-0001.json').read_bytes()).hexdigest()
    hook._decode_timeline_original = original_decode
    recovered = hook.flush_timeline(raw_base)
    index = json.loads((recovered / 'index.json').read_text())
    need(
        len(index['captures']) == 4 and not index['pending_decode']
        and not index['failures'],
        'Reexport lost a call or hid a pending failure')
    need(actions == actions_before,
         'Reexport performed device transport operations')
    need(
        all(
            hashlib.sha256((directory / f).read_bytes()).hexdigest() == sha
            for f, sha in originals.items()),
        'Recovery modified original raw/input')
    need(
        hashlib.sha256((directory / 'attempts/flush-0001.json'
                        ).read_bytes()).hexdigest() == first_attempt_sha,
        'Recovery erased first failure evidence')

    def inspect(directory, index):
        rows = []
        for row in index['captures']:
            from flagtree.profiler.timeline_capture_store import load_capture_file
            capture = load_capture_file(directory / row['capture_file'])
            need(capture['capture_status'] == 'raw_complete',
                 'Ordinary capture incomplete')
            need(
                capture['machine_counter_mapping']['status'] ==
                'counter_mapping_complete_region_unverified',
                'Machine/source boundary status changed')
            canonical = validate_raw_batch(
                json.loads((directory / capture['events_file']).read_text()))
            need(canonical['complete'] and canonical['events'],
                 'Actual canonical data lost')
            need(
                canonical['clock_status'] == 'unverified'
                and canonical['boundary_status'] == 'unverified',
                'Raw recovery falsely grants qualification')
            rows.append(
                dict(invocation_id=row['invocation_id'],
                     events=len(canonical['events']),
                     records=len(canonical['records']),
                     raw_sha256=capture['raw_sha256']))
        return rows

    rows = inspect(directory, index)
    next_base = args.output / 'after-fault'
    next_session = profiler.start(str(next_base), detail='timeline')
    try:
        workload.run(args.output / 'after-fault-math')
    finally:
        profiler.finalize(next_session)
    next_directory = next_base / 'timeline'
    next_index = json.loads((next_directory / 'index.json').read_text())
    need(len(next_index['captures']) == 4, 'Next legal session failed')
    next_rows = inspect(next_directory, next_index)
    result = dict(
        status='actual_owner_salvage_and_offline_retry_passed_not_full_P01',
        injected_invocation=injected[0],
        original_directory=str(directory),
        explicit_workload_runs=2,
        fault_capture_calls=4,
        subsequent_capture_calls=4,
        first_attempt_sha256=first_attempt_sha,
        transport_actions=actions,
        recovery_transport_actions=0,
        originals=originals,
        recovered_captures=rows,
        subsequent_captures=next_rows,
        clock_qualified=False,
        region_boundaries_verified=False,
        perfetto_qualified=False)
    (args.output /
     'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
