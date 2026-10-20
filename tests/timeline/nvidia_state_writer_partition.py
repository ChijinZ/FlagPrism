"""Finite PTX integer-cone check for retained qualification State stores.

This checks actual per-thread addresses and predicates, not floating-point
mathematics, source timing, native scheduling, or arbitrary PTX semantics.
Unsupported cones/control stay unverified. Callers must independently bind PTX,
compiled objects, launch geometry, State argument and mathematical receipts.
"""
from collections import Counter
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Pointer:
    parameter: str
    offset: int = 0


def _need(value, message):
    if not value:
        raise ValueError(message)


# Exact finite operations only: a familiar prefix does not establish the
# semantics of .hi, carry, saturation, rounding or compound predicate forms.
_ARITIES = {}
for _opcode in ('mov.b32', 'mov.b64', 'mov.u32', 'mov.u64', 'mov.pred',
                'cvta.to.global.u64'):
    _ARITIES[_opcode] = 2
for _dest in ('u32', 's32', 'u64', 's64'):
    for _source in ('u32', 's32', 'u64', 's64'):
        _ARITIES['cvt.' + _dest + '.' + _source] = 2
for _prefix in ('add', 'sub', 'mul.lo'):
    for _type in ('u32', 's32', 'u64', 's64'):
        _ARITIES[_prefix + '.' + _type] = 3
for _type in ('u32', 's32'):
    _ARITIES['mul.wide.' + _type] = 3
    _ARITIES['bfe.' + _type] = 4
for _type in ('u32', 's32', 'u64', 's64'):
    _ARITIES['mad.lo.' + _type] = 4
    _ARITIES['shr.' + _type] = 3
for _type in ('b32', 'b64'):
    _ARITIES['shl.' + _type] = 3
for _prefix in ('and', 'or', 'xor'):
    for _type in ('b32', 'b64', 'pred'):
        _ARITIES[_prefix + '.' + _type] = 3
for _comparison in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
    for _type in ('u32', 's32', 'u64', 's64') + (
        ('b32', 'b64') if _comparison in ('eq', 'ne') else ()):
        _ARITIES['setp.' + _comparison + '.' + _type] = 3
for _type in ('b32', 'b64', 'u32', 's32', 'u64', 's64'):
    _ARITIES['selp.' + _type] = 4


def _split(text):
    return [
        part.strip() for part in re.split(r',\s*(?![^\[\]{}]*[\]}])', text)
    ]


def _parse(ptx):
    _need(len(re.findall(r'\.entry\s+', ptx)) == 1, 'Ambiguous PTX entries')
    start = re.search(r'\.entry\s+([\w$]+)\s*\((.*?)\)\s*(?:\.\w+[^{}]*)?\{',
                      ptx, re.S)
    _need(start, 'Missing single PTX entry')
    parameters = re.findall(r'\.param\s+\.u64[^,\n]*?\s+([\w$]+)\s*(?:,|$)',
                            start[2], re.M)
    _need(parameters, 'Missing pointer parameter ABI')
    body = ptx[start.end():]
    # PTX vector braces are balanced; the first depth-zero brace ends the entry.
    depth = 1
    end = None
    for i, char in enumerate(body):
        depth += (char == '{') - (char == '}')
        if depth == 0:
            end = i
            break
    _need(end is not None, 'Unterminated PTX entry')
    instructions, labels, pending = [], {}, []
    for line, raw in enumerate(body[:end].splitlines(), 1):
        text = raw.split('//', 1)[0].strip()
        if not text or text.startswith('.'):
            continue
        if text.endswith(':'):
            pending.append(text[:-1])
            continue
        m = re.fullmatch(r'(?:@(!?%[\w$]+)\s+)?([A-Za-z][\w.]*)\s*(.*);', text)
        _need(m, 'Unknown PTX body statement: ' + text[:100])
        for label in pending:
            _need(label not in labels, 'Duplicate PTX label')
            labels[label] = len(instructions)
        pending.clear()
        instructions.append(
            dict(predicate=m[1],
                 opcode=m[2],
                 args=_split(m[3]),
                 source_line=line))
    _need(instructions and len(instructions) <= 20000, 'PTX instruction bound')
    graph = {}
    for i, row in enumerate(instructions):
        opcode = row['opcode']
        _need(opcode != 'ret' or row['predicate'] is None,
              'Conditional return')
        _need(not opcode.startswith(('call', 'brx', 'exit')),
              'Unsupported PTX control')
        targets = []
        if opcode.startswith('bra'):
            _need(row['args'][0] in labels, 'Missing PTX branch target')
            targets.append(labels[row['args'][0]])
            if row['predicate'] is not None:
                targets.append(i + 1)
        elif opcode != 'ret':
            targets.append(i + 1)
        _need(all(x < len(instructions) for x in targets),
              'PTX falls out of entry')
        graph[i] = tuple(targets)
    definitions = {}
    for i, row in enumerate(instructions):
        if row['opcode'].startswith(('st.', 'bra', 'bar.', 'membar.', 'ret')):
            continue
        for reg in re.findall(r'%[\w$]+', row['args'][0]):
            definitions.setdefault(reg, []).append(i)
    return parameters, instructions, graph, definitions


