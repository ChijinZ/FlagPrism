"""Finite GCU LLVM-input State transfer ranges, not a native schedule proof.

Bind the unchanged LLVM-dialect input to its original binary and the actual
SDK transfer/launch ABI separately. Unknown State escapes, integer/address
cones or writer paths fail. Floating point and native scheduling are omitted.
"""
from collections import Counter
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Pointer:
    formal: str
    byte_offset: int = 0


@dataclass(frozen=True)
class ObserverPayloadAdmission:
    """Object-bound source/certificate admission supplied by the QA caller.

    The caller must check these hashes against the actual capture, source-use
    audit and checked before/after certificate. This record is not a signature,
    a substitute for those checks, or permission to ignore State transfers.
    """
    source_sha256: str
    before_sha256: str
    after_sha256: str
    certificate_sha256: str
    state_index: int

    def __post_init__(self):
        for digest in (self.source_sha256, self.before_sha256,
                       self.after_sha256, self.certificate_sha256):
            _need(
                type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest),
                'Observer admission requires actual object hashes')
        _need(
            type(self.state_index) is int and self.state_index >= 0,
            'Observer admission State index')


def _need(condition, message):
    if not condition:
        raise ValueError(message)


class UnknownCone(ValueError):
    """An integer value cannot be resolved by this finite interpreter."""


def _split(text):
    if not text.strip():
        return []
    parts, start, stack = [], 0, []
    pairs = {')': '(', ']': '[', '}': '{', '>': '<'}
    for i, char in enumerate(text):
        if char in '([{<':
            stack.append(char)
        elif char in ')]}>':
            _need(stack and stack.pop() == pairs[char],
                  'Unbalanced LLVM operand')
        elif char == ',' and not stack:
            parts.append(text[start:i].strip())
            start = i + 1
    _need(not stack, 'Unbalanced LLVM operand')
    parts.append(text[start:].strip())
    return parts


def _call(text):
    match = re.search(r'\bcall\s+.*?@([\w.$-]+)\(', text)
    _need(match, 'Unsupported indirect call')
    depth = 1
    start = match.end()
    for i in range(start, len(text)):
        depth += (text[i] == '(') - (text[i] == ')')
        if depth == 0:
            return match[1], _split(text[start:i])
    raise ValueError('Unterminated LLVM call')


def _value(typed):
    match = re.fullmatch(r'i(1|8|16|32|64)\s+(-?\d+|true|false|%[\w.$-]+)',
                         typed)
    _need(match, 'Unsupported typed integer operand: ' + typed)
    return int(match[1]), match[2]


def _signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _comment_free(line):
    quoted, escaped = False, False
    for i, char in enumerate(line):
        if char == ';' and not quoted:
            return line[:i]
        if char == '"' and not escaped:
            quoted = not quoted
        escaped = char == "\\" and not escaped
    return line


