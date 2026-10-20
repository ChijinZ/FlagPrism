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
