"""Finite control-order facts for native cp.async waits, not timing certificates.

Callers must first validate the CUBIN/PTX/two disassemblies with counter_map.
This component checks the inspected leaf-call/forward-branch pattern. It never
promotes source boundaries, record-value provenance, participation or clocks.
"""
import hashlib
import json
import re

MAX_REGION_INSTRUCTIONS = 2048
MODEL = 'nvidia.cp_async.wait_control.v2'

# Explicit scalar families inspected in the logger lowering. Unknown operations
# invalidate predicate facts rather than silently preserving an entry guard.
_SCALAR_FAMILIES = frozenset(
    ('MOV', 'ISETP', 'UISETP', 'PSETP', 'PLOP3', 'LOP3', 'SHF', 'VIMNMX',
     'IMAD', 'IADD3', 'IADD', 'SEL', 'USEL', 'ULEA', 'SGXT', 'LDCU', 'DEPBAR',
     'BAR'))


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _compact(value):
    return re.sub(r'\s+', '', value)


def _operands(value):
    # nvdisasm 13.2 JSON omits the comma before a bracketed LDS operand.
    # Preserve every register, immediate and address expression.
    return re.sub(r',(?=\[)', '', _compact(value))


def _text_instructions(raw):
    section, pending, labels, instructions = None, [], {}, {}
    for line in raw.decode('utf-8').splitlines():
        match = re.match(r'^\s*\.section\s+([^,\s]+)', line)
        if match:
            section, pending = match[1], []
        label = re.fullmatch(r'\s*([^\s:]+):\s*', line)
        if label:
            pending.append(label[1])
        match = re.match(r'\s*/\*([0-9a-fA-F]+)\*/\s*(.*?)\s*;\s*$', line)
        if match and section:
            pc = int(match[1], 16)
            for name in pending:
                _need((section, name) not in labels, 'Duplicate SASS label')
                labels[section, name] = pc
            pending = []
            content = match[2]
            predicate = None
            if content.startswith('@'):
                predicate, content = content.split(None, 1)
            fields = content.split(None, 1)
            instructions[section, pc] = (fields[0], predicate,
                                         fields[1] if len(fields) == 2 else '')
    return labels, instructions


def _bound_functions(machine_map, sass_lines, sass_json):
    artifacts = machine_map['artifacts']
    for key, payload in [('sass_lines_sha256', sass_lines),
                         ('sass_json_sha256', sass_json)]:
        _need(
            type(payload) is bytes
            and hashlib.sha256(payload).hexdigest() == artifacts[key],
            'Control inputs differ from the validated machine map')
    from .timeline_nvidia_machine import normalized_json_instruction
    labels, text = _text_instructions(sass_lines)
    functions = {}
    ranges = {row['function']: row for row in machine_map['function_ranges']}
    for function in json.loads(sass_json)[1]:
        name = function['function-name']
        extent = ranges[name]
        _need(
            function['start'] == extent['start']
            and len(function['sass-instructions']) * 16
            == extent['instruction_bytes'],
            'Control function differs from the actual instruction body')
        body = {}
        for i, row in enumerate(function['sass-instructions']):
            row = normalized_json_instruction(row)
            pc = function['start'] + i * 16
            opcode, predicate, operands = text[extent['section'], pc]
            _need(
                opcode == row['opcode'] and predicate == row.get('predicate'),
                'Control instruction differs between disassemblies')
            if opcode in ('BRA', 'BRA.U') or opcode.startswith('BSSY'):

                def resolve(match):
                    target = labels.get((extent['section'], match[1]))
                    _need(target is not None, 'Unresolved control label')
                    return hex(target)

                operands = re.sub(r'`\(([^()\s]+)\)', resolve, operands)
            elif opcode.startswith('RET'):
                operands = re.sub(r'\s+`\(([^()\s]+)\)', r',\1', operands)
            elif opcode.startswith('CALL'):
                operands = re.sub(r'`\(([^()\s]+)\)', r'\1', operands)
            _need(
                _operands(operands) == _operands(row.get('operands', '')),
                'Control operands differ between disassemblies: ' + name +
                ':' + hex(pc) + ' ' + opcode + ' ' + repr(operands) + ' != ' +
                repr(row.get('operands', '')))
            body[pc] = row
        functions[name] = body
    _need(set(functions) == set(ranges), 'Missing control function body')
    return functions


