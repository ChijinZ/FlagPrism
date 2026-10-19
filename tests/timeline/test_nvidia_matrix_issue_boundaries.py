"""Synthetic native/PTX fixtures for the finite matrix issue rule."""
import copy

import pytest
from flagtree.profiler.timeline_nvidia_late_boundaries import _matrix_issue_sites


def fixture(count=4):
    token = ('mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32'
             '{%r0,%r1,%r2,%r3},{%r4,%r5,%r6,%r7},{%r8,%r9},'
             '{%r0,%r1,%r2,%r3};')
    end = (count + 1) * 16
    body = {0: dict(opcode='CS2R'), end: dict(opcode='CS2R')}
    body.update({
        (i + 1) * 16: dict(opcode='HMMA.16816.F32')
        for i in range(count)
    })
    readers = {
        (7, phase): dict(function='kernel', pc=pc, ptx_line=line)
        for phase, pc, line in [('entry', 0, 1), ('exit', end, count + 2)]
    }
    return dict(functions={'kernel': body},
                native_lines={
                    ('kernel', i + 2): [(i + 1) * 16]
                    for i in range(count)
                },
                lines=['mov.u64'] + [token] * count + ['mov.u64'],
                readers=readers,
                plan=dict(sites=[
                    dict(site_id=7,
                         kind='matrix_issue_bracket',
                         record_semantics='observer_issue_bracket',
                         members=[{}] * count)
                ]))


@pytest.mark.parametrize('count', [1, 4])
def test_supported_matrix_issues(count):
    row = _matrix_issue_sites(**fixture(count))[0]
    assert row['status'] == 'matrix_issue_control_order_checked'
    assert len(row['issues']) == count
    assert row['source_cost_qualified'] is False
    assert row['matrix_completion_verified'] is False
    assert row['hardware_busy_qualified'] is False
    assert row['participation_verified'] is False


@pytest.mark.parametrize('mutation', [
    'different_geometry', 'predicated_ptx', 'predicated_reader',
    'predicated_matrix', 'aliased_pc', 'missing_native', 'outside_readers',
    'unknown_extra_matrix', 'missing_member', 'internal_branch',
    'external_entry'
])
def test_invalid_matrix_boundary_stays_unverified(mutation):
    args = copy.deepcopy(fixture())
    body = args['functions']['kernel']
    if mutation == 'different_geometry':
        args['lines'][1] = args['lines'][1].replace('m16n8k16', 'm16n8k32')
    elif mutation == 'predicated_ptx':
        args['lines'][1] = '@%p0' + args['lines'][1]
    elif mutation == 'predicated_reader':
        args['readers'][7, 'entry']['sass_predicate'] = '@P0'
    elif mutation == 'predicated_matrix':
        body[16]['predicate'] = '@P0'
    elif mutation == 'aliased_pc':
        args['native_lines']['kernel', 3] = [16]
    elif mutation == 'missing_native':
        args['native_lines']['kernel', 2] = []
    elif mutation == 'outside_readers':
        args['native_lines']['kernel', 2] = [96]
        body[96] = dict(opcode='HMMA.16816.F32')
    elif mutation in ('unknown_extra_matrix', 'internal_branch'):
        args['functions']['kernel'] = {
            pc + 16 if pc >= 32 else pc: row
            for pc, row in body.items()
        }
        body = args['functions']['kernel']
        for key, values in args['native_lines'].items():
            args['native_lines'][key] = [
                pc + 16 if pc >= 32 else pc for pc in values
            ]
        args['readers'][7, 'exit']['pc'] += 16
        body[32] = (dict(
            opcode='IMMA.16816.S32') if mutation == 'unknown_extra_matrix' else
                    dict(opcode='BRA', operands='0x50'))
    elif mutation == 'missing_member':
        args['plan']['sites'][0]['members'].pop()
    else:
        body[96] = dict(opcode='BRA', operands='0x20')
    row = _matrix_issue_sites(**args)[0]
    assert row['status'] == 'unverified'
    assert row['reason']
    assert row['source_cost_qualified'] is False
    assert row['hardware_busy_qualified'] is False
