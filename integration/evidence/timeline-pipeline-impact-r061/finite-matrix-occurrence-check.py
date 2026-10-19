"""Finite, retained-device evidence check; no compilation or application replay."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from flagtree.profiler import timeline_unit_nvidia_late as units
from flagtree.profiler.timeline_nvidia_control import _bound_functions
from flagtree.profiler.timeline_nvidia_late_boundaries import _native_lines, _straight_path
from flagtree.profiler.timeline_nvidia_machine import _lex


def need(value, message):
    if not value:
        raise RuntimeError(message)


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True)
root = Path('/workspace/chijin-timeline-r061-nvidia/runs')
reports = []
for mode, case in [('default', 'budget-pipeline-v1'), ('sparse', 'sparse-pipeline-v1')]:
    device = root / case / 'output/device'
    timeline = device / 'profile/timeline'
    math_file = device / 'math.json'
    math = json.loads(math_file.read_text())
    profiles = [row for row in math if row['phase'] == 'profile']
    need(len(profiles) == 2 and [r['tiles'] for r in profiles] == [3, 7],
         'Original runtime-K mathematical calls differ')
    index_file = timeline / 'index.json'
    index = json.loads(index_file.read_text())
    need(len(index['captures']) == 2 and not index['failures'], 'Original capture count differs')
    for item, call in zip(index['captures'], profiles):
        capture_file = timeline / item['capture_file']
        capture = json.loads(capture_file.read_text())
        binary = capture['owner']['binary_id']
        need(binary == call['hash'], 'Capture is not the actual mathematical binary')
        machine = units.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / binary
        native_text = base / 'lines.stdout'
        native_json = base / 'json.stdout'
        text, structured = native_text.read_bytes(), native_json.read_bytes()
        functions = _bound_functions(machine, text, structured)
        native_lines = _native_lines(text, functions)
        ptx_rows = [r for r in capture['metadata']['timeline_artifacts'] if r['retained_file'].endswith('.ptx')]
        need(len(ptx_rows) == 1, 'Ambiguous retained PTX')
        ptx_file = timeline / ptx_rows[0]['retained_file']
        ptx = ptx_file.read_bytes()
        tokens, _ = _lex(ptx.decode(), 'late-v1')
        plan = capture['owner']['plan']
        sites = [s for s in plan['sites'] if s['kind'] == 'matrix_issue_bracket']
        need(len(sites) == 1, 'This finite example must have one grouped matrix site')
        site = sites[0]
        readers = {r['phase']: r for r in machine['counter_pcs'] if r['site_id'] == site['site_id']}
        begin, end = readers['entry'], readers['exit']
        need(begin['function'] == end['function'] and begin['sass_predicate'] is None
             and end['sass_predicate'] is None, 'Readers are conditional or split')
        body = functions[begin['function']]
        _straight_path(body, begin['pc'], end['pc'])
        expected = [(i + 1, tokens[i]) for i in range(begin['ptx_line'], end['ptx_line'] - 1)
                    if tokens[i].startswith('mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32')]
        need(len(expected) == len(site['members']) == 4, 'Actual grouped FP16/F32 matrix operations differ')
        native_pcs = []
        for line, operation in expected:
            matches = [pc for pc in native_lines.get((begin['function'], line), [])
                       if body[pc]['opcode'] == 'HMMA.16816.F32']
            need(len(matches) == 1, 'PTX matrix operation lacks a unique native issue')
            pc = matches[0]
            need(begin['pc'] < pc < end['pc'] and body[pc].get('predicate') is None,
                 'Actual matrix operation moved outside its unconditional readers')
            native_pcs.append(pc)
        need(len(set(native_pcs)) == 4, 'Different PTX operations alias one native issue')
        actual = [pc for pc, row in body.items() if begin['pc'] < pc < end['pc']
                  and row['opcode'].startswith(('HMMA', 'IMMA', 'MMA'))]
        need(sorted(actual) == sorted(native_pcs), 'Unbound matrix issue inside bracket')
        events_file = timeline / capture['events_file']
        batch = json.loads(events_file.read_text())
        raw_file = timeline / capture['raw_file']
        raw = raw_file.read_bytes()
        need(batch['complete'] and hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
             'Retained raw or completeness differs')
        canonical_sites = [s for s in batch['sites'] if s['backend_site_id'] == str(site['site_id'])]
        need(len(canonical_sites) == 1, 'Missing actual matrix event site')
        sid = canonical_sites[0]['id']
        records = {r['id']: r for r in batch['records']}
        events = [e for e in batch['events'] if e['site_id'] == sid]
        durations = []
        observers = []
        for observer in batch['observers']:
            selected = [e for e in events if e['observer_id'] == observer['id']]
            need(len(selected) == call['tiles'], 'Observed matrix occurrence count differs from runtime tiles')
            need(sorted(e['occurrence'] for e in selected) == list(range(call['tiles'])),
                 'Occurrence identity is incomplete')
            need(all(e['iteration_id'] is None for e in selected), 'Occurrence was silently promoted to loop iteration identity')
            for event in selected:
                need(event['kind'] == 'interval' and len(event['record_ids']) == 2,
                     'Actual grouped issue is not an interval')
                first, last = [records[k] for k in event['record_ids']]
                for record in [first, last]:
                    need(struct.unpack_from('<Q', raw, record['offset'])[0] == record['tick'],
                         'Canonical endpoint is not its actual raw timestamp word')
                need(first['tick'] == event['start_tick'] and last['tick'] == event['end_tick']
                     and last['tick'] > first['tick'], 'Matrix interval endpoints or positive duration differ')
                durations.append(last['tick'] - first['tick'])
            observers.append(dict(observer_id=observer['id'],occurrences=len(selected)))
        used = [index_file, math_file, capture_file, events_file, raw_file, ptx_file,
                native_text, native_json, base / 'counter-map.json']
        reports.append(dict(mode=mode, tiles=call['tiles'], binary_id=binary,
                            invocation_id=item['invocation_id'], site_id=site['site_id'],
                            source_members=site['members'], begin_reader_pc=begin['pc'],
                            end_reader_pc=end['pc'], native_matrix_pcs=native_pcs,
                            native_single_entry_straight_path_checked=True,
                            observers=observers, positive_intervals=len(durations),
                            min_duration_ticks=min(durations), max_duration_ticks=max(durations),
                            input_seals={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in used}))
need(len(reports) == 4, 'Wrong existing-capture denominator')
for report in reports:
    for path, digest in report['input_seals'].items():
        need(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'Original input mutated')
result = dict(status='actual_four_retained_matrix_issue_and_occurrence_checks_passed',
              application_replayed=False, device_executed=False, compiler_invoked=False,
              product_changed=False, source_exclusive_cost_qualified=False,
              engine_completion_qualified=False, ordinary_overlap_preservation_qualified=False,
              scope='Finite actual FP16/F32 matrix issue placement and runtime occurrence evidence only; not an arbitrary-kernel certificate',
              reports=reports)
(args.output / 'result.json').write_text(json.dumps(result, indent=2))
