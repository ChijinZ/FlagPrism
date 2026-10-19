"""Synthetic native control graphs; these do not execute device kernels."""
import copy

import pytest

from flagtree.profiler.timeline_nvidia_loops import inspect_native_loops


def fixture():
    body = {pc: dict(opcode='NOP') for pc in range(0, 112, 16)}
    body[32] = dict(opcode='CS2R')
    body[48] = dict(opcode='HMMA.16816.F32')
    body[64] = dict(opcode='CS2R')
    body[80] = dict(opcode='BRA', operands='0x10', predicate='@P0')
    body[96] = dict(opcode='EXIT')
    boundary = dict(site_id=7,
                    kind='matrix_issue_bracket',
                    function='kernel',
                    status='matrix_issue_control_order_checked',
                    begin_reader_pc=32,
                    end_reader_pc=64)
    return dict(functions={'kernel': body},
                boundaries=[boundary],
                binary_id='b' * 64)


@pytest.mark.parametrize('variant', [
    'simple', 'forward_detour', 'two_latches', 'innermost', 'scalar',
    'never_taken_exit', 'exit_after_pair'
])
def test_native_iteration_reader_paths(variant):
    args = fixture()
    body, boundary = args['functions']['kernel'], args['boundaries'][0]
    if variant == 'forward_detour':
        body[16] = dict(opcode='BRA', operands='0x70', predicate='@P1')
        body[112] = dict(opcode='NOP')
        body[128] = dict(opcode='BRA', operands='0x20')
    elif variant == 'two_latches':
        body[96] = dict(opcode='BRA', operands='0x10', predicate='@P1')
        body[112] = dict(opcode='EXIT')
    elif variant == 'innermost':
        body[80]['operands'] = '0x20'
        body[96] = dict(opcode='BRA', operands='0x10', predicate='@P1')
        body[112] = dict(opcode='EXIT')
    elif variant == 'never_taken_exit':
        body[16] = dict(opcode='EXIT', predicate='@!PT')
    elif variant == 'exit_after_pair':
        body[80] = dict(opcode='EXIT', predicate='@P1')
        body[96] = dict(opcode='BRA', operands='0x10', predicate='@P0')
        body[112] = dict(opcode='EXIT')
    elif variant == 'scalar':
        body[48]['opcode'] = 'FFMA'
        boundary.update(kind='compute_issue_bracket',
                        status='source_issue_control_order_checked')
    row = inspect_native_loops(**args)[0]
    assert row['status'] == 'native_iteration_control_checked'
    assert row['native_iteration_boundaries_verified'] is True
    assert row['loop_header_pc'] == (32 if variant == 'innermost' else 16)
    assert row['latch_pcs'] == ([80, 96] if variant == 'two_latches' else
                                [96] if variant == 'exit_after_pair' else [80])
    assert row['exit_instruction_pcs'] == ([80] if variant == 'exit_after_pair'
                                           else [])
    assert row['begin_reader_pc'] == 32 and row['end_reader_pc'] == 64
    assert row['source_iteration_identity_verified'] is False
    assert row['source_cost_qualified'] is False
    assert row['participation_verified'] is False
    assert row['hardware_overlap_verified'] is False
    changed = copy.deepcopy(args)
    changed['binary_id'] = 'c' * 64
    assert inspect_native_loops(
        **changed)[0]['native_loop_id'] != row['native_loop_id']


@pytest.mark.parametrize('mutation', [
    'exit_before_pair', 'bypass_begin', 'bypass_end', 'repeat_end',
    'multi_entry', 'no_loop', 'no_exit', 'unknown_branch', 'unverified_issue',
    'unreachable_pair', 'same_endpoint', 'oversized_function',
    'conditional_exit_before_pair', 'conditional_exit_before_end'
])
def test_incomplete_or_ambiguous_native_iteration(mutation):
    args = fixture()
    body, boundary = args['functions']['kernel'], args['boundaries'][0]
    if mutation == 'exit_before_pair':
        # The issue bracket itself is still a straight single-entry path;
        # only the new loop exit check can reject this earlier break.
        body[16] = dict(opcode='BRA', operands='0x60', predicate='@P1')
    elif mutation == 'bypass_begin':
        body[16] = dict(opcode='BRA', operands='0x40', predicate='@P1')
    elif mutation == 'bypass_end':
        body[48] = dict(opcode='BRA', operands='0x50', predicate='@P1')
    elif mutation == 'repeat_end':
        body[80]['operands'] = '0x40'
        body[96] = dict(opcode='BRA', operands='0x10', predicate='@P1')
        body[112] = dict(opcode='EXIT')
    elif mutation == 'multi_entry':
        body[0] = dict(opcode='BRA', operands='0x30', predicate='@P1')
    elif mutation == 'no_loop':
        body[80] = dict(opcode='NOP')
    elif mutation == 'no_exit':
        del body[80]['predicate']
    elif mutation == 'unknown_branch':
        body[80] = dict(opcode='BRX', operands='R0')
    elif mutation == 'unverified_issue':
        boundary['status'] = 'unverified'
    elif mutation == 'unreachable_pair':
        body[0] = dict(opcode='BRA', operands='0x60')
    elif mutation == 'conditional_exit_before_pair':
        body[16] = dict(opcode='EXIT', predicate='@P1')
    elif mutation == 'conditional_exit_before_end':
        body[48] = dict(opcode='EXIT', predicate='@P1')
    elif mutation == 'same_endpoint':
        boundary['end_reader_pc'] = boundary['begin_reader_pc']
    else:
        args['functions']['kernel'] = {
            pc: dict(opcode='NOP')
            for pc in range(0, 4097 * 16, 16)
        }
    row = inspect_native_loops(**args)[0]
    assert row['status'] == 'unverified'
    assert row['reason']
    assert row['native_iteration_boundaries_verified'] is False
    assert row['source_iteration_identity_verified'] is False
    assert row['source_cost_qualified'] is False
    assert row['participation_verified'] is False
    assert row['hardware_overlap_verified'] is False


def test_failure_in_another_function_does_not_erase_valid_loop():
    args = fixture()
    args['functions']['bad'] = {0: dict(opcode='CALL', operands='0x10')}
    args['boundaries'].append(
        dict(args['boundaries'][0], site_id=8, function='bad'))
    rows = inspect_native_loops(**args)
    assert [row['status'] for row in rows
            ] == ['native_iteration_control_checked', 'unverified']
