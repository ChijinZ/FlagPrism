"""Finite control-path checks for reader pairs in actual native loops.

This identifies native CFG iterations, not source iteration numbers, elapsed
source ownership, collective participation, termination or hardware activity.
The caller supplies object-bound instructions and independently checked issue
boundaries. No captured path is selected to bypass an alternative CFG edge.
"""
from collections import deque
import hashlib
import json

from .timeline_nvidia_control import _need

MAX_NODES = 4096
MAX_UPDATES = 1000000
MAX_BACKEDGES = 128


def _dominators(predecessors, entry):
    """Bounded bitset analysis of a reachable graph."""
    nodes = sorted(predecessors)
    _need(entry in predecessors and len(nodes) <= MAX_NODES,
          'Native loop graph exceeds its node budget')
    index = {pc: i for i, pc in enumerate(nodes)}
    full = (1 << len(nodes)) - 1
    dominators = {pc: full for pc in nodes}
    dominators[entry] = 1 << index[entry]
    successors = {pc: set() for pc in nodes}
    for pc, parents in predecessors.items():
        for parent in parents:
            _need(parent in predecessors,
                  'Native loop predecessor is outside graph')
            successors[parent].add(pc)
    pending = deque(pc for pc in nodes if pc != entry)
    queued = set(pending)
    updates = 0
    while pending:
        pc = pending.popleft()
        queued.remove(pc)
        common = full
        _need(predecessors[pc],
              'Native loop graph contains a disconnected entry')
        for parent in predecessors[pc]:
            common &= dominators[parent]
        value = common | (1 << index[pc])
        updates += 1
        _need(updates <= MAX_UPDATES,
              'Native loop dominators exceed work budget')
        if value != dominators[pc]:
            dominators[pc] = value
            for target in successors[pc]:
                if target != entry and target not in queued:
                    pending.append(target)
                    queued.add(target)
    return index, dominators, successors


def _inventory(body):
    from .timeline_nvidia_late_values import _predecessors, _predicate
    _need(body and len(body) <= MAX_NODES,
          'Native function exceeds finite loop node budget')
    predecessors = _predecessors(body)
    entry = min(body)
    index, dominators, successors = _dominators(predecessors, entry)
    backedges = [(tail, header) for tail in predecessors
                 for header in successors[tail]
                 if dominators[tail] & (1 << index[header])]
    _need(
        len(backedges) <= MAX_BACKEDGES,
        'Native function exceeds finite loop backedge budget')
    loops = {}
    visits = 0
    for tail, header in backedges:
        loop = loops.setdefault(header, dict(nodes={header}, latches=set()))
        loop['latches'].add(tail)
        pending = [tail]
        while pending:
            node = pending.pop()
            visits += 1
            _need(visits <= MAX_UPDATES,
                  'Native loop inventory exceeds work budget')
            if node in loop['nodes']:
                continue
            _need(dominators[node] & (1 << index[header]),
                  'Native cycle has a non-header entry')
            loop['nodes'].add(node)
            pending.extend(predecessors[node])
    # The value-flow graph need only retain paths to later instructions;
    # conditional EXIT has a fallthrough there but also terminates an actor.
    # Loop boundaries must separately cover that taken termination path.
    exit_instructions = {
        pc
        for pc in predecessors if body[pc]['opcode'] == 'EXIT'
        and _predicate(body[pc].get('predicate')) is not False
    }
    return predecessors, successors, loops, exit_instructions


