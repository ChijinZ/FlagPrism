"""Program-associated observation views with explicit clock and join boundaries."""
from collections import defaultdict
from html import escape
import json
from pathlib import Path

from .observations import observation


def reconstruct(payload, launches, binaries, native_events):
    launch_map = {row['id']: row for row in launches}
    binary_map = {row['id']: row for row in binaries}
    groups, rejected = defaultdict(list), []
    for raw in payload.get('observations', []):
        try:
            record = observation(raw)
        except (ValueError, TypeError, KeyError) as error:
            rejected.append({'original_record': raw, 'reason': str(error)})
            continue
        launch = launch_map.get(record.get('invocation_id'))
        evidence = record.get('association_evidence') or {}
        linked = record[
            'association_status'] == 'verified' and launch is not None
        if linked and (launch.get('status') == 'rejected_before_launch' or
                       (evidence.get('binary_id') is not None
                        and evidence['binary_id'] != launch.get('binary_id'))):
            linked = False
        record[
            'reconstruction_association'] = 'verified' if linked else 'unassociated'
        record['binary_id'] = launch.get('binary_id') if linked else None
        record['source_available'] = record['binary_id'] in binary_map
        source_sites = ((binary_map.get(record['binary_id'],
                                        {}).get('execution_manifest')
                         or {}).get('source_operations', []))
        matches = [
            site for site in source_sites if str(
                site.get('opId', site.get('op_id'))) == str(record.get('site'))
        ]
        # Native late sites and Proton scope IDs occupy different namespaces.
        # Only Debugger's actual assigned op IDs use this source table.
        record['source_site'] = (
            matches[0] if len(matches) == 1 and record['source']
            in {'flagtree_ir_snapshot', 'flagtree_ir_dynamic'} else None)
        record['source_site_association'] = ('compiler_assigned_observer_id'
                                             if record['source_site'] else
                                             'partial')
        compiler_site = record.get('compiler_site')
        if not isinstance(compiler_site, dict):
            compiler_site = {}
        region_origin = None
        if (linked and record['source_available']
                and compiler_site.get('kind') == 'explicit_proton_scope'
                and compiler_site.get('binary_id') == record['binary_id']
                and compiler_site.get('scope_id') == record.get('site')
                and isinstance(compiler_site.get('origin'), dict)):
            region_origin = compiler_site['origin']
        record['source_region_origin'] = region_origin
        record['source_region_origin_status'] = (region_origin.get(
            'status', 'unknown') if region_origin else 'unassociated')
        clock = record.get('clock') or {}
        key = (record['capture_id'],
               record.get('invocation_id') if linked else None,
               record.get('program'),
               json.dumps(record.get('actor', record.get('actor_slot')),
                          sort_keys=True), clock.get('domain'),
               clock.get('scope'))
        groups[key].append(record)
    result = []
    for index, (key, records) in enumerate(groups.items()):
        invocation = key[1]
        result.append({
            'id':
            index,
            'capture_id':
            key[0],
            'invocation_id':
            invocation,
            'program':
            key[2],
            'actor':
            json.loads(key[3]),
            'clock_domain':
            key[4],
            'clock_scope':
            key[5],
            'binary_id':
            records[0]['binary_id'],
            'observations':
            records,
            'native_event_ids': [
                event['id'] for event in native_events if
                invocation is not None and event.get('launch_id') == invocation
            ],
            'time_relation':
            'separate_clock_frame',
            'limits': [
                'Invocation association does not establish timestamp alignment.',
                'Inclusive source intervals are not an exclusive engine pipeline.'
            ],
        })
    alignment_candidates = defaultdict(list)
    for group in result:
        clocks = [record.get('clock') for record in group['observations']]
        if not clocks or any(clock is None for clock in clocks):
            continue
        clock = clocks[0]
        proof = clock.get('alignment_evidence') or {}
        if (clock.get('alignment') == 'verified_shared'
                and group['invocation_id'] and isinstance(proof, dict)
                and proof.get('invocation_id') == group['invocation_id']
                and all(candidate == clock for candidate in clocks)):
            alignment_candidates[(group['invocation_id'],
                                  json.dumps(clock,
                                             sort_keys=True))].append(group)
    alignment_sets = []
    for index, ((invocation, _),
                members) in enumerate(alignment_candidates.items()):
        clock = members[0]['observations'][0]['clock']
        starts = [
            event['start_tick'] for group in members
            for event in group['observations']
            if event.get('start_tick') is not None
        ]
        alignment_sets.append({
            'id':
            index,
            'invocation_id':
            invocation,
            'group_ids': [group['id'] for group in members],
            'clock':
            clock,
            'display_origin_tick':
            min(starts) if starts else None,
            'display_origin_basis':
            'first_observed_control_event',
            'limits': [
                'Shared control timestamps do not measure hardware engine occupancy.'
            ]
        })
        for group in members:
            group['time_relation'] = 'verified_shared_control_clock'
            group['alignment_set_id'] = index
    return {
        'schema_version':
        1,
        'groups':
        result,
        'alignment_sets':
        alignment_sets,
        'rejected':
        rejected,
        'captures':
        payload.get('captures', []),
        'limits': [
            'No name/order association or duration scaling is performed.',
            'Independent counter replays remain in counter_groups.json.'
        ]
    }


