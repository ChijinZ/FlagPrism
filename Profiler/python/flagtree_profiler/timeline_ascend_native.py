"""Exact c220 native flag words and marked final-image observations.

These facts do not authorize engine busy intervals or a completion instant.
The catalogue contains only actually compiled tuples; unknown tuples stay unknown.
"""
import struct

from . import timeline_ascend_machine as machine
from .timeline_events_ascend import compiler_actors, NATIVE_CONTROL_FILE
from .timeline_store import read_artifact
from .timeline_views import document_sha256

# Baseline and native words come from actual SDK compilations. The original
# sixteen tuples use the first archive; twenty-four additional tuples were
# checked as exact single-word insertions on both actual AIC and AIV job types.
# Event-ID extension bits remain part of unknown-family detection.
REFERENCE_ARCHIVE_SHA256 = '75d5951d83a57f8eb16017d7958ab89b4ad7ed45741e2b554ecb272a145a9302'
ADDITIONAL_REFERENCE_ARCHIVE_SHA256 = '585e4d0fdbe7b5207a251ad87197a5ed7bdbfa97836bd58d63e115e85105a7bb'
REFERENCE_ARCHIVES_SHA256 = (REFERENCE_ARCHIVE_SHA256,
                             ADDITIONAL_REFERENCE_ARCHIVE_SHA256)
WORDS = {
    0x40a00280: ('set_flag', (0, 5, 0)),
    0x40a00400: ('set_flag', (1, 0, 0)),
    0x40a00401: ('set_flag', (1, 0, 1)),
    0x40a00600: ('set_flag', (1, 4, 0)),
    0x40a00601: ('set_flag', (1, 4, 1)),
    0x40a00602: ('set_flag', (1, 4, 2)),
    0x40a00603: ('set_flag', (1, 4, 3)),
    0x40a00680: ('set_flag', (1, 5, 0)),
    0x40a00681: ('set_flag', (1, 5, 1)),
    0x40a00e00: ('set_flag', (3, 4, 0)),
    0x40a00e01: ('set_flag', (3, 4, 1)),
    0x40a00e02: ('set_flag', (3, 4, 2)),
    0x40a00e03: ('set_flag', (3, 4, 3)),
    0x40a01080: ('set_flag', (4, 1, 0)),
    0x40a01081: ('set_flag', (4, 1, 1)),
    0x40a01180: ('set_flag', (4, 3, 0)),
    0x40a01181: ('set_flag', (4, 3, 1)),
    0x40a01480: ('set_flag', (5, 1, 0)),
    0x40a04900: ('set_flag', (2, 10, 0)),
    0x40a40600: ('set_flag', (1, 4, 4)),
    0x40a40e00: ('set_flag', (3, 4, 4)),
    0x40c00280: ('wait_flag', (0, 5, 0)),
    0x40c00400: ('wait_flag', (1, 0, 0)),
    0x40c00401: ('wait_flag', (1, 0, 1)),
    0x40c00600: ('wait_flag', (1, 4, 0)),
    0x40c00601: ('wait_flag', (1, 4, 1)),
    0x40c00602: ('wait_flag', (1, 4, 2)),
    0x40c00603: ('wait_flag', (1, 4, 3)),
    0x40c00680: ('wait_flag', (1, 5, 0)),
    0x40c00681: ('wait_flag', (1, 5, 1)),
    0x40c00e00: ('wait_flag', (3, 4, 0)),
    0x40c00e01: ('wait_flag', (3, 4, 1)),
    0x40c00e02: ('wait_flag', (3, 4, 2)),
    0x40c00e03: ('wait_flag', (3, 4, 3)),
    0x40c01080: ('wait_flag', (4, 1, 0)),
    0x40c01081: ('wait_flag', (4, 1, 1)),
    0x40c01480: ('wait_flag', (5, 1, 0)),
    0x40c04900: ('wait_flag', (2, 10, 0)),
    0x40c40600: ('wait_flag', (1, 4, 4)),
    0x40c40e00: ('wait_flag', (3, 4, 4)),
}


def _need(value, message):
    if not value:
        raise ValueError(message)


