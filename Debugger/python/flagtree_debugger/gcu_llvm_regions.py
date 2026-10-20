"""Finite selected-observer LLVM boundaries, including shared-end tuples.

Input is the typed index of the actual SDK-verified codegen input. These checks
establish LLVM placement/tuple facts for a lowering-family rule; they do not
independently prove native scheduling, hardware busy time or source-exclusive
cost. No operator names, source hashes, site numbers or block numbers select a
rule. Unsupported control/record shapes remain explicit per-site results.
"""
import re

_CLOCK = '_ZN4tops12global_timerEv'
_IDENTITY = 'flagprism_gcu_clock_identity_v1'
_DYNAMIC = -(1 << 31)


def _need(condition, reason):
    if not condition:
        raise ValueError(reason)


def _literal(bits, value):
    return bits, value & ((1 << bits) - 1), ()


def _atom(bits, name):
    return bits, 0, ((name, 1), )


def _scale(value, factor):
    bits, constant, terms = value
    mask = (1 << bits) - 1
    return bits, constant * factor & mask, tuple(
        (name, coefficient * factor & mask) for name, coefficient in terms
        if coefficient * factor & mask)


def _add(left, right):
    _need(left[0] == right[0], 'LLVM integer expression widths differ')
    bits = left[0]
    mask = (1 << bits) - 1
    terms = dict(left[2])
    for name, coefficient in right[2]:
        terms[name] = (terms.get(name, 0) + coefficient) & mask
    _need(len(terms) <= 32, 'LLVM boundary expression exceeds term budget')
    return bits, (left[1] + right[1]) & mask, tuple(
        sorted((name, coefficient) for name, coefficient in terms.items()
               if coefficient))


