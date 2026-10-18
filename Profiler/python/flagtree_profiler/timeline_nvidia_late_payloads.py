"""SM120 native shared-address / source-valid-byte payload value witnesses.

An epoch-local native slice, not a source-cost or absolute raw-slot certificate.
Mutable loop registers start at distinct header inputs; loop-invariant aliases
may be reconstructed only through acyclic preheader definitions. No static PC
is used to equate values from different loop executions.
"""
import hashlib
import json
import re
from pathlib import Path

from .timeline_nvidia_control import _bound_functions, _compact, _need, _registers
from .timeline_nvidia_late_values import _predecessors, _destinations, _predicate
from .timeline_nvidia_late_boundaries import _native_lines, _ptx_operation, _straight_path
from .timeline_nvidia_late_records import derive_record_fields
from .timeline_nvidia_machine import _lex

MODEL = 'nvidia.late.shared_payload_values.v1'
MASK = 0xffffffff
MAX_STATES = 32768
_KINDS = frozenset(('copy_submit_after', 'shared_store_after',
                    'shared_load_issue_bracket', 'shared_load_native_bracket'))


class _Arena:

    def __init__(self):
        self.nodes = {}

    def node(self, op, *args):
        data = (op, *args)
        key = hashlib.sha256(json.dumps(
            data, separators=(',', ':')).encode()).hexdigest()
        _need(
            len(self.nodes) < MAX_STATES or key in self.nodes,
            'Native expression node budget exceeded')
        self.nodes[key] = data
        return key

    def add(self, *args):
        terms, constant = [], 0
        for arg in args:
            if type(arg) is int:
                constant = (constant + arg) & MASK
            elif self.nodes.get(arg, (None, ))[0] == 'add':
                for child in self.nodes[arg][1:]:
                    if type(child) is int:
                        constant = (constant + child) & MASK
                    else:
                        terms.append(child)
            else:
                terms.append(arg)
        terms.sort()
        if constant:
            terms.append(constant)
        return 0 if not terms else terms[0] if len(terms) == 1 else self.node(
            'add', *terms)

    def mul(self, left, right):
        if type(left) is int and type(right) is int:
            return (left * right) & MASK
        if left == 0 or right == 0:
            return 0
        if left == 1:
            return right
        if right == 1:
            return left
        return self.node('mul', *sorted((left, right), key=repr))

    def bits(self, op, *args):
        terms, constant = [], MASK if op == 'and' else 0
        for arg in args:
            children = self.nodes[arg][1:] if type(
                arg) is str and self.nodes.get(arg,
                                               (None, ))[0] == op else (arg, )
            for child in children:
                if type(child) is int:
                    constant = ((constant & child) if op == 'and' else
                                (constant | child) if op == 'or' else
                                (constant ^ child)) & MASK
                else:
                    terms.append(child)
        if op == 'and' and constant == 0 or op == 'or' and constant == MASK:
            return constant
        if op in ('and', 'or'):
            terms = sorted(set(terms))
        else:
            terms = sorted(value for value in set(terms)
                           if terms.count(value) % 2)
        if constant != (MASK if op == 'and' else 0):
            terms.append(constant)
        return constant if not terms else terms[0] if len(
            terms) == 1 else self.node(op, *terms)

    def invert(self, predicate):
        if type(predicate) is bool:
            return not predicate
        row = self.nodes[predicate]
        return row[1] if row[0] == 'not' else self.node('not', predicate)

    def select(self, predicate, yes, no):
        if yes == no:
            return yes
        if type(predicate) is bool:
            return yes if predicate else no
        if self.nodes[predicate][0] == 'not':
            predicate, yes, no = self.nodes[predicate][1], no, yes
        return self.node('select', predicate, yes, no)

    def lut(self, lut, a, b, c):
        if all(type(value) is int for value in (a, b, c)):
            result = 0
            for bit in range(32):
                index = (((a >> bit) & 1) << 2) | (((b >> bit) & 1) << 1) | (
                    (c >> bit) & 1)
                result |= ((lut >> index) & 1) << bit
            return result
        if lut == 0xfc:
            return self.bits('or', a, b)
        if lut == 0xc0:
            return self.bits('and', a, b)
        if lut == 0x3c:
            return self.bits('xor', a, b)
        if lut in (0xf8, 0x78):
            return self.bits('or' if lut == 0xf8 else 'xor',
                             self.bits('and', a, b), c)
        return self.node('lut', lut, a, b, c)


