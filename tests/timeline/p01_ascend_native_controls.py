"""Check fresh decoding of retained real Ascend native-control recordings.

No application replay, compiler invocation or device access. Zero-width native
brackets remain zero; source elapsed time and native completion are distinct.
Run with the matching installed product in its server Docker, normal and -O.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from flagtree.profiler.timeline_events_ascend import canonicalize_ascend_capture


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline',
                        type=Path,
                        action='append',
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for directory in args.timeline:
        before = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()
        }
        index = json.loads((directory / 'index.json').read_text())
        for row in index['captures']:
            from flagtree.profiler.timeline_capture_store import load_capture_file
            exported = load_capture_file(directory / row['capture_file'])
            original = directory / ('captures/' + row['invocation_id'] +
                                    '.input.json')
            from flagtree.profiler.timeline_capture_store import load_capture_file
            capture = load_capture_file(original)
            raw = (directory / capture['raw_file']).read_bytes()
            need(
                hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
                'Raw changed')

            def decode(data):
                return canonicalize_ascend_capture(
                    data,
                    owner=capture['owner'],
                    metadata=capture['metadata']['compiler_metadata'],
                    association=capture['launch'])

            batch = decode(raw)
            need(
                batch == json.loads(
                    (directory / exported['events_file']).read_text()),
                'Fresh raw decode differs from the original exported canonical'
            )
            sites = {s['id']: s for s in batch['sites']}
            records = {r['id']: r for r in batch['records']}
            for record in records.values():
                need(
                    struct.unpack_from('<Q', raw,
                                       record['offset'])[0] == record['tick'],
                    'A canonical timestamp is not its actual raw field')
            native, zero = Counter(), 0
            positive_source = set()
            fault_checked = False
            for event in batch['events']:
                attrs = sites[event['site_id']]['attributes']
                if attrs.get('ascend.native_control_version') not in (1, 2):
                    if event['end_tick'] > event['start_tick']:
                        positive_source.add(event['site_id'])
                    continue
                need(
                    event['semantic'] == 'observer_region_elapsed'
                    and attrs['ascend.completion_status'] == 'unverified'
                    and attrs['ascend.engine_activity_verified'] is False,
                    'Scalar native observations were promoted to engine/completion time'
                )
                key = (attrs['ascend.native_operation'],
                       attrs['ascend.native_source_pipe'],
                       attrs['ascend.native_destination_pipe'],
                       attrs['ascend.native_event_id'])
                native[str(key)] += 1
                zero += event['start_tick'] == event['end_tick']
                if not fault_checked:
                    # Change only the semantic code and update the commit tag.
                    # An intact tag must not make a native pair a source pair.
                    damaged = bytearray(raw)
                    offset = records[event['record_ids'][0]]['offset'] - 16
                    descriptor = struct.unpack_from('<Q', raw, offset)[0]
                    forged = (descriptor & 0xffffffff) | (1 << 32)
                    tag = struct.unpack_from('<Q', raw, offset + 56)[0]
                    struct.pack_into('<Q', damaged, offset, forged)
                    struct.pack_into('<Q', damaged, offset + 56,
                                     tag ^ descriptor ^ forged)
                    try:
                        decode(bytes(damaged))
                    except ValueError:
                        fault_checked = True
                    else:
                        raise RuntimeError(
                            'Native/source semantic substitution was accepted')
            need(
                native and fault_checked and len(positive_source) >= 2,
                'Real native controls and multiple positive source regions are required'
            )
            results.append(
                dict(invocation_id=row['invocation_id'],
                     native_counts=dict(native),
                     native_intervals=sum(native.values()),
                     zero_width_native_intervals=zero,
                     total_intervals=len(batch['events']),
                     raw_semantic_fault_rejected=True))
        need(
            before == {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in directory.rglob('*') if p.is_file()
            }, 'Original bundle changed')
    need(results, 'No actual recordings checked')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'real_ascend_native_raw_decoder_passed_not_async_qualification',
            captures=results),
                   indent=2))


if __name__ == '__main__':
    main()
