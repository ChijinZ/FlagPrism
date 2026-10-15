"""Public source-linked dynamic records derived from verified reconstruction.

No inference joins and no clock conversion are introduced in this view. Original
backend capture/loss evidence remains accessible beside the normalized records.
"""
from html import escape
import json
from pathlib import Path
import posixpath


def _location_candidates(value):
    found = {}

    def visit(node, role='compiler_primary'):
        if isinstance(node, dict):
            file = node.get('source_file', node.get('file'))
            directory = node.get('directory', node.get('debug_directory'))
            if isinstance(file, str) and isinstance(
                    directory, str) and not posixpath.isabs(file):
                # The compiler supplied the directory explicitly. No basename
                # or neighboring-file inference is used for an inline frame.
                file = posixpath.join(directory, file)
            line = node.get('line')
            column = node.get('column', 0)
            if isinstance(file,
                          str) and file and type(line) is int and line > 0:
                location = dict(file=file, line=line, column=column, role=role)
                found[(file, line, column, role)] = location
            for key, child in node.items():
                child_role = {
                    'inline_chain': 'inline_callsite',
                    'inlined_at': 'inline_callsite',
                    'caller': 'inline_callsite',
                    'callee': 'compiler_callee',
                    'entry': 'interval_entry',
                    'exit': 'interval_exit',
                    'source_capture': 'captured_location_reference',
                }.get(key, role)
                if isinstance(child, (dict, list)):
                    visit(child, child_role)
        elif isinstance(node, list):
            for child in node:
                visit(child, role)

    visit(value)
    return list(found.values())


def _locations(value):
    return list({
        (row['file'], row['line'], row['column']): {
            key: row[key]
            for key in ('file', 'line', 'column')
        }
        for row in _location_candidates(value)
    }.values())


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
            if verified and compiler.get(
                    'kind') != 'automatic_compiler_operation':
                origin = compiler
            locations = _locations(origin) if verified else []
            candidates = _location_candidates(origin) if verified else []
            if verified and source.get('sourceLoc'):
                from .execution_enflame import _location_evidence
                evidence, _ = _location_evidence(source['sourceLoc'], {})
                locations += evidence.get('locations', [])
                candidates += [
                    dict(location, role='frontend_source')
                    for location in evidence.get('locations', [])
                ]
            locations = list({
                (row['file'], row['line'], row.get('column', 0)):
                row
                for row in locations
            }.values())
            row = {
                key: event.get(key)
                for key in ('id', 'capture_id', 'invocation_id', 'binary_id',
                            'program', 'actor', 'site', 'semantic',
                            'occurrence', 'iteration', 'clock', 'start_tick',
                            'end_tick', 'duration_ticks', 'duration_ns',
                            'relative_start_ns', 'unit', 'truncated',
                            'sampling', 'association_evidence')
            }
            row['actor'] = event.get('actor', event.get('actor_slot'))
            row.update(source_locations=locations,
                       source_location_candidates=candidates,
                       operation=origin.get(
                           'operation',
                           compiler.get(
                               'operation',
                               compiler.get(
                                   'compiler_opcode',
                                   compiler.get(
                                       'callee',
                                       source.get(
                                           'mlirOpName',
                                           compiler.get('semantics')))))),
                       association_status=event['reconstruction_association'],
                       source_status='located' if locations else 'unresolved',
                       native_event_ids=group['native_event_ids'])
            records.append(row)
    return {
        'schema_version': 1,
        'records': records,
        'captures': document.get('captures', []),
        'rejected': document.get('rejected', []),
        'status': 'dynamic_records_available'
        if records else 'no_internal_dynamic_records',
        'limits': document['limits']
    }


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
            for kind in ('operation', 'control'):
                actor_plan = manifest.get(kind + '_plan')
                if actor_plan:
                    plans.append({
                        'binary_id': binary['id'],
                        'compile_id': handoff.get('compile_id'),
                        'actor': artifact.get('actor'),
                        'module_sha256': manifest.get('module_sha256'),
                        'plan_kind': kind,
                        'plan': actor_plan
                    })
    for capture in captures:
        if capture.get('automatic_plan'):
            plans.append({
                'binary_id':
                capture.get('binary_id'),
                'capture_id':
                capture.get('capture_id'),
                'plan':
                capture['automatic_plan'],
                'selected_origins':
                capture.get('scope_id_origins', {})
            })
        # Preserve the exact backend plan, including capacity/selection/loss;
        # counts from different protocols must not be silently added together.
    return {
        'schema_version':
        1,
        'plans':
        plans,
        'capture_evidence':
        captures,
        'limits': [
            'Unselected sites are not evidence of nonexecution.',
            'Loss and sampling use each backend protocol as recorded.'
        ]
    }