def partition(ptx, *, state_argument, threads, grid, elements):
    """Enumerate supported integer cones over the real finite launch geometry."""
    _need(type(threads) is int and 1 <= threads <= 1024, 'Thread extent')
    _need(type(elements) is int and 1 <= elements <= 1 << 20, 'State extent')
    _need(
        len(grid) <= 3 and all(type(x) is int and x > 0 for x in grid),
        'Grid extent')
    grid = tuple(grid) + (1, ) * (3 - len(grid))
    _need(threads * grid[0] * grid[1] * grid[2] <= 1 << 20,
          'Launch enumeration bound')
    parameters, instructions, graph, definitions = _parse(ptx)
    _need(
        type(state_argument) is int and 0 <= state_argument < len(parameters),
        'State ABI')
    state = parameters[state_argument]
    reqntid = re.search(r'\.reqntid\s+(\d+)(?:,\s*(\d+),\s*(\d+))?', ptx)
    _need(
        reqntid is not None
        and tuple(int(x or 1) for x in reqntid.groups()) == (threads, 1, 1),
        'PTX thread geometry differs from the frozen launch')
    reachable = set()
    todo = [0]
    while todo:
        node = todo.pop()
        if node not in reachable:
            reachable.add(node)
            todo.extend(graph[node])
    returns = {i for i in reachable if instructions[i]['opcode'] == 'ret'}
    _need(returns, 'No reachable PTX return')
    dominance_cache = {}

    def dominates(definition, use):
        key = definition, use
        if key not in dominance_cache:
            seen, pending = set(), [0]
            while pending:
                i = pending.pop()
                if i == definition or i in seen:
                    continue
                seen.add(i)
                pending.extend(graph[i])
            dominance_cache[key] = use not in seen
        return dominance_cache[key]

    stores = [
        i for i in reachable
        if instructions[i]['opcode'].startswith('st.global')
    ]
    _need(stores, 'No PTX global stores')
    predecessors = {i: [] for i in reachable}
    for i in reachable:
        for target in graph[i]:
            predecessors[target].append(i)
    reaching_cache = {}

    def reaching_definitions(token, use):
        key = token, use
        if key not in reaching_cache:
            candidates = frozenset(definitions.get(token, ()))
            seen, pending, result = set(), list(predecessors[use]), set()
            if use == 0:
                result.add(None)
            while pending:
                node = pending.pop()
                if node in seen:
                    continue
                seen.add(node)
                if node in candidates:
                    result.add(node)
                    if instructions[node]['predicate'] is None:
                        continue
                if node == 0:
                    result.add(None)
                pending.extend(predecessors[node])
            reaching_cache[key] = frozenset(result)
        return reaching_cache[key]

    root_cache = {}

    def pointer_roots(token, before):
        key = token, before
        if key in root_cache:
            return root_cache[key]
        # Traverse the complete dependency closure before caching. Returning an
        # empty partial result for an active cycle could hide a State root when
        # a later store queries a different member of the same cycle.
        roots, seen, pending = set(), set(), [key]
        while pending:
            operand, use = pending.pop()
            if not operand.startswith('%') or re.fullmatch(
                    r'%(?:tid|ntid|ctaid|nctaid)\.[xyz]', operand) is not None:
                continue
            node = operand, use
            if node in seen:
                continue
            seen.add(node)
            _need(len(seen) <= 20000, 'Pointer-provenance cone bound')
            if node in root_cache:
                roots.update(root_cache[node])
                continue
            for i in reaching_definitions(operand, use):
                if i is None:
                    roots.add('<undefined>')
                    continue
                row = instructions[i]
                if row['opcode'] in ('ld.param.u64', 'ld.param.b64'):
                    roots.add(row['args'][1].strip('[] '))
                elif row['opcode'].startswith('ld.'):
                    # State is a direct ABI pointer in these registered kernels.
                    if re.search(r'(?:\.b|\.u|\.s)64$', row['opcode']):
                        roots.add('<indirect>')
                else:
                    for arg in row['args'][1:]:
                        pending.extend(
                            (reg, i)
                            for reg in re.findall(r'%[\w$]+(?:\.[xyz])?', arg))
        root_cache[key] = frozenset(roots)
        return root_cache[key]

    counts = Counter()
    site_counts = Counter()
    relevant = set()
    path_checked = set()
    for z in range(grid[2]):
        for y in range(grid[1]):
            for x in range(grid[0]):
                for thread in range(threads):
                    special = {
                        '%tid.x': thread,
                        '%tid.y': 0,
                        '%tid.z': 0,
                        '%ctaid.x': x,
                        '%ctaid.y': y,
                        '%ctaid.z': z,
                        '%ntid.x': threads,
                        '%ntid.y': 1,
                        '%ntid.z': 1,
                        '%nctaid.x': grid[0],
                        '%nctaid.y': grid[1],
                        '%nctaid.z': grid[2]
                    }
                    cache, active = {}, set()

                    def evaluate(token, before):
                        token = token.strip()
                        if token.startswith('!'):
                            return not evaluate(token[1:], before)
                        if token in special:
                            return special[token]
                        if re.fullmatch(r'-?(?:0x[0-9a-fA-F]+|\d+)', token):
                            return int(token,
                                       0) if 'x' in token else int(token)
                        key = token, before
                        if key in cache:
                            return cache[key]
                        _need(key not in active and len(active) < 256,
                              'Cyclic/deep State cone')
                        active.add(key)
                        reaching = reaching_definitions(token, before)
                        _need(
                            len(reaching) == 1 and None not in reaching,
                            'Ambiguous/undefined reaching State-cone definition'
                        )
                        i = next(iter(reaching))
                        _need(dominates(i, before),
                              'Non-dominating State-cone definition')
                        row = instructions[i]
                        _need(row['predicate'] is None,
                              'Predicated State-cone definition')
                        args, opcode = row['args'], row['opcode']
                        if opcode in ('ld.param.u64', 'ld.param.b64'):
                            name = args[1].strip('[] ')
                            _need(name in parameters,
                                  'Unknown parameter pointer')
                            value = Pointer(name)
                        else:
                            _need(
                                opcode in _ARITIES
                                and len(args) == _ARITIES[opcode] and
                                re.fullmatch(r'%[\w$]+', args[0]) is not None,
                                'Unsupported State cone opcode/modifiers/arity: '
                                + opcode)
                            values = [evaluate(arg, i) for arg in args[1:]]
                            if not opcode.startswith('cvt.'):
                                source_type = opcode.rsplit('.', 1)[1]
                                normalized = []
                                for operand, value in enumerate(values):
                                    if isinstance(value, Pointer):
                                        normalized.append(value)
                                        continue
                                    _need(isinstance(value, int),
                                          'Non-integer typed source')
                                    predicate_source = source_type == 'pred' or (
                                        opcode.startswith('selp.')
                                        and operand == 2)
                                    if predicate_source:
                                        _need(value in (0, 1),
                                              'Non-boolean predicate source')
                                        normalized.append(bool(value))
                                    else:
                                        bits = int(
                                            re.search(r'(32|64)$',
                                                      source_type)[1])
                                        if (opcode.startswith(
                                            ('shl.', 'shr.')) and operand == 1
                                            ) or (opcode.startswith('bfe.')
                                                  and operand > 0):
                                            bits = 32
                                        normalized.append(value
                                                          & ((1 << bits) - 1))
                                values = normalized
                            if opcode.startswith(('mov.', 'cvt.', 'cvta.')):
                                value = values[0]
                                _need(
                                    not isinstance(value, Pointer)
                                    or opcode in ('mov.u64', 'mov.b64',
                                                  'cvta.to.global.u64'),
                                    'Unsupported pointer conversion')
                                if isinstance(
                                        value,
                                        int) and opcode.startswith('cvt.'):
                                    conversion = re.fullmatch(
                                        r'cvt\.([us])(32|64)\.([us])(32|64)',
                                        opcode)
                                    _need(conversion,
                                          'Unsupported integer conversion')
                                    source_bits = int(conversion[4])
                                    value &= (1 << source_bits) - 1
                                    if conversion[3] == 's' and value & (
                                            1 << (source_bits - 1)):
                                        value -= 1 << source_bits
                            elif opcode.startswith(('add.', 'sub.')):
                                left, right = values
                                if opcode.startswith('sub.'):
                                    _need(
                                        type(right) is int,
                                        'Pointer subtraction')
                                    right = -right
                                if isinstance(left, Pointer):
                                    _need(
                                        type(right) is int
                                        and opcode.endswith('64'),
                                        'Mixed pointer arithmetic')
                                    right = ((right & ((1 << 64) - 1)) ^
                                             (1 << 63)) - (1 << 63)
                                    value = Pointer(left.parameter,
                                                    left.offset + right)
                                else:
                                    _need(
                                        type(left) is int
                                        and type(right) is int,
                                        'Mixed integer arithmetic')
                                    value = left + right
                            else:
                                _need(all(isinstance(v, int) for v in values),
                                      'Non-integer State cone')
                                if opcode.startswith('mul.'):
                                    if opcode == 'mul.wide.s32':
                                        values = [
                                            ((v & 0xffffffff) ^ 0x80000000) -
                                            0x80000000 for v in values
                                        ]
                                    value = values[0] * values[1]
                                elif opcode.startswith('mad.lo.'):
                                    value = values[0] * values[1] + values[2]
                                elif opcode.startswith('shl.'):
                                    bits = int(
                                        re.search(r'(32|64)$', opcode)[1])
                                    value = 0 if values[
                                        1] >= bits else values[0] << values[1]
                                elif opcode.startswith('shr.'):
                                    word = values[0]
                                    if '.s' in opcode:
                                        bits = int(
                                            re.search(r'(32|64)$', opcode)[1])
                                        word = ((word & ((1 << bits) - 1)) ^
                                                (1 <<
                                                 (bits - 1))) - (1 <<
                                                                 (bits - 1))
                                    bits = int(
                                        re.search(r'(32|64)$', opcode)[1])
                                    value = word >> min(values[1], bits)
                                elif opcode.startswith('and.'):
                                    value = values[0] & values[1]
                                elif opcode.startswith('or.'):
                                    value = values[0] | values[1]
                                elif opcode.startswith('xor.'):
                                    value = values[0] ^ values[1]
                                elif opcode.startswith('setp.'):
                                    suffix = opcode.split('.')
                                    left, right = values[:2]
                                    _need(
                                        suffix[-1] in ('u32', 's32', 'b32',
                                                       'u64', 's64', 'b64'),
                                        'Unsupported integer comparison')
                                    bits = int(
                                        re.search(r'(32|64)$', suffix[-1])[1])
                                    left &= (1 << bits) - 1
                                    right &= (1 << bits) - 1
                                    if suffix[-1].startswith('s'):
                                        signed = lambda v: (
                                            (v & ((1 << bits) - 1)) ^
                                            (1 << (bits - 1))) - (1 <<
                                                                  (bits - 1))
                                        left, right = signed(left), signed(
                                            right)
                                    value = {
                                        'eq': left == right,
                                        'ne': left != right,
                                        'lt': left < right,
                                        'le': left <= right,
                                        'gt': left > right,
                                        'ge': left >= right
                                    }[suffix[1]]
                                elif opcode.startswith('selp.'):
                                    value = values[0] if values[2] else values[
                                        1]
                                elif opcode.startswith('bfe.'):
                                    word, shift, width = values
                                    _need(
                                        0 <= shift < 32
                                        and 0 <= width <= 32 - shift,
                                        'Unsupported bitfield extent')
                                    value = (word >> shift) & (
                                        (1 << width) - 1)
                                    if '.s32' in opcode and width and value & (
                                            1 << (width - 1)):
                                        value -= 1 << width
                                else:
                                    raise ValueError(
                                        'Unsupported State cone opcode: ' +
                                        opcode)
                        if isinstance(value, int) and not isinstance(
                                value, bool) and not opcode.endswith('.pred'):
                            width = re.search(r'\.(?:b|u|s)(32|64)', opcode)
                            _need(width is not None,
                                  'Unknown integer result width')
                            bits = int(width[1]) * (
                                2 if opcode.startswith('mul.wide.') else 1)
                            value &= (1 << bits) - 1
                        active.remove(key)
                        cache[key] = value
                        return value

                    for i in stores:
                        row = instructions[i]
                        match = re.fullmatch(
                            r'\[\s*(%[\w$]+)\s*(?:\+\s*(-?\d+))?\s*\]',
                            row['args'][0])
                        _need(match, 'Unsupported global store address')
                        roots = pointer_roots(match[1], i)
                        _need(
                            roots
                            and not any(r.startswith('<') for r in roots),
                            'Global store has no unambiguous direct pointer parameter provenance'
                        )
                        if state not in roots:
                            continue
                        pointer = evaluate(match[1], i)
                        _need(isinstance(pointer, Pointer),
                              'Store has no parameter provenance')
                        if pointer.parameter != state:
                            continue
                        relevant.add(i)
                        if i not in path_checked:
                            _need(all(dominates(i, ret) for ret in returns),
                                  'State store can be bypassed')
                            # A State write may not be reached again before returning.
                            pending, seen = list(graph[i]), set()
                            while pending:
                                node = pending.pop()
                                _need(node != i,
                                      'State store is inside a loop')
                                if node not in seen:
                                    seen.add(node)
                                    pending.extend(graph[node])
                            path_checked.add(i)
                        if row['predicate'] and not evaluate(
                                row['predicate'], i):
                            continue
                        width = re.fullmatch(r'st\.global(?:\.v([24]))?\.b32',
                                             row['opcode'])
                        _need(width, 'Unsupported State store width')
                        address = pointer.offset + int(match[2] or 0)
                        _need(address % 4 == 0, 'Misaligned State store')
                        for lane in range(int(width[1] or 1)):
                            element = address // 4 + lane
                            _need(0 <= element < elements,
                                  'State store writes a guard/tail')
                            counts[element] += 1
                            site_counts[i] += 1
    _need(relevant, 'No State stores identified')
    _need(
        len(counts) == elements and all(v == 1 for v in counts.values()),
        'State partition has missing or duplicate physical writers')
    return dict(status='ptx_physical_state_writer_partition_checked',
                elements=elements,
                threads=threads,
                grid=grid,
                unique_writers=elements,
                stores=[
                    dict(instruction=i,
                         source_line=instructions[i]['source_line'],
                         opcode=instructions[i]['opcode'],
                         predicate=instructions[i]['predicate'],
                         writes=site_counts[i]) for i in sorted(relevant)
                ],
                native_sass_semantics_verified=False,
                device_executed=False)
