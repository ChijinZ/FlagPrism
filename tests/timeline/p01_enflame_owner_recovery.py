"""Real GCU two-stream ownership and decode recovery, not time qualification."""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args();args.output.mkdir(exist_ok=False)
    import torch
    import torch_gcu  # noqa: F401
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    profile = importlib.import_module('flagtree.profiler.profile')
    path = Path(__file__).with_name('ordinary_enflame_timeline_workload.py')
    spec = importlib.util.spec_from_file_location('ordinary_enflame_timeline_workload', path)
    workload = importlib.util.module_from_spec(spec);sys.modules[spec.name]=workload
    spec.loader.exec_module(workload)
    torch.gcu.set_device(0)
    streams = [torch.gcu.Stream(), torch.gcu.Stream()]
    rows = []
    for index, (grid, steps) in enumerate([((3, 2), 3), ((2, 2), 7), ((1, 1), 11)]):
        with torch.gcu.stream(streams[index%2]):
            rows.append(workload.make_inputs(grid, steps))
    session = profiler.start(str(args.output/'failure'), detail='timeline')
    state = profile._active_sessions[session]
    hook = state['timeline_hook'];base = state['name']
    actions = []
    transport = hook.timeline_pool.transport
    for method in ['completion_ready', 'read_raw', 'record_completion', 'release']:
        original = getattr(transport, method)
        def wrapped(owner, original=original, method=method):
            actions.append((method, owner['invocation_id']))
            return original(owner)
        setattr(transport, method, wrapped)
    for index, row in enumerate(rows):
        with torch.gcu.stream(streams[index%2]):
            workload.launch(row)
    ids = hook.timeline_pool.invocation_ids
    need(len(ids)==3 and len({hook.timeline_pool.snapshot(i)['stream'] for i in ids})==2,
         'Two-stream launch association lost')
    need([a[0] for a in actions]==['record_completion']*3,
         'Submission waited or read back before all calls')
    original_decode = hook._decode_timeline_original
    def decode(identity, directory, deadline):
        need(not hook.timeline_pool.invocation_ids and not hook.timeline_pool.pending_bytes,
             'Decoder ran while safely completable originals still owned resources')
        if identity==ids[0]:
            raise ValueError('injected first GCU decoder failure')
        return original_decode(identity, directory, deadline)
    hook._decode_timeline_original = decode
    try:
        profiler.finalize(session)
    except RuntimeError as error:
        need('injected first GCU decoder failure' in str(error), 'Wrong failure')
        (args.output/'first-failure.txt').write_text(str(error)+'\n')
    else:
        raise RuntimeError('Injected decoder failure ignored')
    directory = Path(base).with_suffix('.timeline')
    index = json.loads((directory/'index.json').read_text())
    need(index['pending_decode']==[ids[0]] and not index['retained_owners'] and len(index['captures'])==2,
         'Failure lost independent captures or device owners')
    originals = {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (directory/'captures').glob('*') if p.suffix=='.raw' or p.name.endswith('.input.json')}
    need(len(originals)==6, 'Not all raw/input originals retained')
    first_attempt = (directory/'attempts/flush-0001.json').read_bytes()
    before = list(actions)
    hook._decode_timeline_original = original_decode
    hook.flush_timeline(base)
    need(actions==before, 'Decode recovery touched device transport')
    need((directory/'attempts/flush-0001.json').read_bytes()==first_attempt,
         'Recovery overwrote original failure history')
    for path, digest in originals.items():
        need(hashlib.sha256((directory/path).read_bytes()).hexdigest()==digest, 'Recovery changed original')
    index = json.loads((directory/'index.json').read_text())
    need(len(index['captures'])==3 and not index['pending_decode'], 'Recovery lost or duplicated capture')
    for item in index['captures']:
        capture = json.loads((directory/item['capture_file']).read_text())
        canonical = validate_raw_batch(json.loads((directory/capture['events_file']).read_text()))
        need(canonical['complete'], 'Recovery source capture incomplete')
    for row in rows:
        workload.verify(row)
    # Retain a portable copy of recovery evidence before a later valid session.
    import shutil
    shutil.copytree(directory, args.output/'recovered-originals')
    next_input = workload.make_inputs((3, 2), 5)
    session = profiler.start(str(args.output/'after-failure'), detail='timeline')
    try:
        workload.launch(next_input)
    finally:
        profiler.finalize(session)
    workload.verify(next_input)
    next_index = json.loads((args.output/'after-failure/timeline/index.json').read_text())
    need(len(next_index['captures'])==1 and not next_index['retained_owners'], 'Next valid session failed')
    (args.output/'result.json').write_text(json.dumps(dict(
        status='gcu_two_stream_raw_recovery_passed_not_full_P01', failure_math_calls=3,
        following_math_calls=1, recovered_captures=3, recovery_transport_actions=0,
        original_sha256=originals, clock_qualified=False, boundary_qualified=False,
        perfetto_qualified=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
