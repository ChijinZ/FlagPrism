"""Finite shared-load origins of SM120 matrix input register words.

Qualification tooling only. A native register association does not by itself
bind a raw shared-memory generation or certify source cost/hardware overlap.
"""
from collections import deque
import re

from flagtree.profiler.timeline_nvidia_late_values import (_destinations,
                                                           _predicate,
                                                           _move_source)


def matrix_inputs(body, *, require_loop=False):
    from flagtree.profiler.timeline_nvidia_loops import _inventory
    predecessors, _, loops, _ = _inventory(body)
    result = []
    for pc, row in body.items():
        if not row['opcode'].startswith('HMMA'):
            continue
        if row['opcode'] != 'HMMA.16816.F32' or _predicate(
                row.get('predicate')) is not True:
            raise ValueError('Unsupported or predicated matrix issue')
        fields = [
            field.strip().removesuffix('.reuse')
            for field in row.get('operands', '').split(',')
        ]
        if len(fields) != 4 or any(
                re.fullmatch(r'R\d+', field) is None for field in fields):
            raise ValueError('Unknown native matrix register operands')
        candidates = [(header, loop) for header, loop in loops.items()
                      if pc in loop['nodes']]
        header = None
        graph = predecessors
        if candidates:
            smallest = min(len(loop['nodes']) for _, loop in candidates)
            selected = [(h, loop) for h, loop in candidates
                        if len(loop['nodes']) == smallest]
            if len(selected) != 1:
                raise ValueError('Matrix native iteration is ambiguous')
            header, loop = selected[0]
            graph = {
                node: {
                    parent
                    for parent in predecessors[node] if parent in loop['nodes']
                    and not (node == header and parent in loop['latches'])
                }
                for node in loop['nodes']
            }
        elif require_loop:
            raise ValueError('Matrix issue has no enclosing native iteration')
        # A second cycle could capture an older dynamic load in a register
        # copy. A static PC alone cannot identify that older occurrence.
        if header is not None:
            pending = deque(node for node, parents in graph.items()
                            if not parents)
            degrees = {node: len(parents) for node, parents in graph.items()}
            children = {node: set() for node in graph}
            for node, parents in graph.items():
                for parent in parents:
                    children[parent].add(node)
            visited = 0
            while pending:
                node = pending.popleft()
                visited += 1
                for child in children[node]:
                    degrees[child] -= 1
                    if degrees[child] == 0:
                        pending.append(child)
            if visited != len(graph):
                raise ValueError(
                    'Matrix input iteration contains another cycle')
        words = []
        for operand, width in [('A', 4), ('B', 2)]:
            register = fields[1 if operand == 'A' else 2]
            for offset in range(width):
                root = 'R' + str(int(register[1:]) + offset)
                work = deque((parent, root) for parent in graph[pc])
                if not work:
                    raise ValueError(
                        'Matrix input has no reaching instructions')
                seen, origins = set(), set()
                while work:
                    at, current = work.popleft()
                    if (at, current) in seen:
                        continue
                    seen.add((at, current))
                    if len(seen) > 32768:
                        raise ValueError(
                            'Matrix input cone exceeds finite budget')
                    writer = body[at]
                    active = _predicate(writer.get('predicate'))
                    destinations = _destinations(writer)
                    inputs = {current}
                    if active is not False and current in destinations:
                        if writer['opcode'] in ('LDSM.16.M88.4',
                                                'LDSM.16.MT88.4'):
                            origins.add((at, destinations.index(current)))
                            inputs = set()
                        elif writer['opcode'] in ('MOV', 'MOV.64'):
                            inputs = {_move_source(writer, current)}
                        else:
                            raise ValueError(
                                'Matrix input has a non-LDSM reaching definition'
                            )
                        if active is not True:
                            inputs.add(current)
                    if inputs and not graph[at]:
                        raise ValueError(
                            'Matrix input reaches an undefined entry word')
                    for parent in graph[at]:
                        work.extend((parent, value) for value in inputs)
                if len(origins) != 1:
                    raise ValueError(
                        'Matrix input has missing or ambiguous shared-load origin'
                    )
                load_pc, load_word = origins.pop()
                words.append(
                    dict(operand=operand,
                         word=offset,
                         register=root,
                         load_pc=load_pc,
                         load_word=load_word))
        result.append(
            dict(matrix_pc=pc, native_loop_header_pc=header,
                 input_words=words))
    if not result:
        raise ValueError('No supported matrix instruction')
    return result


def bind_generations(associations, load_sites, matrix_site_id, events, model):
    """One checked matrix group per loop, with fresh collective shared loads.

    An entire modeled load footprint must belong to one generation. That is
    sufficient for any result word, without inventing a lane/byte permutation.
    Multiple matrix groups reusing loads need a richer dynamic association.
    """
    result = []
    previous = -1
    for sequence, event in enumerate(events):
        if event['site_id'] != matrix_site_id:
            continue
        bindings = []
        for association in associations:
            for word in association['input_words']:
                ids = load_sites.get(word['load_pc'], [])
                if len(ids) != 1:
                    raise ValueError(
                        'Matrix load lacks one checked native site')
                reads = [
                    i for i in range(previous + 1, sequence)
                    if events[i]['site_id'] == ids[0]
                ]
                if len(reads) != 1:
                    raise ValueError(
                        'Matrix load has missing, stale or repeated occurrence'
                    )
                ordinal = reads[0]
                edges = [
                    edge for edge in model['consumer_edges']
                    if edge['consumer_sequence'] == ordinal
                    and edge['consumer_site'] == ids[0]
                ]
                producers = {edge['producer'] for edge in edges}
                if len(producers) != 1:
                    raise ValueError(
                        'Matrix load has missing or mixed shared generations')
                identity = producers.pop()
                generations = [
                    g for g in model['generations']
                    if g['identity'] == identity
                ]
                if len(generations) != 1:
                    raise ValueError('Matrix load generation is not unique')
                generation = generations[0]
                ready = generation['completion_observed_sequence']
                publication = generation['publication_barrier_sequence']
                if (ready is None or publication is None
                        or not ready <= publication < ordinal
                        or (generation['kind'] == 'async'
                            and not generation['commit_sequence'] < ready)):
                    raise ValueError(
                        'Matrix load precedes generation readiness')
                bindings.append(
                    dict(matrix_pc=association['matrix_pc'],
                         operand=word['operand'],
                         word=word['word'],
                         load_pc=word['load_pc'],
                         load_word=word['load_word'],
                         load_site_id=ids[0],
                         load_sequence=ordinal,
                         generation_id=identity,
                         completion_observed_sequence=ready,
                         publication_barrier_sequence=publication))
        result.append(
            dict(matrix_sequence=sequence,
                 matrix_site_id=matrix_site_id,
                 input_words=bindings))
        previous = sequence
    if not result:
        raise ValueError('No actual matrix group occurrence')
    return result
