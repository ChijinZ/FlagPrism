"""Bind GCU300 decoded instructions to one retained final ELF image.

This consumes SDK disassembly, never executes a compiler or device, and grants
no source/clock/control qualification. Zero-suppressed bytes are accepted only
when the corresponding executable bytes really are zero. The current finite
format has one executable section and one vendor kernel descriptor.
"""
import hashlib
import re
import struct


def _need(value, message):
    if not value:
        raise ValueError(message)


def bind_instructions(binary, native):
    """Return byte-bound instructions and the descriptor/symbol code extent."""
    _need(
        type(binary) is bytes and 64 <= len(binary) <= 16 * 1024 * 1024,
        'Invalid bounded GCU ELF')
    _need(
        type(native) is bytes and 0 < len(native) <= 16 * 1024 * 1024,
        'Invalid bounded GCU disassembly')
    _need(binary[:7] == b'\x7fELF\x02\x01\x01',
          'Expected GCU ELF64 little endian')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', binary)
    offset, size, count = header[6], header[11], header[12]
    _need(
        size == 64 and 0 < count <= 8192
        and 64 <= offset <= len(binary) - count * size,
        'Invalid GCU ELF section table')
    sections = [
        struct.unpack_from('<IIQQQQIIQQ', binary, offset + i * size)
        for i in range(count)
    ]
    _need(
        sum(s[5] for s in sections if s[1] == 2) <= len(binary),
        'GCU symbol lookup exceeds input byte budget')

    def data(section):
        _need(
            section[4] <= len(binary)
            and section[5] <= len(binary) - section[4],
            'Truncated GCU ELF section')
        return binary[section[4]:section[4] + section[5]]

    executable = [(i, s) for i, s in enumerate(sections) if s[2] & 4 and s[5]]
    _need(len(executable) == 1, 'Expected one GCU executable section')
    section_index, executable = executable[0]
    _need(executable[1] == 1 and executable[3] % 16 == executable[5] % 16 == 0,
          'Unsupported GCU executable extent')
    code = data(executable)
    covered = bytearray(len(code))
    text = native.decode('utf-8')
    instructions, previous = [], -1
    for line in text.splitlines():
        match = re.match(r'^\s*([0-9a-f]+):\s+([^\t]+)\t(.+)$', line)
        if not match:
            continue
        pc = int(match[1], 16)
        raw = bytes.fromhex(match[2])
        relative = pc - executable[3]
        _need(
            0 < len(raw) <= 16 and pc > previous
            and 0 <= relative <= len(code) - len(raw),
            'Invalid GCU decoded instruction extent')
        _need(not any(covered[relative:relative + len(raw)]),
              'Overlapping GCU decoded instructions')
        _need(code[relative:relative + len(raw)] == raw,
              'GCU decoded instruction bytes differ from ELF')
        previous = pc
        covered[relative:relative + len(raw)] = b'\x01' * len(raw)
        operation = match[3].split(None, 1)
        instructions.append(
            dict(pc=pc,
                 opcode=operation[0],
                 operands=operation[1] if len(operation) > 1 else ''))
        _need(
            len(instructions) <= 100000,
            'GCU instruction count exceeds budget')
    descriptors = list(
        re.finditer(
            r'^([0-9a-f]{16}) ([^\n]+):\n\t\.dtu_kernel_code_t\n(.*?)'
            r'\t\.end_dtu_kernel_code_t', text, re.M | re.S))
    _need(len(descriptors) == 1, 'Expected one GCU kernel descriptor')
    descriptor = descriptors[0]
    base, name = int(descriptor[1], 16), descriptor[2]
    entries = re.findall(r'^\s*kernel_code_entry_byte_offset (\d+)\s*$',
                         descriptor[3], re.M)
    lengths = re.findall(r'^\s*kernel_code_size (\d+)\s*$', descriptor[3],
                         re.M)
    _need(
        len(entries) == len(lengths) == 1,
        'Ambiguous GCU descriptor code extent')
    entry, length = int(entries[0]), int(lengths[0])
    symbols = []
    for section in sections:
        if section[1] != 2:
            continue
        _need(
            section[9] == 24 and section[5] % 24 == 0
            and section[6] < len(sections), 'Invalid GCU symbol table')
        strings = data(sections[section[6]])
        table = data(section)
        for position in range(0, len(table), 24):
            index, _, _, ix, value, extent = struct.unpack_from(
                '<IBBHQQ', table, position)
            _need(index < len(strings), 'Invalid GCU symbol name offset')
            end = strings.find(b'\0', index)
            _need(end >= index, 'Unterminated GCU symbol name')
            if strings[index:end].decode('utf-8') == name:
                symbols.append((value, extent, ix))
    _need(
        len(symbols) == 1
        and symbols[0] == (base, entry + length, section_index)
        and executable[3] <= base < base + entry < base + entry + length <=
        executable[3] + len(code) and entry % 16 == length % 16 == 0,
        'GCU descriptor/code range differs from ELF symbol')
    start = base - executable[3]
    _need(not any(covered[start:start + entry]),
          'Decoded instruction overlaps GCU kernel descriptor')
    covered[start:start + entry] = b'\x01' * entry
    _need(not any(value and not seen for value, seen in zip(code, covered)),
          'Unaccounted nonzero GCU executable bytes')
    body = [
        r for r in instructions
        if base + entry <= r['pc'] < base + entry + length
    ]
    return dict(instructions=body,
                start_packet=base + entry,
                end_packet=base + entry + length,
                kernel_symbol=name,
                other_decoded_instruction_count=len(instructions) - len(body),
                elf_sha256=hashlib.sha256(binary).hexdigest(),
                disassembly_sha256=hashlib.sha256(native).hexdigest(),
                source_region_qualified=False,
                reader_valueflow_qualified=False)
