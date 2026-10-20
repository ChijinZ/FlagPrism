"""Observed actor-LLVM fragment paths, distinct from final engine activity.

The native index inputs must be bound to the actual retained compiler handoff.
This layer locates original operation structures on every path between paired
readers in one iteration. It does not prove SSA equivalence, exclusive cost,
native scheduling, participation or the trip count of a source loop.
"""
import re

from .timeline_ascend_regions import _Index, _need, bind_record_endpoints

MARKER = re.compile(
    r'/\* flagprism.source_census_site.v3:(\d+):(\d+):(\d+) \*/')
TERMINATORS = frozenset({
    'br', 'ret', 'switch', 'unreachable', 'invoke', 'resume', 'indirectbr',
    'callbr'
})


def _complete_type(value):
    # LLVM15's scalar floating TypeIDs 0..6 and void7 are fully identified by
    # kind. The index carries widths for integers and spaces for pointers.
    # Aggregate/vector kinds deliberately carry no shape and remain opaque.
    return ('integer_bits' in value or 'address_space' in value
            or value.get('kind') in range(8))


def _signature(instruction, index):
    """A structural operation identity, never an inferred value equivalence."""
    if instruction['opcode'] in (
            'fcmp', 'atomicrmw') or instruction.get('indirect_call'):
        return None
    if instruction['opcode'] == 'call' and instruction.get(
            'callee') is None and instruction.get('assembly') is None:
        return None
    operands = []
    if not _complete_type(instruction['type']):
        return None
    if ('element_type' in instruction
            and not _complete_type(instruction['element_type'])):
        return None
    for value in instruction['operands']:
        # Charge both constructing and comparing this part of a signature;
        # high-arity calls must not turn one candidate charge into unbounded
        # implicit list comparison work.
        index.charge()
        index.charge()
        if not _complete_type(value['type']):
            return None
        operands.append(
            (value['type'], value.get('integer_bits'),
             value.get('integer_hex'), value.get('constant_status')))
    # The late observer deliberately replaces debug locations on these exact
    # immediate flag intrinsics. Their typed callee and complete literal
    # operands remain the operation structure; the replacement marker is not
    # an original source position. Other instructions keep their location.
    location = instruction.get('location')
    if instruction.get('callee') in ('llvm.hivm.SET.FLAG.IMM',
                                     'llvm.hivm.WAIT.FLAG.IMM'):
        location = None
    return (instruction['opcode'], instruction['type'], location,
            instruction.get('callee'), instruction.get('assembly'),
            instruction.get('constraints'), instruction.get('side_effects'),
            instruction.get('predicate'), instruction.get('volatile'),
            instruction.get('atomic'), instruction.get('nsw'),
            instruction.get('nuw'), instruction.get('element_type'),
            instruction.get('inbounds'), operands)


class _Paths:

    def __init__(self, index, function):
        self.index = index
        self.forward, self.reverse = {}, {}
        backs = {(latch, loop['header'])
                 for loop in function['loops']
                 for latch in loop['latches']}
        for block in function['blocks']:
            values = block['instructions']
            _need(values, 'Empty actor basic block')
            for left, right in zip(values, values[1:]):
                self.forward[left['id']] = [right['id']]
            self.forward[values[-1]['id']] = [
                index.blocks[successor]['instructions'][0]['id']
                for successor in block['successors']
                if (block['id'], successor) not in backs
            ]
        for left, targets in self.forward.items():
            for right in targets:
                index.charge()
                self.reverse.setdefault(right, []).append(left)

    def reach(self, start, edges, *, stop=None, avoid=None):
        pending, seen = [start], set()
        while pending:
            self.index.charge()
            current = pending.pop()
            if current == avoid or current in seen:
                continue
            seen.add(current)
            if current != stop:
                pending.extend(edges.get(current, ()))
        return seen

    def corridor(self, begin, end):
        forward = self.reach(begin, self.forward, stop=end)
        _need(end in forward, 'No same-iteration endpoint path')
        return forward & self.reach(end, self.reverse, stop=begin)

    def mandatory(self, begin, end, member):
        return end not in self.reach(begin,
                                     self.forward,
                                     stop=end,
                                     avoid=member)


