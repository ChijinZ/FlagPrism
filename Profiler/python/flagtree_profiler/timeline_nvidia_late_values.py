"""Actual late inline getter -> native global-store value witnesses.

This is a bounded, conservative reaching-definition check on the final native
control graph. It is deliberately separate from proving a store address belongs
to an admitted raw slot, publication, payload geometry or clock comparison.
"""
import hashlib
import re
from pathlib import Path

from .timeline_nvidia_control import (_bound_functions, _branch, _compact,
                                      _need, _registers)
from .timeline_nvidia_late_boundaries import _native_lines
from .timeline_nvidia_late_control import _single_entry
from .timeline_nvidia_machine import _lex

MODEL = 'nvidia.late.timer_store_values.v1'
MAX_STATES = 32768


def _predicate(value):
    if value in (None, '@PT', '@UPT'):
        return True
    if value in ('@!PT', '@!UPT'):
        return False
    _need(
        re.fullmatch(r'@!?(?:U?P)\d+', value) is not None,
        'Unknown native predicate')
    return None


def _predecessors(body):
    """Overapproximate branches/reconvergence, never choose a captured path."""
    pcs = sorted(body)
    _need(pcs and len(pcs) <= MAX_STATES, 'Oversized or empty native body')
    setups = []
    for pc, row in body.items():
        if row['opcode'].startswith('BSSY'):
            match = re.fullmatch(r'(B\d+),0x([0-9a-fA-F]+)',
                                 _compact(row.get('operands', '')))
            _need(match is not None and row.get('predicate') is None,
                  'Unknown reconvergence setup')
            target = int(match[2], 16)
            _need(target in body, 'Reconvergence leaves native function')
            setups.append((pc, match[1], target))
    syncs = set()
    for pc, row in body.items():
        if not row['opcode'].startswith('BSYNC'):
            continue
        barrier = _compact(row.get('operands', ''))
        candidates = [(start, target) for start, name, target in setups
                      if name == barrier and target == pc + 16 and start < pc]
        _need(
            len(candidates) == 1 and row.get('predicate') is None,
            'Native reconvergence is not a matched forward fallthrough')
        first, last = candidates[0]
        _single_entry(body, first, pc)
        for at in range(first + 16, pc, 16):
            instruction = body[at]
            opcode = instruction['opcode']
            operand = _compact(instruction.get('operands', ''))
            _need(
                not (opcode.startswith(
                    ('BSSY', 'BSYNC')) and operand.split(',')[0] == barrier),
                'Reconvergence token overwritten or consumed inside region')
            if opcode in ('BRA', 'BRA.U'):
                _, destination = _branch(instruction)
                _need(first < destination <= pc,
                      'Branch escapes the matched reconvergence region')
        syncs.add(pc)
    successors = {}
    for pc in pcs:
        row = body[pc]
        opcode = row['opcode']
        active = _predicate(row.get('predicate'))
        next_pc = pc + 16
        edges = []
        if opcode in ('BRA', 'BRA.U'):
            predicate, target = _branch(row)
            branch_active = (True if predicate is None else None)
            if branch_active is not False:
                edges.append(target)
            if branch_active is not True:
                edges.append(next_pc)
        elif opcode.startswith('BSYNC'):
            _need(pc in syncs, 'Unverified native reconvergence')
            edges.append(next_pc)
        elif opcode == 'EXIT':
            if active is not True:
                edges.append(next_pc)
        else:
            _need(
                not opcode.startswith(
                    ('BRX', 'JMP', 'JMX', 'CALL', 'RET', 'BREAK', 'CONT')) and
                (row.get('other-attributes', {}).get('control-flow') != 'True'
                 or opcode.startswith('BSSY')),
                'Unknown native control transition')
            edges.append(next_pc)
        _need(all(edge in body or edge == pcs[-1] + 16 for edge in edges),
              'Native control edge leaves inspected body')
        successors[pc] = set(edges)
    reachable, work = set(), [pcs[0]]
    while work:
        pc = work.pop()
        if pc not in reachable:
            _need(pc in body,
                  'Reachable native path falls outside the function')
            reachable.add(pc)
            work.extend(successors[pc])
    predecessors = {pc: set() for pc in reachable}
    for pc in reachable:
        for target in successors[pc]:
            predecessors[target].add(pc)
    return predecessors