def native_control_map(*, binary, dwarf_lines, metadata):
    """Recompute image/marker facts; a saved status is never a certificate."""
    counter = machine.counter_map(binary=binary,
                                  dwarf_lines=dwarf_lines,
                                  metadata=metadata)
    sections, functions = machine._elf(binary)
    actors = compiler_actors(metadata)
    expected, planned = {}, {}
    for actor in actors.values():
        if actor['function'] in planned:
            continue
        _need(actor['native_control_version'] == 2,
              'Native point analysis requires feature version 2')
        planned[actor['function']] = functions[actor['function']]
        for sid, site in actor['sites'].items():
            if site['semantic_code'] not in (2, 3):
                continue
            marker = site['native_instruction_marker']
            _need(marker['status'] == 'debug_locations_emitted',
                  'Native point has no emitted instruction marker')
            expected[actor['function'], sid] = site
    _need(expected, 'This compilation contains no native flag observations')
    all_flags = {}
    unknown = []
    for section in sections.values():
        for offset in range(0, len(section['data']), 4):
            word = struct.unpack_from('<I', section['data'], offset)[0]
            pc = section['address'] + offset
            if word in WORDS:
                all_flags[pc] = dict(pc=pc,
                                     instruction_word=word,
                                     operation=WORDS[word][0],
                                     arguments=list(WORDS[word][1]))
            elif word & 0xffe00000 in (0x40a00000, 0x40c00000):
                unknown.append(dict(pc=pc, instruction_word=word))
    mapped, covered, pc_bindings = [], set(), {}
    for row in machine._dwarf_rows(dwarf_lines,
                                   marker_file=NATIVE_CONTROL_FILE):
        pc = row['pc']
        candidates = [
            (name, value) for name, value in planned.items()
            if (name, row['line']) in expected and value[1] <= pc and pc +
            4 <= value[1] + value[2]
        ]
        _need(
            len(candidates) == 1,
            'Native marker has no unique planned actor/site')
        name, (section, address, length) = candidates[0]
        key = (name, row['line'])
        _need(pc not in pc_bindings or pc_bindings[pc] == key,
              'One native instruction aliases different sites')
        site = expected[key]
        _need(
            pc in all_flags
            and all_flags[pc]['operation'] == site['native_operation']
            and all_flags[pc]['arguments'] == site['native_arguments'],
            'Native marker does not point to its exact reference primitive/arguments'
        )
        pc_bindings[pc] = key
        covered.add(key)
        entry = dict(all_flags[pc],
                     function=name,
                     site_id=key[1],
                     backend_site_id=site['backend_identity'])
        if entry not in mapped:
            mapped.append(entry)
    getters = {}
    for row in counter['counter_pcs']:
        getters.setdefault((row['function'], row['site_id'], row['phase']),
                           set()).add(row['pc'])
    brackets, unbounded = [], []
    for key, site in expected.items():
        entries = getters.get((*key, 'entry'), set())
        exits = getters.get((*key, 'exit'), set())
        native = {
            r['pc']
            for r in mapped if (r['function'], r['site_id']) == key
        }
        found = []
        for start in entries:
            for stop in exits:
                between = [pc for pc in all_flags if start < pc < stop]
                if len(between) == 1 and between[0] in native:
                    found.append(
                        dict(function=key[0],
                             site_id=key[1],
                             entry_pc=start,
                             native_pc=between[0],
                             exit_pc=stop))
        if not found or {r['entry_pc']
                         for r in found
                         } != entries or {r['exit_pc']
                                          for r in found} != exits:
            unbounded.append(
                dict(function=key[0],
                     site_id=key[1],
                     reason='not_all_getters_bound_to_exact_single_native_word'
                     ))
        brackets.extend(found)
    unbound = [r for pc, r in all_flags.items() if pc not in pc_bindings]
    complete = covered == set(
        expected) and not unknown and not unbound and not unbounded
    return dict(schema_version=1,
                model='ascend.c220.native_flags.dwarf.v1',
                status='native_points_mapped_not_dynamic_qualification'
                if complete else 'native_points_partial',
                binary_id=metadata['hash'],
                binary_sha256=machine._sha(binary),
                dwarf_sha256=machine._sha(dwarf_lines),
                counter_map_sha256=document_sha256(counter),
                reference_archive_sha256=REFERENCE_ARCHIVE_SHA256,
                reference_archives_sha256=list(REFERENCE_ARCHIVES_SHA256),
                native_pcs=sorted(mapped,
                                  key=lambda r:
                                  (r['function'], r['site_id'], r['pc'])),
                getter_brackets=brackets,
                missing_marker_sites=[
                    dict(function=f, site_id=s)
                    for f, s in sorted(set(expected) - covered)
                ],
                unbound_image_flag_words=unbound,
                uncatalogued_family_candidates=unknown,
                unbounded_sites=unbounded,
                complete=complete,
                dynamic_dependencies_qualified=False,
                physical_completion_time_qualified=False,
                hardware_busy_qualified=False)


