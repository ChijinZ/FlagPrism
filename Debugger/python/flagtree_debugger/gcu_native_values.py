"""Bounded scalar value flow for a GCU native recorder's non-full tail.

Input instructions must already be bound to the executable bytes. Reader
registers must come from an independently checked reader path. This component
checks relative record fields only: it does not prove the MMIO address, ring
allocation, incoming begin/site tuple, selection predicate or source boundary.
"""
import re

_MASK = (1 << 32) - 1


def _need(value, message):
    if not value:
        raise ValueError(message)


def _linear(constant=0, terms=()):
    combined = {}
    for symbol, coefficient in terms:
        combined[symbol] = (combined.get(symbol, 0) + coefficient) & _MASK
    return (constant & _MASK,
            tuple(sorted((s, c) for s, c in combined.items() if c)))


def _symbol(name):
    return _linear(terms=((name, 1), ))


def _add(left, right):
    return _linear(left[0] + right[0], left[1] + right[1])


def _scale(value, count):
    return _linear(value[0] * count, ((s, c * count) for s, c in value[1]))


def check_record_tail(instructions, *, low_register, high_register,
                      identity_register):
    """Check end-low/high and identity fields on one bounded straight path.

    The register inputs denote values *at this tail's entry*. The upper word
    is still unmasked there. Any unsupported instruction, repeated PC, missing
    field, changed value or aliasing store is rejected. Unknown unrelated entry
    values are symbols, never guessed constants. Arithmetic is native 32-bit
    modular arithmetic, not LLVM signed/unsigned poison arithmetic.
    """
    _need(
        isinstance(instructions, list) and 0 < len(instructions) <= 512,
        'Native record tail instruction bound')
    roots = (low_register, high_register, identity_register)
    _need(
        len(set(roots)) == 3 and all(
            isinstance(r, str) and re.fullmatch(r'r(?:[1-9]|[12]\d|3[01])', r)
            for r in roots), 'Ambiguous native reader registers')
    low, high, identity = map(_symbol, ('end_low', 'end_high_raw', 'identity'))
    values = dict(zip(roots, (low, high, identity)))
    values['r0'] = _linear()
    stores, pcs = [], set()
    packet, packet_writes = None, set()

    def value(token):
        token = token.strip()
        if re.fullmatch(r'r(?:\d|[12]\d|3[01])', token):
            return values.get(token, _symbol('entry:' + token))
        _need(re.fullmatch(r'-?(?:0x[\da-f]+|\d+)', token),
              'Unsupported native scalar operand')
        return _linear(int(token, 16 if 'x' in token else 10))

    def address(text):
        m = re.fullmatch(r'\[([\w]+)(?:,\s*(-?(?:0x[\da-f]+|\d+)))?\]', text)
        _need(m, 'Unsupported native memory address')
        return _add(
            value(m[1]) if m[1] != 'sp' else _symbol('entry:sp'),
            value(m[2] or '0'))

    for row in instructions:
        pc, opcode, operands = row['pc'], row['opcode'], row['operands']
        _need(
            type(pc) is int and pc >= 0 and pc not in pcs,
            'Invalid or repeated native instruction PC')
        _need(not pcs or pc > max(pcs), 'Native record path is not ordered')
        pcs.add(pc)
        if opcode in ('c.nop', 's.nop16',
                      'v.nop') or (opcode == 'c.addi4spn'
                                   and operands.replace(' ', '') == 'r8,0x0'):
            continue
        args = [a.strip() for a in re.split(r',\s*(?![^\[]*\])', operands)]
        if pc // 16 != packet:
            packet, packet_writes = pc // 16, set()
        destination = None if opcode == 'l.st.w' else args[0]
        reads = set(
            re.findall(r'\br(?:\d|[12]\d|3[01])\b',
                       ','.join(args if destination is None else args[1:])))
        if opcode in ('c.add', 'l.ldi_hi'):
            reads.add(destination)
        _need(
            not (packet_writes & reads) and destination not in packet_writes,
            'Unsupported same-packet register forwarding or multiple writes')
        if destination is not None:
            packet_writes.add(destination)
        if opcode == 'l.st.w':
            _need(len(args) == 2, 'Invalid native store')
            stores.append((address(args[1]), value(args[0]), pc))
            continue
        _need(args and re.fullmatch(r'r(?:\d|[12]\d|3[01])', args[0]),
              'Unsupported native destination')
        dest = args[0]
        _need(dest != 'r0', 'Unexpected write to native zero register')
        if opcode in ('c.li', 'l.ldi16.s', 'l.ldi16.u'):
            _need(
                len(args) == 2
                and re.fullmatch(r'-?(?:0x[\da-f]+|\d+)', args[1]),
                'Invalid immediate')
            immediate = int(args[1], 16 if 'x' in args[1] else 10)
            lower, upper = (-32, 31) if opcode == 'c.li' else (
                -32768, 32767) if opcode == 'l.ldi16.s' else (0, 65535)
            _need(lower <= immediate <= upper, 'Native immediate range')
            result = _linear(immediate)
        elif opcode == 'l.ldi_hi':
            _need(len(args) == 2, 'Invalid native high immediate')
            old, imm = value(dest), value(args[1])
            _need(not old[1] and not imm[1] and imm[0] <= 0xffff,
                  'Unknown high-immediate input')
            result = _linear((old[0] & 0xffff) | imm[0] << 16)
        elif opcode in ('c.mv', 'l.mov'):
            _need(len(args) == 2, 'Invalid native move')
            result = value(args[1])
        elif opcode in ('c.add', 'l.adda.s', 'l.adda.u', 'l.addia.u',
                        'l.addia.s'):
            _need(
                len(args) == (2 if opcode == 'c.add' else 3),
                'Invalid native addition')
            result = _add(value(dest), value(
                args[1])) if opcode == 'c.add' else _add(
                    value(args[1]), value(args[2]))
        elif opcode == 'l.sllia':
            _need(len(args) == 3, 'Invalid native shift')
            shift = value(args[2])
            _need(not shift[1] and shift[0] < 32, 'Native shift bound')
            result = _scale(value(args[1]), 1 << shift[0])
        elif opcode == 'l.anda':
            _need(len(args) == 3, 'Invalid native mask')
            left, right = value(args[1]), value(args[2])
            if left == high and right == _linear(
                    0x3fff) or right == high and left == _linear(0x3fff):
                result = _symbol('end_high_masked')
            elif not left[1] and not right[1]:
                result = _linear(left[0] & right[0])
            else:
                result = _symbol('mask:' + str((left, right)))
        elif opcode == 'l.sraia':
            _need(
                len(args) == 3 and not value(args[2])[1]
                and value(args[2])[0] < 32, 'Invalid arithmetic shift')
            result = _symbol('sra:' + str((value(args[1]), value(args[2]))))
        elif opcode == 'l.ld.w':
            _need(len(args) == 2, 'Invalid native load')
            result = _symbol('load:' + str(pc) + ':' + str(address(args[1])))
        else:
            raise ValueError('Unsupported native record instruction: ' +
                             opcode)
        values[dest] = result

    magic = [(addr, pc) for addr, val, pc in stores
             if val == _linear(0x46504733)]
    _need(len(magic) == 1, 'Missing or ambiguous record magic')
    base, magic_pc = magic[0]
    fields = {}
    # Check the complete tail, including any later overwrite of a field.
    for addr, val, pc in stores:
        if addr[1] == base[1]:
            offset = (addr[0] - base[0]) & _MASK
            _need(offset % 4 == 0, 'Overlapping unaligned native record store')
            fields[offset] = (val, pc)
        else:
            # A store with a distinct symbolic address can still alias a field.
            # The caller must prove its region disjoint; do not ignore it here.
            raise ValueError('Native record store has an unbound alias')
    _need(
        fields.get(0, (None, ))[0] == _linear(0x46504733),
        'Record magic overwritten')
    expected = {
        24: low,
        28: _symbol('end_high_masked'),
        32: identity,
        76: identity
    }
    _need(
        all(offset in fields and fields[offset][0] == expected[offset]
            for offset in expected),
        'Reader value does not reach record field')
    return dict(status='relative_end_record_fields_checked',
                magic_store_pc=magic_pc,
                field_store_pcs={str(o // 4): fields[o][1]
                                 for o in expected},
                record_address_expression=repr(base),
                reader_to_relative_fields_checked=True,
                reader_valueflow_qualified=False,
                source_region_qualified=False,
                ring_allocation_qualified=False,
                incoming_begin_site_qualified=False)


def inspect_inline_reader(instructions, *, marker_packet):
    """Infer registers from a finite low/high/low rollover reader shape.

    A marker denotes a 16-byte packet, not an instruction PC. This recognizes
    actual scalar read/control relationships, including the fallback reread;
    it does not establish the physical MMIO base or external CFG entries.
    The supplied decoded list must be complete and bound to the same ELF.
    """
    _need(
        type(marker_packet) is int and marker_packet >= 0
        and marker_packet % 16 == 0, 'Invalid reader marker packet')
    _need(
        isinstance(instructions, list) and len(instructions) <= 100000,
        'Native reader input bound')
    rows = []
    previous = -1
    for row in instructions:
        pc = row['pc']
        _need(
            type(pc) is int and pc > previous, 'Unordered reader instructions')
        previous = pc
        if pc < marker_packet:
            continue
        op, operands = row['opcode'], row['operands']
        if op in ('c.nop', 's.nop16',
                  'v.nop') or (op == 'c.addi4spn'
                               and operands.replace(' ', '') == 'r8,0x0'):
            continue
        rows.append(row)
        if op == 'l.movs' and operands.replace(' ', '').endswith(',sipinfo'):
            break
        _need(len(rows) <= 32, 'Native inline reader shape bound')
    _need(rows and rows[0]['pc'] // 16 == marker_packet // 16,
          'No effective instruction in reader marker packet')
    values, loads = {}, []
    branch, identity = None, None
    fast_values = None
    merged = False
    packet, written = None, set()

    def read(token):
        if re.fullmatch(r'r(?:\d|[12]\d|3[01])', token):
            return _linear() if token == 'r0' else values.get(
                token, _symbol('entry:' + token))
        _need(re.fullmatch(r'-?(?:0x[\da-f]+|\d+)', token),
              'Unknown reader operand')
        return _linear(int(token, 16 if 'x' in token else 10))

    for index, row in enumerate(rows):
        op, pc = row['opcode'], row['pc']
        args = [
            x.strip() for x in re.split(r',\s*(?![^\[]*\])', row['operands'])
        ]
        if branch is not None and not merged and pc // 16 == branch[
                'target'] // 16:
            _need(len(loads) == 5, 'Rollover branch bypasses required rereads')
            _need(
                loads[1]['dest'] == loads[3]['dest']
                and loads[2]['dest'] == loads[4]['dest'],
                'Rollover register join is ambiguous')
            _need(
                values.get(loads[4]['dest']) == loads[4]['token']
                and values.get(loads[3]['dest']) == loads[3]['token'],
                'Reread output overwritten before join')
            _need(
                loads[1]['address'] == loads[3]['address']
                and loads[2]['address'] == loads[4]['address'],
                'Rollover reread address differs')
            joined = {}
            for reg in set(values) | set(fast_values):
                fall = values.get(reg, _symbol('entry:' + reg))
                fast = fast_values.get(reg, _symbol('entry:' + reg))
                joined[reg] = fall if fall == fast else _symbol(
                    'reader_join:' + reg)
            values = joined
            values[loads[2]['dest']] = _symbol('reader_low')
            values[loads[1]['dest']] = _symbol('reader_high_raw')
            merged = True
        if pc // 16 != packet:
            packet, written = pc // 16, set()
        dest = None if op == 'l.bge.u' else args[0]
        reads = set(
            re.findall(r'\br(?:\d|[12]\d|3[01])\b',
                       ','.join(args if dest is None else args[1:])))
        _need(not written.intersection(reads) and dest not in written,
              'Unsupported same-packet reader forwarding')
        if dest is not None:
            _need(re.fullmatch(r'r(?:[1-9]|[12]\d|3[01])', dest),
                  'Unknown reader destination')
            written.add(dest)
        if op in ('c.li', 'l.ldi16.s', 'l.ldi16.u'):
            _need(
                len(args) == 2
                and re.fullmatch(r'-?(?:0x[\da-f]+|\d+)', args[1]),
                'Invalid reader immediate')
            imm = int(args[1], 16 if 'x' in args[1] else 10)
            lo, hi = (-32, 31) if op == 'c.li' else (
                -32768, 32767) if op == 'l.ldi16.s' else (0, 65535)
            _need(lo <= imm <= hi, 'Reader immediate range')
            values[dest] = _linear(imm)
        elif op in ('l.adda.u', 'l.adda.s', 'l.addia.u', 'l.addia.s'):
            _need(len(args) == 3, 'Invalid reader address addition')
            values[dest] = _add(read(args[1]), read(args[2]))
        elif op == 'l.ld.w':
            _need(not merged and len(args) == 2, 'Unexpected reader load')
            m = re.fullmatch(
                r'\[(r(?:\d|[12]\d|3[01]))(?:,\s*(-?(?:0x[\da-f]+|\d+)))?\]',
                args[1])
            _need(m, 'Unsupported reader address')
            address = _add(read(m[1]), read(m[2] or '0'))
            token = _symbol('sample:' + str(pc))
            loads.append(dict(pc=pc, dest=dest, address=address, token=token))
            values[dest] = token
            _need(len(loads) <= 5, 'Unexpected inline reader load count')
        elif op == 'l.bge.u':
            _need(branch is None and len(loads) == 3 and len(args) == 3,
                  'Unexpected inline reader control')
            target = re.search(r'<0x([\da-f]+)>', args[2])
            _need(
                target and read(args[0]) == loads[2]['token']
                and read(args[1]) == loads[0]['token'],
                'Rollover compares wrong samples')
            _need(
                loads[0]['address'] == loads[2]['address'] and
                loads[1]['address'] == _add(loads[0]['address'], _linear(4)),
                'Counter word addresses differ')
            _need(
                values.get(loads[1]['dest']) == loads[1]['token']
                and values.get(loads[2]['dest']) == loads[2]['token'],
                'Fast-path counter output overwritten')
            branch = dict(pc=pc, target=int(target[1], 16))
            fast_values = dict(values)
            _need(branch['target'] % 16 == 0 and branch['target'] > pc,
                  'Invalid rollover target packet')
        elif op == 'l.movs':
            _need(merged and len(args) == 2 and args[1] == 'sipinfo',
                  'Missing reader identity')
            values[dest] = _symbol('reader_identity')
            identity = dest
        elif op == 'l.anda':
            _need(merged and len(args) == 3, 'Unexpected reader mask')
            left, right = read(args[1]), read(args[2])
            _need((left == _symbol('reader_high_raw')
                   and right == _linear(0x3fff))
                  or (right == _symbol('reader_high_raw')
                      and left == _linear(0x3fff)),
                  'Invalid counter high-word mask')
            values[dest] = _symbol('reader_high_masked')
        else:
            raise ValueError('Unsupported inline reader instruction: ' + op)
        if identity is not None:
            break
        if branch is not None and not merged:
            _need(pc < branch['target'], 'Rollover join packet missing')
    _need(identity is not None and merged, 'Incomplete inline counter reader')
    low = [reg for reg, val in values.items() if val == _symbol('reader_low')]
    high = [
        reg for reg, val in values.items() if val == _symbol('reader_high_raw')
    ]
    _need(
        len(low) == len(high) == 1 and len({low[0], high[0], identity}) == 3,
        'Reader output register was overwritten or ambiguous')
    return dict(status='inline_reader_register_shape_checked',
                marker_packet=marker_packet,
                low_register=low[0],
                high_register=high[0],
                identity_register=identity,
                identity_pc=rows[index]['pc'],
                sample_pcs=[x['pc'] for x in loads],
                rollover_branch=branch,
                clock_base_expression=repr(loads[0]['address']),
                mmio_base_qualified=False,
                external_entries_qualified=False,
                reader_valueflow_qualified=False,
                source_region_qualified=False)