def _branch(row):
    """A BRA.U predicate is an operand, even without a JSON predicate field."""
    predicate = row.get('predicate')
    operands = _compact(row.get('operands', ''))
    if row['opcode'] == 'BRA.U':
        match = re.fullmatch(r'(UP\d+),0x([0-9a-fA-F]+)', operands)
        _need(match is not None and predicate is None,
              'Unknown uniform branch')
        return match[1], int(match[2], 16)
    _need(row['opcode'] == 'BRA', 'Unknown branch instruction')
    match = re.fullmatch(r'0x([0-9a-fA-F]+)', operands)
    _need(match is not None, 'Unknown direct branch target')
    if predicate is not None:
        _need(
            re.fullmatch(r'@!?P\d+', predicate) is not None,
            'Unknown branch predicate')
        predicate = predicate[1:]
    return predicate, int(match[1], 16)


def _truth(predicate, known):
    if predicate is None:
        return True
    name = predicate.lstrip('!')
    value = known.get(name)
    return None if value is None else (
        not value if predicate.startswith('!') else value)


def _registers(base, words):
    match = re.fullmatch(r'(U?R)(\d+)', base)
    _need(match is not None, 'Unrecognized register range')
    return [match[1] + str(int(match[2]) + i) for i in range(words)]


def _writes(row):
    opcode = row['opcode']
    if opcode.split('.')[0] in ('STS', 'STG', 'STL'):
        return []
    _need(
        opcode.split('.')[0] in _SCALAR_FAMILIES,
        'Unknown register-writing opcode: ' + opcode)
    if opcode == 'DEPBAR.LE' or opcode.startswith('BAR.SYNC'):
        return []
    _need(not opcode.startswith(('DEPBAR', 'BAR.')),
          'Unknown synchronization outputs')
    fields = _compact(row.get('operands', '')).split(',')
    first = fields[0]
    result = [first]
    if opcode.startswith(('ISETP', 'UISETP', 'PSETP', 'PLOP3')):
        result = fields[:2]
    elif opcode.startswith('IADD3'):
        result = fields[:3]
    elif opcode.startswith('LOP3') and re.fullmatch(r'U?P\d+', first):
        result = fields[:2]
    if opcode.split('.')[0] in ('IMAD', 'IADD', 'IADD3', 'ULEA', 'SHF'):
        result += [
            field for field in fields[:3] if re.fullmatch(r'U?P\d+', field)
        ]
    if ('.64' in opcode or '.WIDE' in opcode) and re.fullmatch(
            r'U?R\d+', first):
        result = _registers(first, 2) + [
            field for field in result if re.fullmatch(r'U?P\d+', field)
        ]
    return result


def _word(operand, values, epochs, predicate=None):
    operand = operand.removesuffix('.reuse')
    if operand in ('RZ', 'URZ'):
        return 0
    if re.fullmatch(r'-?0x[0-9a-fA-F]+', operand):
        return int(operand, 16) & 0xffffffff
    value, guard = values.get(operand, (None, None))
    active = (predicate,
              epochs.get(predicate.lstrip('@!'), 0)) if predicate else None
    return value if guard is None or guard == active else None


def _move_words(row, values, epochs):
    fields = _compact(row.get('operands', '')).split(',')
    _need(len(fields) == 2, 'Unknown move operands')
    destination, source = fields
    width = 2 if row['opcode'] == 'MOV.64' else 1
    destinations = _registers(destination, width)
    if source in ('RZ', 'URZ'):
        sources = [source] * width
    elif re.fullmatch(r'U?R\d+(?:\.reuse)?', source):
        sources = _registers(source.removesuffix('.reuse'), width)
    elif width == 1:
        sources = [source]
    else:
        raise ValueError('Unknown wide move source')
    # Snapshot all input words first: overlapping MOV.64 is simultaneous.
    words = [
        _word(source, values, epochs, row.get('predicate'))
        for source in sources
    ]
    predicate = row.get('predicate')
    guard = (predicate,
             epochs.get(predicate.lstrip('@!'), 0)) if predicate else None
    for register, value in zip(destinations, words):
        values[register] = value, guard


