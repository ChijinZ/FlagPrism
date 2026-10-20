"""Finite State write-range analysis of actual Ascend kernel LLVM callers.

The caller must bind this LLVM to the executed object, its launch/actor ABI,
State formal, and the inspected int32 memref-transfer implementations. This
module enumerates those physical scalar actors and their logical GM write
ranges. It does not interpret floating-point math, native scheduling, or
arbitrary SDK calls. Unknown State escapes, address cones and control fail.
"""
from collections import Counter
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Pointer:
    formal: str
    byte_offset: int = 0


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


def _parse(text):
    lines = [line.split(';', 1)[0].strip() for line in text.splitlines()]
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


def analyze(function_ir, *, state_parameter, grid_parameters, grid, subblocks,
            elements):
    """Return element-index multiplicities for one actual actor function.

    `subblocks` is the independently established count of this scalar actor
    per logical block, not a value inferred from missing trace slots.
    """
    _need(
        type(elements) is int and 0 < elements <= (1 << 20),
        'State element extent')
    _need(
        type(subblocks) is int and subblocks in (1, 2),
        'Unverified actor extent')
    _need(
        1 <= len(grid) <= 3
        and all(type(x) is int and 0 < x < (1 << 31) for x in grid),
        'Launch grid')
    grid = tuple(grid) + (1, ) * (3 - len(grid))
    total = grid[0] * grid[1] * grid[2]
    _need(total * subblocks <= (1 << 20), 'Actor enumeration bound')
    parameters, rows, definitions, graph, branches = _parse(function_ir)
    _need(
        parameters.get(state_parameter) == 'ptr addrspace(1)',
        'State formal must be the actual GM pointer')
    _need(
        len(grid_parameters) == 3 and len(set(grid_parameters)) == 3
        and all(parameters.get(p) == 'i32' for p in grid_parameters),
        'Actual grid ABI')
    _need(state_parameter not in grid_parameters, 'Aliased State/grid ABI')

    def reach(edges, start=0, stop=None):
        seen, todo = set(), [start]
        while todo:
            node = todo.pop()
            if node == stop or node in seen:
                continue
            seen.add(node)
            todo.extend(edges[node])
        return seen

    full_reachable = reach(graph)
    returns = {i for i in full_reachable if rows[i]['operation'] == 'ret void'}
    _need(returns, 'No reachable LLVM return')
    dominance = {}

    def dominates(definition, use):
        key = definition, use
        if key not in dominance:
            dominance[key] = use not in reach(graph, stop=definition)
        return dominance[key]

    # Whole dependency closure, not a partially cached recursion through phi
    # cycles. A load's integer value is not its source pointer's address.
    dependencies = {}
    for name, index in definitions.items():
        op = rows[index]['operation']
        if op.startswith('load ') or '@llvm.hivm.LD.DEV.' in op:
            dependencies[name] = set()
        elif op.startswith('phi '):
            dependencies[name] = set(re.findall(r'\[\s*(%[\w.$-]+)\s*,', op))
        else:
            dependencies[name] = set(re.findall(
                r'%[\w.$-]+', op)) & (set(definitions) | set(parameters))
    root_cache = {}

    def roots(token):
        if token not in root_cache:
            result, seen, todo = set(), set(), [token]
            while todo:
                current = todo.pop()
                if current in seen:
                    continue
                seen.add(current)
                if current in parameters and parameters[current].startswith(
                        'ptr'):
                    result.add(current)
                todo.extend(dependencies.get(current, ()))
            root_cache[token] = frozenset(result)
        return root_cache[token]

    def operand_roots(operand):
        answer = set()
        for token in re.findall(r'%[\w.$-]+', operand):
            answer.update(roots(token))
        return answer

    writers, calls = [], {}
    for index in full_reachable:
        op = rows[index]['operation']
        _need(
            not re.search(
                r'\bload (?:volatile )?ptr\b|\binttoptr\s+(?:\(\s*)?i\d+\s+[^()]+?\s+to ptr addrspace\(1\)|\bcall ptr\b',
                op), 'Unmodeled loaded/constructed/returned pointer')
        if re.search(r'\bcall\b', op):
            name, arguments = _call(op)
            calls[index] = name, arguments
            state_uses = {
                j
                for j, argument in enumerate(arguments)
                if state_parameter in operand_roots(argument)
            }
            if not state_uses:
                continue
            match = re.fullmatch(r'store_ubuf_to_gm_([12])d_int32_t', name)
            if match:
                dims = int(match[1])
                base = 5 if dims == 1 else 7
                _need(
                    len(arguments) == (11 if dims == 1 else 15)
                    and state_uses == {base, base + 1},
                    'Unexpected State transfer ABI/escape')
                _need(arguments[-1] == 'i32 0',
                      'Unverified State transfer mode')
                writers.append((index, dims, arguments, base))
            elif re.fullmatch(r'load_gm_to_ubuf_[12]d_int32_t', name):
                _need(state_uses == {0, 1},
                      'State escapes through readback destination')
            elif name == 'llvm.hivm.LD.DEV.u32.GM':
                _need(state_uses == {0},
                      'State escapes through scalar load offset')
            elif name in ('llvm.dbg.value', 'llvm.dbg.declare',
                          'llvm.dbg.assign'):
                pass
            else:
                raise ValueError('Unmodeled call receives State: ' + name)
        elif op.startswith('store '):
            operands = _split(op.removeprefix('store '))
            _need(state_parameter not in operand_roots(operands[0]),
                  'State pointer escapes through memory')
            _need(state_parameter not in operand_roots(operands[1]),
                  'Unmodeled direct State store')
        elif state_parameter in operand_roots(op):
            _need(
                op.startswith('getelementptr ')
                or re.match(r'load (?:volatile )?i\d+,', op),
                'Unmodeled instruction uses State address')
    counts, instances, solved_actors = Counter(), [], 0
    for block in range(total):
        for subblock in range(subblocks):
            values = {p: value for p, value in zip(grid_parameters, grid)}
            values.update({
                p: Pointer(p)
                for p, ty in parameters.items() if ty.startswith('ptr')
            })
            active = set()

            def integer(typed, use):
                bits, token = _value(typed)
                result = evaluate(token, use)
                _need(
                    type(result) is int,
                    'Integer address cone contains a pointer')
                return result & ((1 << bits) - 1)

            def evaluate(token, use):
                if token in ('true', 'false'):
                    return int(token == 'true')
                if re.fullmatch(r'-?\d+', token):
                    return int(token)
                if token in definitions:
                    _need(dominates(definitions[token], use),
                          'Address definition does not dominate use')
                if token in values:
                    return values[token]
                _need(token in definitions,
                      'Unknown integer definition: ' + token)
                if token in active:
                    raise UnknownCone('Cyclic integer cone: ' + token)
                index = definitions[token]
                _need(dominates(index, use),
                      'Address definition does not dominate use')
                active.add(token)
                try:
                    result = operation(rows[index]['operation'], index)
                finally:
                    active.remove(token)
                values[token] = result
                return result

            def pointer(operand, use):
                match = re.fullmatch(r'ptr addrspace\(1\) (%[\w.$-]+)',
                                     operand)
                _need(match, 'Unsupported GM pointer operand')
                result = evaluate(match[1], use)
                _need(isinstance(result, Pointer),
                      'GM pointer lost its formal origin')
                return result

            def operation(op, use):
                if re.search(r'\bcall\b', op):
                    name, arguments = calls[use]
                    if arguments:
                        raise UnknownCone('Unknown integer helper arguments')
                    if name == 'llvm.hivm.GET.BLOCK.IDX':
                        return block
                    if name == 'llvm.hivm.GET.SUBBLOCKID':
                        return subblock
                    raise UnknownCone('Unmodeled integer helper: ' + name)
                match = re.fullmatch(r'(sext|zext|trunc) (i\d+ .+) to i(\d+)',
                                     op)
                if match:
                    bits, _ = _value(match[2])
                    value = integer(match[2], use)
                    if match[1] == 'sext':
                        value = _signed(value, bits)
                    return value & ((1 << int(match[3])) - 1)
                match = re.fullmatch(r'select i1 (.+), (i\d+ .+), (i\d+ .+)',
                                     op)
                if match:
                    chosen = match[2] if integer('i1 ' +
                                                 match[1], use) else match[3]
                    return integer(chosen, use)
                match = re.fullmatch(
                    r'icmp (eq|ne|slt|sle|sgt|sge|ult|ule|ugt|uge) (i\d+) ([^,]+), (.+)',
                    op)
                if match:
                    bits = int(match[2][1:])
                    left = integer(match[2] + ' ' + match[3], use)
                    right = integer(match[2] + ' ' + match[4], use)
                    kind = match[1]
                    if kind.startswith('s'):
                        left, right = _signed(left, bits), _signed(right, bits)
                    comparison = kind if kind in ('eq', 'ne') else kind[1:]
                    return int({
                        'eq': left == right,
                        'ne': left != right,
                        'lt': left < right,
                        'le': left <= right,
                        'gt': left > right,
                        'ge': left >= right
                    }[comparison])
                match = re.fullmatch(
                    r'(add|sub|mul|sdiv|udiv|srem|urem|and|or|xor|shl|lshr|ashr)((?: (?:nsw|nuw|exact))*) (i\d+) ([^,]+), (.+)',
                    op)
                if match:
                    kind, flags, ty, x, y = match.groups()
                    bits = int(ty[1:])
                    left = integer(ty + ' ' + x, use)
                    right = integer(ty + ' ' + y, use)
                    a, b = (_signed(left, bits), _signed(
                        right,
                        bits)) if kind.startswith('s') or kind == 'ashr' else (
                            left, right)
                    if kind in ('add', 'sub', 'mul'):
                        result = {
                            'add': left + right,
                            'sub': left - right,
                            'mul': left * right
                        }[kind]
                        if 'nuw' in flags:
                            _need(0 <= result < (1 << bits),
                                  'Unsigned poison arithmetic')
                        if 'nsw' in flags:
                            sa, sb = _signed(left, bits), _signed(right, bits)
                            signed_result = {
                                'add': sa + sb,
                                'sub': sa - sb,
                                'mul': sa * sb
                            }[kind]
                            _need(
                                -(1 << (bits - 1)) <= signed_result <
                                (1 << (bits - 1)), 'Signed poison arithmetic')
                    elif kind in ('sdiv', 'udiv', 'srem', 'urem'):
                        _need(
                            b != 0
                            and not (kind == 'sdiv' and a == -(1 << (bits - 1))
                                     and b == -1), 'Poison integer division')
                        quotient = (abs(a) //
                                    abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
                        remainder = a - quotient * b
                        _need('exact' not in flags or remainder == 0,
                              'Inexact division')
                        result = quotient if kind.endswith(
                            'div') else remainder
                    elif kind in ('and', 'or', 'xor'):
                        result = {
                            'and': left & right,
                            'or': left | right,
                            'xor': left ^ right
                        }[kind]
                    else:
                        _need(right < bits and not flags,
                              'Unmodeled/poison shift')
                        result = left << right if kind == 'shl' else a >> right
                    return result & ((1 << bits) - 1)
                match = re.fullmatch(
                    r'getelementptr(?: inbounds)? i32, (ptr addrspace\(1\) %[^,]+), (i\d+ .+)',
                    op)
                if match:
                    base = pointer(match[1], use)
                    bits, _ = _value(match[2])
                    offset = _signed(integer(match[2], use), bits)
                    result = Pointer(base.formal,
                                     base.byte_offset + offset * 4)
                    if 'getelementptr inbounds ' in op and result.formal == state_parameter:
                        _need(
                            0 <= base.byte_offset <= elements * 4
                            and 0 <= result.byte_offset <= elements * 4,
                            'Poison inbounds State pointer')
                    return result
                raise UnknownCone('Unsupported integer/pointer cone: ' +
                                  op[:100])

            edges = dict(graph)
            for index, condition in branches.items():
                try:
                    selected = integer('i1 ' + condition, index)
                except UnknownCone:
                    continue
                edges[index] = (graph[index][0 if selected else 1], )
            reachable = reach(edges)
            _need(returns & reachable, "No reachable actor return")
            for index, dims, arguments, base in writers:
                if index not in reachable:
                    continue
                _need(not (returns & reach(edges, stop=index)),
                      'State writer may be bypassed')
                _need(
                    all(index not in reach(edges, start=t)
                        for t in edges[index]),
                    'State writer repeats in a loop')
                first, aligned = pointer(arguments[base], index), pointer(
                    arguments[base + 1], index)
                _need(
                    first == aligned and aligned.formal == state_parameter
                    and aligned.byte_offset % 4 == 0,
                    'Aliased/unaligned State descriptor')
                offset_bits, _ = _value(arguments[base + 2])
                offset = _signed(integer(arguments[base + 2], index),
                                 offset_bits) + aligned.byte_offset // 4
                sizes = [
                    integer(arguments[base + 3 + i], index)
                    for i in range(dims)
                ]
                strides = [
                    integer(arguments[base + 3 + dims + i], index)
                    for i in range(dims)
                ]
                _need(
                    all(0 <= n <= (1 << 20) for n in sizes)
                    and all(0 < n <= (1 << 30) for n in strides),
                    'Unverified State transfer extent/stride')
                extent = sizes[0] * (sizes[1] if dims == 2 else 1)
                _need(
                    extent <= (1 << 20)
                    and sum(counts.values()) + extent <= (1 << 22),
                    'State enumeration bound')
                for y in range(sizes[0]):
                    for x in range(sizes[1] if dims == 2 else 1):
                        element = offset + y * strides[0] + (x * strides[1] if
                                                             dims == 2 else 0)
                        _need(0 <= element < elements,
                              'State write exceeds its actual allocation')
                        counts[element] += 1
                        _need(counts[element] == 1,
                              'Overlapping physical State writers')
                instances.append(
                    dict(block=block,
                         subblock=subblock,
                         instruction=index,
                         element_offset=offset,
                         sizes=sizes,
                         strides=strides))
            solved_actors += 1
    return dict(actor_instances=solved_actors,
                write_instances=instances,
                element_writers=dict(counts),
                interpreted_floating_point=False,
                native_schedule_verified=False)