class _Dominators:
    """Linear retained state; ancestor sets are materialized only on demand."""

    def __init__(self, parents):
        self.parents = parents
        self.depths = {
            node: 1
            for node, parent in parents.items() if node == parent
        }

    def __getitem__(self, node):
        result = set()
        while node not in result:
            result.add(node)
            parent = self.parents[node]
            if parent == node:
                return result
            node = parent
        raise ValueError('Cyclic native dominator tree')

    def depth(self, node):
        pending = []
        while node not in self.depths:
            pending.append(node)
            _need(
                len(pending) <= len(self.parents),
                'Cyclic native dominator depths')
            node = self.parents[node]
        value = self.depths[node]
        for at in reversed(pending):
            value += 1
            self.depths[at] = value
        return self.depths[pending[0]] if pending else value


def _dominators(graph):
    entry = min(graph)
    successors = {pc: set() for pc in graph}
    for pc, incoming in graph.items():
        for parent in incoming:
            successors[parent].add(pc)
    visited, postorder = {entry}, []
    stack = [(entry, iter(sorted(successors[entry])))]
    while stack:
        pc, children = stack[-1]
        child = next(children, None)
        if child is None:
            postorder.append(pc)
            stack.pop()
        elif child not in visited:
            visited.add(child)
            stack.append((child, iter(sorted(successors[child]))))
    _need(visited == set(graph), 'Disconnected native dominator graph')
    order = list(reversed(postorder))
    ranks = {node: i for i, node in enumerate(order)}
    parents = {entry: entry}

    def intersect(left, right):
        while left != right:
            while ranks[left] > ranks[right]:
                left = parents[left]
            while ranks[right] > ranks[left]:
                right = parents[right]
        return left

    for _ in range(len(graph) + 1):
        changed = False
        for pc in order[1:]:
            incoming = [
                parent for parent in sorted(graph[pc]) if parent in parents
            ]
            if not incoming:
                continue
            value = incoming[0]
            for parent in incoming[1:]:
                value = intersect(value, parent)
            if parents.get(pc) != value:
                parents[pc], changed = value, True
        if not changed:
            _need(
                set(parents) == set(graph)
                and all(node == entry or ranks[parent] < ranks[node]
                        for node, parent in parents.items()),
                'Invalid native dominator tree')
            return _Dominators(parents)
    raise ValueError('Native dominator budget exceeded')