def _counter_store_flow(counter, call, functions, *, site_id, phase):
    """Conditional value-flow witness, not a raw-storage or dominance proof."""
    leaf = functions[counter['function']]
    first = leaf[counter['pc']]
    output = _compact(first['operands']).split(',')[0]
    low, high = _registers(output, 2)
    values = {low: ('timer_low', None), high: ('timer_high', None)}
    for pc in sorted(leaf):
        if leaf[pc]['opcode'] in ('MOV', 'MOV.64'):
            _move_words(leaf[pc], values, {})
    body = functions[call['function']]
    epochs = {}
    tag = site_id | ((1 << 31) if phase == 'exit' else 0)
    for pc in range(call['pc'] + 16, call['pc'] + 16 * 257, 16):
        row = body.get(pc)
        _need(row is not None, 'No matching log store before the caller ends')
        opcode = row['opcode']
        if opcode == 'STS.128':
            match = re.fullmatch(r'(\[[^\]]+\]),(R\d+|RZ)',
                                 _compact(row['operands']))
            _need(match is not None, 'Unknown vector store operands')
            registers = _registers(match[2],
                                   4) if match[2] != 'RZ' else ['RZ'] * 4
            words = [
                _word(r, values, epochs, row.get('predicate'))
                for r in registers
            ]
            if ((match[2] != 'RZ' and words[0] == tag)
                    or any(v in ('timer_low', 'timer_high') for v in words)):
                _need(words[:3] == [tag, 'timer_low', 'timer_high'],
                      'Log tag or timer word order/value was not preserved')
                return dict(
                    status='counter_to_shared_store_values_checked',
                    phase=phase,
                    getter_function=counter['function'],
                    getter_pc=counter['pc'],
                    call_pc=call['pc'],
                    store_pc=pc,
                    store_predicate=row.get('predicate'),
                    tag_word=tag,
                    word_registers=registers,
                    address_expression=match[1],
                    proof_scope='conditional_on_this_call_and_store_execution',
                    call_dominates_store_verified=False,
                    record_storage_binding_verified=False,
                    record_value_provenance_verified=False)
            continue
        if opcode in ('MOV', 'MOV.64'):
            _move_words(row, values, epochs)
            continue
        if opcode.startswith('BSSY'):
            # Only a reconvergence setup before any branch; this witness is
            # conditional on executing this straight instruction sequence.
            continue
        _need(not opcode.startswith(('CALL', 'RET', 'EXIT', 'BRA', 'BSYNC')),
              'Control transition before the matching log store')
        for register in _writes(row):
            values.pop(register, None)
            if re.fullmatch(r'U?P\d+', register):
                epochs[register] = epochs.get(register, 0) + 1
    raise ValueError('Log-store value-flow budget exceeded')