class _Index:

    def __init__(self, report):
        _need(
            type(report) is dict and type(report.get('schema_version')) is int
            and report['schema_version'] == 1
            and report.get('status') == 'typed_sdk_llvm_structure_indexed',
            'Invalid typed GCU LLVM index')
        blocks = report.get('blocks')
        _need(
            type(blocks) is list and 0 < len(blocks) <= 8192,
            'LLVM boundary block budget')
        self.blocks, self.definitions, self.types, self.pred = {}, {}, {}, {}
        self.work = 0
        for block in blocks:
            identity = block.get('id')
            _need(
                type(identity) is int and identity >= 0
                and identity not in self.blocks,
                'Invalid or duplicate LLVM block')
            self.blocks[identity] = block
            arguments = block.get('arguments')
            types = block.get('argument_types')
            _need(
                type(arguments) is list and type(types) is list
                and len(arguments) == len(types),
                'LLVM block argument types missing')
            for value, kind in zip(arguments, types):
                self.define(value, kind, None)
            rows = block.get('operations')
            _need(type(rows) is list and rows, 'Empty LLVM block')
            for position, row in enumerate(rows):
                results, types = row.get('results'), row.get('result_types')
                _need(
                    type(results) is list and type(types) is list
                    and len(results) == len(types),
                    'LLVM result types missing')
                for value, kind in zip(results, types):
                    self.define(value, kind, (identity, position, row))
        _need(len(self.definitions) <= 250000, 'LLVM boundary value budget')
        _need(
            sum(len(b['operations']) for b in blocks) <= 100000,
            'LLVM boundary operation budget')
        self.pred = {identity: [] for identity in self.blocks}
        self.entry = report.get('entry_block')
        _need(
            type(self.entry) is int and self.entry in self.blocks,
            'Missing LLVM entry block')
        self.false_reachable = {}
        for identity, block in self.blocks.items():
            for position, row in enumerate(block['operations']):
                _need(
                    type(row.get('operands')) is list and all(
                        type(v) is int and v in self.types
                        for v in row['operands']),
                    'LLVM operand does not belong to indexed function')
                successors = row.get('successors', [])
                _need(type(successors) is list, 'Invalid LLVM successors')
                if successors:
                    _need(position == len(block['operations']) - 1,
                          'Nonterminal LLVM transfer')
                marker = row.get('clock_marker')
                if marker is not None:
                    _need(
                        type(marker) is dict
                        and type(marker.get('site')) is int
                        and marker['site'] > 0
                        and type(marker.get('column')) is int
                        and 1 <= marker['column'] <= 4,
                        'Invalid typed LLVM clock marker')
                for number, edge in enumerate(successors):
                    target = edge.get('block')
                    _need(
                        type(target) is int and target in self.blocks,
                        'LLVM successor escapes indexed function')
                    values = edge.get('arguments')
                    formals = self.blocks[target]['arguments']
                    _need(
                        type(values) is list and len(values) == len(formals)
                        and all(
                            type(v) is int and v in self.types
                            and self.types[v] == self.types[a]
                            for v, a in zip(values, formals)),
                        'LLVM forwarded argument types differ')
                    self.pred[target].append((identity, number))
            terminal = block['operations'][-1]
            if terminal['operation'] == 'llvm.br':
                _need(
                    len(terminal.get('successors', [])) == 1
                    and terminal['operands']
                    == terminal['successors'][0]['arguments'],
                    'Invalid direct LLVM branch')
            elif terminal['operation'] == 'llvm.cond_br':
                edges = terminal.get('successors', [])
                _need(
                    len(edges) == 2 and terminal['operands']
                    and self.bits(terminal['operands'][0]) == 1
                    and terminal['operands'][1:]
                    == edges[0]['arguments'] + edges[1]['arguments'],
                    'Invalid conditional LLVM branch')
        _need(not self.pred[self.entry],
              'LLVM entry block has incoming control')

    def define(self, value, kind, definition):
        _need(
            type(value) is int and value >= 0 and value not in self.types
            and type(kind) is str and len(kind) <= 8192,
            'Invalid or duplicate LLVM SSA value')
        self.types[value] = kind
        self.definitions[value] = definition

    def tick(self):
        self.work += 1
        _need(self.work <= 1000000,
              'LLVM boundary analysis work budget exhausted')

    def bits(self, value):
        match = re.fullmatch(r'i(1|8|16|32|64)', self.types[value])
        return int(match[1]) if match else None

    def value(self, identity, env, active=()):
        self.tick()
        if identity in env:
            return env[identity]
        bits = self.bits(identity)
        _need(bits is not None,
              'Required LLVM boundary value is not a scalar integer')
        if identity in active or len(active) >= 64:
            return _atom(bits, 'ssa:' + str(identity))
        definition = self.definitions[identity]
        if definition is None:
            return _atom(bits, 'ssa:' + str(identity))
        row = definition[2]
        operands = row['operands']

        def get(value):
            return self.value(value, env, (*active, identity))

        op = row['operation']
        if op == 'llvm.mlir.constant' and type(
                row.get('integer_constant')) is int:
            return _literal(bits, row['integer_constant'])
        if op in ('llvm.add', 'llvm.sub', 'llvm.mul') and len(operands) == 2:
            left, right = map(get, operands)
            if op == 'llvm.add':
                return _add(left, right)
            if op == 'llvm.sub':
                return _add(left, _scale(right, -1))
            if not right[2]:
                return _scale(left, right[1])
            if not left[2]:
                return _scale(right, left[1])
        if op in ('llvm.trunc', 'llvm.zext',
                  'llvm.sext') and len(operands) == 1:
            source = get(operands[0])
            _need(bits < source[0] if op == 'llvm.trunc' else bits > source[0],
                  'Invalid LLVM integer cast widths')
            if not source[2]:
                number = source[1]
                if op == 'llvm.sext' and number & (1 << (source[0] - 1)):
                    number -= 1 << source[0]
                return _literal(bits, number)
            if bits <= source[0]:
                return bits, source[1] & ((1 << bits) - 1), source[2]
        if op == 'llvm.lshr' and len(operands) == 2:
            source, count = map(get, operands)
            if not count[2] and count[1] == 32 and source[0] == 64:
                for role in ('begin', 'end'):
                    if source == _atom(64, role + ':clock'):
                        return _atom(bits, role + ':high')
            if not source[2] and not count[2] and count[1] < source[0]:
                return _literal(bits, source[1] >> count[1])
        return _atom(bits, 'ssa:' + str(identity))

    def edges(self, block, env):
        row = self.blocks[block]['operations'][-1]
        op, edges = row['operation'], row.get('successors', [])
        if op == 'llvm.br':
            _need(
                len(edges) == 1 and row['operands'] == edges[0]['arguments'],
                'Invalid direct LLVM branch')
            return [(edges[0], dict(env))]
        _need(
            op == 'llvm.cond_br' and len(edges) == 2
            and row['operands'] == [row['operands'][0]] +
            edges[0]['arguments'] + edges[1]['arguments'],
            'Unsupported LLVM boundary control')
        condition = row['operands'][0]
        _need(self.bits(condition) == 1, 'LLVM branch condition is not i1')
        value = self.value(condition, env)
        choices = [0 if value[1] else 1] if not value[2] else [0, 1]
        result = []
        for number in choices:
            selected = dict(env)
            selected[condition] = _literal(1, number == 0)
            result.append((edges[number], selected))
        return result

    def forward(self, edge, env):
        current = dict(env)
        for formal, actual in zip(self.blocks[edge['block']]['arguments'],
                                  edge['arguments']):
            if self.bits(formal) is not None:
                current[formal] = self.value(actual, env)
        return current

    def clock(self, row, env, role, column):
        _need(
            row['operation'] == 'llvm.call' and not row['operands']
            and len(row['results']) == 1, 'Invalid generated clock call')
        value = row['results'][0]
        if column in (1, 2):
            _need(
                row.get('callee') == _CLOCK and self.bits(value) == 64,
                'Counter marker is not the SDK timer call')
            env[value] = _atom(64, role + ':clock')
        else:
            _need(
                row.get('callee') == _IDENTITY and self.bits(value) == 32,
                'Identity marker is not the SDK identity call')
            env[value] = _atom(32, role + ':identity')

    def pointer(self, value, env, depth=0):
        self.tick()
        _need(depth < 32, 'LLVM record pointer exceeds depth budget')
        definition = self.definitions[value]
        if definition is not None and definition[2][
                'operation'] == 'llvm.getelementptr':
            row = definition[2]
            indices = row.get('constant_indices')
            _need(
                row.get('element_type') == 'i32' and type(indices) is list
                and len(indices) == 1, 'Record GEP is not one i32 index')
            if indices[0] == _DYNAMIC:
                _need(len(row['operands']) == 2, 'Invalid dynamic record GEP')
                offset = self.value(row['operands'][1], env)
            else:
                _need(
                    len(row['operands']) == 1 and type(indices[0]) is int,
                    'Invalid constant record GEP')
                offset = _literal(32, indices[0])
            _need(offset[0] == 32, 'Record index is not i32')
            base = row['operands'][0]
            # An existing descriptor/header GEP can have another element type;
            # retain it as the common base, not as a guessed byte displacement.
            parent = self.definitions[base]
            if parent is not None and parent[2][
                    'operation'] == 'llvm.getelementptr' and parent[2].get(
                        'element_type') == 'i32':
                root, previous = self.pointer(base, env, depth + 1)
                return root, _add(previous, offset)
            return base, offset
        raise ValueError('Record store has no typed i32 GEP')


