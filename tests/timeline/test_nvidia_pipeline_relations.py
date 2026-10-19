"""Synthetic dependency mutations; these are not device measurements."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'native_pipeline_relations',
    Path(__file__).with_name('native_pipeline_relations.py'))
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


def fixture():
    body = {
        i * 16: dict(opcode='MOV', operands='R' + str(i) + ',RZ')
        for i in range(6)
    }
    body[96] = dict(opcode='HMMA.16816.F32', operands='R20,R8,R12,R20')
    body[112] = dict(opcode='IMAD.WIDE', operands='R2,R0,0x1,R4')
    body[128] = dict(opcode='NOP', operands='')
    body[144] = dict(opcode='EXIT', operands='')
    return body


def test_unrelated_matrix_result_is_not_a_dependency():
    report = rules.audit(fixture(), 128, {'R2', 'R3'})
    assert report[
        'status'] == 'no_matrix_or_clock_result_in_native_register_cone'
    assert not report['forbidden']
    assert not report['entry_registers']
    assert report['memory_alias_analysis_verified'] is False
    assert report['hidden_scoreboard_decoded'] is False


@pytest.mark.parametrize('mutation',
                         ['low_word', 'wide_addend_high_word', 'clock'])
def test_new_completion_dependency_is_detected(mutation):
    body = fixture()
    if mutation == 'low_word':
        body[112]['operands'] = 'R2,R0,0x1,R20'
    elif mutation == 'wide_addend_high_word':
        body[80] = dict(opcode='MOV', operands='R19,RZ')
        body[112]['operands'] = 'R2,R0,0x1,R19'
    else:
        body[96] = dict(opcode='CS2R', operands='R20,SR_GLOBALTIMERLO')
        body[112]['operands'] = 'R2,R0,0x1,R20'
    report = rules.audit(body, 128, {'R2', 'R3'})
    assert report['status'] == 'forbidden_dependency_found'
    assert {row['pc'] for row in report['forbidden']} == {96}


def test_overwritten_physical_register_does_not_keep_old_identity():
    body = fixture()
    body[112] = dict(opcode='MOV', operands='R20,RZ')
    assert rules.audit(
        body, 128,
        {'R20'
         })['status'] == ('no_matrix_or_clock_result_in_native_register_cone')


def test_predicated_overwrite_keeps_both_reaching_definitions():
    body = fixture()
    body[112] = dict(opcode='MOV', operands='R20,RZ', predicate='@P0')
    report = rules.audit(body, 128, {'R20'})
    assert report['status'] == 'forbidden_dependency_found'


def test_branch_merge_keeps_unobserved_path():
    body = fixture()
    body[80] = dict(opcode='BRA', operands='0x70', predicate='@P0')
    body[112] = dict(opcode='NOP', operands='')
    assert rules.audit(body, 128,
                       {'R20'})['status'] == 'forbidden_dependency_found'


def test_uniform_branch_operand_is_a_real_use():
    from flagtree.profiler.timeline_nvidia_control import _branch
    row = dict(opcode='BRA.U', operands='UP0,0x80')
    predicate, target = _branch(row)
    assert rules.registers(predicate) == {'UP0'} and target == 128


def test_undefined_entry_register_cannot_certify_independence():
    assert rules.audit(fixture(), 128,
                       {'R99'})['status'] == 'unverified_entry_registers'


def test_unknown_writer_is_explicitly_unverified():
    body = fixture()
    body[112] = dict(opcode='FUTURE', operands='R2,R0')
    with pytest.raises(ValueError,
                       match='Unknown native register write family'):
        rules.audit(body, 128, {'R2'})


def test_address_pair_and_descriptor_roots_are_not_only_low_words():
    assert rules.sources(
        dict(opcode='LDGSTS.E.BYPASS.128',
             operands='[R7],desc[UR20][R4.64],P1')) == {
                 'R7', 'UR20', 'UR21', 'R4', 'R5', 'P1'
             }


@pytest.mark.parametrize('opcode', ['ISETP.GT.S64.AND', 'IADD.64'])
def test_implicit_high_input_word_is_not_lost(opcode):
    body = fixture()
    body[16] = dict(opcode='MOV', operands='R19,RZ')
    if opcode.startswith('ISETP'):
        body[112] = dict(opcode=opcode, operands='P0,PT,R19,R0,PT')
        roots = {'P0'}
    else:
        body[112] = dict(opcode=opcode, operands='R2,R19,R0')
        roots = {'R2'}
    assert rules.audit(body, 128,
                       roots)['status'] == 'forbidden_dependency_found'


def test_wide_addend_reuse_modifier_keeps_high_word():
    body = fixture()
    body[16] = dict(opcode='MOV', operands='R19,RZ')
    body[112]['operands'] = 'R2,R0,0x1,R19.reuse'
    assert rules.audit(body, 128,
                       {'R2'})['status'] == 'forbidden_dependency_found'


@pytest.mark.parametrize('opcode', ['UISETP.NE.U64.AND', 'UIADD3.64'])
def test_uniform_64bit_comparison_keeps_high_word(opcode):
    body = fixture()
    body[0] = dict(opcode='UMOV', operands='UR4,URZ')
    body[16] = dict(opcode='UMOV', operands='UR8,URZ')
    body[32] = dict(opcode='UMOV', operands='UR9,URZ')
    body[112] = dict(opcode='R2UR', operands='UR5,R20')
    body[128] = dict(
        opcode=opcode,
        operands=('UP0,UPT,UR4,UR8,UPT'
                  if opcode.startswith('UISETP') else 'UR2,UR4,UR8,UR8'))
    body[144] = dict(opcode='NOP', operands='')
    body[160] = dict(opcode='EXIT', operands='')
    assert rules.audit(body, 144, {'UP0'} if opcode.startswith('UISETP') else
                       {'UR2'})['status'] == 'forbidden_dependency_found'


def test_use_at_function_entry_is_not_independently_defined():
    assert rules.audit(fixture(), 0,
                       {'R0'})['status'] == 'unverified_entry_registers'


@pytest.mark.parametrize('opcode', ['SEL.64', 'USEL.64'])
def test_64bit_select_keeps_both_source_words(opcode):
    body = fixture()
    if opcode == 'SEL.64':
        body[16] = dict(opcode='MOV', operands='R19,RZ')
        body[112] = dict(opcode=opcode, operands='R2,R19,R0,P0')
        pc, roots = 128, {'R2'}
    else:
        body[0] = dict(opcode='UMOV', operands='UR4,URZ')
        body[16] = dict(opcode='UMOV', operands='UR8,URZ')
        body[32] = dict(opcode='UMOV', operands='UR9,URZ')
        body[112] = dict(opcode='R2UR', operands='UR5,R20')
        body[128] = dict(opcode=opcode, operands='UR2,UR4,UR8,UP0')
        body[144] = dict(opcode='NOP', operands='')
        body[160] = dict(opcode='EXIT', operands='')
        pc, roots = 144, {'UR2'}
    assert rules.audit(body, pc,
                       roots)['status'] == 'forbidden_dependency_found'


def test_packed_predicate_sources_include_bank_merge_and_execution_guard():
    assert rules.sources(
        dict(opcode='P2R', operands='R2,PR,R30.reuse,0x1',
             predicate='@UP0')) == {
                 'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'R30', 'UP0'
             }


def test_unknown_entry_values_do_not_become_current_function_result_definitions(
):
    body = fixture()
    body[112] = dict(opcode='P2R', operands='R2,PR,RZ,0x1')
    row = rules.audit(body, 128, {'R2'})
    assert row['status'] == 'unverified_entry_registers'
    assert row['register_entry_definitions_complete'] is False
    assert row['entry_registers'] == ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6']
    assert row['internal_result_register_dependency_excluded'] is True
    assert row['memory_alias_analysis_verified'] is False


@pytest.mark.parametrize('variant', ['predicate', 'merge'])
def test_packed_predicate_or_merge_dependency_keeps_matrix_result(variant):
    body = fixture()
    body[112] = dict(opcode='ISETP.NE.U32.AND', operands='P6,PT,R20,RZ,PT')
    body[128] = dict(opcode='P2R',
                     operands='R2,PR,' +
                     ('R20' if variant == 'merge' else 'RZ') + ',0x1')
    body[144] = dict(opcode='NOP', operands='')
    body[160] = dict(opcode='EXIT', operands='')
    row = rules.audit(body, 144, {'R2'})
    assert row['status'] == 'forbidden_dependency_found'
    assert row['internal_result_register_dependency_excluded'] is False


@pytest.mark.parametrize('opcode,operand', [('P2R.X', 'R2,PR,RZ,0x1'),
                                            ('P2R', 'R2,PR,RZ,0x80')])
def test_unsupported_packed_form_stays_unverified(opcode, operand):
    body = fixture()
    body[112] = dict(opcode=opcode, operands=operand)
    with pytest.raises(ValueError):
        rules.audit(body, 128, {'R2'})