def render(data):
    from .source_view import source_cell
    rows = []
    for row in data['records']:
        clock = row['clock'] or {}
        values = [
            row['operation'], row['invocation_id'], row['binary_id'],
            row['program'], row['actor'], row['site'], row['semantic'],
            row['occurrence'], row['start_tick'], row['end_tick'],
            row['duration_ticks'],
            clock.get('domain'),
            clock.get('scope'), row['association_status']
        ]
        rows.append('<tr data-binary="' +
                    escape(str(row['binary_id']), quote=True) + '"><td>' +
                    source_cell(row) + '</td>' +
                    ''.join('<td>' + escape(str(value)) + '</td>'
                            for value in values) + '</tr>')
    captures = escape(
        json.dumps(data['captures'], indent=2, ensure_ascii=False))
    return (
        '<!doctype html><meta charset="utf-8"><title>Source-linked dynamic records</title>'
        '<style>body{font:14px system-ui;margin:2rem}table{border-collapse:collapse}'
        'td,th{border:1px solid #ddd;padding:.4rem}td{overflow-wrap:anywhere}'
        'input{padding:.5rem;max-width:95%;width:32rem}pre{white-space:pre-wrap}'
        'small{color:#586575}.source-warning{color:#8b4b08;font-size:12px}</style>'
        '<h1>Source-linked dynamic records</h1><p><a href="index.html">Overview</a> | '
        '<a href="sources.html">Captured source</a> | '
        '<a href="execution.html">Execution mapping</a> | '
        '<a href="observations.html">Execution and clock groups</a> | '
        '<a href="../ai/fine_grained.json">Records JSON</a> | '
        '<a href="../ai/observation_plan.json">Collection plan</a></p>'
        '<p>Filter by source path, operation, invocation or actor. Occurrence counts retained '
        'visits, not necessarily loop iterations. Raw ticks are only comparable within the '
        'recorded clock scope; checkpoints record occurrence, not operation busy time. '
        'Intervals measure instrumented source control. None means unavailable.</p>'
        '<p>Source links open captured snapshots at the measured location. Compiler primary and '
        'inline callsite roles are distinct; out-of-range or unavailable positions remain '
        'visible as candidates and do not count as located source. File bounds do not '
        'independently verify that snapshot text matches compiled text.</p>'
        '<input id="filter" aria-label="Filter records" placeholder="Filter source / operation / actor">'
        '<p id="binary-filter"></p>'
        '<p>Status: ' + escape(data['status']) + '</p><table><thead><tr>' +
        ''.join('<th>' + title + '</th>' for title in (
            'Source', 'Operation', 'Invocation', 'Binary', 'Program', 'Actor',
            'Site', 'Semantic', 'Retained occurrence', 'Start tick',
            'End tick', 'Ticks', 'Clock', 'Clock scope', 'Association')) +
        '</tr></thead><tbody id="records">' + ''.join(rows) +
        '</tbody></table>'
        '<details><summary>Original capture, selection and loss evidence</summary><pre>'
        + captures +
        '</pre></details><script>const filter=document.getElementById("filter"),'
        'params=new URLSearchParams(location.search),binary=params.get("binary");'
        'if(binary){let note=document.getElementById("binary-filter");'
        'note.textContent="Binary filter: "+binary+" ";let clear=document.createElement("a");'
        'clear.href="fine_grained.html";clear.textContent="Show all binaries";note.append(clear);}'
        'function apply(){let q=filter.value.toLowerCase();document.querySelectorAll("#records tr").forEach(r=>'
        'r.hidden=(binary&&r.dataset.binary!==binary)||!r.textContent.toLowerCase().includes(q));}'
        'filter.addEventListener("input",apply);filter.value=params.get("filter")||"";'
        'apply();</script>')


def write_view(output, document, report):
    output = Path(output)
    data = normalize(document)
    from .source_view import SourceCatalog
    catalog = SourceCatalog(output)
    catalog.load(data['captures'])
    catalog.annotate(data['records'])
    catalog.write()
    from .execution_view import write_view as write_execution
    write_execution(output, data['records'])
    (output / 'ai/fine_grained.json'
     ).write_text(json.dumps(data, allow_nan=False) + '\n')
    (output / 'ai/observation_plan.json').write_text(
        json.dumps(_plans(report, data['captures']), allow_nan=False) + '\n')
    (output / 'report/fine_grained.html').write_text(render(data))
    overview = output / 'report/index.html'
    if overview.exists():
        overview.write_text(overview.read_text().replace(
            '<main>',
            '<main><p><a href="fine_grained.html">Source-linked internal dynamic records</a> | '
            '<a href="sources.html">Captured source</a> | '
            '<a href="execution.html">Execution mapping</a></p>', 1))


def require_automatic_records(output, request):
    """An automatic capture without internal evidence is an incomplete result."""
    output = Path(output)
    path = output / 'ai/fine_grained.json'
    document = json.loads(path.read_text()) if path.is_file() else {}
    valid = [
        row for row in document.get('records', [])
        if row.get('source_locations') and row.get('operation')
        and row.get('association_status') == 'verified'
        and row.get('semantic') != 'native_lifecycle'
    ]
    if valid:
        return
    internal = [
        row for row in document.get('records', [])
        if row.get('operation') and row.get('association_status') == 'verified'
        and row.get('semantic') != 'native_lifecycle'
    ]
    reason = ('internal_records_lack_valid_source_snapshot_positions'
              if internal else
              'selected_programs_produced_no_source_linked_internal_records')
    action = (
        'Inspect ai/source_index.json diagnostics and source_location_candidates '
        'in ai/fine_grained.json. Captured source snapshots must match their '
        'digest and compiler positions must fall within an unambiguous file snapshot.'
        if internal else
        'Inspect the retained plan, capture/loss status and selected programs. '
        'For conditional work, choose a program that executes the region with '
        'a public ObservationRequest; no application replay was performed.')
    status = {
        'schema_version': 1,
        'status': 'incomplete',
        'reason': reason,
        'request': request,
        'action': action
    }
    (output / 'ai/selection_status.json'
     ).write_text(json.dumps(status, indent=2) + '\n')
    raise RuntimeError(
        f'Automatic profiling is incomplete: {reason}. Original capture and plan retained at '
        f'{output}; see ai/selection_status.json.')