def _destinations(row):
    """Explicit inspected families; unknown writes invalidate a value proof."""
    opcode = row['opcode']
    family = opcode.split('.')[0]
    if family in ('STG', 'STS', 'STL', 'REDG', 'LDGSTS', 'LDGDEPBAR', 'DEPBAR',
                  'BAR', 'NOP', 'BRA', 'BSSY', 'BSYNC', 'EXIT'):
        return []
    fields = _compact(row.get('operands', '')).split(',')
    first = re.match(r'^(U?R\d+|[U]?RZ|U?P\d+|UPT|PT)', fields[0])
    _need(first is not None, 'Unknown native destination format')
    if family in ('ISETP', 'UISETP', 'PSETP', 'PLOP3'):
        return [
            field for field in fields[:2] if re.fullmatch(r'U?P\d+', field)
        ]
    if family == 'VOTEU':
        return [
            field for field in fields[:2]
            if re.fullmatch(r'U?P\d+|U?R\d+', field)
        ]
    scalar = frozenset(
        ('MOV', 'UMOV', 'S2R', 'S2UR', 'R2UR', 'IMAD', 'UIMAD', 'IADD',
         'IADD3', 'UIADD3', 'LEA', 'ULEA', 'LOP3', 'ULOP3', 'SHF', 'USHF',
         'SGXT', 'SEL', 'USEL', 'P2R', 'POPC', 'PRMT', 'UFLO', 'LDC', 'LDCU',
         'LDG', 'LDS', 'LDL', 'CS2R', 'CS2UR'))
    width = 1
    if family in scalar:
        if ('.128' in opcode):
            width = 4
        elif '.64' in opcode or '.WIDE' in opcode or family in ('CS2R',
                                                                'CS2UR'):
            width = 2
    elif family == 'LDSM':
        match = re.fullmatch(r'LDSM\.16\.M(?:T)?88\.([124])', opcode)
        _need(match is not None, 'Unknown matrix shared-load write footprint')
        width = int(match[1])
    elif opcode == 'HMMA.16816.F32':
        width = 4
    else:
        raise ValueError('Unknown native register write family: ' + opcode)
    base = first[1]
    if family in ('LOP3', 'ULOP3') and (base in ('PT', 'UPT')
                                        or re.fullmatch(r'U?P\d+', base)):
        return [
            field for field in fields[:2]
            if re.fullmatch(r'U?P\d+|U?R\d+', field)
        ]
    outputs = [] if base in ('RZ', 'URZ', 'PT',
                             'UPT') else _registers(base, width)
    # Scalar arithmetic may additionally write carry/predicate outputs.
    if family in ('IADD3', 'UIADD3', 'LEA', 'ULEA', 'IMAD', 'UIMAD', 'LOP3',
                  'ULOP3'):
        outputs.extend(field for field in fields[:3]
                       if re.fullmatch(r'U?P\d+', field))
    return outputs


def _move_source(row, register):
    fields = _compact(row.get('operands', '')).split(',')
    _need(len(fields) == 2, 'Unknown move operands')
    width = 2 if row['opcode'].endswith('.64') else 1
    outputs = _registers(fields[0], width)
    offset = outputs.index(register)
    source = fields[1].removesuffix('.reuse')
    _need(
        re.fullmatch(r'U?R\d+', source) is not None,
        'Timer word replaced by an immediate or zero: ' + row['operands'])
    return _registers(source, width)[offset]