def render(document):
    panels = []
    failures = [
        capture for capture in document.get('captures', [])
        if capture.get('capture_status') == 'decode_failed'
    ]
    if failures:
        details = escape(
            json.dumps([{
                'capture_id': capture.get('capture_id'),
                'error': capture.get('decode_error')
            } for capture in failures],
                       ensure_ascii=False))
        panels.append(
            '<section><h2>Failed observation captures</h2>'
            '<p>Decoding failed. Raw bytes and error details are retained; '
            'these captures provide no decoded execution evidence.</p>'
            f'<pre>{details}</pre></section>')
    for group in document['groups']:
        rows = []
        for record in group['observations']:
            source = record.get('source_site') or {}
            origin = record.get('source_region_origin')
            origin_text = (json.dumps(origin, ensure_ascii=False)
                           if origin is not None else
                           'partial; see compiler execution mapping')
            values = (record.get('site'), record.get('scope_name')
                      or source.get('sourceLoc', source.get('source_loc')),
                      origin_text, record['semantic'],
                      record.get('occurrence'), record.get('sequence'),
                      record.get('start_tick'), record.get('end_tick'),
                      record.get('duration_ticks'), record.get('duration_ns'),
                      record.get('storage'))
            rows.append('<tr>' + ''.join('<td>' + escape(str(value)) + '</td>'
                                         for value in values) + '</tr>')
        title = escape(f"{group['invocation_id'] or 'Unassociated capture'} | "
                       f"program {group['program']} actor {group['actor']}")
        clock = escape(
            f"Clock: {group['clock_domain']} ({group['clock_scope']}); "
            f"native event IDs: {group['native_event_ids']}. "
            f"Time relation: {group['time_relation']}.")
        binary = escape(str(group['binary_id']))
        panels.append(
            f'<section><h2>{title}</h2><p>{clock}</p><p>Binary: {binary}</p>'
            '<table><thead><tr>' +
            ''.join('<th>' + field + '</th>' for field in (
                'Site', 'Source scope', 'Source origin (not exclusive cost)',
                'Semantic', 'Retained occurrence', 'Sequence', 'Start tick',
                'End tick', 'Duration ticks', 'Duration ns', 'Storage')) +
            '</tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table></section>')
    return (
        '<!doctype html><meta charset="utf-8"><title>Detailed observations</title>'
        '<style>body{font:15px system-ui;margin:2rem}table{border-collapse:collapse}'
        'th,td{border:1px solid #ccc;padding:.4rem}section{margin-top:2rem}</style>'
        '<h1>Program-associated observations</h1><p><a href="index.html">Capture overview</a> | '
        '<a href="../ai/reconstruction.json">Complete reconstruction</a> | '
        '<a href="../ai/execution.json">Compiler execution mapping</a></p>'
        '<p>Raw ticks stay in their measured clock frame. None denotes an unavailable quantity. '
        'Source-control intervals measure instrumented control, not engine occupancy. '
        'Retained occurrences may omit sampled or truncated executions.</p>' +
        ''.join(panels) +
        f'<p>Rejected observations: {len(document["rejected"])}; details preserved in JSON.</p>'
    )


def write_view(output, payload, report):
    output = Path(output)
    document = reconstruct(payload, report['launches'], report['binaries'],
                           report['events'] + report['untimed_events'])
    (output / 'ai/reconstruction.json'
     ).write_text(json.dumps(document, indent=2, allow_nan=False) + '\n')
    (output / 'report/observations.html').write_text(render(document))
    overview = output / 'report/index.html'
    if overview.exists():
        text = overview.read_text()
        text = text.replace(
            '<main>',
            '<main><p><a href="observations.html">Detailed observations and execution mapping</a></p>',
            1)
        overview.write_text(text)
