"""CPU corruption fixtures for scoped native payload expression equivalence."""
import copy


def run(payloads):

    def word(opcode, operands):
        return dict(opcode=opcode, operands=operands)

    def make(body, graph=None, operation=16, store=64, enabled=True):
        graph = graph or {pc: ({pc - 16} if pc else set()) for pc in body}
        return payloads._Words(body,
                               graph,
                               payloads._dominators(graph),
                               operation_pc=operation,
                               store_pc=store,
                               normalize_invariants=enabled)

    body = {
        0: word('S2R', 'R0,SR_TID.X'),
        16: word('S2R', 'R2,SR_TID.X'),
        32: word('NOP', ''),
        48: word('NOP', ''),
        64: word('EXIT', '')
    }
    w = make(body)
    if w.value(64, 'R0') != w.value(64, 'R2'):
        raise RuntimeError('Same immutable thread identity did not normalize')
    w = make(body, enabled=False)
    if w.value(64, 'R0') == w.value(64, 'R2'):
        raise RuntimeError('Legacy proof mode acquired new invariance rights')
    for special in ('SR_CLOCKLO', 'SR_SMID'):
        changed = copy.deepcopy(body)
        changed[0] = word('S2R', 'R0,' + special)
        changed[16] = word('S2R', 'R2,' + special)
        w = make(changed)
        if w.value(64, 'R0') == w.value(64, 'R2'):
            raise RuntimeError(
                'Uncertified special-register invariance granted')
    changed = copy.deepcopy(body)
    changed[16] = word('S2R', 'R2,SR_TID.Y')
    w = make(changed)
    if w.value(64, 'R0') == w.value(64, 'R2'):
        raise RuntimeError('Different thread coordinates collapsed')
    address = {
        0: word('S2UR', 'UR0,SR_CgaCtaId'),
        16: word('UMOV', 'UR2,0x400'),
        32: word('ULEA', 'UR4,UR0,UR2,0x18'),
        48: word('S2UR', 'UR6,SR_CgaCtaId'),
        64: word('ULEA', 'UR8,UR6,UR2,0x18'),
        80: word('NOP', ''),
        96: word('EXIT', '')
    }
    w = make(address, operation=32, store=80)
    if w.value(80, 'UR4') != w.value(80, 'UR8'):
        raise RuntimeError('Repeated pure address materialization differs')
    address[64]['operands'] = 'UR8,UR6,UR2,0x17'
    w = make(address, operation=32, store=80)
    if w.value(80, 'UR4') == w.value(80, 'UR8'):
        raise RuntimeError('Different address shift collapsed')
    predicate = {
        0: word('ISETP.GT.AND', 'P1,PT,R0,0x1f,PT'),
        16: word('P2R', 'R4,PR,RZ,0x2'),
        32: word('ISETP.NE.AND', 'P3,P5,R4,RZ,PT'),
        48: word('NOP', ''),
        64: word('EXIT', '')
    }
    w = make(predicate)
    original = w.boolean('P1', 64)
    if w.boolean('P3', 64) != original or w.boolean(
            'P5', 64) != w.arena.invert(original):
        raise RuntimeError('Predicate zero/nonzero round trip lost polarity')
    predicate[32]['opcode'] = 'ISETP.EQ.AND'
    w = make(predicate)
    if w.boolean('P3', 64) != w.arena.invert(w.boolean('P1', 64)):
        raise RuntimeError('Equality comparison did not invert predicate')
    for operands in ('R4,PR,RZ,0x3', 'R4,PR,RZ,0x80', 'R4,PR,R6,0x2'):
        changed = copy.deepcopy(predicate)
        changed[16]['operands'] = operands
        changed[32]['opcode'] = 'ISETP.NE.AND'
        w = make(changed)
        if w.boolean('P3', 64) == w.boolean('P1', 64):
            raise RuntimeError('Uncertified predicate packing was forwarded')
    changed = copy.deepcopy(predicate)
    changed[32].update(opcode='ISETP.NE.AND', operands='P3,P5,R4,RZ,P6')
    w = make(changed)
    if w.boolean('P3', 64) == w.boolean('P1', 64):
        raise RuntimeError('Additional predicate guard was ignored')
    loop = {
        0: word('S2R', 'R0,SR_TID.X'),
        16: word('STL', '[R1+0x8],R0'),
        32: word('NOP', ''),
        48: word('LDL', 'R6,[R1+0x8]'),
        64: word('MOV', 'R8,0x99'),
        80: word('STL', '[R1+0x8],R8'),
        96: word('BRA', '0x20')
    }
    graph = {pc: ({pc - 16} if pc else set()) for pc in loop}
    graph[32].add(96)
    w = make(loop, graph, operation=48, store=96)
    previous = w.value(96, 'R6')
    current = w.local_word(96, 'R1', 8, False)
    if previous == current or current != 0x99:
        raise RuntimeError(
            'Previous/current local spill generations collapsed')
    invariant = copy.deepcopy(loop)
    invariant[80] = word('NOP', '')
    w = make(invariant, graph, operation=48, store=96)
    if w.value(96, 'R6') != w.value(96, 'R0'):
        raise RuntimeError(
            'Read-only local slot lost its acyclic preheader value')
    return dict(status='scoped_native_payload_normalization_fixtures_passed',
                fixture_only=True)


if __name__ == '__main__':
    import json
    from flagtree.profiler import timeline_nvidia_late_payloads
    print(json.dumps(run(timeline_nvidia_late_payloads)))
