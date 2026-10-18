"""Conditional native operation order for late SM120 inline observations.

A freshly rebuilt counter_map is a precondition, not a timing certificate.
Original PTX instruction lines bind final SASS operations; a finite straight
path and absence of external entry establish order relative to inline readers.
This does not prove raw register/store provenance or physical engine activity.
"""
import hashlib
import re
from pathlib import Path

from .timeline_nvidia_control import _bound_functions, _compact, _need
from .timeline_nvidia_late_control import _single_entry
from .timeline_nvidia_machine import _lex

MODEL = 'nvidia.late.native_boundaries.v1'
_KINDS = frozenset(('copy_submit_after', 'commit_after', 'cta_barrier_after',
                    'shared_load_issue_bracket'))


def _native_lines(payload, functions):
    """Original embedded-PTX debug line -> exact final function/PCs."""
    function, source_line = None, None
    result = {}
    for line in payload.decode('utf-8').splitlines():
        section = re.match(r'^\s*\.section\s+([^,\s]+)', line)
        if section:
            name = section[1]
            function = name[6:] if name.startswith('.text.') else None
            source_line = None
        label = re.fullmatch(r'\s*([^\s:]+):\s*', line)
        if label and label[1] in functions:
            function, source_line = label[1], None
        annotation = re.fullmatch(
            r'\s*//## File "\.nv_debug_ptx_txt", line (\d+)\s*', line)
        if annotation:
            source_line = int(annotation[1])
        instruction = re.match(r'\s*/\*([0-9a-fA-F]+)\*/', line)
        if instruction and function in functions and source_line is not None:
            pc = int(instruction[1], 16)
            _need(pc in functions[function], 'Unknown annotated native PC')
            result.setdefault((function, source_line), []).append(pc)
    return result


def _straight_path(body, first, last):
    _need(
        type(first) is int and type(last) is int and first <= last
        and (last - first) % 16 == 0 and (last - first) // 16 <= 2048,
        'Native operation and reader do not bound a finite forward path')
    _single_entry(body, first, last)
    for pc in range(first, last + 16, 16):
        row = body.get(pc)
        _need(row is not None, 'Missing instruction in native boundary path')
        opcode = row['opcode']
        _need(
            not opcode.startswith(('BRA', 'BRX', 'JMP', 'JMX', 'CALL', 'RET',
                                   'BSSY', 'BSYNC', 'BREAK', 'CONT', 'EXIT'))
            and row.get('other-attributes', {}).get('control-flow') != 'True',
            'Control flow within native boundary path is not verified')


def _ptx_operation(lines, markers, site, counters):
    key = site['site_id']
    end = counters[key, 'exit']
    if site['kind'] == 'shared_load_issue_bracket':
        begin = counters[key, 'entry']
        _need(begin['ptx_line'] < end['ptx_line'], 'Reversed PTX readers')
        # Exclude both reader instructions, keep original one-based PTX lines.
        candidates = [
            (n + 1, lines[n])
            for n in range(begin['ptx_line'], end['ptx_line'] - 1)
            if lines[n] and not lines[n].startswith(('.loc', '.file'))
        ]
        _need(len(candidates) == 1, 'Ambiguous PTX bracket contents')
        return candidates[0]
    marker = markers[key, 'exit']
    for n in range(marker - 2, -1, -1):
        token = lines[n]
        if token and not token.startswith(('.loc', '.file')):
            return n + 1, token
    raise ValueError('No PTX operation before late checkpoint')


def _matches(kind, token, row):
    """Inspected native families; no operator/source/shape identifiers."""
    opcode = row['opcode']
    _need(row.get('predicate') is None, 'Predicated native boundary operation')
    if kind == 'copy_submit_after':
        _need(
            re.fullmatch(
                r'cp\.async\.(?:ca|cg)\.shared\.global\[.+\],\[.+\],(?:0x10|16)(?:,.+)?;',
                token) is not None and opcode.startswith('LDGSTS.')
            and opcode.endswith('.128'),
            'Unverified PTX/native asynchronous copy form')
    elif kind == 'commit_after':
        _need(token == 'cp.async.commit_group;' and opcode == 'LDGDEPBAR',
              'Unverified PTX/native asynchronous commit')
    elif kind == 'cta_barrier_after':
        _need(
            token == 'bar.sync0;' and opcode.startswith('BAR.SYNC.')
            and _compact(row.get('operands', '')) == '0x0',
            'Unverified PTX/native full CTA barrier')
    else:
        match = re.fullmatch(
            r'ldmatrix\.sync\.aligned\.m8n8\.x([124])(\.trans)?\.shared\.b16\{.+\},\[.+\];',
            token)
        _need(match is not None, 'Unverified PTX matrix shared load')
        expected = 'LDSM.16.' + ('MT88.' if match[2] else 'M88.') + match[1]
        _need(opcode == expected, 'Native matrix shared load geometry differs')