def _origins(location):
    return set((path, int(line)) for path, line in re.findall(
        r'"((?:[^"\\\n]|\\.)*)":(\d+):\d+', location))


def _body_family(site, rows):
    prefix = {
        'memref_ext.slice_start': 'tops_slice_async_',
        'memref_ext.slice_pad_start': 'tops_slice_pad_async_',
        'memref_ext.slice_deslice_start': 'tops_slice_deslice_async_',
        'memref_ext.deslice_start': 'tops_deslice_async_',
        'memref_ext.memset_start': 'tops_memset_async_',
        'memref_ext.transpose_start': 'tops_transpose_async_',
        'memref_ext.broadcast_start': 'tops_broadcast_async_',
        'memref.dma_start': 'tops_memcpy_async',
        'memref.dma_wait': 'tops_wait_dte',
        'gcu.matmul': 'tops_addmm_',
        'gpu.barrier': 'tops_syncthreads',
    }.get(site.get('operation'))
    origins = _origins(site.get('location', ''))
    matching = [(block, position, row) for block, position, row in rows
                if origins & _origins(row.get('location', ''))]
    if prefix:
        matching = [(b, p, r) for b, p, r in matching
                    if r.get('callee', '').startswith(prefix)]
        family = 'primitive_issue_or_wait'
    elif site.get('operation') == 'gcu.border' and site.get('kind') == 5:
        matching = [(b, p, r) for b, p, r in matching if r['operation'] in (
            'llvm.load', 'llvm.store', 'llvm.fadd', 'llvm.fsub', 'llvm.fmul',
            'llvm.fdiv', 'llvm.call') and r.get('callee') not in (_CLOCK,
                                                                  _IDENTITY)]
        family = 'paired_fusion_observer_body'
    else:
        raise ValueError(
            'Source primitive is outside finite LLVM boundary families')
    _need(matching, 'No original source body/caller in selected clock bracket')
    return family, [
        dict(block=b,
             operation=p,
             name=r['operation'],
             callee=r.get('callee'),
             location=r.get('location')) for b, p, r in matching
    ]