def _leaf(counter, call, functions):
    body = functions[counter['function']]
    pcs = sorted(body)
    _need(pcs and counter['pc'] == pcs[0],
          'Timer is not the first leaf instruction')
    _need(
        len(pcs) <= 32
        and all(not row.get('predicate') for row in body.values()),
        'Conditional or oversized timer leaf')
    for pc in pcs[1:-1]:
        row = body[pc]
        _need(
            row['opcode'] in ('MOV', 'MOV.64')
            and re.fullmatch(r'(?:U?R\d+),(?:U?R\d+|U?RZ|0x[0-9a-fA-F]+)',
                             _compact(row.get('operands', ''))) is not None,
            'Unrecognized timer leaf instruction')
    tail = body[pcs[-1]]
    _need(
        tail['opcode'] == 'RET.REL.NODEC'
        and re.fullmatch(r'R\d+,' + re.escape(call['function']),
                         _compact(tail.get('operands', ''))) is not None,
        'Timer leaf does not return to the actual caller')
    # A printed parent symbol does not establish the dynamic return address.
    # Follow the leaf MOV chain back to explicit caller-side RPC initialization.
    rpc = _compact(tail['operands']).split(',')[0]
    for pc in reversed(pcs[1:-1]):
        destination, source = _compact(body[pc]['operands']).split(',')
        destination_register = re.fullmatch(r'(U?R)(\d+)', destination)
        writes = [destination]
        if body[pc]['opcode'] == 'MOV.64' and destination_register:
            writes.append(destination_register[1] +
                          str(int(destination_register[2]) + 1))
        if rpc in writes:
            offset = writes.index(rpc)
            source_register = re.fullmatch(r'(U?R)(\d+)', source)
            rpc = (source_register[1] + str(int(source_register[2]) + offset)
                   if source_register else source)
    getter_output = _compact(body[pcs[0]]['operands']).split(',')[0]
    match = re.fullmatch(r'(U?R)(\d+)', getter_output)
    getter_registers = ({match[1] + str(int(match[2]) + i)
                         for i in (0, 1)} if match else set())
    setup = functions[call['function']].get(call['pc'] - 16, {})
    _need(
        re.fullmatch(r'R\d+', rpc) is not None and rpc not in getter_registers
        and setup.get('opcode') == 'MOV' and not setup.get('predicate')
        and _compact(setup.get('operands',
                               '')) == rpc + ',' + hex(call['pc'] + 16),
        'Timer leaf lacks the checked caller return address')


def _check_region(begin, end, body, pending):
    first, last = begin['pc'], end['pc']
    _need(0 < last - first <= MAX_REGION_INSTRUCTIONS * 16,
          'Non-forward or oversized bracket')
    _need(not begin.get('predicate') and not end.get('predicate'),
          'Predicated counter call')
    known = {}
    guard_pc = first - 32
    guard = body.get(guard_pc)
    # The emitted optional counter call has a two-instruction guarded entry.
    # Guard facts are usable only if no other control edge can enter the body.
    if guard is not None and guard['opcode'] == 'BRA':
        predicate, target = _branch(guard)
        if predicate is not None and target > first and body[
                first - 16]['opcode'] == 'MOV':
            for row in body.values():
                if row['opcode'] in ('BRA', 'BRA.U'):
                    _, incoming = _branch(row)
                    _need(incoming not in (first - 16, first),
                          'Counter guard can be bypassed')
                elif row['opcode'].startswith('BSSY'):
                    match = re.fullmatch(r'B\d+,0x([0-9a-fA-F]+)',
                                         _compact(row['operands']))
                    _need(match is not None, 'Unknown reconvergence target')
                    _need(
                        int(match[1], 16) not in (first - 16, first),
                        'Reconvergence can bypass the counter guard')
                elif (row.get('other-attributes', {}).get('control-flow')
                      == 'True' or row['opcode'].startswith(
                          ('BRX', 'JMP', 'JMX', 'RET'))):
                    _need(
                        row['opcode'].startswith(
                            ('CALL.REL.NOINC', 'BSYNC', 'EXIT')),
                        'Unknown caller control instruction')
            known[predicate.lstrip('!')] = predicate.startswith('!')
    wait_pcs = [
        pc for pc, row in body.items()
        if first < pc < last and row['opcode'] == 'DEPBAR.LE'
        and _compact(row.get('operands', '')) == 'SB0,' + hex(pending)
    ]
    _need(len(wait_pcs) == 1, 'Missing or ambiguous native wait operand')
    wait_pc = wait_pcs[0]
    _need(not body[wait_pc].get('predicate'), 'Conditional native wait')
    work, visited, arrivals = [(first + 16, False,
                                tuple(sorted(known.items())))], set(), []
    while work:
        pc, seen, facts = work.pop()
        state = (pc, seen, facts)
        if state in visited:
            continue
        visited.add(state)
        _need(
            len(visited) <= MAX_REGION_INSTRUCTIONS * 4,
            'Control-state budget exceeded')
        if pc == last:
            arrivals.append(seen)
            continue
        _need(first < pc < last and pc in body,
              'Path escapes the counter bracket')
        row = body[pc]
        known = dict(facts)
        if row['opcode'] in ('BRA', 'BRA.U'):
            predicate, target = _branch(row)
            _need(target > pc, 'Backward branch inside the counter bracket')
            value = _truth(predicate, known)
            if value is not False:
                work.append((target, seen, facts))
            if value is not True:
                work.append((pc + 16, seen, facts))
            continue
        _need(
            not row['opcode'].startswith(
                ('CALL', 'RET', 'EXIT', 'BSSY', 'BSYNC'))
            and row.get('other-attributes', {}).get('control-flow') != 'True',
            'Unrecognized control inside the bracket')
        try:
            for destination in _writes(row):
                known.pop(destination, None)
        except ValueError:
            known.clear()
        work.append((pc + 16, seen
                     or pc == wait_pc, tuple(sorted(known.items()))))
    _need(arrivals and all(arrivals),
          'Native wait can be bypassed between counter calls')
    return dict(begin_call_pc=first,
                end_call_pc=last,
                wait_pc=wait_pc,
                pending_group_limit=pending,
                checked_control_states=len(visited))