def _parse(text):
    lines = [_comment_free(line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    _need(2 < len(lines) <= 20000 and lines[-1] == '}',
          'Bounded single LLVM function')
    header = re.fullmatch(r'define\s+.*?@([\w.$-]+)\((.*)\)[^{]*\{', lines[0])
    _need(header, 'Missing single LLVM function')
    parameters = {}
    for item in _split(header[2]):
        match = re.fullmatch(
            r'(i\d+|ptr(?: addrspace\(\d+\))?)\s+(?:\w+\s+)*(%[\w.$-]+)', item)
        _need(match and match[2] not in parameters, 'Unsupported formal ABI')
        parameters[match[2]] = match[1]
    instructions, labels, definitions = [], {}, {}
    for line in lines[1:-1]:
        label = re.fullmatch(r'([\w.$-]+):', line)
        if label:
            _need(label[1] not in labels, 'Duplicate LLVM label')
            labels[label[1]] = len(instructions)
            continue
        match = re.fullmatch(r'(?:(%[\w.$-]+)\s*=\s*)?(.+)', line)
        result, operation = match.groups()
        _need(
            not operation.startswith(
                ('switch ', 'indirectbr ', 'invoke ', 'callbr ', 'catch',
                 'resume ', 'unreachable')), 'Unsupported LLVM control')
        index = len(instructions)
        if result:
            _need(result not in definitions and result not in parameters,
                  'Non-SSA definition')
            definitions[result] = index
        instructions.append(dict(result=result, operation=operation))
    _need(instructions, 'Empty LLVM body')
    graph, branches = {}, {}
    for i, row in enumerate(instructions):
        op = row['operation']
        if op.startswith('br '):
            targets = re.findall(r'label %([\w.$-]+)', op)
            _need(targets and all(t in labels for t in targets),
                  'Unknown LLVM branch target')
            _need(len(targets) in (1, 2), 'Unsupported LLVM branch')
            graph[i] = tuple(labels[t] for t in targets)
            if len(targets) == 2:
                match = re.match(r'br i1 (%[\w.$-]+|true|false), label ', op)
                _need(match, 'Unsupported LLVM conditional branch')
                branches[i] = match[1]
        elif op == 'ret void':
            graph[i] = ()
        else:
            _need(not op.startswith('ret '), 'Nonvoid kernel return')
            graph[i] = (i + 1, )
        _need(all(t < len(instructions) for t in graph[i]),
              'LLVM falls out of function')
    return parameters, instructions, definitions, graph, branches


def analyze(function_ir,
            *,
            state_parameter,
            grid,
            threads,
            elements,
            observer_admission=None):
    _need(type(elements) is int and 0 < elements <= 1 << 20, 'State extent')
    _need(type(threads) is int and 0 < threads <= 64, 'Physical thread extent')
    _need(
        1 <= len(grid) <= 3
        and all(type(x) is int and 0 < x < 1 << 31 for x in grid),
        'Grid extent')
    grid = tuple(grid) + (1, ) * (3 - len(grid))
    _need(grid[0] * grid[1] * grid[2] * threads <= 1 << 20,
          'Enumeration bound')
    params, rows, defs, graph, branches = _parse(function_ir)
    _need(params.get(state_parameter) == 'ptr', 'Actual State formal ABI')
    if observer_admission is not None:
        _need(
            isinstance(observer_admission, ObserverPayloadAdmission)
            and observer_admission.state_index
            == list(params).index(state_parameter),
            'Object-bound observer admission State formal differs')

    def reach(edges, start=0, stop=None):
        seen, todo = set(), [start]
        while todo:
            at = todo.pop()
            if at == stop or at in seen:
                continue
            seen.add(at)
            todo.extend(edges[at])
        return seen

    reachable = reach(graph)
    returns = {i for i in reachable if rows[i]['operation'] == 'ret void'}
    _need(returns, 'No reachable return')
    dom = {}

    def dominates(index, use):
        if (index, use) not in dom:
            dom[index, use] = use not in reach(graph, stop=index)
        return dom[index, use]

    deps = {}
    for name, at in defs.items():
        op = rows[at]['operation']
        deps[name] = set() if op.startswith('load ') else set(
            re.findall(r'\[\s*(%[\w.$-]+)\s*,', op)) if op.startswith(
                'phi ') else set(re.findall(r'%[\w.$-]+', op)) & (
                    set(defs) | set(params))
    roots_cache = {}

    def roots(name):
        if name not in roots_cache:
            found, seen, todo = set(), set(), [name]
            while todo:
                at = todo.pop()
                if at in seen: continue
                seen.add(at)
                if at in params and params[at].startswith('ptr'): found.add(at)
                todo.extend(deps.get(at, ()))
            roots_cache[name] = found
        return roots_cache[name]

    def has_state(operand):
        return any(state_parameter in roots(x)
                   for x in re.findall(r'%[\w.$-]+', operand))

    # Only the two address-word projections emitted by the checked observer
    # are data. Direct SSA uses may only produce the next word projection or
    # enter a positively identified private store. This is not memory taint:
    # subsequent ring loads/uses are covered by the independently bound whole
    # high-IR observer isolation certificate, not by this LLVM use check.
    # The source audit separately excludes original user address payloads.
    projections = set()
    if observer_admission is not None:
        for row in rows:
            op = row['operation']
            match = re.fullmatch(
                r'(?:trunc i64 (%[\w.$-]+) to i32|'
                r'lshr i64 (%[\w.$-]+), 32)', op)
            if match and state_parameter in roots(match[1] or match[2]):
                projections.add(row['result'])

    private_cache = {}

    def private_destination(value, active=None):
        if value in private_cache:
            return private_cache[value]
        active = set() if active is None else active
        if value not in defs or value in active:
            return False
        active.add(value)
        op = rows[defs[value]]['operation']
        result = bool(
            re.fullmatch(r'call ptr @tops_get_(?:local|shared)_memory\(\)',
                         op))
        result |= op.startswith('alloca ')
        base = None
        if op.startswith('getelementptr '):
            args = _split(
                op.removeprefix('getelementptr ').removeprefix('inbounds '))
            match = re.fullmatch(r'ptr(?: addrspace\(\d+\))? (%[\w.$-]+)',
                                 args[1]) if len(args) >= 2 else None
            if match:
                base = match[1]
        else:
            match = re.fullmatch(
                r'(?:addrspacecast|bitcast) ptr(?: addrspace\(\d+\))? '
                r'(%[\w.$-]+) to ptr(?: addrspace\(\d+\))?', op)
            if match:
                base = match[1]
        if base is not None:
            result = private_destination(base, active)
        active.remove(value)
        private_cache[value] = result
        return result

    calls, writers = {}, []
    transfer_abi = {
        'tops_memcpy_async': (4, 2),
        'tops_deslice_async_1_si32': (6, 3),
        'tops_slice_deslice_async_1_si32': (8, 3),
        'tops_deslice_async_2_si32': (9, 4),
        'tops_slice_deslice_async_2_si32': (13, 4),
        'tops_slice_async_1_si32': (7, 3),
        'tops_slice_async_2_si32': (10, 4),
        'tops_slice_pad_async_1_si32': (8, 3),
        'tops_slice_pad_async_2_si32': (12, 4)
    }
    for at in reachable:
        op = rows[at]['operation']
        projected = projections & set(re.findall(r'%[\w.$-]+', op))
        if rows[at]['result'] in projections:
            continue
        if projected:
            store = re.fullmatch(
                r'store i32 (%[\w.$-]+), '
                r'ptr (%[\w.$-]+)(?:, align \d+)?', op)
            _need(
                store and store[1] in projections and not roots(store[2])
                and private_destination(store[2]),
                'Observer address payload used outside private data store')
            continue
        if op.startswith('load '):
            operands = _split(op.removeprefix('load '))
            if re.search(r'\bptr\b', operands[0]):
                _need(
                    not any(
                        roots(t)
                        for t in re.findall(r'%[\w.$-]+', operands[1])),
                    'Pointer loaded from external formal memory')
        if rows[at]['result'] and re.search(r'\bcall\b[^@]*\bptr\b',
                                            op.split('@', 1)[0]):
            name, _ = _call(op)
            _need(name in ('tops_get_local_memory', 'tops_get_shared_memory'),
                  'Unknown pointer-returning helper')
        _need(not re.search(r'\binttoptr\s*\(', op),
              'Unmodeled constant-expression pointer')
        if op.startswith('inttoptr '):
            _need(bool(roots(rows[at]['result'])),
                  'Constructed pointer lacks a formal origin')
        if re.search(r'\bcall\b.*@[\w.$-]+\(', op):
            name, arguments = _call(op)
            calls[at] = name, arguments
            state_args = {i for i, x in enumerate(arguments) if has_state(x)}
            if not state_args: continue
            _need(name in transfer_abi, 'Unmodeled State callee: ' + name)
            size, source_index = transfer_abi[name]
            _need(
                len(arguments) == size and state_args <= {1, source_index},
                'State transfer escape/ABI')
            if 1 in state_args:
                _need(
                    source_index not in state_args and not name.startswith(
                        ('tops_slice_async_', 'tops_slice_pad_async_')),
                    'Unmodeled State destination transfer')
                writers.append((at, name, arguments))
        elif has_state(op):
            if op.startswith('store '):
                args = _split(op.removeprefix('store '))
                _need(not has_state(args[0]),
                      'State pointer escapes to memory')
                _need(False, 'Unmodeled direct State store')
            _need(
                op.startswith(('ptrtoint ', 'inttoptr ', 'getelementptr ',
                               'add ', 'sub ')) or re.match(r'load i\d+,', op),
                'Unmodeled State instruction')
    counts, instances = Counter(), []
    for z in range(grid[2]):
        for y in range(grid[1]):
            for x in range(grid[0]):
                for thread in range(threads):
                    values = {
                        p: Pointer(p)
                        for p, ty in params.items() if ty.startswith('ptr')
                    }
                    active = set()

                    def evaluate(token, use):
                        if token in ('true', 'false'):
                            return int(token == 'true')
                        if re.fullmatch(r'-?\d+', token): return int(token)
                        _need(token in params or token in defs,
                              'Unknown SSA definition: ' + token)
                        if token in defs:
                            _need(dominates(defs[token], use),
                                  'Address definition does not dominate use')
                        if token in values: return values[token]
                        if token in active: raise UnknownCone('Cyclic cone')
                        _need(token in defs, 'Unmodeled scalar parameter')
                        active.add(token)
                        try:
                            value = operation(rows[defs[token]]['operation'],
                                              defs[token])
                        finally:
                            active.remove(token)
                        values[token] = value
                        return value

                    def integer(arg, use, signed=False):
                        bits, token = _value(arg)
                        value = evaluate(token, use)
                        _need(type(value) is int, 'Expected integer')
                        return _signed(value, bits) if signed else value & (
                            (1 << bits) - 1)

                    def pointer(arg, use):
                        m = re.fullmatch(
                            r'ptr(?: addrspace\(\d+\))? (%[\w.$-]+)', arg)
                        _need(m, 'Pointer operand ABI')
                        value = evaluate(m[1], use)
                        _need(isinstance(value, Pointer),
                              'Pointer origin lost')
                        return value

                    def operation(op, use):
                        if use in calls:
                            name, args = calls[use]
                            if name in ('tops_get_thread_id',
                                        'tops_get_block_id'):
                                _need(len(args) == 1, 'Getter ABI')
                                axis = integer(args[0], use)
                                _need(axis in (0, 1, 2), 'Getter dimension')
                                return ((thread, 0, 0)
                                        if name == 'tops_get_thread_id' else
                                        (x, y, z))[axis]
                            if name in ('tops_get_local_memory',
                                        'tops_get_shared_memory'):
                                _need(not args, 'Local base ABI')
                                return Pointer('@' + name)
                            if name == 'tops_extsi_si32_to_si64':
                                _need(
                                    len(args) == 1
                                    and _value(args[0])[0] == 32,
                                    'Extension ABI')
                                return integer(args[0], use, signed=True) & (
                                    (1 << 64) - 1)
                            if name in ('tops_minsi_si32', 'tops_maxsi_si32',
                                        'tops_remsi_si32', 'tops_divsi_si32',
                                        'tops_floordivsi_si32'):
                                _need(
                                    len(args) == 2
                                    and all(_value(a)[0] == 32 for a in args),
                                    'Integer helper ABI')
                                a, b = [
                                    integer(v, use, signed=True) for v in args
                                ]
                                if name == 'tops_minsi_si32':
                                    return min(a, b) & 0xffffffff
                                if name == 'tops_maxsi_si32':
                                    return max(a, b) & 0xffffffff
                                _need(
                                    b != 0
                                    and not (a == -(1 << 31) and b == -1),
                                    'Poison division')
                                q = (abs(a) //
                                     abs(b)) * (-1 if
                                                (a < 0) != (b < 0) else 1)
                                return (a - q * b
                                        if name == 'tops_remsi_si32' else a //
                                        b if name == 'tops_floordivsi_si32'
                                        else q) & 0xffffffff
                            raise UnknownCone('Unmodeled integer helper: ' +
                                              name)
                        m = re.fullmatch(
                            r'ptrtoint (ptr(?: addrspace\(\d+\))? %[^ ]+) to i64',
                            op)
                        if m: return pointer(m[1], use)
                        m = re.fullmatch(r'inttoptr i64 (%[^ ]+) to ptr', op)
                        if m:
                            v = evaluate(m[1], use)
                            _need(isinstance(v, Pointer),
                                  'Constructed pointer lacks origin')
                            return v
                        m = re.fullmatch(
                            r'(sext|zext|trunc) (i\d+ .+) to i(\d+)', op)
                        if m:
                            return integer(m[2], use, signed=m[1]
                                           == 'sext') & ((1 << int(m[3])) - 1)
                        m = re.fullmatch(
                            r'getelementptr(?: inbounds)? (i8|i16|i32|i64|half|float), (ptr(?: addrspace\(\d+\))? %[^,]+), (i\d+ .+)',
                            op)
                        if m:
                            base = pointer(m[2], use)
                            size = {
                                'i8': 1,
                                'i16': 2,
                                'half': 2,
                                'i32': 4,
                                'float': 4,
                                'i64': 8
                            }[m[1]]
                            offset = integer(m[3], use, signed=True) * size
                            value = Pointer(base.formal,
                                            base.byte_offset + offset)
                            if 'inbounds' in op and base.formal == state_parameter:
                                _need(
                                    0 <= base.byte_offset <= elements * 4
                                    and 0 <= value.byte_offset <= elements * 4,
                                    'Poison inbounds State pointer')
                            return value
                        m = re.fullmatch(
                            r'icmp (eq|ne|slt|sle|sgt|sge|ult|ule|ugt|uge) (i\d+) ([^,]+), (.+)',
                            op)
                        if m:
                            kind, ty, a, b = m.groups()
                            a, b = integer(
                                ty + ' ' + a, use,
                                signed=kind.startswith('s')), integer(
                                    ty + ' ' + b,
                                    use,
                                    signed=kind.startswith('s'))
                            kind = kind if kind in ('eq', 'ne') else kind[1:]
                            return int({
                                'eq': a == b,
                                'ne': a != b,
                                'lt': a < b,
                                'le': a <= b,
                                'gt': a > b,
                                'ge': a >= b
                            }[kind])
                        m = re.fullmatch(
                            r'(add|sub|mul|and|or|xor|sdiv|udiv|srem|urem)((?: (?:nsw|nuw|exact))*) (i\d+) ([^,]+), (.+)',
                            op)
                        if m:
                            kind, flags, ty, a, b = m.groups()
                            bits = int(ty[1:])
                            av, bv = evaluate(a, use), evaluate(b, use)
                            if isinstance(av, Pointer) or isinstance(
                                    bv, Pointer):
                                _need(
                                    bits == 64 and not flags
                                    and kind in ('add', 'sub'),
                                    'Unmodeled pointer integer operation')
                                _need(
                                    isinstance(av, Pointer)
                                    and type(bv) is int,
                                    'Ambiguous pointer arithmetic')
                                return Pointer(
                                    av.formal, av.byte_offset +
                                    (_signed(bv, bits)
                                     if kind == 'add' else -_signed(bv, bits)))
                            a, b = integer(ty + ' ' + a,
                                           use), integer(ty + ' ' + b, use)
                            if kind in ('add', 'sub', 'mul'):
                                value = {
                                    'add': a + b,
                                    'sub': a - b,
                                    'mul': a * b
                                }[kind]
                                if 'nuw' in flags:
                                    _need(0 <= value < 1 << bits,
                                          'Poison unsigned arithmetic')
                                if 'nsw' in flags:
                                    sa, sb = _signed(a, bits), _signed(b, bits)
                                    v = {
                                        'add': sa + sb,
                                        'sub': sa - sb,
                                        'mul': sa * sb
                                    }[kind]
                                    _need(
                                        -(1 << (bits - 1)) <= v < 1 <<
                                        (bits - 1), 'Poison signed arithmetic')
                            elif kind in ('and', 'or', 'xor'):
                                _need(not flags, 'Unmodeled bit flags')
                                value = {
                                    'and': a & b,
                                    'or': a | b,
                                    'xor': a ^ b
                                }[kind]
                            else:
                                if kind.startswith('s'):
                                    a, b = _signed(a, bits), _signed(b, bits)
                                _need(
                                    b != 0
                                    and not (kind in ('sdiv', 'srem') and a
                                             == -(1 <<
                                                  (bits - 1)) and b == -1),
                                    'Poison division')
                                q = (abs(a) //
                                     abs(b)) * (-1 if
                                                (a < 0) != (b < 0) else 1)
                                rem = a - q * b
                                _need('exact' not in flags or rem == 0,
                                      'Poison inexact division')
                                value = q if kind.endswith('div') else rem
                            return value & ((1 << bits) - 1)
                        raise UnknownCone(
                            'Unsupported integer/address cone: ' + op[:100])

                    edges = dict(graph)
                    for at, condition in branches.items():
                        try:
                            choice = integer('i1 ' + condition, at)
                        except UnknownCone:
                            continue
                        edges[at] = (graph[at][0 if choice else 1], )
                    live = reach(edges)
                    _need(returns & live, 'No reachable actor return')
                    for at, name, args in writers:
                        if at not in live: continue
                        _need(not (returns & reach(edges, stop=at)),
                              'State writer may be bypassed')
                        _need(
                            all(at not in reach(edges, start=t)
                                for t in edges[at]),
                            'State writer repeats in loop')
                        dest = pointer(args[1], at)
                        _need(
                            dest.formal == state_parameter
                            and dest.byte_offset % 4 == 0,
                            'State destination origin/alignment')
                        origin = dest.byte_offset // 4
                        if name == 'tops_memcpy_async':
                            length = integer(args[3], at, signed=True)
                            _need(
                                0 <= length <= 4 * (1 << 20)
                                and length % 4 == 0, 'State byte copy extent')
                            indices = list(range(origin, origin + length // 4))
                            descriptor = dict(bytes=length)
                        else:
                            dims = 2 if '_2_' in name else 1
                            source_index = 4 if dims == 2 else 3
                            dshape = [
                                integer(v, at, signed=True)
                                for v in args[2:2 + dims]
                            ]
                            sshape = [
                                integer(v, at, signed=True)
                                for v in args[source_index + 1:source_index +
                                              1 + dims]
                            ]
                            if name.startswith('tops_slice_deslice_'):
                                start = source_index + 1 + dims
                                soff = [
                                    integer(v, at, signed=True)
                                    for v in args[start:start + dims]
                                ]
                                size = [
                                    integer(v, at, signed=True)
                                    for v in args[start + dims:start +
                                                  2 * dims]
                                ]
                                doff = [
                                    integer(v, at, signed=True)
                                    for v in args[start + 2 * dims:start +
                                                  3 * dims]
                                ]
                            else:
                                soff = [0] * dims
                                doff = [
                                    integer(v, at, signed=True)
                                    for v in args[source_index + 1 +
                                                  dims:source_index + 1 +
                                                  2 * dims]
                                ]
                                size = sshape
                            _need(
                                all(0 <= v <= 1 << 20
                                    for v in dshape + sshape + size + soff +
                                    doff), 'State transfer shape/offset bound')
                            _need(
                                all(doff[d] <= dshape[d]
                                    and soff[d] <= sshape[d]
                                    for d in range(dims)),
                                'State source/destination window origin')
                            lo = [0] * dims
                            hi = [
                                min(size[d], dshape[d] - doff[d])
                                for d in range(dims)
                            ]
                            if name == 'tops_deslice_async_2_si32':
                                _need(
                                    all(doff[d] + sshape[d] <= dshape[d]
                                        for d in range(dims)),
                                    'Unclipped 2D destination window')
                                hi = sshape
                            _need(
                                all(soff[d] + hi[d] <= sshape[d]
                                    for d in range(dims)),
                                'State source window exceeds shape')
                            _need((hi[0] - lo[0]) *
                                  (hi[1] - lo[1] if dims == 2 else 1)
                                  <= 1 << 20, 'Transfer enumeration bound')
                            indices = [
                                origin + (doff[0] + i) *
                                (dshape[1] if dims == 2 else 1) +
                                (doff[1] + j if dims == 2 else 0)
                                for i in range(lo[0], hi[0])
                                for j in (range(lo[1], hi[1]) if dims ==
                                          2 else range(1))
                            ]
                            descriptor = dict(destination_shape=dshape,
                                              source_shape=sshape,
                                              source_offset=soff,
                                              destination_offset=doff,
                                              size=size)
                        for element in indices:
                            _need(0 <= element < elements,
                                  'State write exceeds allocation')
                            counts[element] += 1
                            _need(counts[element] == 1,
                                  'Overlapping physical State writers')
                        instances.append(
                            dict(block=[x, y, z],
                                 thread=thread,
                                 instruction=at,
                                 primitive=name,
                                 destination_element_base=origin,
                                 elements=len(indices),
                                 descriptor=descriptor))
    return dict(element_writers=dict(counts),
                write_instances=instances,
                native_schedule_verified=False,
                SDK_transfer_ABI_verified=False)