def load_native_control_map(directory, capture):
    metadata = capture['metadata']['compiler_metadata']
    prefix = 'machine/' + metadata['hash']
    binary = read_artifact(directory,
                           prefix + '/loaded.elf',
                           limit=machine.LIMIT)
    _need(binary == machine._bound_binary(capture['metadata']),
          'Native image differs from loaded executable')
    dwarf = read_artifact(directory,
                          prefix + '/dwarf.stdout',
                          limit=machine.LIMIT)
    return native_control_map(binary=binary,
                              dwarf_lines=dwarf,
                              metadata=metadata)


def load_observed_dependency_inputs(directory, capture, raw):
    """Native queue generations within one actually observed scalar context.

    A non-scalar wait exit is only an enqueue observation. Only a wait whose
    actual destination is PIPE_S supplies a scalar readiness checkpoint. Neither
    observation measures a physical completion instant or an engine busy span.
    """
    import hashlib
    import json
    from pathlib import Path
    import re
    from .timeline_events import stable_id
    from .timeline_events_ascend import canonicalize_ascend_capture
    from .timeline_unit_ascend import load_counter_unit_proofs
    from .timeline_shared import SharedCounterProof
    from .timeline_dependencies import ObservedDependencyProof

    _need(
        type(raw) is bytes
        and raw == read_artifact(directory, capture['raw_file']),
        'Native dependency raw bytes differ from the retained capture')
    batch = canonicalize_ascend_capture(
        raw,
        owner=capture['owner'],
        metadata=capture['metadata']['compiler_metadata'],
        association=capture['launch'])
    mapping = load_native_control_map(directory, capture)
    _need(mapping['complete'],
          'Native instruction/getter bindings are incomplete')
    compiled = capture['metadata']['compiler_metadata']
    for artifact in compiled['flagprism_ascend_handoff']['artifacts']:
        plan = artifact['metadata'].get('control_plan') or {}
        _need(not plan.get('unobserved'),
              'Native control inventory contains unobserved primitives')
        names = re.findall(
            r'\bcall\b[^\n]*?@(llvm\.hivm\.(?:SET|WAIT)\.[\w.]+)\(',
            artifact['llir'])
        _need(
            all(name in ('llvm.hivm.SET.FLAG.IMM', 'llvm.hivm.WAIT.FLAG.IMM')
                for name in names if '.FLAG.' in name or '.CROSS.' in name),
            'Native flag inventory includes a mechanism outside this provider')
    units = {
        p.observer_id: p
        for p in load_counter_unit_proofs(directory, capture, batch)
    }
    sites = {s['id']: s for s in batch['sites']}
    records = {r['id']: r for r in batch['records']}
    implementation = document_sha256(
        dict(native_rules=hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
             machine_rules=hashlib.sha256(Path(
                 machine.__file__).read_bytes()).hexdigest()))
    proofs = []
    identity = tuple(batch['identity'][key]
                     for key in ('capture_id', 'invocation_id', 'binary_id'))
    for observer in batch['observers']:
        if not observer['retained_records']:
            continue
        _need(
            observer['complete'] and not observer['filtered_records'],
            'Native queue generation reconstruction requires a complete observed context'
        )
        events = sorted(
            (e for e in batch['events'] if e['observer_id'] == observer['id']),
            key=lambda e: records[e['record_ids'][-1]]['sequence'])
        native_events = [
            e for e in events if sites[e['site_id']]['attributes'].get(
                'ascend.native_control_version') == 2
        ]
        _need(native_events,
              'Observed scalar context contains no native controls')
        edges, pending, generations = [], {}, {}

        def edge(source, target, relation, key, label, attrs):
            edges.append(
                dict(source=source,
                     target=target,
                     relation=relation,
                     association_key=key,
                     display_label=label,
                     attributes=attrs))

        for event in native_events:
            attrs = sites[event['site_id']]['attributes']
            channel = (attrs['ascend.native_source_pipe'],
                       attrs['ascend.native_destination_pipe'],
                       attrs['ascend.native_event_id'])
            operation = attrs['ascend.native_operation']
            if operation == 'set_flag':
                _need(channel not in pending,
                      'A native flag was set again before its recorded wait')
                generation = generations.get(channel, 0)
                pending[channel] = (event, generation)
            else:
                _need(channel in pending,
                      'A recorded native wait has no observed matching set')
                producer, generation = pending.pop(channel)
                generations[channel] = generation + 1
                key = json.dumps([observer['id'], *channel, generation],
                                 separators=(',', ':'))
                edge(
                    producer['record_ids'][-1], event['record_ids'][0],
                    'native_flag_generation_queued_before_wait', key,
                    'flag ' + str(channel) + ' generation ' + str(generation) +
                    ': queued SET -> WAIT',
                    dict(
                        channel=list(channel),
                        generation=generation,
                        generation_basis='complete_scalar_issuer_record_order',
                        physical_completion_instant_verified=False))
            key = json.dumps([observer['id'], *channel, generation],
                             separators=(',', ':'))
            scalar_ready = operation == 'wait_flag' and channel[1] == 0
            backend_site = sites[event['site_id']]['backend_site_id']
            points = [
                point for point in mapping['native_pcs']
                if point['backend_site_id'] == backend_site
            ]
            _need(
                points,
                'An observed native site has no final instruction candidates')
            backend_evidence = dict(
                model=mapping['model'],
                native_map_sha256=document_sha256(mapping),
                instruction_candidates=[
                    dict(point, instruction_hex=hex(point['instruction_word']))
                    for point in points
                ],
                getter_brackets=[
                    bracket for bracket in mapping['getter_brackets']
                    if bracket['function'] == points[0]['function']
                    and bracket['site_id'] == points[0]['site_id']
                ])
            edge(
                event['record_ids'][0], event['record_ids'][-1],
                'native_scalar_wait_readiness_observed'
                if scalar_ready else 'native_control_issue_bracket', key,
                ('scalar readiness observed after WAIT'
                 if scalar_ready else operation + ' enqueue observation') +
                ' / flag ' + str(channel) + ' generation ' + str(generation),
                dict(channel=list(channel),
                     generation=generation,
                     scalar_readiness_observed=scalar_ready,
                     backend_evidence=backend_evidence,
                     destination_engine_completion_time_verified=False,
                     hardware_busy_qualified=False))
            # Containment is source navigation, never a buffer/data dependency.
            if attrs[
                    'ascend.source_binding'] == 'containing_original_block_fragment_navigation':
                carrier = attrs['ascend.coordinate_carrier_source_op_id']
                source_events = [
                    outer for outer in events
                    if sites[outer['site_id']]['attributes'].get(
                        'ascend.native_control_version') is None
                    and sites[outer['site_id']]['attributes'].get(
                        'ascend.source_op_id') == carrier
                    and sites[outer['site_id']]['attributes'].get(
                        'ascend.original_block') ==
                    attrs['ascend.original_block']
                    and records[outer['record_ids'][-1]]['sequence'] > records[
                        event['record_ids'][-1]]['sequence']
                ]
                _need(
                    source_events,
                    'Native control has no closing original source fragment')
                outer = source_events[0]
                _need(
                    outer['start_tick'] <= event['start_tick'] <=
                    event['end_tick'] <= outer['end_tick'],
                    'Native control escaped its original source observation')
                edge(
                    outer['record_ids'][0], event['record_ids'][0],
                    'observed_fragment_contains_control_entry', key,
                    'native control observed within its lowered source fragment',
                    dict(source_cost_qualified=False))
                edge(
                    event['record_ids'][-1], outer['record_ids'][-1],
                    'observed_fragment_contains_control_exit', key,
                    'native control observed before its source fragment closed',
                    dict(source_cost_qualified=False))
        _need(not pending,
              'Observed native flag generations contain unmatched sets')
        unit = units[observer['id']]
        clock = SharedCounterProof(
            **batch['identity'],
            raw_sha256=batch['raw_artifact']['sha256'],
            canonical_sha256=document_sha256(batch),
            observer_ids=(observer['id'], ),
            program_coordinates=tuple(observer['program_coordinates']),
            domain_id=stable_id(identity, 'ascend-scalar-counter-scope',
                                observer['id']),
            epoch_id=stable_id(identity, 'ascend-scalar-capture-epoch',
                               observer['id']),
            period_numerator_ns=unit.period_numerator_ns,
            period_denominator=unit.period_denominator,
            max_elapsed_ns=unit.max_elapsed_ns,
            provider='ascend.c220.scalar_SYS_CNT_scope.v1',
            implementation_sha256=document_sha256(
                dict(native=implementation, unit=unit.implementation_sha256)),
            evidence_ids=unit.evidence_ids +
            ('native_map_sha256:' + document_sha256(mapping), ),
            scope_kind='single_observer')
        proofs.append(
            ObservedDependencyProof(
                clock=clock,
                provider=
                'ascend.c220.scalar_observed_native_flag_generations.v1',
                implementation_sha256=implementation,
                evidence_ids=
                ('native_map_sha256:' + document_sha256(mapping),
                 'compiled_native_references_sha256:' +
                 REFERENCE_ARCHIVE_SHA256,
                 'compiled_native_references_sha256:' +
                 ADDITIONAL_REFERENCE_ARCHIVE_SHA256,
                 'https://www.hiascend.com/doc_center/source/en/canncommercial/800/apiref/ascendcopapi/atlasascendc_api_07_0181.html'
                 ),
                edges=tuple(edges)))
    _need(proofs, 'No complete observed scalar counter scopes are available')
    return batch, proofs
