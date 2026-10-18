"""Invocation-scoped native scratch/header origin checks for late recording.

The scratch root comes from the actual ELF entry parameter layout. Remaining
address terms are evaluated against the actual launch geometry and hardware
thread/block getters; no operator, fixed parameter offset or native PC selects
the rules. These checks do not qualify a clock or an engine activity interval.
"""
import hashlib
import re
import struct
from pathlib import Path

from .timeline_nvidia_control import _bound_functions, _compact, _need, _registers
from .timeline_nvidia_machine import _elf_section, _lex
from .timeline_nvidia_late_boundaries import _native_lines
from .timeline_nvidia_late_records import _native_store, _constant_word
from .timeline_nvidia_late_addresses import (_Wide, _predecessors,
                                             _published_header_address,
                                             derive_record_addresses)
from .timeline_nvidia_late_values import _predicate

MODEL = 'nvidia.late.native_launch_header_origins.v1'
MASK32, MASK64 = (1 << 32) - 1, (1 << 64) - 1


def _parameter_bank_symbol(cubin, ordinal, function):
    """PARAM_CBANK names a symbol, not a section-table index."""
    symbols = _elf_section(cubin, '.symtab')
    strings = _elf_section(cubin, '.strtab')
    _need(
        len(symbols) % 24 == 0 and ordinal < len(symbols) // 24,
        'Invalid parameter-bank symbol index')
    name, _, _, section, value, _ = struct.unpack_from('<IBBHQQ', symbols,
                                                       ordinal * 24)
    wanted = ('.nv.constant0.' + function).encode()
    _need(
        name < len(strings) and strings[name:].split(b'\0', 1)[0] == wanted
        and value == 0,
        'Parameter bank symbol is not this entry constant bank')
    table = struct.unpack_from('<Q', cubin, 40)[0]
    size, count, _ = struct.unpack_from('<HHH', cubin, 58)
    _need(size == 64 and section < count,
          'Parameter bank symbol has invalid section')
    section_name = struct.unpack_from('<I', cubin, table + section * size)[0]
    names = _elf_section(cubin, '.shstrtab')
    _need(
        section_name < len(names)
        and names[section_name:].split(b'\0', 1)[0] == wanted,
        'Parameter bank symbol points to another section')
    return len(_elf_section(cubin, wanted.decode()))


def _parameter_root(cubin, ptx, function, plan):
    """Bound the SM120 ELF entry's parameter bank and reserved pointer field."""
    _need(
        plan.get('profile_argument_abi') == 1
        and type(plan.get('scratch_arg')) is int,
        'Missing actual reserved profile argument ABI')
    signature = re.search(
        r'\.visible\s+\.entry\s+' + re.escape(function) + r'\s*\((.*?)\)',
        ptx.decode(), re.S)
    _need(signature is not None, 'Missing actual PTX entry signature')
    parameters = [s.strip() for s in signature[1].split(',') if s.strip()]
    index = plan['scratch_arg']
    _need(index == len(parameters) - 1 and index >= 0,
          'Reserved scratch is not the actual final ABI parameter')
    _need(
        re.fullmatch(
            r'\.param\s+\.u64\s+\.ptr\s+\.global\s+\.align\s+\d+\s+[\w.$]+',
            parameters[index]),
        'Reserved scratch is not an actual global u64 pointer parameter')
    data = _elf_section(cubin, '.nv.info.' + function)
    entries, banks, at = {}, [], 0
    while at < len(data):
        _need(at + 4 <= len(data), 'Truncated entry parameter metadata')
        kind, attribute, value = struct.unpack_from('<BBH', data, at)
        at += 4
        _need(kind in (1, 2, 3, 4), 'Unknown CUDA entry attribute encoding')
        payload = b''
        if kind == 4:
            _need(value <= len(data) - at, 'Truncated CUDA entry attribute')
            payload, at = data[at:at + value], at + value
        if attribute == 0x17:
            _need(kind == 4 and len(payload) == 12,
                  'Unknown kernel parameter record')
            _, ordinal, offset, flags = struct.unpack('<IHHI', payload)
            width = flags >> 18
            _need(ordinal not in entries and 0 < width <= 4096,
                  'Duplicate or invalid kernel parameter extent')
            entries[ordinal] = (offset, width)
        elif attribute == 0x0a:
            _need(kind == 4 and len(payload) == 8,
                  'Unknown parameter bank record')
            symbol, base, extent = struct.unpack('<IHH', payload)
            _need(
                base + extent
                <= _parameter_bank_symbol(cubin, symbol, function),
                'Actual parameter extent exceeds constant-bank section')
            banks.append((base, extent))
    _need(
        len(banks) == 1 and sorted(entries) == list(range(len(parameters))),
        'Entry parameter table differs from actual PTX signature')
    base, extent = banks[0]
    _need(all(offset + width <= extent for offset, width in entries.values()),
          'Entry parameter exceeds its actual constant bank')
    offset, width = entries[index]
    _need(width == 8 and offset % 8 == 0,
          'Reserved scratch parameter has wrong size/alignment')
    return dict(parameter_index=index,
                parameter_offset=offset,
                parameter_bytes=width,
                bank_base=base,
                bank_bytes=extent,
                bank_operand='c[0x0][' + hex(base + offset) + ']')


