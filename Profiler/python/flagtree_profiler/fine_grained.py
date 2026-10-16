"""Public source-linked dynamic records derived from verified reconstruction.

No inference joins and no clock conversion are introduced in this view. Original
backend capture/loss evidence remains accessible beside the normalized records.
"""
from html import escape
import copy
import json
from pathlib import Path
import posixpath

EXPORT_REFERENCE_FIELDS = frozenset({
    'raw_base64',
    'clock',
    'compiler_actor',
    'association_evidence',
    'runtime_metadata',
    'source_region_origin',
    'source_location_candidates',
})


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
                if key in ('source_loc', 'sourceLoc') and isinstance(
                        child, str):
                    # Preserve every actual MLIR location atom, including the
                    # caller of an inlined library operation. A candidate is
                    # not an assertion of exclusive source ownership.
                    from .execution_enflame import _location_evidence
                    evidence, _ = _location_evidence(child, {})
                    for item in evidence['locations']:
                        candidate = dict(item,
                                         role='compiler_location_candidate')
                        found[(item['file'], item['line'], item['column'],
                               candidate['role'])] = candidate
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


def candidate_observation_status(captures, records):
    """Join compiler candidates to retained records by exact capture/binary/site."""
    rows = []
    for capture in captures:
        plan = capture.get('automatic_plan') or {}
        binary = capture.get('binary_id')
        capture_id = capture.get('capture_id')
        for candidate in plan.get('inventory', []):
            site = candidate.get('scope_id')
            selected = candidate.get('selected')
            bound = (isinstance(capture_id, str) and bool(capture_id)
                     and isinstance(binary, str) and bool(binary)
                     and type(site) is int and site >= 0)
            count = sum(
                1 for row in records
                if bound and row.get('capture_id') == capture_id
                and row.get('binary_id') == binary and row.get('site') == site
                and row.get('association_status') == 'verified')
            status = ('site_budget_excluded' if selected is False else
                      'unbound_scope_identity' if not bound
                      or selected is not True else 'observed_retained_records'
                      if count else 'selected_no_retained_records')
            rows.append(
                dict(capture_id=capture_id,
                     binary_id=binary,
                     invocation_id=capture.get('invocation_id'),
                     candidate_ordinal=candidate.get('candidate_ordinal'),
                     scope_id=site,
                     selected=selected,
                     operation=candidate.get('operation'),
                     candidate_class=candidate.get('candidate_class'),
                     selection_reason=candidate.get('selection_reason'),
                     retained_records=count,
                     status=status))
    return rows