def inspect_inline_record_fields(instructions, *, marker_packet, tail_start_pc,
                                 tail_end_pc):
    """Connect inferred reader outputs to a caller-selected non-full tail.

    Tail boundaries and full instruction/ELF binding are still caller inputs.
    The intervening scalar guard path must preserve all three reader values.
    This does not qualify its selection predicate, external CFG entries,
    physical clock address, actual ring allocation or incoming begin/site.
    """
    reader = inspect_inline_reader(instructions, marker_packet=marker_packet)
    _need(
        type(tail_start_pc) is int and type(tail_end_pc) is int
        and reader['identity_pc'] < tail_start_pc <= tail_end_pc,
        'Invalid native record tail bounds')
    outputs = {
        reader[k]
        for k in ('low_register', 'high_register', 'identity_register')
    }
    bridge = [
        row for row in instructions
        if reader['identity_pc'] < row['pc'] < tail_start_pc
    ]
    _need(len(bridge) <= 64, 'Native reader-to-record bridge bound')
    control = {'l.beq', 'l.bne', 'l.blt.u', 'l.blt.s', 'l.bge.u', 'l.bge.s'}
    scalar = {
        'l.ld.w', 'c.li', 'l.ldi16.s', 'l.ldi16.u', 'l.ldi_hi', 'l.addia.u',
        'l.addia.s', 'l.adda.u', 'l.adda.s', 'c.mv', 'l.mov'
    }
    for row in bridge:
        op, args = row['opcode'], row['operands']
        if op in ('c.nop', 's.nop16',
                  'v.nop') or (op == 'c.addi4spn'
                               and args.replace(' ', '') == 'r8,0x0'):
            continue
        _need(op in control | scalar | {'l.st.w'},
              'Unknown reader-to-record guard instruction')
        if op in scalar:
            _need(
                args.split(',', 1)[0].strip() not in outputs,
                'Reader output overwritten before record tail')
        if op in control:
            m = re.search(r'<0x([\da-f]+)>', args)
            _need(m is not None, 'Unknown native guard target')
            target = int(m[1], 16)
            _need(target % 16 == 0 and target >= (row['pc'] & ~15) + 16,
                  'Unsupported cyclic reader-to-record guard')
            _need(not tail_start_pc // 16 <= target // 16 <= tail_end_pc // 16,
                  'Native guard enters record tail partway')
    tail = [
        row for row in instructions
        if tail_start_pc <= row['pc'] <= tail_end_pc
    ]
    _need(
        tail and tail[0]['pc'] == tail_start_pc
        and tail[-1]['pc'] == tail_end_pc,
        'Native record tail endpoints missing')
    result = check_record_tail(
        tail, **{
            k: reader[k]
            for k in ('low_register', 'high_register', 'identity_register')
        })
    result.update(reader=reader,
                  reader_outputs_inferred=True,
                  reader_bridge_registers_preserved=True,
                  reader_bridge_instruction_count=len(bridge),
                  record_path_selection_qualified=False,
                  tail_boundaries_automatically_selected=False)
    return result
