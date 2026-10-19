"""Synthetic matrix register-flow checks, never measured GPU activity."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'native_matrix_inputs',
    Path(__file__).with_name('native_matrix_inputs.py'))
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


def fixture():
    return {
        0: dict(opcode='LDSM.16.M88.4', operands='R0,[R40]'),
        16: dict(opcode='LDSM.16.MT88.4', operands='R4,[R44]'),
        32: dict(opcode='HMMA.16816.F32', operands='R8,R0,R4,R8'),
        48: dict(opcode='EXIT', operands='')
    }


def test_all_six_operand_words_have_exact_load_origin():
    item = rules.matrix_inputs(fixture())[0]
    assert item['native_loop_header_pc'] is None
    assert [(word['load_pc'], word['load_word'])
            for word in item['input_words']] == [(0, 0), (0, 1), (0, 2),
                                                 (0, 3), (16, 0), (16, 1)]


@pytest.mark.parametrize('opcode,source', [('MOV.64', 'R4'),
                                           ('MOV.64', 'R4.reuse')])
def test_full_width_register_copy_keeps_word_offsets(opcode, source):
    body = fixture()
    body[32] = dict(opcode=opcode, operands='R10,' + source)
    body[48] = dict(opcode='HMMA.16816.F32', operands='R16,R0,R10,R16')
    body[64] = dict(opcode='EXIT', operands='')
    words = rules.matrix_inputs(body)[0]['input_words'][-2:]
    assert [(w['load_pc'], w['load_word']) for w in words] == [(16, 0),
                                                               (16, 1)]


@pytest.mark.parametrize('mutation', [
    'clock', 'matrix_result', 'high_word', 'predicated_overwrite',
    'ambiguous_origin', 'unknown_writer', 'unknown_matrix',
    'predicated_matrix', 'unknown_load_geometry'
])
def test_incomplete_or_changed_matrix_input_is_rejected(mutation):
    body = fixture()
    if mutation == 'clock':
        body[16] = dict(opcode='CS2R', operands='R4,SR_GLOBALTIMERLO')
    elif mutation == 'matrix_result':
        body[16] = dict(opcode='HMMA.16816.F32', operands='R4,R0,R4,R4')
    elif mutation == 'unknown_matrix':
        body[32]['opcode'] = 'HMMA.16816.F16'
    elif mutation == 'predicated_matrix':
        body[32]['predicate'] = '@P0'
    elif mutation == 'unknown_load_geometry':
        body[0]['opcode'] = 'LDSM.16.M88.2'
    else:
        body[32] = dict(opcode='MOV', operands='R3,RZ')
        body[48] = dict(opcode='HMMA.16816.F32', operands='R8,R0,R4,R8')
        body[64] = dict(opcode='EXIT', operands='')
        if mutation == 'predicated_overwrite':
            body[32]['predicate'] = '@P0'
        elif mutation == 'unknown_writer':
            body[32]['opcode'] = 'FUTURE'
        elif mutation == 'ambiguous_origin':
            body[32] = dict(opcode='BRA', operands='0x40', predicate='@P0')
            body[48] = dict(opcode='LDSM.16.M88.4', operands='R0,[R48]')
            body[64] = dict(opcode='HMMA.16816.F32', operands='R8,R0,R4,R8')
            body[80] = dict(opcode='EXIT', operands='')
    with pytest.raises(ValueError):
        rules.matrix_inputs(body)


def test_actual_native_iteration_starts_fresh():
    body = fixture()
    body[48] = dict(opcode='BRA', operands='0x0', predicate='@P0')
    body[64] = dict(opcode='EXIT', operands='')
    assert rules.matrix_inputs(
        body, require_loop=True)[0]['native_loop_header_pc'] == 0


def test_unique_preloop_load_does_not_become_a_fresh_loop_generation():
    body = fixture()
    body[48] = dict(opcode='BRA', operands='0x10', predicate='@P0')
    body[64] = dict(opcode='EXIT', operands='')
    with pytest.raises(ValueError, match='undefined entry word'):
        rules.matrix_inputs(body, require_loop=True)


def test_required_iteration_is_not_satisfied_by_straightline_body():
    with pytest.raises(ValueError, match='no enclosing native iteration'):
        rules.matrix_inputs(fixture(), require_loop=True)


def binding_fixture():
    association = rules.matrix_inputs(fixture())
    sites = {0: [1], 16: [2]}
    events = [{'site_id': site} for site in [9, 9, 9, 1, 2, 3, 1, 2, 3]]
    model = dict(generations=[
        dict(identity='async-1',
             kind='async',
             commit_sequence=0,
             completion_observed_sequence=1,
             publication_barrier_sequence=2)
    ],
                 consumer_edges=[
                     dict(consumer_sequence=i,
                          consumer_site=events[i]['site_id'],
                          producer='async-1') for i in [3, 4, 6, 7]
                 ])
    return association, sites, 3, events, model


def test_unique_collective_generation_covers_each_native_input_word():
    rows = rules.bind_generations(*binding_fixture())
    assert [row['matrix_sequence'] for row in rows] == [5, 8]
    assert all(len(row['input_words']) == 6 for row in rows)
    assert {
        word['generation_id']
        for row in rows
        for word in row['input_words']
    } == {'async-1'}


@pytest.mark.parametrize('mutation', [
    'stale_load', 'repeated_load', 'missing_edge', 'mixed_generation',
    'late_publication', 'ambiguous_site', 'no_matrix'
])
def test_dynamic_association_rejects_stale_or_ambiguous_generation(mutation):
    association, sites, matrix, events, model = binding_fixture()
    if mutation == 'stale_load':
        events[6]['site_id'] = 9
    elif mutation == 'repeated_load':
        events.insert(5, {'site_id': 1})
    elif mutation == 'missing_edge':
        model['consumer_edges'] = model['consumer_edges'][1:]
    elif mutation == 'mixed_generation':
        model['consumer_edges'].append(
            dict(model['consumer_edges'][0], producer='async-2'))
    elif mutation == 'late_publication':
        model['generations'][0]['publication_barrier_sequence'] = 4
    elif mutation == 'ambiguous_site':
        sites[0] = [1, 2]
    else:
        events = [{'site_id': 9} for _ in events]
    with pytest.raises(ValueError):
        rules.bind_generations(association, sites, matrix, events, model)