class _Words:

    def __init__(self, body, graph, dominators, *, operation_pc, store_pc):
        _need(operation_pc in dominators[store_pc],
              'Native operation does not dominate its payload store')
        common = dominators[operation_pc] & dominators[store_pc]
        choices = [
            pc for pc in common if pc == min(graph) or len(graph[pc]) > 1
        ]
        self.cut = max(choices, key=dominators.depth)
        self.body, self.graph = body, graph
        self.arena, self.cache, self.active, self.def_cache = _Arena(
        ), {}, set(), {}
        successors = {pc: set() for pc in graph}
        for pc, parents in graph.items():
            for parent in parents:
                successors[parent].add(pc)

        def reachable(edges):
            visited, work = set(), [self.cut]
            while work:
                pc = work.pop()
                if pc not in visited:
                    visited.add(pc)
                    work.extend(edges[pc])
            return visited

        self.loop = reachable(successors) & reachable(graph)
        if len(self.loop) == 1 and self.cut not in graph[self.cut]:
            self.loop = set()
        self.mutable = {
            register
            for pc in self.loop
            for register in _destinations(body[pc])
        }

    def definitions(self, pc, register, pre):
        key = pc, register, pre
        if key in self.def_cache:
            return self.def_cache[key]
        results, visited, work = set(), set(), [pc]
        while work:
            at = work.pop()
            if at in visited:
                continue
            visited.add(at)
            _need(
                len(visited) <= MAX_STATES,
                'Native reaching-definition budget exceeded')
            if not pre and at == self.cut:
                results.add(
                    ('preheader' if self.loop and register not in self.mutable
                     else 'input', self.cut, register))
                continue
            parents = self.graph[at]
            if pre and at == self.cut:
                parents = parents - self.loop
            if not parents:
                results.add(('entry', at, register))
            for parent in parents:
                _need(parent < at, 'An uncut loop can mix native value epochs')
                row = self.body[parent]
                active = _predicate(row.get('predicate'))
                if active is not False and register in _destinations(row):
                    results.add(('definition', parent, register))
                    if active is True:
                        continue
                work.append(parent)
        _need(results, 'Native value has no reaching definition')
        _need(
            len(self.def_cache) < MAX_STATES,
            'Native definition cache budget exceeded')
        self.def_cache[key] = results
        return results

    def value(self, pc, register, pre=False):
        if register in ('RZ', 'URZ'):
            return 0
        if register in ('PT', 'UPT'):
            return True
        key = pc, register, pre
        if key in self.cache:
            return self.cache[key]
        _need(key not in self.active and len(self.active) < 128,
              'Cyclic or oversized native expression')
        _need(
            len(self.cache) < MAX_STATES, 'Native value cache budget exceeded')
        self.active.add(key)
        try:
            expressions = set()
            for kind, at, value in self.definitions(pc, register, pre):
                if kind == 'definition':
                    expressions.add(self.definition(at, value, pre))
                elif kind == 'preheader':
                    expressions.add(self.value(at, value, True))
                else:
                    expressions.add(self.arena.node(kind, self.cut, at, value))
            _need(
                len(expressions) == 1,
                'Native paths disagree on a payload value')
            result = expressions.pop()
            self.cache[key] = result
            return result
        finally:
            self.active.remove(key)

    def operand(self, operand, pc, pre=False, word=0):
        operand = operand.removesuffix('.reuse')
        if operand in ('RZ', 'URZ', 'SRZ'):
            return 0
        if re.fullmatch(r'-?0x[0-9a-fA-F]+', operand):
            return (int(operand, 16) >> (32 * word)) & MASK
        if operand.startswith('-'):
            _need(word == 0, 'Unknown wide negated native operand')
            return self.arena.mul(MASK, self.operand(operand[1:], pc, pre))
        _need(
            re.fullmatch(r'U?R\d+', operand) is not None,
            'Unknown native value operand: ' + operand)
        if word:
            operand = _registers(operand, word + 1)[word]
        return self.value(pc, operand, pre)

    def boolean(self, operand, pc, pre=False):
        negative = operand.startswith('!')
        operand = operand.lstrip('!')
        _need(
            re.fullmatch(r'U?P\d+|PT|UPT', operand) is not None,
            'Unknown native selector predicate')
        result = self.value(pc, operand, pre)
        return self.arena.invert(result) if negative else result

    def definition(self, pc, register, pre):
        row = self.body[pc]
        opcode = row['opcode']
        fields = _compact(row.get('operands', '')).split(',')

        def opaque():
            return self.arena.node('opaque', self.cut, pre, pc, register)

        if re.fullmatch(r'U?P\d+', register):
            return opaque()
        if opcode in ('MOV', 'MOV.64', 'UMOV', 'UMOV.64', 'CS2R', 'CS2UR'):
            width = 2 if opcode.endswith('.64') or opcode.startswith(
                'CS2') else 1
            word = _registers(fields[0], width).index(register)
            if opcode.startswith('CS2') and fields[1] != 'SRZ':
                return opaque()
            if width == 2 and re.fullmatch(r'0x[0-9a-fA-F]+', fields[1]):
                _need(not 0x80000000 <= int(fields[1], 16) <= MASK,
                      'Ambiguous native wide literal')
            return self.operand(fields[1], pc, pre, word)
        if opcode in ('SEL', 'SEL.64', 'USEL', 'USEL.64'):
            width = 2 if opcode.endswith('.64') else 1
            word = _registers(fields[0], width).index(register)
            return self.arena.select(self.boolean(fields[3], pc, pre),
                                     self.operand(fields[1], pc, pre, word),
                                     self.operand(fields[2], pc, pre, word))
        if opcode in ('LOP3.LUT', 'ULOP3.LUT'):
            start = 1 if re.fullmatch(r'U?P\d+|PT|UPT', fields[0]) else 0
            _need(fields[start] == register and len(fields) == start + 6,
                  'Unknown native LUT output form')
            lut = int(fields[start + 4], 16)
            _need(0 <= lut <= 255, 'Unknown native LUT')
            return self.arena.lut(
                lut,
                *(self.operand(x, pc, pre)
                  for x in fields[start + 1:start + 4]))
        if opcode in ('IADD3', 'UIADD3',
                      'UIADD3.64') and register == fields[0]:
            _need(len(fields) == 6, 'Unknown native add operands')
            return self.arena.add(*(self.operand(x, pc, pre)
                                    for x in fields[3:]))
        if opcode == 'IADD.64' and register == fields[0]:
            _need(len(fields) == 3, 'Unknown native wide add operands')
            return self.arena.add(*(self.operand(x, pc, pre)
                                    for x in fields[1:]))
        if opcode in ('IMAD', 'IMAD.U32', 'IMAD.SHL.U32', 'UIMAD',
                      'UIMAD.U32') and register == fields[0]:
            _need(len(fields) == 4, 'Unknown native multiply-add operands')
            a, b, c = (self.operand(x, pc, pre) for x in fields[1:])
            return self.arena.add(self.arena.mul(a, b), c)
        return opaque()

    def address(self, pc, text):
        _need(
            text.startswith('[') and text.endswith(']'),
            'Unknown native shared address')
        parts = text[1:-1].split('+')
        _need(parts and len(parts) <= 3, 'Unknown native shared address arity')
        return self.arena.add(*(self.operand(part, pc) for part in parts))