def _coords(flat, dimensions):
    _need(
        type(flat) is int and flat >= 0 and len(dimensions) == 3
        and all(type(v) is int and v > 0 for v in dimensions),
        'Invalid actual launch coordinates')
    x, yz = flat % dimensions[0], flat // dimensions[0]
    y, z = yz % dimensions[1], yz // dimensions[1]
    _need(z < dimensions[2], 'Actual flat identity exceeds launch geometry')
    return x, y, z


class _Context:
    """Evaluate a finite native header dependency slice, never replay a kernel."""

    def __init__(self, wide, *, grid, block, program, actor, grid_inputs):
        self.wide, self.words = wide, wide.words
        self.grid, self.block = grid, block
        self.ctaid, self.tid = _coords(program, grid), _coords(actor, block)
        self.grid_inputs = grid_inputs
        self.cache, self.active = {}, set()

    def operand32(self, pc, operand, word=0):
        operand = operand.removesuffix('.reuse')
        if operand in ('RZ', 'URZ', 'SRZ'):
            return 0
        if re.fullmatch(r'-?0x[0-9a-fA-F]+', operand):
            return (int(operand, 16) >> (word * 32)) & MASK32
        _need(re.fullmatch(r'U?R\d+', operand),
              'Unknown concrete native header operand')
        register = _registers(operand, word + 1)[word]
        return self.scalar(self.words.value(pc, register))

    def operand64(self, pc, operand):
        return self.operand32(pc,
                              operand) | self.operand32(pc, operand, 1) << 32

    def boolean(self, pc, operand):
        return bool(self.scalar(self.words.boolean(operand, pc)))

    def scalar(self, expression):
        if type(expression) in (int, bool):
            return expression
        if expression in self.cache:
            return self.cache[expression]
        _need(expression not in self.active and len(self.active) < 128,
              'Cyclic or oversized native header slice')
        _need(len(self.cache) < 32768, 'Native header context budget exceeded')
        self.active.add(expression)
        try:
            row = self.words.arena.nodes[expression]
            kind, args = row[0], row[1:]
            if kind == 'opaque':
                _, _, pc, register = args
                result = self.native(pc, register)
            elif kind == 'not':
                result = not bool(self.scalar(args[0]))
            elif kind == 'select':
                result = self.scalar(
                    args[1] if self.scalar(args[0]) else args[2])
            elif kind in ('add', 'mul', 'and', 'or', 'xor'):
                values = [self.scalar(a) for a in args]
                result = 1 if kind == 'mul' else MASK32 if kind == 'and' else 0
                for value in values:
                    if kind == 'add':
                        result += value
                    elif kind == 'mul':
                        result *= value
                    elif kind == 'and':
                        result &= value
                    elif kind == 'or':
                        result |= value
                    else:
                        result ^= value
                result &= MASK32
            else:
                raise ValueError('Unresolved native header scalar input: ' +
                                 kind)
            self.cache[expression] = result
            return result
        finally:
            self.active.remove(expression)

    def native(self, pc, register):
        row = self.wide.body[pc]
        _need(
            _predicate(row.get('predicate')) is True,
            'Predicated native header input')
        op = row['opcode']
        fields = _compact(row.get('operands', '')).split(',')
        if op in ('S2R', 'S2UR'):
            match = re.fullmatch(r'SR_(TID|CTAID)\.([XYZ])', fields[1])
            _need(match is not None, 'Unknown hardware header identity getter')
            return (self.tid if match[1] == 'TID' else self.ctaid)['XYZ'.index(
                match[2])]
        if op in ('LDC', 'LDCU'):
            _need(pc in self.grid_inputs,
                  'Unbound native constant-memory header input')
            return self.grid[self.grid_inputs[pc]]
        if op in ('IMAD.WIDE.U32', 'UIMAD.WIDE.U32'):
            _need(len(fields) == 4, 'Unknown native wide multiply-add')
            value = (
                self.operand32(pc, fields[1]) * self.operand32(pc, fields[2]) +
                self.operand64(pc, fields[3])) & MASK64
            word = _registers(fields[0], 2).index(register)
            return (value >> (32 * word)) & MASK32
        if op == 'IADD.64':
            value = (self.operand64(pc, fields[1]) +
                     self.operand64(pc, fields[2])) & MASK64
            return (value >>
                    (32 * _registers(fields[0], 2).index(register))) & MASK32
        if op.startswith(('ISETP.', 'UISETP.')):
            _need(
                len(fields) == 5 and register == fields[0]
                and fields[1] in ('PT', 'UPT'),
                'Unknown native header predicate output')
            parts = op.split('.')
            _need(
                parts[-1] in ('AND', 'OR', 'XOR')
                and parts[1] in ('EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
                'Unknown native header comparison')
            wide = 'U64' in parts or '64' in parts
            a, b = [(self.operand64 if wide else self.operand32)(pc, f)
                    for f in fields[2:4]]
            if not any(p in ('U32', 'U64') for p in parts):
                sign = 1 << (63 if wide else 31)
                a, b = [(v ^ sign) - sign for v in (a, b)]
            compare = {
                'EQ': a == b,
                'NE': a != b,
                'LT': a < b,
                'LE': a <= b,
                'GT': a > b,
                'GE': a >= b
            }[parts[1]]
            other = self.boolean(pc, fields[4])
            return compare and other if parts[
                -1] == 'AND' else compare or other if parts[
                    -1] == 'OR' else compare != other
        raise ValueError('Unknown native header identity instruction: ' + op)

    def pointer_offset(self, expression, scratch):
        """Exactly one unscaled scratch root; all other terms are pointer-free."""
        row = self.wide.nodes.get(expression)
        _need(
            row is not None and row[0] == 'add64'
            and row[1:].count(scratch) == 1,
            'Header address lacks exactly one actual scratch parameter root')
        return sum(self.integer(a) for a in row[1:] if a != scratch) & MASK64

    def integer(self, expression):
        if type(expression) is int:
            return expression
        row = self.wide.nodes[expression]
        kind, args = row[0], row[1:]
        if kind == 'add64':
            return sum(self.integer(a) for a in args) & MASK64
        if kind == 'shift64':
            return (self.integer(args[0]) << args[1]) & MASK64
        if kind == 'words64':
            return self.scalar(args[0]) | self.scalar(args[1]) << 32
        if kind == 'select64':
            return self.integer(args[1] if self.scalar(args[0]) else args[2])
        raise ValueError(
            'Header offset contains unresolved or additional pointer input: ' +
            kind)


def _grid_roots(lines, annotations, function, body):
    roots = {}
    for (name, line), pcs in annotations.items():
        if name != function:
            continue
        _need(0 < line <= len(lines),
              'Native header annotation exceeds retained PTX')
        source = re.fullmatch(r'mov\.u32%r\d+,%nctaid\.([xyz]);',
                              lines[line - 1])
        if source:
            matches = [
                pc for pc in pcs if body[pc]['opcode'] in ('LDC', 'LDCU')
            ]
            _need(
                len(matches) == 1,
                'Ambiguous actual launch-grid constant input')
            _need(
                re.fullmatch(r'U?R\d+,c\[0x0\]\[0x[0-9a-fA-F]+\]',
                             _compact(body[matches[0]]['operands'])),
                'Unknown actual launch-grid constant input')
            roots[matches[0]] = 'xyz'.index(source[1])
    return roots


def _admitted_layout(owner, raw_bytes):
    from .timeline_nvidia_late_storage import plan_late_storage
    layout = owner['layout']
    expected = plan_late_storage(owner['plan'],
                                 grid=layout['grid'],
                                 scratch_size=layout['scratch_size'],
                                 alignment=layout['alignment'],
                                 num_ctas=layout['num_ctas'])
    _need([list(r)
           for r in expected['slots']] == [list(r) for r in layout['slots']]
          and expected['raw_bytes'] == raw_bytes,
          'Header slots differ from actual admitted launch geometry')
    return expected


def derive_header_origin_bindings(*, machine_map, sass_lines, sass_json, ptx,
                                  cubin, owner, decoded):
    _need(
        hashlib.sha256(
            cubin).hexdigest() == machine_map['artifacts']['cubin_sha256'],
        'Header parameter table belongs to another actual cubin')
    _need(
        owner['binary_id'] == machine_map['binary_id']
        and decoded['complete'] is True,
        'Header origin binding requires this binary and complete raw')
    plan, layout = owner['plan'], owner['layout']
    expected_layout = _admitted_layout(owner, decoded['raw_bytes'])
    _need([(r['physical_slot'], r['program_id']) for r in decoded['programs']
           ] == [tuple(r) for r in expected_layout['slots']],
          'Decoded header program coverage differs from admitted launch')
    _need(
        all([r['actor']
             for r in p['observers']] == list(range(plan['actors'])) and all(
                 r['arrived'] and r['complete'] for r in p['observers'])
            for p in decoded['programs']),
        'Incomplete decoded header actor coverage')
    arithmetic = derive_record_addresses(machine_map=machine_map,
                                         sass_lines=sass_lines,
                                         sass_json=sass_json,
                                         ptx=ptx,
                                         plan=plan)
    _need(len(arithmetic['functions']) == 1, 'Ambiguous actual native entry')
    report = arithmetic['functions'][0]
    function, header = report['function'], report['header']
    dimensions = re.search(
        r'\.visible\s+\.entry\s+' + re.escape(function) +
        r'\s*\(.*?\)\s*\.reqntid\s+(\d+(?:\s*,\s*\d+){0,2})', ptx.decode(),
        re.S)
    _need(dimensions is not None, 'Missing actual compiled block dimensions')
    block = [int(v) for v in dimensions[1].split(',')]
    block += [1] * (3 - len(block))
    _need(block == plan['block_dimensions'],
          'Header plan differs from actual compiled block dimensions')
    body = _bound_functions(machine_map, sass_lines, sass_json)[function]
    graph = _predecessors(body)
    wide = _Wide(body, graph, counter=header['value_register'])
    expression = _published_header_address(wide, header)
    parameter = _parameter_root(cubin, ptx, function, plan)
    scratch = wide.node('constant_memory_u64', parameter['bank_operand'])
    lines, _ = _lex(ptx.decode(), 'late-v1')
    annotations = _native_lines(sass_lines, {function: body})
    grid_inputs = _grid_roots(lines, annotations, function, body)
    stride = plan['actors'] * 8
    headers = {}
    for label, field in [('magic', 2), ('program', 3), ('shared_base', 4),
                         ('actor', 5)]:
        matches = [
            n + 1 for n, token in enumerate(lines) if re.fullmatch(
                r'st\.global\.b64\[' + re.escape(report['source_header']) +
                r'\+' + str(field * stride) +
                r'\],(?:%rd\d+|1179667508);', token) and (function,
                                                          n + 1) in annotations
        ]
        _need(len(matches) == 1, 'Missing native identity header store')
        native = _native_store(function, matches[0], annotations, body)
        _need(
            wide.add(wide.pair(native['pc'], native['address_register']),
                     native['offset']) == wide.add(expression, field * stride),
            'Identity header store has a different native address')
        _need(
            wide.pair(native['pc'], native['descriptor']) == wide.pair(
                header['pc'], header['descriptor']),
            'Identity header has a different actual memory descriptor')
        headers[label] = native
    for word, register in enumerate(
            _registers(headers['magic']['value_register'], 2)):
        _constant_word(body,
                       graph,
                       store_pc=headers['magic']['pc'],
                       register=register,
                       expected=(0x46504c34 >> (32 * word)) & MASK32)
    # The shared symbol's actual native getter value is published in this
    # header. Its numerical value need not be guessed from a chip-wide base.
    shared = headers['shared_base']
    low, high = _registers(shared['value_register'], 2)
    low_value, high_value = wide.words.value(shared['pc'],
                                             low), wide.words.value(
                                                 shared['pc'], high)
    shared_node = wide.words.arena.nodes.get(low_value)
    _need(high_value == 0 and shared_node and shared_node[0] == 'opaque',
          'Unknown actual native shared-symbol header value')
    materialization_pc = shared_node[-2]
    getter_pc = materialization_pc
    materialization = body[materialization_pc]
    materialized = dict(native_pc=materialization_pc)
    if materialization['opcode'] == 'ULEA':
        fields = _compact(materialization['operands']).split(',')
        _need(
            len(fields) == 4 and re.fullmatch(r'0x[0-9a-fA-F]+', fields[3]),
            'Unknown native shared-symbol address materialization')
        shift = int(fields[3], 16)
        displacement = wide.words.operand(fields[2], materialization_pc)
        special = wide.words.operand(fields[1], materialization_pc)
        source_node = wide.words.arena.nodes.get(special)
        _need(
            0 <= shift < 32 and type(displacement) is int and source_node
            and source_node[0] == 'opaque',
            'Unresolved native shared-symbol components')
        getter_pc = source_node[-2]
        materialized.update(shift=shift, displacement=displacement)
    getter = body[getter_pc]
    _need(
        getter['opcode'] == 'S2UR'
        and _compact(getter['operands']).split(',')[1] == 'SR_CgaCtaId',
        'Unknown native shared-symbol getter')
    symbol_lines = [
        n + 1 for n, token in enumerate(lines)
        if re.fullmatch(r'mov\.b32%r\d+,[A-Za-z_$][\w.$]*;', token)
    ]
    _need(
        any(materialization_pc in annotations.get((function, line), ())
            and getter_pc in annotations.get((function, line), ())
            for line in symbol_lines),
        'Native shared-symbol materialization lacks original PTX symbol correspondence'
    )
    rows = []
    for program in decoded['programs']:
        for actor in program['observers']:
            context = _Context(wide,
                               grid=layout['grid'],
                               block=plan['block_dimensions'],
                               program=program['program_id'],
                               actor=actor['actor'],
                               grid_inputs=grid_inputs)
            actual_offset = context.pointer_offset(expression, scratch)
            expected = program['physical_slot'] * plan[
                'segment_words'] * 8 + actor['actor'] * 8
            _need(
                actual_offset == expected == actor['header_offset_bytes'],
                'Native header address disagrees with actual program/thread allocation slot'
            )
            for label, value in [('program', program['program_id']),
                                 ('actor', actor['actor'])]:
                native = headers[label]
                _need(
                    context.operand64(native['pc'],
                                      native['value_register']) == value,
                    'Native header identity differs from actual launch geometry'
                )
            rows.append([program['program_id'], actor['actor'], actual_offset])
    return dict(model=MODEL,
                status='native_launch_header_origins_checked',
                identity={
                    key: owner[key]
                    for key in ('capture_id', 'invocation_id', 'binary_id')
                },
                raw_sha256=decoded['raw_sha256'],
                cubin_sha256=hashlib.sha256(cubin).hexdigest(),
                parameter=parameter,
                header=header,
                identity_stores=headers,
                shared_symbol_getter_pc=getter_pc,
                shared_symbol_materialization=materialized,
                shared_symbol_header_value_origin_verified=True,
                grid=list(layout['grid']),
                block=list(plan['block_dimensions']),
                grid_input_pcs=sorted(grid_inputs),
                columns=['program', 'actor', 'header_offset_bytes'],
                rows=rows,
                header_allocation_origin_verified=True,
                record_ordinal_binding_required=True,
                full_record_value_provenance_verified=False,
                time_flows_qualified=False,
                implementation_sha256=_rule_digests())


def _rule_digests():
    from . import timeline_nvidia_late_addresses, timeline_nvidia_machine, timeline_nvidia_late_values, timeline_nvidia_late_payloads, timeline_nvidia_late_records, timeline_nvidia_late_boundaries, timeline_nvidia_control, timeline_nvidia_late_control, timeline_runtime, timeline_cuda_runtime, timeline_storage, timeline_nvidia_late_storage, timeline_nvidia_late_raw, timeline_store
    paths = [
        Path(__file__),
        *(Path(m.__file__)
          for m in (timeline_nvidia_late_addresses, timeline_nvidia_machine,
                    timeline_nvidia_late_values, timeline_nvidia_late_payloads,
                    timeline_nvidia_late_records,
                    timeline_nvidia_late_boundaries, timeline_nvidia_control,
                    timeline_nvidia_late_control, timeline_runtime,
                    timeline_cuda_runtime, timeline_storage,
                    timeline_nvidia_late_storage, timeline_nvidia_late_raw,
                    timeline_store))
    ]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def load_native_header_origins(directory, capture, machine_map):
    from .timeline_store import read_artifact
    from .timeline_nvidia_late_raw import decode_late_raw
    artifacts = capture['metadata']['timeline_artifacts']
    source = {}
    for suffix in ('.ptx', '.cubin'):
        rows = [r for r in artifacts if r['retained_file'].endswith(suffix)]
        _need(len(rows) == 1, 'Ambiguous actual header-origin input')
        data = read_artifact(directory, rows[0]['retained_file'])
        _need(
            hashlib.sha256(data).hexdigest() == rows[0]['sha256'],
            'Header-origin object changed')
        source[suffix] = data
    owner = capture['owner']
    compiled = capture['metadata']['compiler_metadata'][
        'flagprism_late_manifest']
    _need({
        k: v
        for k, v in owner['plan'].items() if k != 'binary_id'
    } == compiled and capture['metadata']['automatic_plan'] == owner['plan']
          and capture['metadata']['binary_id'] == owner['binary_id'],
          'Header owner differs from its actual compiled manifest')
    _need(
        owner.get('submission_outcome') == 'returned'
        and owner.get('readback_integrity', {}).get('status') == 'passed'
        and owner.get('completion_known') is True,
        'Header allocation needs a completed invocation and validated readback'
    )
    raw = read_artifact(directory, capture['raw_file'])
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Header-origin raw changed')
    _admitted_layout(owner, len(raw))
    decoded = decode_late_raw(owner['plan'],
                              raw,
                              slots=owner['layout']['slots'])
    base = 'machine/' + owner['binary_id']
    proof = derive_header_origin_bindings(
        machine_map=machine_map,
        sass_lines=read_artifact(directory, base + '/lines.stdout'),
        sass_json=read_artifact(directory, base + '/json.stdout'),
        ptx=source['.ptx'],
        cubin=source['.cubin'],
        owner=owner,
        decoded=decoded)
    return proof


def inspect_native_header_origins(directory, capture, machine_map):
    try:
        return load_native_header_origins(directory, capture, machine_map)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as error:
        return dict(model=MODEL,
                    status='unverified_native_header_origins_or_pattern',
                    binary_id=capture.get('owner', {}).get('binary_id'),
                    reason=str(error),
                    header_allocation_origin_verified=False,
                    time_flows_qualified=False,
                    implementation_sha256=_rule_digests())
