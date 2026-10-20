"""Check loop context and per-observer summaries against a real raw capture."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-tool', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    clone = args.output / 'timeline'
    shutil.copytree(args.directory, clone)
    from flagtree.profiler.timeline_capture_store import load_capture
    from flagtree.profiler.timeline_ascend_fragment_store import load_fragment_paths, _attach_observations
    from flagtree.profiler.timeline_ascend_offline import decode_capture
    capture = load_capture(clone, args.capture)
    raw_file = clone / capture['raw_file']
    raw = raw_file.read_bytes()
    batch = decode_capture(capture, raw)
    status = load_fragment_paths(clone, capture)
    report = json.loads((clone / status['report_file']).read_text())
    if report['model'] != 'ascend.fragment_path_report.v2' or report[
            'invocation_id'] != capture['owner']['invocation_id'] or report[
                'raw_sha256'] != hashlib.sha256(raw).hexdigest():
        raise RuntimeError(
            'Observation report is not bound to this actual invocation/raw')
    sites = {row['id']: row for row in batch['sites']}
    observers = {row['id']: row for row in batch['observers']}
    checked_observers, loop_regions, repeated_loop_regions, selected_brackets = 0, 0, 0, 0
    repeated_checked_regions = []
    for actor in report['actors']:
        for region in actor['regions']:
            observation = region['observations']
            events = [
                event for event in batch['events']
                if event['kind'] == 'interval' and sites[event['site_id']]
                ['backend_site_id'] == observation['backend_site_id']
            ]
            if observation['interval_count'] != len(
                    events) or observation['positive_interval_count'] != sum(
                        e['end_tick'] > e['start_tick'] for e in events):
                raise RuntimeError(
                    'Region summary differs from fresh raw intervals')
            for row in observation['observers']:
                actual = [
                    e for e in events if e['observer_id'] == row['observer_id']
                ]
                observer = observers[row['observer_id']]
                first_event = min(actual, key=lambda e: e['start_tick'])
                last_event = max(actual, key=lambda e: e['end_tick'])
                if (row['interval_count'] != len(actual)
                        or row['elapsed_ticks_sum'] != sum(
                            e['end_tick'] - e['start_tick'] for e in actual)
                        or row['first_tick'] != min(e['start_tick']
                                                    for e in actual)
                        or row['last_tick'] != max(e['end_tick']
                                                   for e in actual)
                        or row['first_event_id'] != first_event['id']
                        or row['first_record_ids'] != first_event['record_ids']
                        or row['last_event_id'] != last_event['id']
                        or row['last_record_ids'] != last_event['record_ids']
                        or row['clock_domain_id']
                        != observer['clock_domain_id']
                        or row['epoch_id'] != observer['epoch_id']
                        or row['complete'] != observer['complete']
                        or row['time_unit'] != 'raw_counter_ticks'
                        or row['source_iteration_ids_verified'] is not False):
                    raise RuntimeError(
                        'Observer summary merged clocks or changed actual durations'
                    )
                checked_observers += 1
            context = region.get('adapted_loop_context', {})
            if context.get('status') == 'indexed_natural_loop_context':
                loop_regions += 1
                if context[
                        'source_iteration_ids_verified'] is not False or context[
                            'trip_count_verified'] is not False or region[
                                'loop_verified'] is not False:
                    raise RuntimeError(
                        'Loop context was promoted to iteration/trip proof')
                if any(row['interval_count'] > 1
                       and row['positive_interval_count'] > 1
                       for row in observation['observers']):
                    repeated_loop_regions += 1
                if region['selected_loop_bracket'][
                        'status'] == 'selected_llvm_bracket_within_iteration':
                    selected_brackets += 1
                    repeated = [
                        row['observer_id'] for row in observation['observers']
                        if row['positive_interval_count'] > 1
                    ]
                    if repeated:
                        repeated_checked_regions.append(
                            dict(function=actor['function'],
                                 site_id=region['site_id'],
                                 observer_ids=repeated))
    if not checked_observers or not loop_regions or not repeated_loop_regions:
        raise RuntimeError(
            'Actual capture lacks repeated positive source intervals in a loop'
        )
    if not selected_brackets or not repeated_checked_regions:
        raise RuntimeError(
            'Actual loop has no selected endpoint-to-end path proof')
    # A legal paired stream can have nonmonotonic starts (nested intervals).
    # The temporal bounds must retain references to their own source records.
    nested = copy.deepcopy(batch)
    selected_site = next(region['observations']['canonical_site_id']
                         for actor in report['actors']
                         for region in actor['regions']
                         if region['observations']['interval_count'])
    template = next(
        e for e in nested['events']
        if e['kind'] == 'interval' and e['site_id'] == selected_site)
    nested['events'] = []
    for identity, start, end in [('outer-first', 20, 30),
                                 ('outer-second', 10, 40), ('tie', 10, 40)]:
        event = copy.deepcopy(template)
        event.update(id=identity,
                     start_tick=start,
                     end_tick=end,
                     record_ids=[identity + '-begin', identity + '-end'])
        nested['events'].append(event)
    nested_reports = copy.deepcopy(report['actors'])
    _attach_observations(nested_reports, nested,
                         capture['metadata']['compiler_metadata'])
    nested_rows = [
        row for actor in nested_reports for region in actor['regions']
        for row in region['observations']['observers']
    ]
    if len(nested_rows) != 1:
        raise RuntimeError(
            'Nested interval fixture has an ambiguous source join')
    row = nested_rows[0]
    if (row['first_tick'], row['last_tick'], row['first_event_id'],
            row['last_event_id'], row['first_record_ids'],
            row['last_record_ids']) != (10, 40, 'outer-second', 'outer-second',
                                        [
                                            'outer-second-begin',
                                            'outer-second-end'
                                        ], [
                                            'outer-second-begin',
                                            'outer-second-end'
                                        ]):
        raise RuntimeError(
            'Temporal bounds refer to different events or tie order changed')
    empty = copy.deepcopy(batch)
    empty['events'] = []
    missing = copy.deepcopy(report['actors'])
    _attach_observations(missing, empty,
                         capture['metadata']['compiler_metadata'])
    if any(r['observations']['status'] != 'not_observed' or r['observations']
           ['observers'] or r['observations']['interval_count']
           for a in missing for r in a['regions']):
        raise RuntimeError(
            'Missing observations were filled with synthetic intervals')
    wrong = copy.deepcopy(batch)
    first = next(s for s in wrong['sites']
                 if s['attributes'].get('ascend.source_op_id') is not None)
    first['attributes']['ascend.source_op_id'] += 1000000
    try:
        _attach_observations(copy.deepcopy(report['actors']), wrong,
                             capture['metadata']['compiler_metadata'])
    except ValueError:
        wrong_site_rejected = True
    else:
        raise RuntimeError('Incorrect canonical source site accepted')
    raw_file.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    try:
        load_fragment_paths(clone, capture)
    except ValueError:
        changed_raw_rejected = True
    else:
        raise RuntimeError('Different raw bytes accepted')
    finally:
        raw_file.write_bytes(raw)
    from flagtree.profiler import timeline_ascend_loops, timeline_ascend_fragments
    case_path = Path(__file__).with_name('ascend_loop_rule_cases.py')
    spec = importlib.util.spec_from_file_location('native_loop_cases',
                                                  case_path)
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    tool = args.native_tool or Path(timeline_ascend_loops.__file__
                                    ).parent / 'lib/flagprism-ascend-structure'
    loop_cases = cases.check_native_loop_cases(timeline_ascend_loops,
                                               timeline_ascend_fragments, tool,
                                               args.output / 'loop-cases')
    (args.output / 'result.json').write_text(
        json.dumps(dict(status='real_raw_fragment_observations_checked',
                        raw_sha256=hashlib.sha256(raw).hexdigest(),
                        checked_observer_summaries=checked_observers,
                        loop_regions=loop_regions,
                        repeated_positive_loop_regions=repeated_loop_regions,
                        selected_loop_brackets=selected_brackets,
                        repeated_checked_regions=repeated_checked_regions,
                        nested_interval_references_checked=True,
                        native_loop_cases=loop_cases,
                        not_observed_preserved=True,
                        wrong_site_rejected=wrong_site_rejected,
                        changed_raw_rejected=changed_raw_rejected,
                        source_iteration_ids_verified=False,
                        device_executed=False),
                   indent=2))


if __name__ == '__main__':
    main()
