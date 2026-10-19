"""Qualification-only finite native register cones; no device execution.

These helpers consume object-bound instructions from the installed reader.
They check actual uses rather than physical register names over a function.
They do not certify memory aliasing, complete scheduling or engine activity.
Unknown register writers and control transitions fail closed. Register roots
left undefined at function entry also remain unverified. A separate, bounded
negative result excludes paths from this function's matrix/clock definitions;
external entry symbols do not become definitions made by this function. This
never excludes through-memory, implicit scoreboard or physical completion edges.
"""
from collections import deque
import re

from flagtree.profiler.timeline_nvidia_late_values import (_predecessors,
                                                           _destinations,
                                                           _predicate)

REG = re.compile(r'(?<![A-Za-z0-9_])(?:UR|UP|R|P)\d+(?![A-Za-z0-9_])')


def registers(text):
    values = set(REG.findall(text))
    for prefix, index in re.findall(r'(?<![A-Za-z0-9_])(UR|R)(\d+)\.64', text):
        values.add(prefix + str(int(index) + 1))
    return values


def sources(row):
    op = row['opcode']
    fields = [s.strip() for s in row.get('operands', '').split(',')]
    family = op.split('.')[0]
    _destinations(row)
    count = 0 if family in {
        'STG', 'STS', 'STL', 'REDG', 'LDGSTS', 'LDGDEPBAR', 'DEPBAR', 'BAR',
        'NOP', 'BRA', 'BSSY', 'BSYNC', 'EXIT'
    } else 1
    if family in {'ISETP', 'UISETP', 'PSETP', 'PLOP3', 'VOTEU'}:
        count = 2
    elif family in {'LOP3', 'ULOP3'} and fields and re.fullmatch(
            r'(?:U?P\d+|UPT|PT)', fields[0]):
        count = 2
    elif family in {'IADD3', 'UIADD3', 'LEA', 'ULEA', 'IMAD', 'UIMAD'}:
        while count < min(3, len(fields)) and re.fullmatch(
                r'(?:U?P\d+|UPT|PT)', fields[count]):
            count += 1
    operands = ','.join(fields[count:])
    packed = set()
    if re.search(r'\bPR\b', operands):
        if (op != 'P2R' or len(fields) != 4 or fields[1] != 'PR'
                or re.fullmatch(r'R\d+', fields[0]) is None
                or re.fullmatch(r'R(?:\d+|Z)(?:\.reuse)?', fields[2]) is None
                or re.fullmatch(r'0x[0-9a-fA-F]+', fields[3]) is None
                or int(fields[3], 16) > 0x7f):
            raise ValueError('Packed predicate source form is not modeled')
        # NVIDIA documents P2R as predicate-register to register movement
        # and the physical predicate bank as P0..P6. Include the whole bank;
        # do not assume a particular immediate-bit to predicate mapping.
        packed = {'P' + str(i) for i in range(7)}
    values = registers(operands) | packed
    if family in {'IMAD', 'UIMAD'} and '.WIDE' in op:
        addend = fields[-1]
        m = re.fullmatch(r'(UR|R)(\d+)(?:\.reuse)?', addend)
        if m:
            values.add(m[1] + str(int(m[2]) + 1))
    if (family in {'IADD', 'IADD3', 'UIADD3', 'MOV', 'UMOV', 'SEL', 'USEL'}
            and '.64' in op) or (family in {'ISETP', 'UISETP'} and
                                 ('.S64' in op or '.U64' in op)):
        for token in list(values):
            m = re.fullmatch(r'(UR|R)(\d+)', token)
            if m:
                values.add(m[1] + str(int(m[2]) + 1))
    # A descriptor base is conservatively traced as two uniform words.
    for index in re.findall(r'desc\[UR(\d+)(?:\.reuse)?\]', operands):
        values.add('UR' + str(int(index) + 1))
    values.update(registers(row.get('predicate', '') or ''))
    return values


def audit(body, pc, roots):
    pred = _predecessors(body)
    work = deque((parent, root) for parent in pred[pc] for root in roots)
    seen = set()
    definitions = {}
    forbidden = []
    entry = set(roots) if not pred[pc] else set()
    while work:
        at, reg = work.popleft()
        if (at, reg) in seen:
            continue
        seen.add((at, reg))
        if len(seen) > 32768:
            raise ValueError('Finite dependency state budget exceeded')
        row = body[at]
        active = _predicate(row.get('predicate'))
        outputs = _destinations(row)
        wanted = {reg}
        if active is not False and reg in outputs:
            definitions[at] = dict(pc=at, **row)
            if row['opcode'].startswith('HMMA'):
                forbidden.append(
                    dict(pc=at,
                         register=reg,
                         reason='matrix_result_reaches_input'))
                continue
            if row['opcode'].startswith(('CS2R', 'CS2UR')):
                forbidden.append(
                    dict(pc=at,
                         register=reg,
                         reason='clock_result_reaches_input'))
                continue
            wanted = sources(row) | ({reg} if active is not True else set())
        if not pred[at]:
            entry.update(wanted)
        for parent in pred[at]:
            work.extend((parent, value) for value in wanted)
    return dict(status='forbidden_dependency_found'
                if forbidden else 'unverified_entry_registers' if entry else
                'no_matrix_or_clock_result_in_native_register_cone',
                seed_pc=pc,
                seed_registers=sorted(roots),
                visited_states=len(seen),
                definitions=list(definitions.values()),
                entry_registers=sorted(entry),
                register_entry_definitions_complete=not entry,
                internal_result_register_dependency_excluded=not forbidden,
                register_source_traversal_complete=True,
                forbidden=forbidden,
                memory_alias_analysis_verified=False,
                hidden_scoreboard_decoded=False)
