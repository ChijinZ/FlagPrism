"""Check the automatic matrix rule against retained actual captures and raw.

Run in the SDK Docker. No application execution or compilation is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def run(timelines, output):
    from flagtree.profiler import timeline_unit_nvidia_late as units
    from flagtree.profiler.timeline_nvidia_late_boundaries import derive_native_boundaries
    output.mkdir(parents=True)
    reports = []
    for timeline in timelines:
        index = json.loads((timeline / 'index.json').read_text())
        for entry in index['captures']:
            from flagtree.profiler.timeline_capture_store import load_capture_file
            capture = load_capture_file(timeline / entry['capture_file'])
            machine = units.load_late_machine_map(timeline, capture)
            base = timeline / 'machine' / capture['owner']['binary_id']
            ptx = [
                r for r in capture['metadata']['timeline_artifacts']
                if r['retained_file'].endswith('.ptx')
            ]
            if len(ptx) != 1:
                raise RuntimeError('Ambiguous actual retained PTX')
            report = derive_native_boundaries(
                machine_map=machine,
                sass_lines=(base / 'lines.stdout').read_bytes(),
                sass_json=(base / 'json.stdout').read_bytes(),
                ptx=(timeline / ptx[0]['retained_file']).read_bytes(),
                plan=capture['owner']['plan'])
            selected = report['matrix_issue_sites']
            if not selected or any(
                    r['status'] != 'matrix_issue_control_order_checked'
                    for r in selected):
                raise RuntimeError('Actual automatic matrix rule failed: ' +
                                   repr(selected))
            batch = json.loads((timeline / capture['events_file']).read_text())
            raw = (timeline / capture['raw_file']).read_bytes()
            if not batch['complete'] or hashlib.sha256(
                    raw).hexdigest() != capture['raw_sha256']:
                raise RuntimeError('Actual raw capture changed/incomplete')
            records = {r['id']: r for r in batch['records']}
            event_count = 0
            for row in selected:
                sites = [
                    s for s in batch['sites']
                    if s['backend_site_id'] == str(row['site_id'])
                ]
                if len(sites) != 1:
                    raise RuntimeError('Native site lost canonical navigation')
                events = [
                    e for e in batch['events']
                    if e['site_id'] == sites[0]['id']
                ]
                if len(events) < 2:
                    raise RuntimeError(
                        'Missing actual repeated matrix intervals')
                for event in events:
                    endpoints = [records[key] for key in event['record_ids']]
                    if len(endpoints
                           ) != 2 or event['end_tick'] <= event['start_tick']:
                        raise RuntimeError(
                            'Matrix interval is not positive/paired')
                    for endpoint in endpoints:
                        if struct.unpack_from(
                                '<Q', raw,
                                endpoint['offset'])[0] != endpoint['tick']:
                            raise RuntimeError('Actual endpoint word differs')
                    if [r['tick'] for r in endpoints
                        ] != [event['start_tick'], event['end_tick']]:
                        raise RuntimeError(
                            'Matrix event differs from actual endpoints')
                event_count += len(events)
            reports.append(
                dict(binary_id=capture['owner']['binary_id'],
                     invocation_id=capture['owner']['invocation_id'],
                     matrix_sites=selected,
                     actual_matrix_intervals=event_count,
                     raw_sha256=capture['raw_sha256']))
    (output / 'result.json').write_text(
        json.dumps(dict(
            status='actual_automatic_matrix_issue_boundaries_and_raw_passed',
            reports=reports,
            device_executed=False,
            application_replayed=False,
            source_exclusive_cost_qualified=False,
            ordinary_overlap_preservation_qualified=False),
                   indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline',
                        action='append',
                        type=Path,
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.timeline, args.output)


if __name__ == '__main__':
    main()