def _record(index, block, position, env, site, capacity):
    rows = index.blocks[block]['operations']
    identity_seen = False
    columns = []
    for row in rows[position:]:
        marker = row.get('clock_marker')
        if marker:
            _need(marker['column'] in (2, 4),
                  'Another begin enters end-record path')
            index.clock(row, env, 'end', marker['column'])
            columns.append((marker['site'], marker['column']))
            identity_seen |= marker['column'] == 4
        else:
            _need(
                row['operation']
                in ('llvm.trunc', 'llvm.lshr', 'llvm.load', 'llvm.icmp',
                    'llvm.add', 'llvm.select', 'llvm.store', 'llvm.cond_br'),
                'Original effect or unsupported operation follows end counter')
    _need(identity_seen, 'End counter has no matching physical identity')
    _need(
        len(columns) == 2 and columns[0][1] == 2 and columns[1][1] == 4
        and columns[0][0] == columns[1][0],
        'End counter and identity markers differ')
    terminal = rows[-1]
    _need(
        terminal['operation'] == 'llvm.cond_br'
        and len(terminal.get('successors', [])) == 2,
        'End-record capacity diamond is missing')
    predicate = index.definitions[terminal['operands'][0]]
    _need(predicate is not None, 'Capacity predicate has no definition')
    compare = predicate[2]
    _need(
        compare['operation'] == 'llvm.icmp'
        and compare.get('predicate') == 'ult'
        and len(compare['operands']) == 2,
        'Record capacity is not an unsigned bound')
    sequence = index.value(compare['operands'][0], env)
    _need(
        index.value(compare['operands'][1], env) == _literal(32, capacity),
        'Record capacity differs from manifest')
    source = index.definitions[compare['operands'][0]]
    _need(
        source is not None and source[0] == block and source[1] >= position
        and source[2]['operation'] == 'llvm.load'
        and index.bits(compare['operands'][0]) == 32,
        'Record sequence is not the actual attempted-count load')
    updates = [
        row for row in rows[position:] if row['operation'] == 'llvm.store'
    ]
    _need(
        len(updates) == 1 and len(updates[0]['operands']) == 2
        and updates[0]['operands'][1] == source[2]['operands'][0],
        'End block writes outside its attempted-count status word')
    update = index.definitions[updates[0]['operands'][0]]
    _need(
        update is not None and update[2]['operation'] == 'llvm.select'
        and len(update[2]['operands']) == 3,
        'Attempted-count update is not the saturating protocol')
    condition, saturated, incremented = update[2]['operands']
    saturating_compare = index.definitions[condition]
    _need(
        saturating_compare is not None
        and saturating_compare[2]['operation'] == 'llvm.icmp'
        and saturating_compare[2].get('predicate') == 'eq',
        'Attempted-count saturation comparison is missing')
    comparison_values = [
        index.value(v, env) for v in saturating_compare[2]['operands']
    ]
    _need(
        len(comparison_values) == 2 and sequence in comparison_values
        and _literal(32, 0x7fffffff) in comparison_values
        and index.value(saturated, env) == sequence
        and index.value(incremented, env) == _add(sequence, _literal(32, 1)),
        'Attempted-count update reuses or changes the record sequence')
    normal, full = terminal['successors']
    current = index.forward(normal, env)
    tail = normal['block']
    tail_rows = index.blocks[tail]['operations']
    _need(
        tail_rows[-1]['operation'] == 'llvm.br'
        and len(tail_rows[-1].get('successors', [])) == 1
        and tail_rows[-1]['successors'][0]['block'] == full['block'],
        'Record/full paths do not rejoin before the next execution')
    stores = []
    for offset, row in enumerate(tail_rows[:-1]):
        index.tick()
        _need(
            not row.get('successors') and not row.get('clock_marker')
            and row['operation']
            in ('llvm.add', 'llvm.sub', 'llvm.mul', 'llvm.trunc', 'llvm.lshr',
                'llvm.shl', 'llvm.and', 'llvm.or', 'llvm.sext', 'llvm.zext',
                'llvm.ptrtoint', 'llvm.load', 'llvm.extractvalue',
                'llvm.getelementptr', 'llvm.mlir.constant', 'llvm.icmp',
                'llvm.select', 'llvm.store'), 'Unknown effect in record block')
        if row['operation'] == 'llvm.store':
            _need(
                len(row['operands']) == 2
                and index.bits(row['operands'][0]) == 32,
                'Record field is not an i32 store')
            stores.append((index.pointer(row['operands'][1], current),
                           index.value(row['operands'][0], current), offset))
    _need(len(stores) == 32, 'Record block does not write one complete record')
    magic = [
        address for address, value, _ in stores
        if value == _literal(32, 0x46504733)
    ]
    _need(len(magic) == 1, 'Missing or ambiguous record magic')
    base, start = magic[0]
    expected_start = _add(_scale(sequence, 32), _literal(32, 8))
    _need(start == expected_start, 'Record slot differs from guarded sequence')
    fields = {}
    for (root, address), value, operation in stores:
        _need(root == base and address[2] == start[2],
              'Record field has an unbound alias')
        offset = (address[1] - start[1]) & 0xffffffff
        _need(offset < 32 and offset not in fields,
              'Overlapping or foreign record field')
        fields[offset] = (value, operation)
    required = {
        0: _literal(32, 0x46504733),
        1: _literal(32, site['id']),
        2: sequence,
        3: _literal(32, site['kind']),
        4: _atom(32, 'begin:clock'),
        5: _atom(32, 'begin:high'),
        6: _atom(32, 'end:clock'),
        7: _atom(32, 'end:high'),
        8: _atom(32, 'end:identity'),
        18: _atom(32, 'begin:identity'),
        19: _atom(32, 'end:identity'),
        31: _literal(32, 0x46504743)
    }
    _need(all(fields[word][0] == value for word, value in required.items()),
          'Site/begin/end/identity tuple does not reach this record')
    return dict(end_block=block,
                record_block=tail,
                join_block=full['block'],
                field_refs={
                    str(word): dict(block=tail, operation=fields[word][1])
                    for word in required
                },
                sequence_value=compare['operands'][0])