def _local_access(row):
    """Decode bounded fixed local slots, preserving 32-bit word addresses."""
    opcode = row['opcode']
    match = re.fullmatch(r'(LDL(?:\.LU)?|STL)(?:\.(32|64|128))?', opcode)
    _need(match is not None, 'Unknown native local-memory access')
    size = int(match[2] or 32) // 8
    operands = _compact(row.get('operands', ''))
    if match[1] == 'STL':
        parsed = re.fullmatch(r'(\[[^\[\]]+\]),(R\d+|RZ)', operands)
        _need(parsed is not None, 'Unknown local store operands')
        address, value = parsed[1], parsed[2]
    else:
        # The inspected nvdisasm JSON omits the delimiter before a local
        # address; its text counterpart is independently bound by the caller.
        parsed = re.fullmatch(r'(R\d+),?(\[[^\[\]]+\])', operands)
        _need(parsed is not None, 'Unknown local load operands')
        value, address = parsed[1], parsed[2]
    slot = re.fullmatch(r'\[(R\d+)(?:\+(-?0x[0-9a-fA-F]+))?\]', address)
    _need(slot is not None,
          'Dynamic local-memory address is not a fixed spill slot')
    offset = int(slot[2], 16) if slot[2] else 0
    _need(offset % 4 == 0 and abs(offset) + size <= 1024 * 1024,
          'Unaligned or oversized local spill slot')
    if value == 'RZ' and match[1] == 'STL':
        values = ['RZ'] * (size // 4)
    else:
        _need(
            re.fullmatch(r'R\d+', value) is not None,
            'Unknown local spill register range')
        values = _registers(value, size // 4)
    return slot[1], offset, values


def check_timer_word(body, predecessors, *, reader, store_pc, word_register,
                     word_index):
    """Every possible reaching definition must be this reader's actual word.

    State means the register *after* the instruction at PC. Predicated moves
    conservatively include both paths; reaching a different definition, the
    function entry, or an unknown instruction fails. Loops are a finite state
    graph; stopping at the getter means the latest dynamic execution, not a
    guessed mathematical iteration.
    """
    _need(word_index in (0, 1), 'Unknown timer word')
    pc = reader['pc']
    _need(
        pc in body and store_pc in predecessors
        and _predicate(reader.get('sass_predicate')) is True,
        'Missing reachable unconditional getter/store')
    getter = body[pc]
    _need(
        getter['opcode'] in ('CS2R', 'CS2UR')
        and getter.get('predicate') is None
        and _compact(getter['operands']).endswith(',SR_GLOBALTIMERLO'),
        'Getter is not the actual full-width global timer')
    destination = _compact(getter['operands']).split(',')[0]
    expected = _registers(destination, 2)[word_index]
    work = [(p, word_register) for p in predecessors[store_pc]]
    _need(work, 'Store has no reaching instructions')
    seen, roots = set(), set()
    while work:
        at, register = work.pop()
        state = at, register
        if state in seen:
            continue
        seen.add(state)
        _need(
            len(seen) <= MAX_STATES, 'Native timer value-flow budget exceeded')
        row = body[at]
        if at == pc:
            _need(register == expected,
                  'Timer words swapped or unrelated value')
            roots.add(at)
            continue
        active = _predicate(row.get('predicate'))
        inputs = [register]
        if isinstance(register, tuple):
            _, base, offset = register
            _need(active is False or base not in _destinations(row),
                  'Local spill base changed before its reaching store')
            if active is not False and row['opcode'].split('.')[0] == 'STL':
                actual_base, actual_offset, values = _local_access(row)
                _need(actual_base == base,
                      'Possible alias from another local spill base')
                delta = offset - actual_offset
                if 0 <= delta < 4 * len(values):
                    source = values[delta // 4]
                    inputs = [source] if active is True else [register, source]
        elif active is not False and register in _destinations(row):
            if row['opcode'].split('.')[0] == 'LDL':
                base, offset, values = _local_access(row)
                source = ('local', base, offset + 4 * values.index(register))
            else:
                _need(
                    row['opcode'] in ('MOV', 'MOV.64', 'UMOV', 'UMOV.64'),
                    'Timer word overwritten before native global store at ' +
                    hex(at) + ': ' + register + ' ' + row['opcode'])
                source = _move_source(row, register)
            inputs = [source] if active is True else [register, source]
        parents = predecessors.get(at, ())
        _need(parents, 'A native store path bypasses the expected timer read')
        work.extend((parent, value) for parent in parents for value in inputs)
    _need(roots == {pc}, 'No reaching full-width timer getter')
    return len(seen)


def derive_timer_store_values(*, machine_map, sass_lines, sass_json, ptx,
                              plan):
    _need(
        machine_map.get('status')
        == 'counter_mapping_complete_region_unverified'
        and machine_map.get('marker_flavor') == 'late-v1'
        and machine_map.get('expected_sm') == [12, 0]
        and machine_map.get('binary_id') == plan.get('binary_id'),
        'Timer value witnesses require the matching actual SM120 late object')
    _need(
        type(ptx) is bytes and hashlib.sha256(ptx).hexdigest()
        == machine_map['artifacts']['ptx_sha256'], 'Original PTX changed')
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    annotations = _native_lines(sass_lines, functions)
    lines, _ = _lex(ptx.decode('utf-8'), 'late-v1')
    predecessor_maps = {
        name: _predecessors(body)
        for name, body in functions.items()
    }
    results = []
    keys = [(r['site_id'], r['phase']) for r in machine_map['counter_pcs']]
    _need(len(set(keys)) == len(keys), 'Duplicate static getter identity')
    for reader in machine_map['counter_pcs']:
        result = dict(site_id=reader['site_id'],
                      phase=reader['phase'],
                      status='unverified',
                      stores=[])
        try:
            token = lines[reader['ptx_line'] - 1]
            match = re.fullmatch(r'mov\.u64(%rd\d+),%globaltimer;', token)
            _need(match is not None, 'Unknown original PTX timer result')
            variable = match[1]
            stores = [
                (i + 1,
                 re.fullmatch(
                     r'st\.global\.b64(\[.+\]),' + re.escape(variable) + ';',
                     line)) for i, line in enumerate(lines)
            ]
            stores = [(line, match) for line, match in stores if match]
            _need(stores,
                  'Original PTX getter has no direct 64-bit record store')
            body = functions[reader['function']]
            for line, match in stores:
                native = [
                    (pc, body[pc])
                    for pc in annotations.get((reader['function'], line), ())
                    if body[pc]['opcode'] == 'STG.E.64'
                ]
                _need(
                    len(native) == 1,
                    'Missing or ambiguous PTX/native timer store')
                pc, row = native[0]
                operand = re.fullmatch(r'(desc\[UR\d+\]\[[^\]]+\]),(R\d+)',
                                       _compact(row.get('operands', '')))
                _need(operand is not None,
                      'Unknown native 64-bit record store')
                registers = _registers(operand[2], 2)
                states = [
                    check_timer_word(body,
                                     predecessor_maps[reader['function']],
                                     reader=reader,
                                     store_pc=pc,
                                     word_register=register,
                                     word_index=index)
                    for index, register in enumerate(registers)
                ]
                result['stores'].append(
                    dict(ptx_line=line,
                         ptx_address=match[1],
                         store_pc=pc,
                         store_predicate=row.get('predicate'),
                         native_address=operand[1],
                         word_registers=registers,
                         checked_word_states=states))
            result.update(status='timer_to_native_store_values_checked',
                          function=reader['function'],
                          getter_pc=reader['pc'],
                          getter_registers=_registers(
                              _compact(reader['operands']).split(',')[0], 2))
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    from . import timeline_nvidia_control, timeline_nvidia_late_boundaries, timeline_nvidia_machine, timeline_nvidia_late_control
    rules = [
        Path(__file__),
        Path(timeline_nvidia_control.__file__),
        Path(timeline_nvidia_late_boundaries.__file__),
        Path(timeline_nvidia_late_control.__file__),
        Path(timeline_nvidia_machine.__file__)
    ]
    return dict(
        model=MODEL,
        binary_id=machine_map['binary_id'],
        sites=results,
        implementation_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in rules
        },
        proof_scope=
        'all_reaching_definitions_of_timer_words_at_bound_native_stores',
        record_storage_binding_verified=False,
        record_value_provenance_verified=False,
        payload_provenance_verified=False,
        source_region_qualified=False,
        clock_qualified=False,
        hardware_overlap_verified=False,
        time_flows_qualified=False)


def inspect_timer_store_values(**inputs):
    try:
        return derive_timer_store_values(**inputs)
    except (ValueError, KeyError, TypeError) as error:
        return dict(model=MODEL,
                    binary_id=inputs['machine_map'].get('binary_id'),
                    status='unverified_timer_store_inputs_or_pattern',
                    sites=[],
                    reason=str(error),
                    record_value_provenance_verified=False,
                    record_storage_binding_verified=False,
                    payload_provenance_verified=False,
                    time_flows_qualified=False)
