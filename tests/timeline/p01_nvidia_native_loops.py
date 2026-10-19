"""Actual native loop paths plus independently requested dynamic trip counts.

Run in the NVIDIA SDK Docker against retained real captures. Expected counts
come from the original workload's runtime arguments, not observed events.
This script never compiles a kernel or replays a mathematical application.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


def run(timelines, expected, kind, member_count, output):
    from flagtree.profiler.timeline_nvidia_late_boundaries import load_native_boundary_report
    from flagtree.profiler.timeline_unit_nvidia_late import load_late_machine_map
    output.mkdir(parents=True)
    results = []
    for timeline in timelines:
        entries = json.loads((timeline / 'index.json').read_text())['captures']
        if len(entries) != len(expected):
            raise RuntimeError(
                'Expected counts differ from actual capture registration')
        for entry, iterations in zip(entries, expected):
            capture = json.loads(
                (timeline / entry['capture_file']).read_text())
            machine = load_late_machine_map(timeline, capture)
            native = load_native_boundary_report(timeline, capture, machine)
            # The registered scalar case has both a two-member recurrence
            # and a one-member final expression outside the loop. Select the
            # original compiler group, never a checker success status.
            requested = {
                site['site_id']
                for site in capture['owner']['plan']['sites']
                if site['kind'] == kind and
                (member_count is None or site['member_count'] == member_count)
            }
            selected = [
                row for row in native['native_loop_sites']
                if row['site_id'] in requested
            ]
            if not selected or any(
                    row['status'] != 'native_iteration_control_checked'
                    for row in selected):
                raise RuntimeError('Actual native iteration path failed: ' +
                                   repr(selected))
            batch = json.loads((timeline / capture['events_file']).read_text())
            raw = (timeline / capture['raw_file']).read_bytes()
            if not batch['complete'] or hashlib.sha256(
                    raw).hexdigest() != capture['raw_sha256']:
                raise RuntimeError(
                    'Actual capture is incomplete or raw bytes differ')
            records = {row['id']: row for row in batch['records']}
            actual = []
            for row in selected:
                sites = [
                    site for site in batch['sites']
                    if site['backend_site_id'] == str(row['site_id'])
                ]
                if len(sites) != 1:
                    raise RuntimeError(
                        'Native loop site has ambiguous canonical identity')
                events = [
                    event for event in batch['events']
                    if event['site_id'] == sites[0]['id']
                ]
                if any(event['kind'] != 'interval' for event in events):
                    raise RuntimeError(
                        'Native loop site contains a non-interval event')
                counts = Counter(event['observer_id'] for event in events)
                if not counts or any(count != iterations
                                     for count in counts.values()):
                    raise RuntimeError(
                        'Runtime trip argument differs from raw occurrences: '
                        + repr(counts))
                for event in events:
                    endpoints = [records[key] for key in event['record_ids']]
                    if len(endpoints) != 2:
                        raise RuntimeError(
                            'Native loop interval lost an endpoint')
                    ticks = [
                        struct.unpack_from('<Q', raw, endpoint['offset'])[0]
                        for endpoint in endpoints
                    ]
                    if ticks != [
                            endpoint['tick'] for endpoint in endpoints
                    ] or ticks != [event['start_tick'], event['end_tick']]:
                        raise RuntimeError(
                            'Actual loop interval differs from raw endpoint words'
                        )
                if row['source_iteration_identity_verified'] or row[
                        'source_cost_qualified']:
                    raise RuntimeError(
                        'Native CFG structure granted unrelated source timing rights'
                    )
                actual.append(
                    dict(site_id=row['site_id'],
                         native_loop=row,
                         actual_intervals=len(events),
                         counts_per_observer=dict(counts)))
            results.append(
                dict(binary_id=capture['owner']['binary_id'],
                     invocation_id=entry['invocation_id'],
                     expected_runtime_iterations=iterations,
                     raw_sha256=capture['raw_sha256'],
                     sites=actual))
    (output / 'result.json').write_text(
        json.dumps(dict(
            status='actual_native_iteration_paths_and_runtime_counts_passed',
            results=results,
            device_executed=False,
            application_replayed=False,
            source_iteration_identity_verified=False),
                   indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline',
                        action='append',
                        type=Path,
                        required=True)
    parser.add_argument(
        '--expected-iterations',
        required=True,
        help='Comma-separated original runtime trip arguments, in capture order'
    )
    parser.add_argument(
        '--kind',
        choices=['matrix_issue_bracket', 'compute_issue_bracket'],
        default='matrix_issue_bracket')
    parser.add_argument('--member-count',
                        type=int,
                        help='Optional registered original LLVM group size')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    expected = [int(value) for value in args.expected_iterations.split(',')]
    if not expected or any(value <= 0 for value in expected):
        raise ValueError('Expected positive runtime trip counts')
    if args.member_count is not None and args.member_count <= 0:
        raise ValueError('Expected positive registered group size')
    run(args.timeline, expected, args.kind, args.member_count, args.output)


if __name__ == '__main__':
    main()
