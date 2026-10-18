"""Stdlib byte audit of retained device evidence; never imports the product."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def need(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tarfile.open(args.archive) as archive:
        names = archive.getnames()
        need(len(names) == len(set(names)), 'Duplicate archive member')

        def raw(name):
            member = archive.getmember(name)
            need(member.isfile(), 'Evidence member is not a regular file')
            return archive.extractfile(member).read()

        def document(name):
            return json.loads(raw(name))

        inventory = document('inventory.json')
        need(
            set(names) == set(inventory) | {'inventory.json'},
            'Unmanifested evidence')
        for name, entry in inventory.items():
            payload = raw(name)
            need(
                len(payload) == entry['bytes']
                and hashlib.sha256(payload).hexdigest() == entry['sha256'],
                name)
        bridge = document('runs/installed-v2/output/native-source-bridge.json')
        for name, digest in bridge['matching_native_sources'].items():
            need(
                hashlib.sha256(
                    (args.source / name).read_bytes()).hexdigest() == digest,
                'Current native source differs from actual build: ' + name)
        installed = document('evidence-v2/installed-byte-inputs.json')
        matched_python = 0
        for name, entry in installed.items():
            prefix = 'flagtree/profiler/'
            if name.startswith(prefix):
                source = args.source / 'Profiler/python/flagtree_profiler' / name[
                    len(prefix):]
                if source.is_file():
                    need(
                        hashlib.sha256(source.read_bytes()).hexdigest() ==
                        entry['sha256'],
                        'Current Python differs from final installation: ' +
                        name)
                    matched_python += 1

        base = 'runs/followup-v1/output/device/public/timeline/'
        results = []
        for entry in document(base + 'index.json')['captures']:
            capture = document(base + entry['capture_file'])
            decoded = document(base + capture['decoded_file'])
            canonical = document(base + capture['events_file'])
            facts = document(base + capture['async_file'])
            payload = raw(base + capture['raw_file'])
            need(
                hashlib.sha256(payload).hexdigest() == capture['raw_sha256'],
                'Raw SHA mismatch')
            need(decoded['record_version'] == 3 and decoded['complete'],
                 'Missing complete actual v3 records')
            need(facts['model'] == 'nvidia.cp_async.shared_views.v2',
                 'Wrong mechanism model')
            by_offset = {
                row['raw_byte_offset']: row
                for row in decoded['records']
            }
            need(
                len(by_offset) == len(decoded['records']),
                'Aliased actual raw fields')
            for offset, row in by_offset.items():
                tag, low, high, sequence, kind, address, reserved0, reserved1 = struct.unpack_from(
                    '<8I', payload, offset)
                need((tag & 0x7fffffff, (high << 32) | low,
                      sequence) == (row['site'], row['tick'], row['sequence']),
                     'Decoded prefix differs from bytes')
                need(('exit' if tag >> 31 else 'entry') == row['phase']
                     and row['raw_byte_length'] == 32,
                     'Wrong actual phase/extent')
                need(kind in (0, 1) and not reserved0 and not reserved1,
                     'Invalid actual payload')
                association = row['association']
                if kind:
                    need(
                        association == dict(kind='nvidia.shared_view_origin',
                                            address_space=3,
                                            byte_address=address,
                                            raw_byte_offset=offset + 16,
                                            raw_byte_length=16),
                        'Decoded shared view differs from actual payload')
                else:
                    need(not address and association is None,
                         'Absent payload acquired an address')
            sites = {
                site['id']: int(site['backend_site_id'])
                for site in canonical['sites']
            }
            for row in canonical['records']:
                actual = by_offset[row['offset']]
                need((row['length'], sites[row['site_id']], row['phase'],
                      row['sequence'],
                      row['tick']) == (32, actual['site'], actual['phase'],
                                       actual['sequence'], actual['tick']),
                     'Common event reference differs from actual record')
            need(
                len(canonical['records']) == len(by_offset),
                'Common mapping lost physical records')
            for row in facts['records'].values():
                actual = by_offset[row['raw_byte_offset']]
                need(
                    all(row[key] == actual[key] for key in [
                        'program', 'warp', 'sequence', 'site', 'phase', 'tick',
                        'raw_byte_length'
                    ]), 'Mechanism evidence differs from actual record')
            operations = {op['id']: op for op in facts['operations']}
            generations = {
                g['id']: g
                for g in facts['shared_view_generations']
            }
            waits = {wait['id']: wait for wait in facts['waits']}
            for generation in generations.values():
                need(generation['may_be_predicated_empty'] is True,
                     'Attempt became a physical write certificate')
                for submit in generation['submit_operation_ids']:
                    op = operations[submit]
                    need(
                        op['mechanism'] == 'nvidia.cp_async.submit'
                        and op['shared_view']['byte_address']
                        == generation['byte_address'],
                        'Generation does not refer to an actual same-origin submit'
                    )
            for load in facts['shared_view_loads']:
                generation = generations[load['generation_id']]
                op, wait = operations[load['operation_id']], waits[
                    load['wait_operation_id']]
                need(load['status'] == 'same_origin_prior_group_wait_covered',
                     'Missing development load association')
                need(
                    generation['group_id']
                    in wait['newly_guaranteed_group_ids'],
                    'Wait does not cover this group')
                need(
                    generation['byte_address'] == load['byte_address'] ==
                    op['shared_view']['byte_address'],
                    'A generation association crossed actual origins')
                need(
                    all(generation[k] == load[k] == op[k] == wait[k]
                        for k in ['program', 'warp']),
                    'An association crossed recording observers')
                need(operations[wait['id']]['end_tick'] <= op['begin_tick'],
                     'Wait is after the load')
                need(load['time_arrow_verified'] is False,
                     'Unqualified time arrow')
                need(all(r in facts['records'] for r in load['record_ids']),
                     'Dangling mechanism raw reference')
            paths = defaultdict(list)
            for op in operations.values():
                if op['mechanism'] == 'nvidia.shared.load' and op[
                        'program'] == 0 and op['warp'] == 0:
                    paths[str(op['site'])].append(
                        op['shared_view']['byte_address'])
            durations = [
                e['end_tick'] - e['start_tick'] for e in canonical['events']
            ]
            results.append(
                dict(invocation_id=entry['invocation_id'],
                     records=len(by_offset),
                     intervals=len(durations),
                     positive_intervals=sum(v > 0 for v in durations),
                     zero_intervals=sum(v == 0 for v in durations),
                     observers=len(decoded['observers']),
                     committed_attempt_generations=len(generations),
                     loads=len(facts['shared_view_loads']),
                     program0_warp0_load_origins=dict(paths)))

        report = dict(
            status='retained_bytes_and_current_source_bridges_passed_not_P01',
            archive=dict(bytes=args.archive.stat().st_size,
                         sha256=hashlib.sha256(
                             args.archive.read_bytes()).hexdigest(),
                         members=len(names)),
            matching_native_sources=len(bridge['matching_native_sources']),
            matching_installed_python=matched_python,
            installed_core=installed['triton/_C/libtriton.so'],
            captures=results,
            limits=[
                'No source-boundary or ordinary-pipeline certificate',
                'No timer precision or cross-observer epoch certificate',
                'Generations are committed attempts, not certified byte writes or safe reuse',
                'Three-backend qualification and independent six-math matrix remain incomplete'
            ])
        args.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