def derive_wait_control_brackets(*, machine_map, sass_lines, sass_json, plan):
    """Derive narrowly scoped order facts from a freshly validated machine map."""
    _need(
        machine_map.get('status')
        == 'counter_mapping_complete_region_unverified'
        and machine_map.get('expected_sm') == [12, 0]
        and plan.get('binary_id') == machine_map.get('binary_id'),
        'Wait control analysis requires the actual sm_120 map and matching plan'
    )
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    counters = {}
    for row in machine_map['counter_call_sites']:
        counters.setdefault((row['site_id'], row['phase']), []).append(row)
    results = []
    for site in plan['inventory']:
        if not site.get('selected') or site.get(
                'timeline_mechanism') != 'nvidia.cp_async.wait':
            continue
        result = dict(site_id=site['scope_id'],
                      status='unverified',
                      source_region_qualified=False,
                      record_value_provenance_verified=False,
                      clock_qualified=False,
                      participation_verified=False)
        try:
            pending = site['timeline_wait_pending']
            _need(
                type(pending) is int and 0 <= pending <= 7,
                'Invalid wait operand')
            calls, endpoints = [], []
            for phase in ('entry', 'exit'):
                rows = counters.get((site['scope_id'], phase), [])
                _need(
                    len(rows) == 1 and len(rows[0]['direct_call_sites']) == 1,
                    'Counter read has ambiguous static callers')
                counter = rows[0]
                call = counter['direct_call_sites'][0]
                _leaf(counter, call, functions)
                calls.append(call)
                endpoints.append(counter)
            _need(calls[0]['function'] == calls[1]['function'],
                  'Counters have different callers')
            result.update(
                _check_region(*calls, functions[calls[0]['function']],
                              pending))
            result.update(status='wait_control_order_checked',
                          function=calls[0]['function'])
            flows = []
            for counter, call in zip(endpoints, calls):
                try:
                    flow = _counter_store_flow(counter,
                                               call,
                                               functions,
                                               site_id=site['scope_id'],
                                               phase=counter['phase'])
                except ValueError as error:
                    flow = dict(phase=counter['phase'],
                                status='unverified',
                                reason=str(error))
                flows.append(flow)
            result['endpoint_store_value_flows'] = flows
        except ValueError as error:
            result['reason'] = str(error)
        results.append(result)
    return dict(
        model=MODEL,
        binary_id=machine_map['binary_id'],
        sites=results,
        proof_scope='native_wait_control_order_between_inspected_leaf_calls',
        source_region_qualified=False,
        clock_qualified=False,
        hardware_overlap_verified=False)


def inspect_wait_control_brackets(**inputs):
    """Optional derived analysis cannot invalidate an already valid unit view.

    Unsupported syntax and missing evidence produce an explicit diagnostic.
    Callers still validate the original machine inputs before invoking this.
    """
    try:
        return derive_wait_control_brackets(**inputs)
    except (ValueError, KeyError, TypeError) as error:
        return dict(model=MODEL,
                    binary_id=inputs['machine_map'].get('binary_id'),
                    status='unverified_control_inputs_or_pattern',
                    sites=[],
                    reason=str(error),
                    exception=type(error).__name__,
                    source_region_qualified=False,
                    clock_qualified=False,
                    hardware_overlap_verified=False)