def _loop_context(index, function, instruction_ids):
    """Locate an indexed natural loop without assigning dynamic iterations."""
    blocks = {index.block[key] for key in instruction_ids}
    enclosing = []
    for loop in function['loops']:
        for _ in loop['blocks']:
            index.charge()
        if blocks <= set(loop['blocks']):
            enclosing.append(loop)
    if not enclosing:
        return dict(status='outside_indexed_natural_loops')
    enclosing.sort(key=lambda loop: len(loop['blocks']))
    if len(enclosing) > 1 and len(enclosing[0]['blocks']) == len(
            enclosing[1]['blocks']):
        return dict(status='ambiguous_indexed_loop_context')
    loop = enclosing[0]
    return dict(status='indexed_natural_loop_context',
                header_block_id=loop['header'],
                latch_block_ids=loop['latches'],
                parent_header_block_id=loop['parent_header'],
                enclosing_header_block_ids=[
                    row['header'] for row in reversed(enclosing)
                ],
                source_iteration_ids_verified=False,
                trip_count_verified=False)


def bind_fragment_paths(original_graph, adapted_graph, *, manifest, function,
                        trace_argument_index, original_input_sha256,
                        adapted_input_sha256, selected_source_ids):
    """Bind original operation structures to observed reader-to-reader paths.

    Input hashes refer to freshly indexed original/adapted bytes, not a saved
    report. The caller obtains them from the checked compiler artifact. This
    intentionally grants only a typed-LLVM path fact; it cannot certify native
    issue placement or full source/value equivalence.
    """
    for graph, digest in ((original_graph, original_input_sha256),
                          (adapted_graph, adapted_input_sha256)):
        _need(
            graph.get('model') == 'ascend.actor_llvm15.structure.v1'
            and graph.get('schema_version') == 1
            and graph.get('input_sha256') == digest,
            'Actor index differs from actual compiler input')
    _need(original_input_sha256 == manifest['module_input_sha256'],
          'Original actor differs from compiler manifest')
    original = [
        f for f in original_graph['functions'] if f['name'] == function
    ]
    adapted = [f for f in adapted_graph['functions'] if f['name'] == function]
    _need(len(original) == len(adapted) == 1, 'Ambiguous declared actor')
    before, after = _Index(original[0]), _Index(adapted[0])
    paths = _Paths(after, adapted[0])
    tuples = bind_record_endpoints(adapted_graph,
                                   manifest=manifest,
                                   function=function,
                                   trace_argument_index=trace_argument_index)
    bindings = {r['site_id']: r for r in tuples['regions']}
    selected = set(selected_source_ids)
    original_markers, adapted_markers = {}, {}
    for index, markers in ((before, original_markers), (after,
                                                        adapted_markers)):
        for block in index.blocks.values():
            for position, value in enumerate(block['instructions']):
                index.charge()
                match = MARKER.fullmatch(value.get('assembly', ''))
                if match:
                    markers.setdefault((int(match[1]), int(match[2])),
                                       []).append((block, position, value))
    rows = []
    for site in manifest['dynamic_sites']:
        if site['semantic_code'] != 1:
            continue
        row = dict(site_id=site['site_id'],
                   source_op_id=site['source_op_id'],
                   status='unverified',
                   source_value_equivalence_verified=False,
                   runtime_selection_guard_verified=False,
                   loop_verified=False,
                   native_schedule_qualified=False)
        try:
            _need(site['source_op_id'] in selected,
                  'Fragment is outside actual selected source operations')
            record = bindings[site['site_id']]
            _need(record['status'] == 'llvm_tuple_endpoints_bound',
                  'Fragment has no unique complete endpoint tuple')
            key = site['source_op_id'], site['frontend_column']
            originals = original_markers.get(key, [])
            replacements = adapted_markers.get(key, [])
            _need(
                len(originals) == len(replacements) == 1,
                'Missing or ambiguous original/adapted source carrier')
            block, position, original_marker = originals[0]
            body = []
            for value in block['instructions'][position + 1:]:
                before.charge()
                if MARKER.fullmatch(value.get(
                        'assembly', '')) or value['opcode'] in TERMINATORS:
                    break
                body.append(value)
            _need(body and len(body) == site['original_instruction_count'],
                  'Original body does not match declared fragment extent')
            marker = replacements[0][2]['id']
            begin, end = record['begin_id'], record['end_id']
            corridor = paths.corridor(begin, end)
            _need(marker in corridor and paths.mandatory(begin, end, marker),
                  'Source carrier can be bypassed between endpoints')
            # Source op structures must occur uniquely after the same actual
            # carrier and before the end. No nearest-debug-line association.
            candidates = paths.reach(marker, paths.forward,
                                     stop=end) & corridor
            _need(
                len(original[0]['arguments']) == len(adapted[0]['arguments']),
                'Actor argument extent changed')
            definitions = {
                left['id']: right['id']
                for left, right in zip(original[0]['arguments'], adapted[0]
                                       ['arguments'])
                if left['type'] == right['type']
            }
            used, members = set(), []
            for operation in body:
                signature = _signature(operation, before)
                _need(signature is not None,
                      'Original operation contains an opaque indexed type')
                matches = []
                for candidate in candidates:
                    after.charge()
                    actual = after.instructions[candidate]
                    if candidate in used or _signature(actual,
                                                       after) != signature:
                        continue
                    # Preserve already-bound local definitions and declared
                    # actor arguments. External SSA definitions remain opaque;
                    # this is not recursive whole-program value equivalence.
                    if any(left['id'] in definitions
                           and definitions[left['id']] != right['id']
                           for left, right in zip(operation['operands'],
                                                  actual['operands'])):
                        continue
                    matches.append(candidate)
                _need(
                    len(matches) == 1,
                    'Missing or ambiguous original operation structure: ' +
                    str(operation['id']) + ' ' + operation['opcode'] + ' ' +
                    str(operation.get('callee')) + '; candidates=' +
                    str(len(matches)))
                member = matches[0]
                _need(paths.mandatory(begin, end, member),
                      'Original operation can be bypassed between endpoints')
                _need(
                    paths.mandatory(marker, end, member),
                    'Original operation can be bypassed after source carrier')
                used.add(member)
                definitions[operation['id']] = member
                members.append(
                    dict(original_id=operation['id'],
                         adapted_id=member,
                         opcode=operation['opcode'],
                         callee=operation.get('callee')))
            row.update(
                status='llvm_observed_fragment_operations_bound',
                begin_id=begin,
                end_id=end,
                original_carrier_id=original_marker['id'],
                adapted_carrier_id=marker,
                members=members,
                original_loop_context=_loop_context(before, original[0], [
                    original_marker['id'],
                    *[m['original_id'] for m in members]
                ]),
                adapted_loop_context=_loop_context(
                    after, adapted[0],
                    [begin, marker, end, *[m['adapted_id'] for m in members]]),
                frontend_selection_verified=True,
                observed_endpoint_path_verified=True)
            from .timeline_ascend_loops import selected_loop_bracket
            row['selected_loop_bracket'] = selected_loop_bracket(
                after,
                adapted[0],
                begin_id=begin,
                end_id=end,
                context=row['adapted_loop_context'])
        except (ValueError, KeyError, TypeError) as error:
            # This per-region result never grants module-wide uniqueness or a
            # property of an unvisited region. Budget exhaustion stays visible.
            row['reason'] = str(error)
        rows.append(row)
    return dict(schema_version=1,
                model='ascend.observed_fragment_paths.v1',
                function=function,
                original_input_sha256=original_input_sha256,
                adapted_input_sha256=adapted_input_sha256,
                regions=rows,
                native_schedule_qualified=False)
