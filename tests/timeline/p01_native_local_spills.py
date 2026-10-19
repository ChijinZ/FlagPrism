"""CPU corruption fixtures for fixed thread-local timer spill provenance.
These fixtures do not stand in for real device timing or native code samples.
"""
import copy


def run(values):

    def instruction(opcode, operands, predicate=None):
        return dict(opcode=opcode, operands=operands, predicate=predicate)

    body = {
        0: instruction('CS2R', 'R2, SR_GLOBALTIMERLO'),
        16: instruction('STL.64', '[R1+0x8], R2'),
        32: instruction('MOV', 'R2, RZ'),
        48: instruction('LDL.LU.64', 'R6, [R1+0x8]'),
        64: instruction('STG.E.64', 'desc[UR4][R10.64], R6'),
    }
    graph = {0: set(), 16: {0}, 32: {16}, 48: {32}, 64: {48}}
    reader = dict(pc=0, sass_predicate=None)

    def check(sample, predecessors=graph, register='R6', word=0):
        return values.check_timer_word(sample,
                                       predecessors,
                                       reader=reader,
                                       store_pc=64,
                                       word_register=register,
                                       word_index=word)

    check(body)
    check(body, register='R7', word=1)
    vector = copy.deepcopy(body)
    vector[48] = instruction('LDL.128', 'R4, [R1]')
    check(vector)
    check(vector, register='R7', word=1)
    json_form = copy.deepcopy(body)
    json_form[48]['operands'] = 'R6[R1+0x8]'
    check(json_form)
    disjoint = copy.deepcopy(body)
    disjoint[32] = instruction('STL', '[R1+0x20], RZ')
    check(disjoint)
    failed = []

    def reject(name, sample, **kwargs):
        try:
            check(sample, **kwargs)
        except ValueError:
            failed.append(name)
        else:
            raise RuntimeError('Invalid timer spill accepted: ' + name)

    for name, row in [
        ('different_slot', instruction('LDL.LU.64', 'R6, [R1+0xc]')),
        ('dynamic_slot', instruction('LDL.LU.64', 'R6, [R1+R5]')),
        ('unaligned_slot', instruction('LDL.LU.64', 'R6, [R1+0x9]')),
        ('unknown_width', instruction('LDL.16', 'R6, [R1+0x8]')),
    ]:
        wrong = copy.deepcopy(body)
        wrong[48] = row
        reject(name, wrong)
    for name, row in [
        ('overwritten_low', instruction('STL', '[R1+0x8], RZ')),
        ('changed_base', instruction('MOV', 'R1, R20')),
        ('potential_alias', instruction('STL', '[R20+0x8], R2')),
    ]:
        wrong = copy.deepcopy(body)
        wrong[32] = row
        reject(name, wrong)
    wrong = copy.deepcopy(body)
    wrong[16]['predicate'] = '@P0'
    reject('predicated_missing_store_path', wrong)
    wrong_graph = copy.deepcopy(graph)
    wrong_graph[48].add(0)
    reject('branch_bypasses_spill', body, predecessors=wrong_graph)
    reject('wrong_timer_word', body, register='R7')
    return dict(positive_cases=6, rejected=failed, fixture_only=True)