def _selection(index, begin, edge):
    """Accept direct or merged selected diamonds, using actual incoming tuples.

    A previous selected record diamond can precede this reader. The join still
    receives either this reader's fresh tuple or the invariant selector's zero
    tuple. False-selector reachability checks every function entry path rather
    than assuming that an absent immediate guard means an unconditional read.
    """
    guards, selectors = [], set()
    for predecessor, number in index.pred[edge['block']]:
        if predecessor == begin:
            continue
        row = index.blocks[predecessor]['operations'][-1]
        _need(
            row['operation'] == 'llvm.cond_br' and number == 1
            and len(row.get('successors', [])) == 2,
            'Body has an incoming path that bypasses its fresh begin tuple')
        excluded = row['successors'][number]
        _need(
            len(excluded['arguments']) == 3 and all(
                index.value(value, {}) == _literal(32, 0)
                for value in excluded['arguments']),
            'Unselected body path has a nonzero begin tuple')
        selectors.add(row['operands'][0])
        guards.append(predecessor)
    _need(guards and len(selectors) == 1,
          'Body has ambiguous observer selection')
    selector = selectors.pop()
    definition = index.definitions[selector]
    _need(
        index.bits(selector) == 1
        and (selector in index.blocks[index.entry]['arguments']
             or definition is not None and definition[0] == index.entry),
        'Observer selector is not an entry-invariant i1 value')
    if selector not in index.false_reachable:
        visited, pending = set(), [index.entry]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            index.tick()
            visited.add(current)
            row = index.blocks[current]['operations'][-1]
            successors = row.get('successors', [])
            if row['operation'] == 'llvm.cond_br' and row['operands'][
                    0] == selector:
                successors = successors[1:2]
            pending.extend(item['block'] for item in successors)
        index.false_reachable[selector] = visited
    _need(begin not in index.false_reachable[selector],
          'Begin counter can execute for an unselected observer')
    return selector, guards