def derive_native_boundaries(*, machine_map, sass_lines, sass_json, ptx, plan):
    _need(
        machine_map.get('status')
        == 'counter_mapping_complete_region_unverified'
        and machine_map.get('marker_flavor') == 'late-v1'
        and machine_map.get('expected_sm') == [12, 0]
        and machine_map.get('binary_id') == plan.get('binary_id'),
        'Native boundaries require the matching actual SM120 late object map')
    _need(
        type(ptx) is bytes and hashlib.sha256(ptx).hexdigest()
        == machine_map['artifacts']['ptx_sha256'], 'Original PTX changed')
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    native_lines = _native_lines(sass_lines, functions)
    lines, marker_rows = _lex(ptx.decode('utf-8'), 'late-v1')
    markers = {}
    for line, site_id, phase in marker_rows:
        _need((site_id, phase) not in markers, 'Duplicate PTX late marker')
        markers[site_id, phase] = line
    readers = {}
    for row in machine_map['counter_pcs']:
        key = row['site_id'], row['phase']
        _need(key not in readers, 'Ambiguous static inline reader')
        _need(row['annotation_line'] == markers.get(key),
              'PTX marker mismatch')
        readers[key] = row
    results = []
    for site in plan['sites']:
        kind = site['kind']
        if kind not in _KINDS:
            continue
        result = dict(site_id=site['site_id'], kind=kind, status='unverified')
        try:
            key = site['site_id']
            bracket = kind == 'shared_load_issue_bracket'
            semantic = 'observer_issue_bracket' if bracket else 'observer_checkpoint_after'
            _need(site['record_semantics'] == semantic,
                  'Unexpected site semantics')
            _need(len(site['members']) == 1, 'Ambiguous native source members')
            end = readers[key, 'exit']
            begin = readers[key, 'entry'] if bracket else None
            _need(
                end.get('sass_predicate') is None and
                (begin is None or (begin['function'] == end['function']
                                   and begin.get('sass_predicate') is None)),
                'Predicated or split native readers')
            line, token = _ptx_operation(lines, markers, site, readers)
            body = functions[end['function']]
            candidates = []
            for pc in native_lines.get((end['function'], line), []):
                try:
                    _matches(kind, token, body[pc])
                except ValueError:
                    continue
                candidates.append(pc)
            _need(
                len(candidates) == 1,
                'Missing or ambiguous original PTX/native operation')
            native_pc = candidates[0]
            first = begin['pc'] if bracket else native_pc
            _need(
                first <= native_pc < end['pc']
                and (not bracket or first < native_pc),
                'Native operation moved outside readers')
            _straight_path(body, first, end['pc'])
            result.update(status='native_boundary_control_order_checked',
                          function=end['function'],
                          ptx_operation_line=line,
                          ptx_operation=token,
                          native_pc=native_pc,
                          native_opcode=body[native_pc]['opcode'],
                          native_operands=body[native_pc].get('operands', ''),
                          begin_reader_pc=begin['pc'] if bracket else None,
                          end_reader_pc=end['pc'],
                          relation='between_inline_readers'
                          if bracket else 'before_exit_reader',
                          byte_transfer_completion_verified=False)
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    from . import timeline_nvidia_control, timeline_nvidia_late_control, timeline_nvidia_machine
    rules = [
        Path(__file__),
        Path(timeline_nvidia_control.__file__),
        Path(timeline_nvidia_late_control.__file__),
        Path(timeline_nvidia_machine.__file__)
    ]
    return dict(model=MODEL,
                binary_id=machine_map['binary_id'],
                sites=results,
                implementation_sha256={
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in rules
                },
                proof_scope='conditional_native_instruction_order',
                record_value_provenance_verified=False,
                participation_verified=False,
                source_region_qualified=False,
                clock_qualified=False,
                hardware_overlap_verified=False,
                time_flows_qualified=False)


def load_native_boundary_report(directory, capture, machine_map):
    """Read retained PTX only; callers freshly validate the full object map."""
    from .timeline_store import read_artifact
    owner, metadata = capture['owner'], capture['metadata']
    _need(
        owner['binary_id'] == metadata['binary_id'] ==
        machine_map['binary_id'],
        'Native boundary evidence belongs to another binary')
    rows = [
        row for row in metadata['timeline_artifacts']
        if row['retained_file'].endswith('.ptx')
    ]
    _need(len(rows) == 1, 'Missing or ambiguous original native-boundary PTX')
    ptx = read_artifact(directory, rows[0]['retained_file'])
    _need(
        hashlib.sha256(ptx).hexdigest() == rows[0]['sha256'],
        'Retained native-boundary PTX changed')
    base = 'machine/' + owner['binary_id']
    inputs = dict(machine_map=machine_map,
                  sass_lines=read_artifact(directory, base + '/lines.stdout'),
                  sass_json=read_artifact(directory, base + '/json.stdout'),
                  ptx=ptx,
                  plan=owner['plan'])
    report = derive_native_boundaries(**inputs)
    from .timeline_nvidia_late_values import inspect_timer_store_values
    report['timer_store_values'] = inspect_timer_store_values(**inputs)
    from .timeline_nvidia_late_records import inspect_record_fields
    report['relative_record_fields'] = inspect_record_fields(**inputs)
    from .timeline_nvidia_late_payloads import inspect_shared_payloads
    report['shared_payload_values'] = inspect_shared_payloads(**inputs)
    return report
