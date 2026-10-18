"""Native four-field late-record layout and literal payload witnesses.

Checks field identity, relative displacement and stable common native addresses.
It does not prove the absolute allocation/program/ordinal address expression or
variable shared-address/valid-size payloads. Those remain separate obligations.
"""
import hashlib
import json
import re
from pathlib import Path

from .timeline_nvidia_control import _bound_functions, _compact, _need, _registers
from .timeline_nvidia_late_boundaries import _native_lines, _straight_path, derive_native_boundaries
from .timeline_nvidia_late_control import derive_late_wait_control
from .timeline_nvidia_late_values import (_predecessors, _destinations,
                                          _predicate, _move_source,
                                          derive_timer_store_values,
                                          MAX_STATES)
from .timeline_nvidia_machine import _lex

MODEL = 'nvidia.late.relative_record_fields.v1'


def _constant_word(body, graph, *, store_pc, register, expected):
    """All reaching definitions of one native store word equal the literal."""
    _need(
        type(expected) is int and 0 <= expected <= 0xffffffff,
        'Invalid literal word')
    work = [(pc, register) for pc in graph[store_pc]]
    _need(work, 'Native literal store has no reaching instructions')
    visited, roots = set(), 0
    while work:
        pc, register = work.pop()
        if register in ('RZ', 'URZ'):
            _need(expected == 0, 'Zero register differs from expected literal')
            roots += 1
            continue
        state = pc, register
        if state in visited:
            continue
        visited.add(state)
        _need(len(visited) <= MAX_STATES, 'Literal value-flow budget exceeded')
        row = body[pc]
        active = _predicate(row.get('predicate'))
        inputs = [register]
        if active is not False and register in _destinations(row):
            opcode = row['opcode']
            _need(
                opcode
                in ('MOV', 'MOV.64', 'UMOV', 'UMOV.64', 'CS2R', 'CS2UR'),
                'Native literal overwritten by an unknown value at ' + hex(pc))
            fields = _compact(row.get('operands', '')).split(',')
            _need(len(fields) == 2, 'Unknown native literal definition')
            width = 2 if opcode.endswith('.64') or opcode.startswith(
                'CS2') else 1
            word = _registers(fields[0], width).index(register)
            literal = None
            if fields[1] in ('RZ', 'URZ', 'SRZ'):
                literal = 0
            elif re.fullmatch(r'-?0x[0-9a-fA-F]+', fields[1]):
                value = int(fields[1], 16)
                _need(not (width == 2 and 0x80000000 <= value <= 0xffffffff),
                      'Ambiguous native wide literal sign extension')
                literal = (value >> (32 * word)) & 0xffffffff
            if literal is not None:
                _need(literal == expected,
                      'Native literal word differs from source field')
                roots += 1
                inputs = [] if active is True else [register]
            else:
                _need(opcode in ('MOV', 'MOV.64', 'UMOV', 'UMOV.64'),
                      'Unknown native special-register literal')
                source = _move_source(row, register)
                inputs = [source] if active is True else [register, source]
        if not inputs:
            continue
        parents = graph.get(pc, ())
        _need(parents,
              'Native field path lacks the expected literal definition')
        work.extend((parent, value) for parent in parents for value in inputs)
    _need(roots > 0, 'No reaching literal definition')
    return len(visited)


def _native_store(function, line, annotations, body):
    rows = [(pc, body[pc]) for pc in annotations.get((function, line), ())
            if body[pc]['opcode'] == 'STG.E.64']
    _need(len(rows) == 1, 'Missing or ambiguous native 64-bit field store')
    pc, row = rows[0]
    _need(row.get('predicate') is None, 'Predicated native record field')
    match = re.fullmatch(
        r'desc\[(UR\d+)\]\[(R\d+)\.64(?:\+(-?0x[0-9a-fA-F]+))?\],(R\d+|RZ)',
        _compact(row.get('operands', '')))
    _need(match is not None,
          'Unknown native record field address/value operands')
    return dict(pc=pc,
                descriptor=match[1],
                address_register=match[2],
                offset=int(match[3], 16) if match[3] else 0,
                value_register=match[4],
                ptx_line=line)