def _ptx_memory(lines, markers, site, readers):
    line, token = _ptx_operation(
        lines, markers, site,
        readers) if site['kind'] in ('copy_submit_after', 'shared_store_after',
                                     'shared_load_issue_bracket') else (None,
                                                                        None)
    if line is None:
        begin, end = readers[site['site_id'],
                             'entry'], readers[site['site_id'], 'exit']
        candidates = [
            (n + 1, lines[n])
            for n in range(begin['ptx_line'], end['ptx_line'] - 1)
            if lines[n] and not lines[n].startswith(('.loc', '.file'))
        ]
        _need(len(candidates) == 1, 'Ambiguous original shared-load bracket')
        line, token = candidates[0]
    if site['kind'] == 'copy_submit_after':
        match = re.fullmatch(
            r'cp\.async\.(?:ca|cg)\.shared\.global\[[^\]]+\],\[[^\]]+\],0x10,(%r\d+|(?:0x[0-9a-fA-F]+|\d+));',
            token)
        _need(match is not None, 'Unknown source async copy form')
        size = match[1]
        if size.startswith('%'):
            start = max((i for i, value in enumerate(lines[:line - 1])
                         if value.startswith(('.visible.entry', '.entry',
                                              '.visible.func', '.func',
                                              '.weak.func', '.extern.func'))),
                        default=0)
            definitions = [
                value for value in lines[start:line - 1] if re.fullmatch(
                    r'(?:@!?%p\d+)?[a-z][a-z0-9.]*' + re.escape(size) +
                    r',.*;', value)
            ]
            _need(definitions,
                  'Source async valid-byte value has no definition')
            selected = re.fullmatch(
                r'selp\.b32' + re.escape(size) + r',16,0,%p\d+;',
                definitions[-1])
            constant = re.fullmatch(
                r'mov\.(?:u|b)32' + re.escape(size) +
                r',(0x[0-9a-fA-F]+|\d+);', definitions[-1])
            _need(
                selected is not None
                or constant is not None and int(constant[1], 0) in (0, 16),
                'Source async copy does not declare zero-or-sixteen valid bytes'
            )
        else:
            _need(
                int(size, 0) in (0, 16),
                'Unknown constant source valid-byte count')
        return line, token, 16
    if site['kind'] == 'shared_load_issue_bracket':
        _need(
            re.fullmatch(
                r'ldmatrix\.sync\.aligned\.m8n8\.x4(?:\.trans)?\.shared\.b16\{.+\},\[.+\];',
                token) is not None, 'Unknown source matrix shared-load form')
        return line, token, None
    match = re.fullmatch(
        r'(?:st|ld)\.shared\.(?:v([24])\.)?[busf](8|16|32|64).+;', token)
    _need(match is not None, 'Unknown source shared memory width')
    return line, token, (int(match[1]) if match[1] else 1) * int(match[2]) // 8