def _region(index, site, block, capacity):
    rows = index.blocks[block]['operations']
    _need(rows[-1]['operation'] == 'llvm.br',
          'Begin reader does not rejoin the body')
    edge = rows[-1]['successors'][0]
    selector, guards = _selection(index, block, edge)
    env = {selector: _literal(1, 1)}
    begin_columns = []
    for row in rows[:-1]:
        marker = row.get('clock_marker')
        if marker:
            _need(
                marker.get('site') == site['id']
                and marker.get('column') in (1, 3),
                'Begin marker/site differs')
            begin_columns.append(marker['column'])
            index.clock(row, env, 'begin', marker['column'])
        else:
            _need(row['operation'] in ('llvm.trunc', 'llvm.lshr'),
                  'Begin diamond contains unexpected effects')
    _need(begin_columns == [1, 3], 'Begin counter/identity order differs')
    _need(
        len(edge['arguments']) == 3
        and [index.value(value, env) for value in edge['arguments']] == [
            _atom(32, 'begin:clock'),
            _atom(32, 'begin:high'),
            _atom(32, 'begin:identity')
        ], 'Selected and zero tuples do not rejoin the same body')
    pending = [(edge['block'], index.forward(edge, env), (), [])]
    outcomes = []
    while pending:
        _need(len(pending) + len(outcomes) <= 128, 'LLVM boundary path budget')
        current, state, visited, body = pending.pop()
        index.tick()
        _need(current not in visited and len(visited) < 512,
              'Cycle or excessive path inside the selected clock bracket')
        visited = (*visited, current)
        body = list(body)
        found = False
        for position, row in enumerate(index.blocks[current]['operations']):
            index.tick()
            marker = row.get('clock_marker')
            if marker:
                _need(
                    marker.get('column') == 2,
                    'Another marker interrupts selected body')
                record = _record(index, current, position, dict(state), site,
                                 capacity)
                family, references = _body_family(site, body)
                outcomes.append(
                    dict(**record,
                         family=family,
                         body_refs=references,
                         body_blocks=list(visited)))
                found = True
                break
            if row['operation'] not in ('llvm.br', 'llvm.cond_br'):
                body.append((current, position, row))
        if not found:
            for next_edge, next_state in index.edges(current, state):
                pending.append((next_edge['block'],
                                index.forward(next_edge,
                                              next_state), visited, body))
    _need(outcomes, 'Selected begin has no complete end-record path')
    result = dict(site_id=site['id'],
                  status='llvm_observer_boundary_checked',
                  selection_value=selector,
                  selection_guards=guards,
                  begin_block=block,
                  origin=site.get('location'),
                  operation=site.get('operation'),
                  paths=outcomes,
                  native_schedule_qualified=False,
                  source_exclusive_cost_qualified=False)
    try:
        result['loop'] = _loop(index, result)
    except ValueError as error:
        result['loop'] = dict(status='unverified', reason=str(error))
    return result


