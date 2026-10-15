"""Public source-linked dynamic records derived from verified reconstruction.

No inference joins and no clock conversion are introduced in this view. Original
backend capture/loss evidence remains accessible beside the normalized records.
"""
from html import escape
import json
from pathlib import Path


def _locations(value):
    found = {}

    def visit(node):
        if isinstance(node, dict):
            file = node.get('file', node.get('source_file'))
            line = node.get('line')
            column = node.get('column', 0)
            if isinstance(file, str) and file and type(line) is int and line > 0:
                location = {'file': file, 'line': line, 'column': column}
                found[(file, line, column)] = location
            for child in node.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    return list(found.values())


def normalize(document):
    records = []
    for group in document['groups']:
        for event in group['observations']:
            source = event.get('source_site') or {}
            compiler = event.get('compiler_site') or {}
            verified = event.get('reconstruction_association') == 'verified'
            origin = event.get('source_region_origin') or {}
            # Late compiler sites have already been checked against the actual
            # actor manifest by the decoder. Do not attach an unrelated binary.
            if verified and compiler.get('kind') != 'automatic_compiler_operation':
                origin = compiler
            locations = _locations(origin) if verified else []
            if verified and source.get('sourceLoc'):
                from .execution_enflame import _location_evidence
                evidence, _ = _location_evidence(source['sourceLoc'], {})
                locations += evidence.get('locations', [])
            locations = list({(row['file'], row['line'], row.get('column', 0)): row
                              for row in locations}.values())
            row = {key: event.get(key) for key in (
                'id', 'capture_id', 'invocation_id', 'binary_id', 'program', 'actor',
                'site', 'semantic', 'occurrence', 'iteration', 'clock', 'start_tick',
                'end_tick', 'duration_ticks', 'duration_ns', 'relative_start_ns',
                'unit', 'truncated', 'sampling', 'association_evidence')}
            row['actor'] = event.get('actor', event.get('actor_slot'))
            row.update(source_locations=locations,
                       operation=origin.get('operation', compiler.get('operation',
                           compiler.get('compiler_opcode', compiler.get('callee',
                               source.get('mlirOpName', compiler.get('semantics')))))),
                       association_status=event['reconstruction_association'],
                       source_status='located' if locations else 'unresolved',
                       native_event_ids=group['native_event_ids'])
            records.append(row)
    return {'schema_version': 1, 'records': records,
            'captures': document.get('captures', []),
            'rejected': document.get('rejected', []),
            'status': 'dynamic_records_available' if records else 'no_internal_dynamic_records',
            'limits': document['limits']}


def _plans(report, captures):
    plans = []
    for binary in report['binaries']:
        metadata = binary.get('compiler_metadata') or {}
        plan = metadata.get('debug_automatic_plan')
        if plan:
            plans.append({'binary_id': binary['id'], 'plan': plan})
        handoff = metadata.get('flagprism_ascend_handoff') or {}
        for artifact in handoff.get('artifacts', []):
            manifest = artifact.get('metadata') or {}
            operation_plan = manifest.get('operation_plan')
            if operation_plan:
                plans.append({'binary_id': binary['id'],
                              'compile_id': handoff.get('compile_id'),
                              'actor': artifact.get('actor'),
                              'module_sha256': manifest.get('module_sha256'),
                              'plan': operation_plan})
    for capture in captures:
        if capture.get('automatic_plan'):
            plans.append({'binary_id': capture.get('binary_id'),
                          'capture_id': capture.get('capture_id'),
                          'plan': capture['automatic_plan'],
                          'selected_origins': capture.get('scope_id_origins', {})})
        # Preserve the exact backend plan, including capacity/selection/loss;
        # counts from different protocols must not be silently added together.
    return {'schema_version': 1, 'plans': plans,
            'capture_evidence': captures,
            'limits': ['Unselected sites are not evidence of nonexecution.',
                       'Loss and sampling use each backend protocol as recorded.']}


def render(data):
    rows = []
    for row in data['records']:
        source = ', '.join(f"{loc['file']}:{loc['line']}:{loc.get('column', 0)}"
                           for loc in row['source_locations']) or 'Unresolved source'
        clock = row['clock'] or {}
        values = [source, row['operation'], row['invocation_id'], row['binary_id'],
                  row['program'], row['actor'], row['site'], row['semantic'],
                  row['occurrence'], row['start_tick'], row['end_tick'],
                  row['duration_ticks'], clock.get('domain'), clock.get('scope'),
                  row['association_status']]
        rows.append('<tr>' + ''.join('<td>' + escape(str(value)) + '</td>'
                                     for value in values) + '</tr>')
    captures = escape(json.dumps(data['captures'], indent=2, ensure_ascii=False))
    return ('<!doctype html><meta charset="utf-8"><title>Source-linked dynamic records</title>'
            '<style>body{font:14px system-ui;margin:2rem}table{border-collapse:collapse}'
            'td,th{border:1px solid #ddd;padding:.4rem}td{overflow-wrap:anywhere}'
            'input{padding:.5rem;width:32rem}pre{white-space:pre-wrap}</style>'
            '<h1>Source-linked dynamic records</h1><p><a href="index.html">Overview</a> | '
            '<a href="observations.html">Execution and clock groups</a> | '
            '<a href="../ai/fine_grained.json">Records JSON</a> | '
            '<a href="../ai/observation_plan.json">Collection plan</a></p>'
            '<p>Filter by source path, operation, invocation or actor. Occurrence counts retained '
            'visits, not necessarily loop iterations. Raw ticks are only comparable within the '
            'recorded clock scope; checkpoints record occurrence, not operation busy time. '
            'Intervals measure instrumented source control. None means unavailable.</p>'
            '<input id="filter" aria-label="Filter records" placeholder="Filter source / operation / actor">'
            '<p>Status: ' + escape(data['status']) + '</p><table><thead><tr>' +
            ''.join('<th>' + title + '</th>' for title in (
                'Source', 'Operation', 'Invocation', 'Binary', 'Program', 'Actor', 'Site',
                'Semantic', 'Retained occurrence', 'Start tick', 'End tick', 'Ticks',
                'Clock', 'Clock scope', 'Association')) +
            '</tr></thead><tbody id="records">' + ''.join(rows) + '</tbody></table>'
            '<details><summary>Original capture, selection and loss evidence</summary><pre>' + captures +
            '</pre></details><script>document.getElementById("filter").addEventListener("input",e=>{'
            'let q=e.target.value.toLowerCase();document.querySelectorAll("#records tr").forEach(r=>'
            'r.hidden=!r.textContent.toLowerCase().includes(q));});</script>')


def write_view(output, document, report):
    output = Path(output)
    data = normalize(document)
    (output / 'ai/fine_grained.json').write_text(json.dumps(data, allow_nan=False) + '\n')
    (output / 'ai/observation_plan.json').write_text(json.dumps(
        _plans(report, data['captures']), allow_nan=False) + '\n')
    (output / 'report/fine_grained.html').write_text(render(data))
    overview = output / 'report/index.html'
    if overview.exists():
        overview.write_text(overview.read_text().replace('<main>',
            '<main><p><a href="fine_grained.html">Source-linked internal dynamic records</a></p>', 1))