def _stable_field_addresses(body, fields, stride):
    tag = fields[0]
    first, last = min(r['pc'] for r in fields), max(r['pc'] for r in fields)
    _straight_path(body, first, last)
    for i, field in enumerate(fields):
        _need(
            field['descriptor'] == tag['descriptor']
            and field['address_register'] == tag['address_register']
            and field['offset'] - tag['offset'] == i * stride,
            'Native fields differ from one coalesced four-word record')
    registers = set(
        _registers(tag['descriptor'], 2) +
        _registers(tag['address_register'], 2))
    for pc in range(first, last, 16):
        row = body[pc]
        if _predicate(row.get('predicate')) is not False:
            _need(
                not registers.intersection(_destinations(row)),
                'Common record address/descriptor overwritten between field stores'
            )
    return dict(descriptor_registers=_registers(tag['descriptor'], 2),
                address_registers=_registers(tag['address_register'], 2),
                first_store_pc=first,
                last_store_pc=last,
                relative_field_offsets=[i * stride for i in range(4)])


def derive_record_fields(*, machine_map, sass_lines, sass_json, ptx, plan):
    # Recompute native timer values from the actual object, never trust a saved
    # successful diagnostic supplied by the caller.
    timer_values = derive_timer_store_values(machine_map=machine_map,
                                             sass_lines=sass_lines,
                                             sass_json=sass_json,
                                             ptx=ptx,
                                             plan=plan)
    _need(
        plan.get('header_words') == 6
        and plan.get('word_layout') == 'program/logical_word/actor'
        and type(plan.get('actors')) is int and 1 <= plan['actors'] <= 1024,
        'Unknown native late field layout')
    stride = plan['actors'] * 8
    lines, _ = _lex(ptx.decode('utf-8'), 'late-v1')
    stores = {}
    for line, token in enumerate(lines, 1):
        match = re.fullmatch(
            r'st\.global\.b64\[(%rd\d+)(?:\+(-?\d+))?\],(.+);', token)
        if match:
            stores.setdefault((match[1], int(match[2]) if match[2] else 0),
                              []).append(dict(line=line, value=match[3]))
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    annotations = _native_lines(sass_lines, functions)
    graphs = {name: _predecessors(body) for name, body in functions.items()}
    readers = {
        (r['site_id'], r['phase']): r
        for r in machine_map['counter_pcs']
    }
    timer_sites = {
        (r['site_id'], r['phase']): r
        for r in timer_values['sites']
    }
    control_inputs = dict(machine_map=machine_map,
                          sass_lines=sass_lines,
                          sass_json=sass_json,
                          plan=plan)
    waits = {
        row['site_id']: row
        for row in derive_late_wait_control(**control_inputs)['sites']
    }
    native_sites = {
        row['site_id']: row
        for row in derive_native_boundaries(
            **dict(control_inputs, ptx=ptx))['sites']
    }
    results = []
    for site in plan['sites']:
        key = site['site_id']
        result = dict(site_id=key, kind=site['kind'], status='unverified')
        try:
            candidates = [
                (base, offset, rows[0])
                for (base, offset), rows in stores.items()
                if len(rows) == 1 and rows[0]['value'] == str(key)
                and offset >= plan['header_words'] *
                stride and (offset // stride - plan['header_words']) %
                4 == 0 and offset % stride == 0
            ]
            # The same PTX register name can exist in another function. Only
            # candidates with this reader function's actual field instruction
            # are admitted, without choosing nearest PCs or source locations.
            reader = readers[key, 'exit']
            function = reader['function']
            candidates = [(base, offset, row)
                          for base, offset, row in candidates
                          if (function, row['line']) in annotations]
            _need(
                len(candidates) == 1,
                'Missing or ambiguous original PTX record tag')
            base, offset, _ = candidates[0]
            record_index = (offset // stride - plan['header_words']) // 4
            _need(
                type(plan.get('capacity_per_program')) is int
                and 0 <= record_index < plan['capacity_per_program'],
                'PTX batch record index exceeds admitted capacity')
            quartet = []
            for i in range(4):
                rows = stores.get((base, offset + i * stride), [])
                _need(
                    len(rows) == 1, 'Missing or ambiguous original PTX field')
                quartet.append(rows[0])
            fields = [
                _native_store(function, row['line'], annotations,
                              functions[function]) for row in quartet
            ]
            address_proof = _stable_field_addresses(functions[function],
                                                    fields, stride)
            graph = graphs[function]
            tag_registers = (['RZ', 'RZ'] if fields[0]['value_register']
                             == 'RZ' else _registers(
                                 fields[0]['value_register'], 2))
            for word, register in enumerate(tag_registers):
                _constant_word(functions[function],
                               graph,
                               store_pc=fields[0]['pc'],
                               register=register,
                               expected=(key >> (word * 32)) & 0xffffffff)
            for index, phase in ((1, 'entry'), (2, 'exit')):
                if site['record_semantics'] == 'observer_checkpoint_after':
                    phase = 'exit'
                proof = timer_sites[key, phase]
                _need(
                    proof['status'] == 'timer_to_native_store_values_checked',
                    'Field getter values were not verified')
                matching = [
                    row for row in proof['stores']
                    if row['ptx_line'] == quartet[index]['line']
                    and row['store_pc'] == fields[index]['pc']
                ]
                _need(
                    len(matching) == 1,
                    'Native field is not the verified site/phase timer store')
            literal = None
            if re.fullmatch(r'\d+', quartet[3]['value']):
                literal = int(quartet[3]['value'])
                _need(0 <= literal <= 0xffffffffffffffff,
                      'Oversized payload literal')
                registers = (['RZ', 'RZ'] if fields[3]['value_register']
                             == 'RZ' else _registers(
                                 fields[3]['value_register'], 2))
                for word, register in enumerate(registers):
                    _constant_word(functions[function],
                                   graph,
                                   store_pc=fields[3]['pc'],
                                   register=register,
                                   expected=(literal >>
                                             (word * 32)) & 0xffffffff)
            control_payload = None
            if site['kind'] == 'wait_bracket':
                wait = waits.get(key, {})
                _need(
                    wait.get('status') == 'late_wait_control_order_checked'
                    and literal == wait['pending_group_limit'],
                    'Recorded wait payload differs from the actual native group limit'
                )
                control_payload = dict(kind='native_wait_group_limit',
                                       value=literal,
                                       native_pc=wait['wait_pc'])
            elif site['kind'] in ('commit_after', 'cta_barrier_after'):
                native = native_sites.get(key, {})
                _need(
                    native.get('status')
                    == 'native_boundary_control_order_checked'
                    and literal == 0,
                    'Recorded control payload lacks its actual native boundary'
                )
                control_payload = dict(kind='reserved_zero_control_payload',
                                       value=0,
                                       native_pc=native['native_pc'])
            result.update(status='native_record_fields_checked',
                          function=function,
                          native_control_payload=control_payload,
                          source_base=base,
                          source_tag_byte_offset=offset,
                          source_batch_record_index=record_index,
                          fields=[
                              dict(field=label, **native)
                              for label, native in zip(('tag', 'begin', 'end',
                                                        'payload'), fields)
                          ],
                          address_proof=address_proof,
                          tag_value_verified=True,
                          timer_field_values_verified=True,
                          literal_payload=literal,
                          payload_status='native_literal_checked' if literal
                          is not None else 'variable_payload_unverified',
                          relative_field_binding_verified=True,
                          absolute_raw_slot_binding_verified=False)
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    return dict(
        model=MODEL,
        binary_id=machine_map['binary_id'],
        sites=results,
        implementation_sha256=_rule_digests(),
        proof_scope=
        'native_four_field_relative_addresses_tag_timer_and_literal_payload_values',
        absolute_raw_slot_binding_verified=False,
        record_storage_binding_verified=False,
        record_value_provenance_verified=False,
        variable_payload_provenance_verified=False,
        clock_qualified=False,
        hardware_overlap_verified=False,
        time_flows_qualified=False)


def _rule_digests():
    from . import timeline_nvidia_control, timeline_nvidia_late_boundaries, timeline_nvidia_late_values, timeline_nvidia_late_control, timeline_nvidia_machine
    rules = [
        Path(__file__),
        Path(timeline_nvidia_control.__file__),
        Path(timeline_nvidia_late_boundaries.__file__),
        Path(timeline_nvidia_late_values.__file__),
        Path(timeline_nvidia_late_control.__file__),
        Path(timeline_nvidia_machine.__file__)
    ]
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in rules
    }


def inspect_record_fields(**inputs):
    try:
        return derive_record_fields(**inputs)
    except (ValueError, KeyError, TypeError) as error:
        return dict(model=MODEL,
                    binary_id=inputs['machine_map'].get('binary_id'),
                    status='unverified_native_record_inputs_or_pattern',
                    implementation_sha256=_rule_digests(),
                    sites=[],
                    reason=str(error),
                    absolute_raw_slot_binding_verified=False,
                    record_value_provenance_verified=False,
                    time_flows_qualified=False)


def validate_control_payloads(report, decoded):
    """Decoded raw agrees with newly derived native control operands.

    The report must be freshly obtained from the bound object. This is a raw
    value consistency test, not an absolute raw-slot/variable payload proof.
    """
    _need(
        report.get('model') == MODEL and decoded.get('schema_version') == 1 and
        report.get('status') != 'unverified_native_record_inputs_or_pattern',
        'Unknown native control payload/decoded schema')
    _need(
        decoded.get('complete') is True,
        'Control payload check needs complete raw')
    sites = {
        row['site_id']: row
        for row in report['sites']
        if row.get('status') == 'native_record_fields_checked'
        and row.get('native_control_payload') is not None
    }
    occurrences = []
    for program in decoded['programs']:
        for actor in program['observers']:
            for ordinal, event in enumerate(actor['events']):
                site = sites.get(event['site_id'])
                if site is None:
                    continue
                native = site['native_control_payload']
                _need(
                    event['payload'] == native['value'],
                    'Decoded control payload contradicts the final native operation'
                )
                occurrences.append(
                    dict(program=program['program_id'],
                         actor=actor['actor'],
                         ordinal=ordinal,
                         site_id=event['site_id'],
                         value=event['payload'],
                         function=site['function'],
                         native_pc=native['native_pc'],
                         raw_tag_span=[event['raw_tag_offset_bytes'], 8],
                         raw_payload_span=[
                             event['raw_payload_offset_bytes'], 8
                         ]))
    return dict(model='nvidia.late.native_control_payload_agreement.v1',
                status='native_control_payloads_consistent'
                if occurrences else 'no_verified_control_payload_occurrences',
                binary_id=report['binary_id'],
                raw_sha256=decoded['raw_sha256'],
                occurrences=occurrences,
                absolute_raw_slot_binding_verified=False,
                variable_payload_provenance_verified=False,
                time_flows_qualified=False)


def load_control_payload_agreement(directory, capture, fields_report):
    from .timeline_store import read_artifact
    from .timeline_nvidia_late_raw import decode_late_raw
    owner = capture['owner']
    _need(
        fields_report.get('binary_id') == owner['binary_id'],
        'Native control payload report belongs to another binary')
    raw = read_artifact(directory, capture['raw_file'])
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Native control raw artifact changed')
    decoded = decode_late_raw(owner['plan'],
                              raw,
                              slots=owner['layout']['slots'])
    result = validate_control_payloads(fields_report, decoded)
    result['identity'] = {
        key: owner[key]
        for key in ('capture_id', 'invocation_id', 'binary_id')
    }
    from . import timeline_nvidia_late_raw, timeline_store
    result['field_report_sha256'] = hashlib.sha256(
        json.dumps(fields_report, sort_keys=True,
                   separators=(',', ':')).encode()).hexdigest()
    result['implementation_sha256'] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), Path(timeline_nvidia_late_raw.__file__),
                     Path(timeline_store.__file__))
    }
    return result