def _loop(index, region):
    """Check the finite header/body/record/latch family, not arbitrary loops."""
    joins = {path['join_block'] for path in region['paths']}
    _need(len(joins) == 1, 'Region has multiple loop/continuation joins')
    latch = joins.pop()
    visited, pending = set(), [latch]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        index.tick()
        visited.add(current)
        pending.extend(edge['block']
                       for edge in index.blocks[current]['operations'][-1].get(
                           'successors', []))
    if region['begin_block'] not in visited:
        return dict(status='no_enclosing_runtime_loop')
    row = index.blocks[latch]['operations'][-1]
    _need(
        row['operation'] == 'llvm.br' and len(row.get('successors', [])) == 1,
        'Loop continuation is outside the finite latch family')
    back = row['successors'][0]
    header = back['block']
    guard_list = region['selection_guards']
    _need(len(guard_list) == 1, 'Loop selection has multiple external guards')
    guard = guard_list[0]
    decision = index.blocks[header]['operations'][-1]
    _need(
        decision['operation'] == 'llvm.cond_br'
        and len(decision.get('successors', [])) == 2
        and decision['successors'][0]['block'] == guard,
        'Loop header does not enter the selected-body guard')
    comparison = index.definitions[decision['operands'][0]]
    _need(comparison is not None and comparison[0] == header,
          'Runtime loop comparison is not in its header')
    compare = comparison[2]
    _need(
        compare['operation'] == 'llvm.icmp'
        and compare.get('predicate') in ('slt', 'ult')
        and len(compare['operands']) == 2,
        'Runtime loop trip comparison is outside the finite family')
    induction, trip = compare['operands']
    formals = index.blocks[header]['arguments']
    _need(induction in formals and index.bits(induction) in (32, 64),
          'Loop induction is not an integer header argument')
    trip_value = index.value(trip, {})
    _need(trip_value[2], 'Loop trip bound is compile-time constant')
    trip_definition = index.definitions[trip]
    _need(
        trip in index.blocks[index.entry]['arguments']
        or (trip_definition is not None and trip_definition[0] == index.entry),
        'Runtime trip bound is not entry-invariant')
    number = formals.index(induction)
    bits = index.bits(induction)
    token = _atom(bits, 'loop:iteration')
    _need(
        index.value(back['arguments'][number],
                    {induction: token}) == _add(token, _literal(bits, 1)),
        'Loop latch does not forward the next induction value')
    initial = []
    for predecessor, edge_number in index.pred[header]:
        if predecessor == latch:
            continue
        edge = index.blocks[predecessor]['operations'][-1]['successors'][
            edge_number]
        _need(
            index.value(edge['arguments'][number], {}) == _literal(bits, 0),
            'Loop entry does not initialize its induction')
        initial.append(predecessor)
    _need(initial, 'Runtime loop has no initial entry')
    selector = region['selection_value']
    end_blocks = {path['end_block'] for path in region['paths']}
    todo = [(guard, {selector: _literal(1, 1)}, (), False, False)]
    iteration_blocks, paths = set(), 0
    while todo:
        _need(len(todo) <= 128, 'Loop path budget exceeded')
        current, state, previous, begun, ended = todo.pop()
        index.tick()
        _need(
            current != header and current not in previous
            and len(previous) < 512,
            'Loop iteration bypasses the declared latch or contains another cycle'
        )
        iteration_blocks.add(current)
        if current == region['begin_block']:
            _need(not begun,
                  'Loop reuses or repeats its begin reader before the latch')
            begun = True
        if current in end_blocks:
            _need(begun and not ended,
                  'Loop end is not paired with this iteration begin')
            ended = True
        if current == latch:
            _need(begun and ended, 'Selected loop path bypasses begin or end')
            paths += 1
            continue
        for edge, next_state in index.edges(current, state):
            todo.append((edge['block'], index.forward(edge, next_state),
                         (*previous, current), begun, ended))
    _need(paths, 'Loop has no checked iteration path')
    _need(
        decision['successors'][1]['block'] not in iteration_blocks
        and decision['successors'][1]['block'] != header,
        'Loop exit reenters the declared iteration')
    for current in iteration_blocks:
        for predecessor, number in index.pred[current]:
            if predecessor in iteration_blocks:
                continue
            if predecessor == header and current == guard and number == 0:
                continue
            source = index.blocks[predecessor]['operations'][-1]
            if source['operation'] == 'llvm.cond_br' and source['operands'][
                    0] == selector and number == 1:
                continue
            raise ValueError('External entry into the declared loop iteration')
    return dict(status='llvm_runtime_iteration_checked',
                header=header,
                latch=latch,
                exit_block=decision['successors'][1]['block'],
                initial_blocks=initial,
                induction_value=induction,
                runtime_trip_value=trip,
                body_blocks=sorted(iteration_blocks),
                selected_paths=paths,
                source_iteration_id_qualified=False)