def derive_shared_payloads(*, machine_map, sass_lines, sass_json, ptx, plan):
    fields_report = derive_record_fields(machine_map=machine_map,
                                         sass_lines=sass_lines,
                                         sass_json=sass_json,
                                         ptx=ptx,
                                         plan=plan)
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    graphs = {name: _predecessors(body) for name, body in functions.items()}
    dominators = {name: _dominators(graph) for name, graph in graphs.items()}
    annotations = _native_lines(sass_lines, functions)
    lines, marker_rows = _lex(ptx.decode(), 'late-v1')
    markers = {(site, phase): line for line, site, phase in marker_rows}
    readers = {
        (r['site_id'], r['phase']): r
        for r in machine_map['counter_pcs']
    }
    field_sites = {r['site_id']: r for r in fields_report['sites']}
    sources, source_errors, results = {}, {}, []
    for site in plan['sites']:
        if site['kind'] in _KINDS:
            try:
                sources[site['site_id']] = _ptx_memory(lines, markers, site,
                                                       readers)
            except (ValueError, KeyError, TypeError) as error:
                source_errors[site['site_id']] = str(error)
    for site in plan['sites']:
        if site['kind'] not in _KINDS:
            continue
        key, kind = site['site_id'], site['kind']
        result = dict(site_id=key, kind=kind, status='unverified')
        try:
            _need(key not in source_errors,
                  source_errors.get(key, 'Source memory pattern unavailable'))
            field = field_sites[key]
            _need(field['status'] == 'native_record_fields_checked',
                  'Native record field values unavailable')
            payload = next(r for r in field['fields']
                           if r['field'] == 'payload')
            function = field['function']
            body, graph = functions[function], graphs[function]
            line, token, source_bytes = sources[key]
            family = 'LDGSTS.' if kind == 'copy_submit_after' else 'LDSM.' if kind == 'shared_load_issue_bracket' else 'STS' if kind == 'shared_store_after' else 'LDS'
            candidates = [
                (pc, body[pc], 0, [key])
                for pc in annotations.get((function, line), ())
                if body[pc]['opcode'].startswith(family)
                and _predicate(body[pc].get('predicate')) is not False
            ]
            # A pair of adjacent scalar source loads may become one native LDS.64.
            # Keep both source origins and the physical byte subrange explicit.
            if not candidates and kind == 'shared_load_native_bracket':
                current = re.fullmatch(
                    r'ld\.shared\.b32%r\d+,\[(%r\d+)\+(\d+)\];', token)
                if current:
                    for other_key, (other_line, other_token,
                                    _) in sources.items():
                        if other_line >= line:
                            continue
                        first = re.fullmatch(
                            r'ld\.shared\.b32%r\d+,\[' +
                            re.escape(current[1]) + r'(?:\+(\d+))?\];',
                            other_token)
                        if not first or int(current[2]) - int(first[1]
                                                              or 0) != 4:
                            continue
                        between = [
                            s for s in lines[other_line:line - 1]
                            if s and not s.startswith(('.loc', '.file'))
                        ]
                        if not between or not all(
                                re.fullmatch(r'mov\.u64%rd\d+,%globaltimer;',
                                             s) for s in between):
                            continue
                        candidates.extend(
                            (pc, body[pc], 4, [other_key, key])
                            for pc in annotations.get((function,
                                                       other_line), ())
                            if body[pc]['opcode'] == 'LDS.64')
            _need(
                len(candidates) == 1,
                'Missing or ambiguous native shared operation')
            pc, native, suboffset, origins = candidates[0]
            _need(
                native.get('predicate') is None,
                'Predicated shared operation requires participation evidence')
            operand = _compact(native.get('operands', ''))
            address = re.search(r'\[[^\]]+\]', operand)
            _need(address is not None,
                  'Native shared operation lacks its address')
            match = re.fullmatch(r'(?:LDS|STS)(?:\.(32|64|128))?',
                                 native['opcode'])
            if kind not in ('copy_submit_after', 'shared_load_issue_bracket'):
                _need(match is not None, 'Unknown native shared width')
                native_bytes = int(match[1] or 32) // 8
                _need(suboffset + source_bytes <= native_bytes,
                      'Source subrange exceeds native memory width')
            else:
                native_bytes = 16 if kind == 'copy_submit_after' else None
                if kind == 'shared_load_issue_bracket':
                    _need(
                        native['opcode'] == ('LDSM.16.MT88.4' if '.trans.'
                                             in token else 'LDSM.16.M88.4'),
                        'Native matrix geometry differs from source collective'
                    )
            words = _Words(body,
                           graph,
                           dominators[function],
                           operation_pc=pc,
                           store_pc=payload['pc'])
            registers = _registers(payload['value_register'], 2)
            actual_low = words.value(payload['pc'], registers[0])
            expected_low = words.arena.add(words.address(pc, address[0]),
                                           suboffset)
            _need(actual_low == expected_low,
                  'Recorded low word differs from the native shared address')
            actual_high = words.value(payload['pc'], registers[1])
            if kind == 'copy_submit_after':
                pred = re.fullmatch(
                    r'\[[^\]]+\],desc\[UR\d+\]\[[^\]]+\],(!?(?:P\d+|PT))',
                    operand)
                _need(
                    pred is not None and native['opcode']
                    in ('LDGSTS.E.BYPASS.128', 'LDGSTS.E.128'),
                    'Unknown native copy valid-byte predicate')
                expected_high = words.arena.select(words.boolean(pred[1], pc),
                                                   16, 0)
            else:
                expected_high = 0 if kind == 'shared_load_issue_bracket' else source_bytes
            _need(
                actual_high == expected_high,
                'Recorded high word differs from native byte/valid-source semantics'
            )
            entry = readers.get((key, 'entry'))
            result.update(status='native_shared_payload_words_checked',
                          function=function,
                          operation_pc=pc,
                          native_opcode=native['opcode'],
                          native_operands=operand,
                          payload_store_pc=payload['pc'],
                          payload_registers=registers,
                          source_ptx_line=line,
                          source_bytes=source_bytes,
                          native_bytes=native_bytes,
                          native_byte_suboffset=suboffset,
                          source_origins=origins,
                          native_operation_before_source_entry=bool(
                              entry and pc < entry['pc']),
                          epoch_cut_pc=words.cut,
                          loop_members=len(words.loop),
                          expression_nodes=len(words.arena.nodes),
                          shared_address_expression=actual_low,
                          high_word_expression=actual_high,
                          variable_payload_words_verified=True,
                          absolute_raw_slot_binding_verified=False,
                          time_flows_qualified=False)
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    groups = {}
    for row in results:
        if row['status'] == 'native_shared_payload_words_checked':
            groups.setdefault((row['function'], row['operation_pc']),
                              []).append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: row['source_ptx_line'])
        origins = [row['site_id'] for row in rows]
        native_bytes = rows[0]['native_bytes']
        coverage = sorted((row['native_byte_suboffset'], row['source_bytes'])
                          for row in rows if row['source_bytes'] is not None)
        frontier = 0
        for offset, size in coverage:
            if offset != frontier:
                break
            frontier += size
        complete = native_bytes is not None and frontier == native_bytes
        witness = next(
            (row for row in rows if row['native_byte_suboffset'] == 0),
            rows[0])
        observer = readers[witness['site_id'], 'exit']
        if witness['kind'] in ('shared_load_issue_bracket',
                               'shared_load_native_bracket'):
            before = readers[witness['site_id'], 'entry']
            _need(
                before['pc'] < witness['operation_pc'] < observer['pc'],
                'Native memory group lacks a matching observed issue bracket')
            _straight_path(functions[witness['function']], before['pc'],
                           observer['pc'])
        else:
            _need(witness['operation_pc'] < observer['pc'],
                  'Native shared write is after its recorded checkpoint')
            _straight_path(functions[witness['function']],
                           witness['operation_pc'], observer['pc'])
        for row in rows:
            row.update(source_origins=origins,
                       native_byte_coverage_complete=complete,
                       observation_witness_site=witness['site_id'],
                       native_issue_observation_order_checked=True)
    return dict(model=MODEL,
                binary_id=machine_map['binary_id'],
                sites=results,
                implementation_sha256=_rule_digests(),
                absolute_raw_slot_binding_verified=False,
                record_value_provenance_verified=False,
                clock_qualified=False,
                hardware_overlap_verified=False,
                time_flows_qualified=False)


