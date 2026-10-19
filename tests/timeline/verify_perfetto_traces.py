"""Independent generated-protobuf and pinned real Trace Processor validation.

Run in the server tools venv. This script does not import FlagPrism or replay
applications; input views retain their actual raw identities and proof limits.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    from perfetto.protos.perfetto.trace import perfetto_trace_pb2 as proto
    from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig
    tool = Path(
        '/workspace/chijin-timeline-r011/tools-input/trace_processor_shell')
    need(
        hashlib.sha256(tool.read_bytes()).hexdigest() ==
        '55ba613fc6d4f71df81eee2dbfc293020063655c241b3e314bff75345b802684',
        'Pinned TP changed')
    manifest = json.loads(args.manifest.read_text())
    checks = []
    for item in manifest:
        path = Path(item['trace_file'])
        view = json.loads(Path(item['view_file']).read_text())
        shared = view.get('coordinate_system'
                          ) == 'single_invocation_program_shared_counter_ns'
        if shared:
            need(
                view.get('schema_version') == 2
                and view.get('counter_epoch_shared') is True
                and view.get('physical_temporal_comparison_verified') is False
                and view.get('time_arrows_verified') is False,
                'Shared coordinates falsely claim physical timing rights')
            for record in view['records']:
                need(
                    record['relative_ns'] == (record['tick'] -
                                              view['origin_tick']) *
                    view['unit_proof']['period_numerator_ns'] //
                    view['unit_proof']['period_denominator'],
                    'Shared coordinate independently zeroed an observer')
        raw = path.read_bytes()
        if item.get('raw_file'):
            observed = Path(item['raw_file']).read_bytes()
            need(
                hashlib.sha256(observed).hexdigest() == view['raw_artifact']
                ['sha256'], 'Retained raw input changed')
            original = json.loads(Path(item['canonical_file']).read_text())
            by_id = {row['id']: row for row in original['records']}
            selected_ids = ({row['id']
                             for row in view['observers']}
                            if shared else {view['observer']['id']})
            selected_records = [
                row for row in original['records']
                if row['observer_id'] in selected_ids
            ]
            need(
                view['origin_tick'] == min(row['tick']
                                           for row in selected_records),
                'Counter view invented a different origin')
            period = view['unit_proof']
            for record in view['records']:
                actual = by_id[record['id']]
                need(
                    struct.unpack_from('<Q', observed, actual['offset'])[0] ==
                    actual['tick'] == record['tick'],
                    'View record is not its actual raw counter word')
                need(
                    record['relative_ns'] == (actual['tick'] -
                                              view['origin_tick']) *
                    period['period_numerator_ns'] //
                    period['period_denominator'],
                    'View coordinate differs from independently converted raw ticks'
                )
            records = {row['id']: row for row in view['records']}
            for event in view['events']:
                refs = [records[key] for key in event['record_ids']]
                expected_end = refs[-1]['relative_ns'] if event[
                    'kind'] == 'interval' else None
                need(
                    event['start_ns'] == refs[0]['relative_ns']
                    and event['end_ns'] == expected_end,
                    'View event differs from its actual endpoint coordinates')
        need(
            hashlib.sha256(raw).hexdigest() == item['sha256'],
            'Trace changed before importer')
        trace = proto.Trace()
        trace.ParseFromString(raw)
        timed = [p for p in trace.packet if p.HasField('track_event')]
        need(timed and all(p.timestamp_clock_id == 11 for p in timed),
             'Not isolated trace-file ns clock')
        need(trace.packet[0].clock_snapshot.primary_trace_clock == 11,
             'Wrong primary trace clock')
        expected_packets = sum(2 if e['kind'] == 'interval' else 1
                               for e in view['events'])
        need(
            len(timed) == expected_packets,
            'Generated protobuf lost endpoint packets')
        need(
            all(not p.track_event.flow_ids
                and not p.track_event.terminating_flow_ids
                for p in timed), 'Unit-only coordinates gained time flows')
        config = TraceProcessorConfig(bin_path=str(tool),
                                      unique_port=True,
                                      fetch_latest_trace_processor=False,
                                      load_timeout=20)
        with TraceProcessor(trace=str(path), config=config) as tp:
            query = '''SELECT ts, dur, name,
                extract_arg(arg_set_id, 'debug.event_id') AS event_id,
                extract_arg(arg_set_id, 'debug.raw_record_ids') AS raw_record_ids,
                extract_arg(arg_set_id, 'debug.time_quality') AS time_quality,
                extract_arg(arg_set_id, 'debug.unit_provider') AS unit_provider,
                extract_arg(arg_set_id, 'debug.observer_id') AS observer_id,
                extract_arg(arg_set_id, 'debug.counter_domain_id') AS counter_domain_id,
                extract_arg(arg_set_id, 'debug.shared_origin_tick') AS shared_origin_tick
                FROM slice ORDER BY ts, id'''
            rows = list(tp.query(query))
            need(
                len(rows) == len(view['events']),
                'TP lost or invented a slice/instant')
            expected = {e['id']: e for e in view['events']}
            seen = set()
            for row in rows:
                need(row.event_id in expected and row.event_id not in seen,
                     'TP event identity mismatch')
                seen.add(row.event_id)
                event = expected[row.event_id]
                duration = event['end_ns'] - event['start_ns'] if event[
                    'kind'] == 'interval' else 0
                need(row.ts == event['start_ns'] and row.dur == duration,
                     'TP changed exact ns endpoints')
                need(
                    json.loads(row.raw_record_ids) == event['record_ids'],
                    'TP lost raw field references')
                need(
                    row.time_quality
                    == ('shared_counter_epoch_precision_unverified' if shared
                        else 'counter_unit_only_precision_unverified')
                    and row.unit_provider == view['unit_proof']['provider'],
                    'TP lost qualification/provenance limits')
                need(row.observer_id == event['observer_id'],
                     'TP changed actual observer identity')
                if shared:
                    need(
                        row.counter_domain_id == view['domain_id']
                        and row.shared_origin_tick == str(view['origin_tick']),
                        'TP lost shared epoch/origin provenance')
            if shared:
                need({row.observer_id
                      for row in rows} == {o['id']
                                           for o in view['observers']},
                     'TP lost one of the shared observer tracks')
            bad = [
                dict(name=row.name, value=row.value, severity=row.severity)
                for row in tp.query(
                    "SELECT name,value,severity FROM stats WHERE value>0 AND severity IN ('error','data_loss')"
                )
            ]
            need(not bad, 'Actual importer errors/data loss: ' + repr(bad))
            flow = list(tp.query('SELECT count(*) AS n FROM flow'))[0].n
            need(flow == 0, 'Unit-only trace invented flows')
        checks.append(
            dict(trace_file=str(path),
                 sha256=item['sha256'],
                 fixture=item.get('fixture', False),
                 slices=len(rows),
                 protobuf_packets=len(timed),
                 exact_ns_and_raw_references=True,
                 importer_errors=bad,
                 flows=flow))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'generated_protobuf_and_real_TP_exact_counter_ns_passed_not_full_P01',
            checks=checks,
            clock_precision_qualified=False,
            source_boundaries_qualified=False,
            async_qualified=False,
            UI_qualified=False),
                   indent=2) + '\n')


if __name__ == '__main__':
    main()