def _iteration(predecessors, successors, exit_instructions, header, loop,
               begin, end):
    """Cut the iteration's return edges, then check every resulting path."""
    nodes, latches = loop['nodes'], loop['latches']
    _need(begin != end and begin in nodes and end in nodes,
          'Reader pair does not lie in the same native loop')
    entries = [(parent, pc) for pc in nodes for parent in predecessors[pc]
               if parent not in nodes]
    _need(all(pc == header for _, pc in entries),
          'Native loop has a non-header entry')
    exits = sorted((pc, target) for pc in nodes for target in successors[pc]
                   if target not in nodes)
    terminal = {pc for pc in nodes if not successors[pc]}
    taken_exits = nodes & exit_instructions
    _need(exits or terminal or taken_exits,
          'Native loop has no inspected exit')
    local = {
        pc: {
            parent
            for parent in predecessors[pc]
            if parent in nodes and not (pc == header and parent in latches)
        }
        for pc in nodes
    }
    _need(not local[header], 'Native loop return edges are incomplete')
    children = {pc: set() for pc in nodes}
    degree = {pc: len(parents) for pc, parents in local.items()}
    for pc, parents in local.items():
        for parent in parents:
            children[parent].add(pc)
    ready = deque(pc for pc in nodes if degree[pc] == 0)
    order = []
    while ready:
        pc = ready.popleft()
        order.append(pc)
        for target in children[pc]:
            degree[target] -= 1
            if degree[target] == 0:
                ready.append(target)
    _need(
        len(order) == len(nodes),
        'Native iteration contains another cycle or nested loop')
    _need(
        order and order[0] == header
        and all(local[pc] for pc in nodes if pc != header),
        'Native iteration contains an additional entry')
    # Local dominators start at this iteration's header, not function entry;
    # an endpoint visited in an earlier iteration cannot satisfy this check.
    index = {pc: i for i, pc in enumerate(order)}
    required = (1 << index[begin]) | (1 << index[end])
    masks = {}
    full = (1 << len(order)) - 1
    for pc in order:
        common = full
        if pc == header:
            common = 0
        else:
            for parent in local[pc]:
                common &= masks[parent]
        masks[pc] = common | (1 << index[pc])
    destinations = set(latches) | {pc
                                   for pc, _ in exits} | terminal | taken_exits
    _need(all(masks[pc] & required == required for pc in destinations),
          'A native iteration return or exit bypasses an endpoint')
    return dict(loop_header_pc=header,
                latch_pcs=sorted(latches),
                exit_edges=[list(edge) for edge in exits],
                terminal_pcs=sorted(terminal),
                exit_instruction_pcs=sorted(taken_exits),
                instruction_pcs=sorted(nodes))


def inspect_native_loops(*, functions, boundaries, binary_id):
    """Return diagnostics without upgrading unrelated timing qualifications."""
    inventories = {}
    results = []
    for boundary in boundaries:
        result = dict(site_id=boundary['site_id'],
                      kind=boundary['kind'],
                      status='unverified',
                      native_iteration_boundaries_verified=False,
                      source_iteration_identity_verified=False,
                      source_cost_qualified=False,
                      participation_verified=False,
                      hardware_overlap_verified=False)
        try:
            _need(
                boundary['status'] in ('matrix_issue_control_order_checked',
                                       'source_issue_control_order_checked'),
                'Native issue reader boundaries are unverified')
            function = boundary['function']
            if function not in inventories:
                try:
                    inventories[function] = _inventory(functions[function])
                except (ValueError, KeyError, TypeError) as error:
                    inventories[function] = str(error)
            inventory = inventories[function]
            _need(
                not isinstance(inventory, str), inventory if isinstance(
                    inventory, str) else 'Invalid native loop inventory')
            predecessors, successors, loops, exit_instructions = inventory
            begin, end = boundary['begin_reader_pc'], boundary['end_reader_pc']
            _need(begin in predecessors and end in predecessors,
                  'Native reader pair is unreachable')
            candidates = [(header, loop) for header, loop in loops.items()
                          if begin in loop['nodes'] and end in loop['nodes']]
            _need(candidates, 'Reader pair has no enclosing native loop')
            smallest = min(len(loop['nodes']) for _, loop in candidates)
            candidates = [(header, loop) for header, loop in candidates
                          if len(loop['nodes']) == smallest]
            _need(len(candidates) == 1, 'Native loop membership is ambiguous')
            header, loop = candidates[0]
            facts = _iteration(predecessors, successors, exit_instructions,
                               header, loop, begin, end)
            identity = json.dumps([binary_id, function, header],
                                  separators=(',', ':'))
            result.update(
                facts,
                status='native_iteration_control_checked',
                native_iteration_boundaries_verified=True,
                function=function,
                begin_reader_pc=begin,
                end_reader_pc=end,
                native_loop_id=hashlib.sha256(identity.encode()).hexdigest(),
                relation='one_reader_pair_per_native_CFG_iteration_or_exit')
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    return results