def analyze_regions(report, manifest):
    """Check every selected site independently; no cached qualification is read."""
    index = _Index(report)
    _need(
        type(manifest) is dict and type(manifest.get('sites')) is list
        and 0 < len(manifest['sites']) <= 512
        and type(manifest.get('capacity')) is int
        and 0 < manifest['capacity'] <= 1048576, 'Invalid GCU region manifest')
    sites, starts = {}, {}
    for site in manifest['sites']:
        _need(
            type(site) is dict and type(site.get('id')) is int
            and site['id'] > 0 and site['id'] not in sites
            and type(site.get('kind')) is int,
            'Invalid or duplicate LLVM region site')
        sites[site['id']] = site
    for identity, block in index.blocks.items():
        for row in block['operations']:
            marker = row.get('clock_marker')
            _need(marker is None or marker['site'] in sites,
                  'LLVM clock marker does not belong to the manifest')
            if marker and marker.get('column') == 1:
                starts.setdefault(marker.get('site'), []).append(identity)
    regions = []
    for identity, site in sites.items():
        try:
            _need(
                len(starts.get(identity, [])) == 1,
                'Missing or ambiguous selected begin marker')
            regions.append(
                _region(index, site, starts[identity][0],
                        manifest['capacity']))
        except ValueError as error:
            regions.append(
                dict(site_id=identity, status='unverified', reason=str(error)))
    return dict(schema_version=1,
                rule_version='gcu300.selected_llvm_tuple.v1',
                semantics='selected_observer_issue_wait_or_body_elapsed',
                regions=regions,
                native_schedule_qualified=False,
                source_exclusive_cost_qualified=False)
