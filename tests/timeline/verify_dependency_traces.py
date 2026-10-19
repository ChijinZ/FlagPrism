"""Independently import real dependency traces and compare SQL with raw records.
Run in the server Perfetto tools environment; no product import or device replay.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from collections import Counter

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--timeline', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
from perfetto.protos.perfetto.trace import perfetto_trace_pb2 as proto
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

root = a.timeline.resolve()
reports = []
for item in json.loads((root / 'index.json').read_text())['captures']:
    cap = json.loads((root / item['capture_file']).read_text())
    if cap.get('observed_dependency_exports'):
        reports.append(
            dict(identity=cap['owner']['invocation_id'],
                 exports=cap['observed_dependency_exports']))
if not reports:
    raise RuntimeError('No real observed dependency exports')
summary = dict(reports=reports)
exe = Path('/workspace/chijin-timeline-r011/tools-input/trace_processor_shell')
if hashlib.sha256(exe.read_bytes()).hexdigest(
) != '55ba613fc6d4f71df81eee2dbfc293020063655c241b3e314bff75345b802684':
    raise RuntimeError('Actual TP changed')
caps = {}
for item in json.loads((root / 'index.json').read_text())['captures']:
    cap = json.loads((root / item['capture_file']).read_text())
    caps[cap['owner']['invocation_id']] = cap
checks = []
for report in summary['reports']:
    cap = caps[report['identity']]
    raw = (root / cap['raw_file']).read_bytes()
    for item in report['exports']:
        path = root / item['trace_file']
        view = json.loads((root / item['view_file']).read_text())
        data = path.read_bytes()
        if hashlib.sha256(
                data).hexdigest() != item['sha256'] or hashlib.sha256(
                    raw).hexdigest() != view['raw_artifact']['sha256']:
            raise RuntimeError('Source bytes changed')
        inputs = json.loads((root / Path(item['receipt_file']).parent /
                             'inputs.json').read_text())
        clock = next((r['clock'] for r in inputs['proofs']
                      if r['clock']['domain_id'] == view['domain_id']))
        for n in view['nodes']:
            if n['raw_length'] != 8 or struct.unpack_from(
                    '<Q', raw, n['raw_offset']
            )[0] != n['tick'] or n['time_ns'] != (
                    n['tick'] - view['origin_tick']
            ) * clock['period_numerator_ns'] // clock['period_denominator']:
                raise RuntimeError('Raw endpoint/scale differs')
        trace = proto.Trace()
        trace.ParseFromString(data)
        starts = Counter((i for packet in trace.packet
                          for i in packet.track_event.flow_ids))
        ends = Counter((i for packet in trace.packet
                        for i in packet.track_event.terminating_flow_ids))
        expected = Counter((int.from_bytes(
            hashlib.sha256(e['id'].encode()).digest()[:8], 'little') or 1
                            for e in view['edges']))
        if starts != expected or ends != expected:
            raise RuntimeError('Actual fixed64 protobuf flows differ')
        with TraceProcessor(trace=str(path),
                            config=TraceProcessorConfig(
                                bin_path=str(exe),
                                unique_port=True,
                                fetch_latest_trace_processor=False,
                                load_timeout=20)) as tp:
            ns = list(
                tp.query(
                    "SELECT ts,dur,extract_arg(arg_set_id,'debug.node_id') AS node_id,extract_arg(arg_set_id,'debug.raw_tick') AS raw_tick,extract_arg(arg_set_id,'debug.raw_offset') AS raw_offset FROM slice WHERE extract_arg(arg_set_id,'debug.node_id') IS NOT NULL"
                ))
            wanted = {n['id']: n for n in view['nodes']}
            if len(ns) != len(wanted) or len({r.node_id
                                              for r in ns}) != len(wanted):
                raise RuntimeError('TP lost/invented dependency endpoints')
            for row in ns:
                n = wanted[row.node_id]
                if row.ts != n[
                        'time_ns'] or row.dur != 0 or row.raw_tick != str(
                            n['tick']) or (row.raw_offset != n['raw_offset']):
                    raise RuntimeError('Actual TP changed raw endpoint/time')
            flows = list(
                tp.query(
                    "SELECT extract_arg(a.arg_set_id,'debug.node_id') AS source_node,extract_arg(b.arg_set_id,'debug.node_id') AS target_node,a.ts AS source_ns,b.ts AS target_ns FROM flow f JOIN slice a ON f.slice_out=a.id JOIN slice b ON f.slice_in=b.id"
                ))
            if Counter(
                ((r.source_node, r.target_node) for r in flows)) != Counter(
                    ((e['source'], e['target']) for e in view['edges'])):
                raise RuntimeError('Actual TP flow direction/count differs')
            if any((r.source_ns > r.target_ns for r in flows)):
                raise RuntimeError(
                    'Actual TP flow reverses observed counter order')
            canonical = json.loads(
                (root / Path(item['view_file']).parent.parent /
                 'canonical.json').read_text())
            records = {r['id']: r for r in canonical['records']}
            wanted_events = {
                e['id']: e
                for e in canonical['events']
                if e['observer_id'] in clock['observer_ids']
            }
            intervals = list(
                tp.query(
                    "SELECT ts,dur,extract_arg(arg_set_id,'debug.event_id') AS event_id FROM slice WHERE extract_arg(arg_set_id,'debug.event_id') IS NOT NULL AND extract_arg(arg_set_id,'debug.node_id') IS NULL"
                ))
            if len(intervals) != len(wanted_events) or len(
                {r.event_id
                 for r in intervals}) != len(wanted_events):
                raise RuntimeError('TP lost/invented observed internal events')
            positive = 0
            for row in intervals:
                event = wanted_events[row.event_id]
                refs = [records[key] for key in event['record_ids']]
                times = [
                    (r['tick'] - view['origin_tick']) *
                    clock['period_numerator_ns'] // clock['period_denominator']
                    for r in refs
                ]
                duration = times[-1] - times[0] if event[
                    'kind'] == 'interval' else 0
                if row.ts != times[0] or row.dur != duration:
                    raise RuntimeError(
                        'TP internal interval differs from original endpoints')
                positive += int(row.dur > 0)
            if positive < 2:
                raise RuntimeError(
                    'Nontrivial dependency trace needs multiple positive internal intervals'
                )
            errors = [
                dict(name=r.name, value=r.value, severity=r.severity)
                for r in tp.query(
                    "SELECT name,value,severity FROM stats WHERE value>0 AND severity IN ('error','data_loss')"
                )
            ]
            if errors:
                raise RuntimeError('Actual TP errors ' + repr(errors))
        checks.append(
            dict(trace=str(path),
                 sha256=item['sha256'],
                 nodes=len(ns),
                 flows=len(flows),
                 internal_events=len(intervals),
                 positive_internal_intervals=positive,
                 raw_offsets_ticks_ns_exact=True,
                 protobuf_fixed64_exact=True,
                 importer_errors=errors))
        print(json.dumps(checks[-1]))
(a.output / 'result.json').write_text(
    json.dumps(dict(
        status=
        'actual_dependency_traces_raw_internal_intervals_protobuf_TP_flows_passed_not_full_goal',
        checks=checks),
               indent=2))
