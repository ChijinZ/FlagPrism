"""Synthetic finite-rule faults; actual final objects are checked separately."""
import copy

import pytest

from flagtree.profiler.timeline_nvidia_late_boundaries import _source_issue_sites


def fixture(kind='compute_issue_bracket',
            token='fma.rn.f32%f1,%f2,0f3F400000,0f3E000000;',
            opcode='FFMA',
            predicate=None):
    body = {
        pc: dict(opcode=op, operands='', predicate=pred)
        for pc, op, pred in [(0, 'CS2R',
                              None), (16, opcode,
                                      predicate), (32, 'MOV',
                                                   None), (48, 'CS2R', None)]
    }
    return dict(functions={'kernel': body},
                native_lines={('kernel', 2): [16, 32]},
                lines=[
                    'mov.u64%rd1,%globaltimer;', token,
                    'mov.u64%rd2,%globaltimer;'
                ],
                readers={
                    (3, 'entry'): dict(function='kernel', pc=0, ptx_line=1),
                    (3, 'exit'): dict(function='kernel', pc=48, ptx_line=3)
                },
                plan=dict(sites=[
                    dict(site_id=3,
                         kind=kind,
                         record_semantics='observer_issue_bracket')
                ]))


@pytest.mark.parametrize('kind,token,opcode,predicate', [
    ('compute_issue_bracket', 'fma.rn.f32%f1,%f2,0f3F400000,0f3E000000;',
     'FFMA', None),
    ('compute_issue_bracket', 'add.s32%r1,%r2,1;', 'IADD3', None),
    ('global_load_issue_bracket', 'ld.global.b32{%r1},[%rd1];', 'LDG.E', None),
    ('global_store_issue_bracket', '@%p18st.global.b32[%rd1],{%r1};', 'STG.E',
     '@!P2')
])
def test_finite_actual_order_does_not_grant_completion_or_predicate_identity(
        kind, token, opcode, predicate):
    row = _source_issue_sites(**fixture(kind, token, opcode, predicate))[0]
    assert row['status'] == 'source_issue_control_order_checked'
    assert row['begin_reader_pc'] < row['native_pc'] < row['end_reader_pc']
    assert row['native_predicate'] == predicate
    assert row['predicate_identity_verified'] is False
    assert row['source_cost_qualified'] is False
    assert row['byte_transfer_completion_verified'] is False


@pytest.mark.parametrize('fault', [
    'empty_ptx', 'hoisted', 'sunk', 'inside_branch', 'outside_entry',
    'duplicate', 'new_predicate', 'missing_pc', 'opcode', 'semantics'
])
def test_self_consistent_markers_do_not_hide_moved_or_bypassable_work(fault):
    args = copy.deepcopy(fixture())
    body = args['functions']['kernel']
    if fault == 'empty_ptx':
        args['lines'][1] = 'mov.u32%r1,0;'
    elif fault in ('hoisted', 'sunk'):
        pc = -16 if fault == 'hoisted' else 64
        body[pc] = body[16]
        body[16] = dict(opcode='NOP', operands='', predicate=None)
        args['native_lines']['kernel', 2] = [pc]
    elif fault == 'inside_branch':
        body[32] = dict(opcode='BRA', operands='0x30', predicate='@P0')
    elif fault == 'outside_entry':
        body[64] = dict(opcode='BRA', operands='0x10', predicate='@P0')
    elif fault == 'duplicate':
        body[32] = body[16]
    elif fault == 'new_predicate':
        body[16]['predicate'] = '@P0'
    elif fault == 'missing_pc':
        del body[32]
    elif fault == 'opcode':
        body[16]['opcode'] = 'IADD3'
    elif fault == 'semantics':
        args['plan']['sites'][0]['record_semantics'] = 'checkpoint'
    row = _source_issue_sites(**args)[0]
    assert row['status'] == 'unverified' and row['reason']
    assert 'native_pc' not in row