def _rule_digests():
    from . import timeline_nvidia_control, timeline_nvidia_late_values, timeline_nvidia_late_boundaries, timeline_nvidia_late_records, timeline_nvidia_machine, timeline_nvidia_late_control
    modules = (timeline_nvidia_control, timeline_nvidia_late_values,
               timeline_nvidia_late_boundaries, timeline_nvidia_late_records,
               timeline_nvidia_machine, timeline_nvidia_late_control)
    paths = [Path(__file__), *(Path(module.__file__) for module in modules)]
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def inspect_shared_payloads(**inputs):
    try:
        return derive_shared_payloads(**inputs)
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        return dict(
            model=MODEL,
            binary_id=inputs['machine_map'].get('binary_id'),
            status='unverified_native_shared_payload_inputs_or_pattern',
            sites=[],
            reason=str(error),
            implementation_sha256=_rule_digests(),
            absolute_raw_slot_binding_verified=False,
            record_value_provenance_verified=False,
            time_flows_qualified=False)


def load_shared_payload_bindings(directory, capture, proof):
    """Raw-domain and coalesced-group checks, not absolute slot ownership."""
    from .timeline_store import read_artifact
    from .timeline_nvidia_late_raw import decode_late_raw
    from .timeline_nvidia_late_async import derive_late_async
    owner = capture['owner']
    _need(
        proof.get('model') == MODEL
        and proof.get('binary_id') == owner['binary_id']
        and proof.get('status')
        != 'unverified_native_shared_payload_inputs_or_pattern',
        'Shared payload proof belongs to another binary or unavailable pattern'
    )
    raw = read_artifact(directory, capture['raw_file'])
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Shared payload raw changed')
    decoded = decode_late_raw(owner['plan'],
                              raw,
                              slots=owner['layout']['slots'])
    _need(decoded['complete'], 'Shared payload binding requires complete raw')
    shared_bytes = capture['metadata']['compiler_metadata']['shared']
    _need(
        type(shared_bytes) is int and shared_bytes >= 0,
        'Missing actual shared allocation size')
    sites = {
        row['site_id']: row
        for row in proof['sites']
        if row['status'] == 'native_shared_payload_words_checked'
    }
    _need(not sites or shared_bytes > 0,
          'Native shared payload sites lack an allocation')
    groups = sorted({(row['function'], row['operation_pc'])
                     for row in sites.values()})
    rows = []
    for program in decoded['programs']:
        for actor in program['observers']:
            pending = {}
            for ordinal, event in enumerate(actor['events']):
                site = sites.get(event['site_id'])
                if site is None:
                    continue
                low, high = event['payload'] & MASK, event['payload'] >> 32
                if site['kind'] == 'copy_submit_after':
                    _need(
                        high in (0, 16),
                        'Raw source-valid size differs from native predicate encoding'
                    )
                    size = 16
                elif site['kind'] == 'shared_load_issue_bracket':
                    _need(high == 0,
                          'Matrix address payload has nonzero high word')
                    size = 1  # Collective byte footprint is independently modeled below.
                else:
                    _need(
                        high == site['source_bytes'],
                        'Raw access width differs from the native source subrange'
                    )
                    size = high
                _need(
                    actor['shared_base'] <= low
                    and low + size <= actor['shared_base'] + shared_bytes,
                    'Raw native shared payload is outside its actual allocation'
                )
                group = groups.index((site['function'], site['operation_pc']))
                origins = site['source_origins']
                index = origins.index(event['site_id'])
                if index == 0:
                    _need(group not in pending,
                          'Previous native source group was not complete')
                    first = ordinal
                    pending[group] = (ordinal,
                                      low - site['native_byte_suboffset'], 1)
                else:
                    _need(
                        group in pending,
                        'Coalesced source origin lacks its native group start')
                    first, address, count = pending[group]
                    _need(
                        count == index and ordinal == first + index
                        and low - site['native_byte_suboffset'] == address,
                        'Coalesced source payloads disagree on one actual native memory operation'
                    )
                    pending[group] = (first, address, count + 1)
                if index == len(origins) - 1:
                    pending.pop(group)
                rows.append([
                    program['program_id'], actor['actor'], ordinal,
                    event['site_id'], event['raw_payload_offset_bytes'],
                    event['payload'], group, first
                ])
            _need(not pending, 'Incomplete final native source group')
    facts = derive_late_async(decoded,
                              owner['plan'],
                              shared_bytes=shared_bytes)
    from . import timeline_nvidia_late_raw, timeline_nvidia_late_async, timeline_nvidia_late_model, timeline_store
    paths = [
        Path(__file__),
        *(Path(module.__file__)
          for module in (timeline_nvidia_late_raw, timeline_nvidia_late_async,
                         timeline_nvidia_late_model, timeline_store))
    ]
    return dict(model='nvidia.late.shared_payload_raw_bindings.v1',
                status='native_shared_payload_domains_and_groups_checked'
                if rows else 'no_verified_shared_payload_occurrences',
                identity={
                    key: owner[key]
                    for key in ('capture_id', 'invocation_id', 'binary_id')
                },
                raw_sha256=decoded['raw_sha256'],
                static_proof_sha256=hashlib.sha256(
                    json.dumps(proof, sort_keys=True,
                               separators=(',', ':')).encode()).hexdigest(),
                implementation_sha256={
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in paths
                },
                groups=[
                    dict(function=function, operation_pc=pc)
                    for function, pc in groups
                ],
                columns=[
                    'program', 'actor', 'ordinal', 'site_id',
                    'raw_payload_offset_bytes', 'payload',
                    'static_group_index', 'native_group_first_ordinal'
                ],
                rows=rows,
                collective_byte_model_status=facts['status'],
                absolute_raw_slot_binding_verified=False,
                time_flows_qualified=False)
