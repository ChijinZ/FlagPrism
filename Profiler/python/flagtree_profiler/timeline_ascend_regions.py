"""Finite actor-LLVM record associations; not native or source qualification.

Inputs must be recomputed from the exact adapted actor by the native indexer.
This first layer binds the eight physical tuple fields to actual clock SSA
definitions. Selection, body containment and loop rules are separate facts.
"""
MASK = (1 << 64) - 1
COMMIT = 0x46505441434f4d31
CLOCK = '__flagprism_sys_cnt_v1__'


class _BudgetExceeded(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise ValueError(message)


class _Index:

    def __init__(self, function):
        self.arguments = function['arguments']
        self.instructions = {}
        self.block = {}
        self.blocks = {}
        self.constants = {}
        self.cache = {}
        self.work = 0
        _need(len(function['blocks']) <= 8192, 'Excessive actor blocks')
        for block in function['blocks']:
            _need(block['id'] not in self.blocks, 'Duplicate actor block')
            self.blocks[block['id']] = block
            for instruction in block['instructions']:
                self.charge()
                key = instruction['id']
                _need(key not in self.instructions,
                      'Duplicate actor definition')
                self.instructions[key] = instruction
                self.block[key] = block['id']
                for operand in instruction['operands']:
                    if 'integer_hex' in operand:
                        bits = operand['integer_bits']
                        _need(
                            type(bits) is int and 0 < bits <= 64,
                            'Invalid indexed integer width')
                        _need(
                            type(operand['integer_hex']) is str
                            and 0 < len(operand['integer_hex']) <= 16,
                            'Invalid bounded indexed literal')
                        value = int(operand['integer_hex'], 16)
                        _need(0 <= value < 1 << bits,
                              'Invalid indexed literal')
                        constant = (bits, value)
                        previous = self.constants.setdefault(
                            operand['id'], constant)
                        _need(previous == constant,
                              'Inconsistent indexed literal')

    def charge(self):
        self.work += 1
        if self.work > 1000000:
            raise _BudgetExceeded('Actor record work budget exceeded')

    def literal(self, key):
        return self.constants.get(key)

    def expr(self, key, depth=0):
        self.charge()
        _need(depth <= 64, 'Actor expression depth exceeded')
        if key in self.cache:
            return self.cache[key]
        constant = self.literal(key)
        if constant:
            return ('constant', *constant)
        instruction = self.instructions.get(key)
        expression = ('value', key)
        if instruction:
            opcode = instruction['opcode']
            operands = instruction['operands']
            # Flagged arithmetic is opaque: algebraic normalization must not
            # silently treat potentially poison-producing arithmetic as wrap.
            if (opcode in ('add', 'mul', 'xor')
                    and instruction['type'].get('integer_bits') == 64
                    and not instruction.get('nsw')
                    and not instruction.get('nuw') and len(operands) == 2):
                terms, total = [], 1 if opcode == 'mul' else 0
                for operand in operands:
                    part = self.expr(operand['id'], depth + 1)
                    parts = part[1:] if part[0] == opcode else (part, )
                    for term in parts:
                        self.charge()
                        if term[:2] == ('constant', 64):
                            value = term[2]
                            total = ((total + value) if opcode == 'add' else
                                     (total * value) if opcode == 'mul' else
                                     (total ^ value)) & MASK
                        else:
                            terms.append(term)
                            if len(terms) > 1024:
                                raise _BudgetExceeded(
                                    'Actor expression term budget exceeded')
                neutral = 1 if opcode == 'mul' else 0
                if total != neutral or not terms:
                    terms.append(('constant', 64, total))
                terms.sort(key=repr)
                expression = terms[0] if len(terms) == 1 else (opcode, *terms)
            # Other instructions retain their actual SSA identity. In
            # particular, no exact/division/cast semantics are inferred.
        self.cache[key] = expression
        return expression

    def address(self, operand):
        instruction = self.instructions.get(operand['id'])
        _need(
            instruction and instruction['opcode'] == 'getelementptr'
            and instruction.get('element_type', {}).get('integer_bits') == 64
            and len(instruction['operands']) == 2,
            'Record address is not one typed i64 GEP')
        pointer, offset = instruction['operands']
        return pointer['id'], self.expr(offset['id'])

    def offset(self, expression):
        terms = list(
            expression[1:]) if expression[0] == 'add' else [expression]
        constant = sum(x[2] for x in terms if x[:2] == ('constant', 64)) & MASK
        return tuple(x for x in terms if x[:2] != ('constant', 64)), constant

    def clock(self, key, line):
        instruction = self.instructions.get(key, {})
        location = instruction.get('location', {})
        _need(
            instruction.get('opcode') == 'call'
            and instruction.get('assembly') == 'MOV $0, SYS_CNT'
            and instruction.get('constraints') == '=l'
            and instruction.get('side_effects') is True
            and instruction.get('type', {}).get('integer_bits') == 64
            and len(instruction.get('operands', [])) == 1
            and location.get('file') == CLOCK and location.get('line') == line
            and location.get('column') == 0,
            'Tuple endpoint differs from actual marked SYS_CNT definition')
        return key

    def start(self, key, line):
        instruction = self.instructions.get(key, {})
        if instruction.get('opcode') != 'phi':
            return self.clock(key, line)
        incoming = instruction.get('incoming', [])
        _need(len(incoming) == 2, 'Start PHI is not a two-edge selection')
        ticks, zeros = [], []
        for edge in incoming:
            value = edge['value']['id']
            if self.literal(value) == (64, 0):
                zeros.append(edge)
            else:
                self.clock(value, line)
                _need(self.block[value] == edge['block'],
                      'Start clock is not defined on its incoming edge')
                ticks.append(value)
        _need(
            len(zeros) == len(ticks) == 1,
            'Start PHI does not select exactly fresh tick or zero')
        return ticks[0]


def bind_record_endpoints(graph, *, manifest, function, trace_argument_index):
    """Associate complete typed tuples, retaining all unproved fact boundaries.

    ``function`` and ``trace_argument_index`` come from the checked compiler
    actor ABI, never from a guessed first definition or last pointer argument.
    """
    _need(
        graph.get('model') == 'ascend.actor_llvm15.structure.v1'
        and graph.get('schema_version') == 1, 'Unsupported actor index')
    functions = [f for f in graph['functions'] if f['name'] == function]
    _need(len(functions) == 1, 'No unique declared actor function')
    index = _Index(functions[0])
    _need(
        type(trace_argument_index) is int
        and 0 <= trace_argument_index < len(index.arguments),
        'Missing explicit actor trace argument')
    pointer = index.arguments[trace_argument_index]
    _need(pointer['type'].get('address_space') == 1,
          'Trace ABI is not a global-memory pointer')
    pointer_id = pointer['id']
    sites = {s['site_id']: s for s in manifest['dynamic_sites']}
    _need(
        len(sites) == len(manifest['dynamic_sites']) <= 256,
        'Duplicate or excessive actor sites')
    candidates = {sid: [] for sid in sites}
    for block in index.blocks.values():
        stores = [i for i in block['instructions'] if i['opcode'] == 'store']
        for position, store in enumerate(stores):
            index.charge()
            value = index.literal(store['operands'][0]['id'])
            if not value or value[0] != 64:
                continue
            descriptor = value[1]
            sid, semantic = descriptor & 0xffffffff, descriptor >> 32
            if sid not in sites or semantic not in (1, 2, 3):
                continue
            try:
                _need(semantic == sites[sid]['semantic_code'],
                      'Tuple semantic differs from manifest')
                fields = stores[position:position + 8]
                _need(len(fields) == 8, 'Incomplete eight-word tuple')
                base = None
                for n, field in enumerate(fields):
                    _need(
                        field.get('volatile') is True
                        and field.get('atomic') is False and
                        field['operands'][0]['type'].get('integer_bits') == 64,
                        'Tuple has nonvolatile/atomic/non-i64 field')
                    root, offset = index.address(field['operands'][1])
                    _need(root == pointer_id, 'Tuple targets another pointer')
                    terms, constant = index.offset(offset)
                    if base is None:
                        base = terms, constant
                    _need(
                        terms == base[0] and constant == (base[1] + n) & MASK,
                        'Tuple words are not one contiguous record')
                ids = [field['operands'][0]['id'] for field in fields]
                begin = index.start(ids[2], 2 * sid - 1)
                end = index.clock(ids[3], 2 * sid)
                expected = [('constant', 64, COMMIT ^ descriptor)]
                for key in (ids[1], ids[4], ids[5], ids[6]):
                    expression = index.expr(key)
                    expected.extend(expression[1:] if expression[0] ==
                                    'xor' else (expression, ))
                # Compare checksum algebra using the same finite XOR normal
                # form, combining constants without inventing any field value.
                constant, terms = 0, []
                for part in expected:
                    if part[:2] == ('constant', 64):
                        constant ^= part[2]
                    else:
                        terms.append(part)
                if constant or not terms:
                    terms.append(('constant', 64, constant))
                terms.sort(key=repr)
                expected = terms[0] if len(terms) == 1 else ('xor', *terms)
                _need(
                    index.expr(ids[7]) == expected,
                    'Tuple commit fields differ')
                candidates[sid].append(
                    dict(status='llvm_tuple_endpoints_bound',
                         block_id=block['id'],
                         begin_id=begin,
                         end_id=end,
                         start_value_id=ids[2],
                         field_value_ids=ids,
                         store_ids=[f['id'] for f in fields]))
            except _BudgetExceeded:
                # An unvisited later tuple may invalidate uniqueness of an
                # earlier match. Never return checked prefixes of this scan.
                raise
            except (ValueError, KeyError, TypeError) as error:
                candidates[sid].append(
                    dict(status='unverified', reason=str(error)))
    regions = []
    for sid in sites:
        matches = candidates[sid]
        result = matches[0] if len(matches) == 1 else dict(
            status='unverified',
            reason='Missing or ambiguous complete actor tuple')
        regions.append(
            dict(site_id=sid,
                 **result,
                 selection_verified=False,
                 source_body_verified=False,
                 actor_identity_verified=False,
                 loop_verified=False,
                 native_schedule_qualified=False))
    return dict(schema_version=1,
                model='ascend.llvm_tuple_endpoints.v1',
                function=function,
                trace_argument_index=trace_argument_index,
                regions=regions,
                native_schedule_qualified=False)