def normalize(document):
    # Derived reports must retract historical exactness even when the retained
    # bundle already contains decoded events. Preserve the original evidence.
    from .source_census import legacy_ascend_visibility_hazard
    document = copy.deepcopy(document)
    hazardous_captures = set()
    for capture in document.get('captures', []):
        metadata = capture.get('runtime_metadata') or {}
        census = metadata.get('ascend_source_census') or {}
        physical = census.get('physical_plan') or {}
        if (legacy_ascend_visibility_hazard(capture)
                or legacy_ascend_visibility_hazard(metadata)
                or physical.get('layout')
                in {'ascend_source_census_v1', 'ascend_source_census_v2'}):
            if capture.get('capture_id'):
                hazardous_captures.add(capture['capture_id'])
            state = dict(
                transport_visibility='legacy_ascend_cache_line_hazard',
                unknown_loss=True)
            capture.update(state)
            metadata = capture.setdefault('runtime_metadata', {})
            census = metadata.setdefault('ascend_source_census', {})
            census.setdefault('loss', {}).update(exact=False, **state)
            census.setdefault('summary', {}).update(state)
            for key in ('source_census', 'census', 'decoded'):
                if isinstance(capture.get(key), dict):
                    capture[key].setdefault('loss', {}).update(exact=False,
                                                               **state)
                    capture[key].setdefault('summary', {}).update(state)
    records = []
    for group in document['groups']:
        for event in group['observations']:
            source = event.get('source_site') or {}
            compiler = event.get('compiler_site') or {}
            if (event.get('semantic') == 'counter' and
                (event.get('capture_id') in hazardous_captures
                 or legacy_ascend_visibility_hazard(
                     dict(actors=[
                         dict(compiler_actor=compiler.get('compiler_actor'))
                     ])))):
                event.update(
                    count_exact=False,
                    unknown_loss=True,
                    transport_visibility='legacy_ascend_cache_line_hazard')
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
                            'sampling', 'association_evidence', 'count',
                            'count_exact', 'counter_kind', 'site_role',
                            'transport_visibility', 'unknown_loss', 'overflow',
                            'mask_activity', 'storage', 'raw_offset',
                            'raw_sha256')
            }
            row['actor'] = event.get('actor', event.get('actor_slot'))
            row['compiler_actor'] = compiler.get(
                'compiler_actor') if verified else None
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
        'schema_version':
        1,
        'records':
        records,
        'candidate_observation_status':
        candidate_observation_status(document.get('captures', []), records),
        'captures':
        document.get('captures', []),
        'rejected':
        document.get('rejected', []),
        'status':
        'dynamic_records_available'
        if records else 'no_internal_dynamic_records',
        'limits':
        document['limits']
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
                        'binary_id':
                        binary['id'],
                        'compile_id':
                        handoff.get('compile_id'),
                        'actor':
                        artifact.get('actor'),
                        'compiler_actors': [{
                            'function':
                            actor.get('function'),
                            'actor_kind':
                            actor.get('actor_kind'),
                            'identity':
                            f'late_llvm:{manifest.get("module_sha256")}:{actor["function"]}'
                            if manifest.get('module_sha256')
                            and actor.get('function') else None,
                            'runtime_actor_binding':
                            manifest.get('runtime_actor_binding') if
                            (manifest.get('runtime_actor_binding')
                             or {}).get('function') == actor.get('function')
                            else None
                        } for actor in manifest.get('actors', [])],
                        'module_sha256':
                        manifest.get('module_sha256'),
                        'plan_kind':
                        kind,
                        'plan':
                        actor_plan
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
    counts_only = bool(data['records']) and all(
        row.get('semantic') == 'counter' for row in data['records'])
    titles = [
        'Source', 'Operation', 'Invocation', 'Binary', 'Program', 'Actor',
        'Site', 'Semantic', 'Visits', 'Count exact'
    ]
    if counts_only:
        titles.append('Site role')
    else:
        titles.extend([
            'Retained occurrence', 'Start tick', 'End tick', 'Ticks', 'Clock',
            'Clock scope'
        ])
    titles.append('Association')
    for row in data['records']:
        clock = row['clock'] or {}
        actor_label = str(row['actor'])
        if isinstance(row['actor'], dict):
            actor = row['actor']
            kind = {
                'logical_warp': 'warp',
                'logical_work_item': 'work-item',
                'logical_program_observer': 'program observer'
            }.get(actor.get('kind'))
            if kind is not None:
                actor_label = f"{kind} {actor.get('id')}"
        compiler_actor = row.get('compiler_actor') or {}
        binding_proof = compiler_actor.get('binding_proof') or {}
        if (binding_proof.get('runtime_slot_status')
                == 'verified_against_raw_record_and_segment'
                and binding_proof.get('observed_actor_slot') == row['actor']
                and binding_proof.get('status')
                == 'verified_compiler_emission_manifest'):
            actor_label += f' · {compiler_actor.get("kind")} / {compiler_actor.get("function")} (verified compiler binding)'
        binary = str(row['binary_id'])
        binary_label = binary if len(binary) <= 16 else binary[:12] + '…'
        values = [
            row['operation'], row['invocation_id'], row['binary_id'],
            row['program'], actor_label, row['site'], row['semantic'],
            row.get('count'),
            row.get('count_exact'), row['occurrence'], row['start_tick'],
            row['end_tick'], row['duration_ticks'],
            clock.get('domain'),
            clock.get('scope'), row['association_status']
        ]
        values[2] = binary_label
        if counts_only:
            values = values[:9] + [
                row.get('site_role'), row['association_status']
            ]
        source_paths = [
            f"{item.get('file', '')}:{item.get('line', '')}:{item.get('column', 0)}"
            for item in row.get('source_links', [])
        ]
        search = ' '.join([binary, str(row['actor']), *source_paths])
        rows.append('<tr data-binary="' + escape(binary, quote=True) +
                    '" data-search="' + escape(search, quote=True) + '"><td>' +
                    source_cell(row, compact=True) + '</td>' +
                    ''.join('<td title="' + escape(binary, quote=True) + '">' +
                            escape(str(value)) +
                            '</td>' if index == 2 else '<td>' +
                            escape(str(value)) + '</td>'
                            for index, value in enumerate(values)) + '</tr>')
    coverage = data.get('automatic_selection_status')
    coverage_html = ''
    if coverage is not None:
        coverage_rows = ''.join(
            '<tr>' +
            ''.join('<td>' + escape(str(row.get(key))) + '</td>'
                    for key in ('capture_id', 'invocation_id', 'binary_id',
                                'source_linked_records', 'status', 'reason')) +
            '</tr>' for row in coverage['captures'])
        coverage_html = (
            '<h2>Automatic capture coverage</h2><p>Status: ' +
            escape(coverage['status']) +
            '. Each captured invocation must have its own source-linked internal records. '
            'This check describes the selected programs and sites; it does not assert '
            'that every program or source region was sampled. '
            '<a href="../ai/selection_status.json">Coverage JSON</a></p>'
            '<table><thead><tr><th>Capture</th><th>Invocation</th><th>Binary</th>'
            '<th>Located records</th><th>Status</th><th>Reason</th></tr></thead><tbody>'
            + coverage_rows + '</tbody></table>')
    candidates = data.get('candidate_observation_status', [])
    candidate_html = ''
    if candidates:
        fields = ('capture_id', 'binary_id', 'candidate_ordinal', 'scope_id',
                  'operation', 'candidate_class', 'selected',
                  'selection_reason', 'retained_records', 'status')
        candidate_html = (
            '<h2>Compiler candidate observations</h2>'
            '<p>Counts join retained records by capture, binary and compiler scope. '
            'A selected scope with no retained record does not establish nonexecution; '
            'inspect original loss and sampling evidence below. A control-region '
            'interval does not establish execution of its conditional body.</p>'
            '<table><thead><tr>' +
            ''.join('<th>' + field.replace('_', ' ').title() + '</th>'
                    for field in fields) + '</tr></thead><tbody>' +
            ''.join(
                '<tr>' + ''.join('<td>' + escape(str(row.get(field))) + '</td>'
                                 for field in fields) + '</tr>'
                for row in candidates) + '</tbody></table>')
    captures = escape(
        json.dumps([{
            key: value
            for key, value in capture.items()
            if key not in {'raw_base64', 'runtime_metadata'}
        } for capture in data['captures']],
                   separators=(',', ':'),
                   ensure_ascii=False))
    return (
        '<!doctype html><meta charset="utf-8"><title>Source-linked dynamic records</title>'
        '<style>body{font:14px system-ui;margin:2rem}table{border-collapse:collapse}'
        '.records-scroll{overflow-x:auto}.records-scroll td:first-child{min-width:13em}'
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
        '<p>Visit counters are one value per selected site and logical observer. '
        'They count reaching a source control position, including masked operations '
        'with no active data lanes. They provide no timestamps or busy duration. '
        'A saturated count is a lower bound, marked Count exact = False. '
        'The census retains all admitted programs in raw data; the default table '
        'presents the lowest program with primary-site visits.</p>'
        '<p>Source links open captured snapshots at the measured location. Compiler primary and '
        'inline callsite roles are distinct; out-of-range or unavailable positions remain '
        'visible as candidates and do not count as located source. File bounds do not '
        'independently verify that snapshot text matches compiled text.</p>'
        '<input id="filter" aria-label="Filter records" placeholder="Filter source / operation / actor">'
        '<p id="binary-filter"></p>'
        '<p>Status: ' + escape(data['status']) +
        '</p><div class="records-scroll"><table><thead><tr>' +
        ''.join('<th>' + title + '</th>' for title in titles) +
        '</tr></thead><tbody id="records">' + ''.join(rows) +
        '</tbody></table></div>' + coverage_html + candidate_html +
        '<details><summary>Original capture, selection and loss evidence</summary><pre>'
        +
        '<a href="../ai/observations.json">Complete raw capture and runtime metadata</a>'
        + captures +
        '</pre></details><script>const filter=document.getElementById("filter"),'
        'params=new URLSearchParams(location.search),binary=params.get("binary");'
        'if(binary){let note=document.getElementById("binary-filter");'
        'note.textContent="Binary filter: "+binary+" ";let clear=document.createElement("a");'
        'clear.href="fine_grained.html";clear.textContent="Show all binaries";note.append(clear);}'
        'function apply(){let q=filter.value.toLowerCase();document.querySelectorAll("#records tr").forEach(r=>'
        'r.hidden=(binary&&r.dataset.binary!==binary)||!'
        '(r.textContent+" "+r.dataset.search).toLowerCase().includes(q));}'
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
    from .export_refs import compact
    original = json.loads((output / 'ai/observations.json').read_text())
    for name, view in (('fine_grained', data), ('observation_plan',
                                                _plans(report,
                                                       data['captures']))):
        exported = compact(view, original, fields=EXPORT_REFERENCE_FIELDS)
        (output / f'ai/{name}.json').write_text(
            json.dumps(exported, separators=(',', ':'), allow_nan=False) +
            '\n')
    (output / 'report/fine_grained.html').write_text(render(data))
    overview = output / 'report/index.html'
    if overview.exists():
        overview.write_text(overview.read_text().replace(
            '<main>',
            '<main><p><a href="fine_grained.html">Source-linked internal dynamic records</a> | '
            '<a href="sources.html">Captured source</a> | '
            '<a href="execution.html">Execution mapping</a></p>', 1))


def require_automatic_records(output, request):
    """Check each captured invocation; another kernel cannot mask a gap."""
    output = Path(output)
    path = output / 'ai/fine_grained.json'
    document = json.loads(path.read_text()) if path.is_file() else {}
    from .export_refs import restore
    original_path = output / 'ai/observations.json'
    original = json.loads(
        original_path.read_text()) if original_path.is_file() else {}
    document = restore(document, original)
    internal = [
        row for row in document.get('records', [])
        if row.get('operation') and row.get('association_status') == 'verified'
        and row.get('semantic') != 'native_lifecycle'
    ]
    launches_path = output / 'ai/launches.json'
    launches = json.loads(
        launches_path.read_text()) if launches_path.is_file() else []
    coverage, captured_invocations = [], set()
    for capture in document.get('captures', []):
        metadata = capture.get('runtime_metadata') or {}
        proof = metadata.get('profiler_association_evidence') or {}
        invocation = capture.get('invocation_id') or metadata.get(
            'profiler_invocation_id')
        binary = capture.get('binary_id') or proof.get('binary_id')
        capture_id = capture.get('capture_id')
        identity = (invocation, binary)
        identity_valid = all(
            isinstance(value, str) and value
            for value in (capture_id, invocation, binary))
        # Do not derive a missing capture identity from some other valid row.
        # Runtime-owned captures use the exact same-launch metadata evidence.
        if metadata:
            identity_valid = (
                identity_valid
                and proof.get('evidence') == 'same_launch_metadata_object'
                and proof.get('invocation_id') == invocation
                and metadata.get('profiler_invocation_id') == invocation
                and proof.get('binary_id') == binary)
        matched = [
            row for row in internal
            if identity_valid and row.get('capture_id') == capture_id
            and row.get('invocation_id') == invocation
            and row.get('binary_id') == binary
        ]
        count_rows = [
            row for row in matched
            if row.get('storage') == 'source_site_census_v1'
        ]
        census = (capture.get('source_census') or capture.get('census')
                  or metadata.get('ascend_source_census') or {})
        census_loss = census.get('loss') or (capture.get('decoded')
                                             or {}).get('loss') or {}
        count_overflow = (any(
            row.get('overflow') is True for row in count_rows)
                          or bool(census_loss.get('overflow_cells')))
        unknown_visibility_loss = (any(
            row.get('unknown_loss') is True for row in count_rows)
                                   or census_loss.get('unknown_loss') is True)
        source_linked = [row for row in matched if row.get('source_locations')]
        valid = [
            row for row in source_linked
            if (row.get('storage') != 'source_site_census_v1' or (
                row.get('site_role') == 'primary' and type(row.get('count')) is
                int and row['count'] > 0 and row.get('count_exact') is True))
        ]
        reason = (
            'source_census_count_overflow'
            if count_overflow else 'source_census_transport_visibility_unknown'
            if unknown_visibility_loss else None if valid else
            'capture_has_no_verified_invocation_identity' if not identity_valid
            else 'internal_records_lack_valid_source_snapshot_positions'
            if matched else
            'selected_programs_produced_no_source_linked_internal_records')
        coverage.append(
            dict(capture_id=capture_id,
                 invocation_id=invocation,
                 binary_id=binary,
                 status='complete' if reason is None else 'incomplete',
                 reason=reason,
                 transport_visibility=census_loss.get('transport_visibility'),
                 unknown_loss=unknown_visibility_loss,
                 internal_records=len(matched),
                 source_linked_records=len(source_linked)))
        if identity_valid:
            captured_invocations.add(identity)
    for launch in launches:
        identity = (launch.get('id'), launch.get('binary_id'))
        if identity not in captured_invocations:
            coverage.append(
                dict(capture_id=None,
                     invocation_id=identity[0],
                     binary_id=identity[1],
                     status='incomplete',
                     reason='invocation_has_no_internal_capture',
                     internal_records=0,
                     source_linked_records=0))
    incomplete = [row for row in coverage if row['status'] != 'complete']
    reason = (incomplete[0]['reason'] if incomplete else None if coverage else
              'selected_programs_produced_no_source_linked_internal_records')
    action = (
        'A source visit counter saturated. The retained value is a lower bound. '
        'Inspect the raw census flags and use a shorter application workload; '
        'this capture cannot establish exact visit counts.'
        if reason == 'source_census_count_overflow' else
        'Historical Ascend census storage can lose scalar GM writes through shared cache lines. '
        'Retained counts are inexact; zero does not establish non-execution. '
        'Use a new version-3 capture for isolated actor storage.'
        if reason == 'source_census_transport_visibility_unknown' else
        'Inspect ai/source_index.json diagnostics and source_location_candidates '
        'in ai/fine_grained.json. Captured source snapshots must match their '
        'digest and compiler positions must fall within an unambiguous file snapshot.'
        if reason == 'internal_records_lack_valid_source_snapshot_positions'
        else
        'Inspect capture runtime_metadata and ai/launches.json for the named invocation '
        'and binary. Preserve raw data and report the missing or conflicting invocation '
        'association; records from another capture cannot establish this association.'
        if reason in ('capture_has_no_verified_invocation_identity',
                      'invocation_has_no_internal_capture') else
        'Inspect the census grid, selected primary sites and retained raw matrix. '
        'All admitted programs were collected; changing the displayed program '
        'cannot create missing primary observations. Preserve this capture when '
        'reporting a compiler-plan coverage defect for executed source regions.'
        if isinstance(request, dict) and request.get('program_policy') ==
        'all_grid_census' else
        'Inspect the retained plan, capture/loss status and selected programs. '
        'For conditional work, choose a program that executes the region with '
        'a public ObservationRequest; no application replay was performed.')
    status = {
        'schema_version': 1,
        'status': 'incomplete' if reason else 'complete',
        'reason': reason,
        'request': request,
        'action': action if reason else None,
        'captures': coverage,
    }
    (output / 'ai/selection_status.json'
     ).write_text(json.dumps(status, indent=2) + '\n')
    document['automatic_selection_status'] = status
    if reason:
        document['status'] = 'incomplete_automatic_capture'
    from .export_refs import compact
    path.write_text(
        json.dumps(compact(document, original, fields=EXPORT_REFERENCE_FIELDS),
                   separators=(',', ':'),
                   allow_nan=False) + '\n')
    html = output / 'report/fine_grained.html'
    if html.is_file():
        html.write_text(render(document))
    if not reason:
        return
    raise RuntimeError(
        f'Automatic profiling is incomplete: {reason}. Original capture and plan retained at '
        f'{output}; see ai/selection_status.json.')
