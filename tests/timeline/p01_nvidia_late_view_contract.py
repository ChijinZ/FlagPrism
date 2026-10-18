"""Validate actual late raw projections, point fields and proof rejection."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct

from flagtree.profiler.timeline_events_nvidia_late import canonicalize_late_capture
from flagtree.profiler.timeline_unit_nvidia_late import load_late_machine_map


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    files = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in a.timeline.rglob('*') if p.is_file()
    }
    captures = json.loads((a.timeline / 'index.json').read_text())['captures']
    positives, negatives = [], []
    for item in captures:
        capture = json.loads((a.timeline / item['capture_file']).read_text())
        raw = (a.timeline / capture['raw_file']).read_bytes()
        batch = canonicalize_late_capture(raw,
                                          owner=capture['owner'],
                                          metadata=capture['metadata'])
        retained = json.loads(
            (a.timeline / capture['events_file']).read_text())
        need(batch == retained,
             'Final bundle differs from fresh complete-raw projection')
        for record in batch['records']:
            need(
                record['length'] == 8 and struct.unpack_from(
                    '<Q', raw, record['offset'])[0] == record['tick'],
                'Canonical endpoint is not its original strided 64-bit field')
        positives.append(
            dict(identity=batch['identity'],
                 events=len(batch['events']),
                 points=sum(r['phase'] == 'point' for r in batch['records']),
                 native_actors=capture['owner']['plan']['actors'],
                 view_observers=len(batch['observers'])))
    need(capture['owner']['plan']['actors'] > 4,
         'Need actual complete CTA data outside the displayed threads')
    plan, owner, metadata = capture['owner']['plan'], capture[
        'owner'], capture['metadata']
    actors = plan['actors']

    def reject(name, operation):
        try:
            operation()
        except (ValueError, RuntimeError) as error:
            negatives.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Malformed late projection accepted: ' + name)

    broken = bytearray(raw)
    struct.pack_into('<Q', broken, ((6 + 1) * actors + actors - 1) * 8, 0)
    reject(
        'bad_clock_outside_displayed_threads',
        lambda: canonicalize_late_capture(
            bytes(broken), owner=owner, metadata=metadata))
    lost = bytearray(raw)
    struct.pack_into('<Q', lost, (actors + actors - 1) * 8, 1)
    partial = canonicalize_late_capture(bytes(lost),
                                        owner=owner,
                                        metadata=metadata)
    need(
        not partial['complete']
        and all(not o['complete'] for o in partial['observers']),
        'Presentation subset hid loss in another recorded thread')
    forged = copy.deepcopy(owner)
    forged['plan']['sites'][0]['kind'] = 'forged_operation_role'
    reject(
        'owner_plan_differs_from_actual_compiler', lambda:
        canonicalize_late_capture(raw, owner=forged, metadata=metadata))
    forged = copy.deepcopy(owner)
    forged['layout']['grid'] = list(forged['layout']['grid'])
    forged['layout']['grid'][0] += 1
    reject(
        'program_slots_differs_from_launch', lambda: canonicalize_late_capture(
            raw, owner=forged, metadata=metadata))
    reject(
        'invalid_view_actor_selection', lambda: canonicalize_late_capture(
            raw, owner=owner, metadata=metadata, actor_indices=[0, 0]))
    # Recheck actual PTX/CUBIN/disassembly; then corrupt only the cached map's
    # qualification flag. It must not override recomputation of the real object.
    checked = load_late_machine_map(a.timeline, capture)
    need(
        checked['marker_flavor'] == 'late-v1'
        and not checked['clock_qualified'], 'Unexpected proof scope')
    replica = a.output / 'corrupt-copy'
    shutil.copytree(a.timeline, replica)
    map_path = replica / capture['machine_counter_mapping']['counter_map_file']
    saved = json.loads(map_path.read_text())
    saved['clock_qualified'] = True
    map_path.write_text(json.dumps(saved))
    reject('forged_cached_clock_flag',
           lambda: load_late_machine_map(replica, capture))
    for file, digest in files.items():
        need(
            hashlib.sha256(Path(file).read_bytes()).hexdigest() == digest,
            'Original final bundle changed')
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_late_raw_view_fields_and_corrupt_proof_contracts_passed_no_device_replay',
            positives=positives,
            rejected=negatives,
            loss_outside_view_visible=True,
            original_files_unchanged=len(files)),
                   indent=2))


if __name__ == '__main__':
    main()
