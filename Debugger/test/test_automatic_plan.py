"""Automatic selection acts on real metadata identities, never operator names."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def planner():
    path = Path(
        __file__).parents[1] / 'python/flagtree_debugger/automatic_plan.py'
    spec = importlib.util.spec_from_file_location('automatic_plan_under_test',
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.plan_operations


def test_bounded_structure_classes_and_input_unchanged(planner):
    names = [
        'arith.constant', 'tt.load', 'arith.addf', 'tt.dot', 'scf.for',
        'tt.store'
    ]
    table = [{
        'opId': i + 1,
        'mlirOpName': name
    } for i, name in enumerate(names)]
    result = planner(table, 3)
    assert set(result['selected_sites']) == {2, 3, 4}
    assert result['candidate_count'] == 4
    assert all('selected' not in row for row in table)
    assert len(result['inventory']) == 6


def test_no_observers_is_actionable_failure(planner):
    with pytest.raises(ValueError,
                       match='no instrumentable internal operations'):
        planner([{'opId': 1, 'mlirOpName': 'arith.constant'}], 8)


@pytest.mark.parametrize('name,synthetic', [
    ('flagtree.debug.operand_capture', True),
    ('flagtree.debug.operand_capture', False),
    ('flagtree_debug.record_summary', False),
    ('arith.addf', True),
])
def test_metadata_only_capture_ids_never_enter_device_plan(
        planner, name, synthetic):
    table = [
        {
            'opId': 901,
            'mlirOpName': name,
            'isSyntheticStatementCapture': synthetic
        },
        {
            'opId': 1,
            'mlirOpName': 'tt.load'
        },
        {
            'opId': 2,
            'mlirOpName': 'arith.addf'
        },
        {
            'opId': 3,
            'mlirOpName': 'tt.store'
        },
    ]
    plan = planner(table, 8)
    assert set(plan['selected_sites']) == {1, 2, 3}
    row = plan['inventory'][0]
    assert not row['automatic_eligible'] and not row['selected']
    assert row[
        'exclusion_reason'] == 'synthetic_metadata_without_device_operation'
    assert table[0]['isSyntheticStatementCapture'] is synthetic


def test_selection_covers_tail_of_ir(planner):
    table = [{'opId': i, 'mlirOpName': 'arith.addf'} for i in range(1, 30)]
    result = planner(table, 4)
    assert 29 in result['selected_sites']
    assert len(result['selected_sites']) == 4


def region(control, index, operation='scf.while', repeated=True):
    return dict(controlId=control,
                parentOpId=100 + control,
                operation=operation,
                regionIndex=index,
                blockIndex=0,
                repeated=repeated)


def test_dynamic_condition_and_body_cannot_be_crowded_out_by_outer_ops(
        planner):
    table = [{'opId': i, 'mlirOpName': 'arith.addf'} for i in range(1, 30)]
    table[11]['controlFlowAncestors'] = [region(1, 0)]
    table[12]['controlFlowAncestors'] = [region(1, 1)]
    result = planner(table, 8)
    assert {12, 13} <= set(result['selected_sites'])
    assert len(result['selected_sites']) == 8
    assert all(row['coverage_status'] == 'direct_representative'
               for row in result['control_regions'])
    assert result['policy_version'] == 3
    assert table[11].get('selected') is None


def test_nested_loops_and_branch_arms_have_independent_region_identity(
        planner):
    outer = region(1, 0, 'scf.for')
    inner = region(2, 0, 'scf.for')
    left = region(3, 0, 'scf.if', False)
    right = region(3, 1, 'scf.if', False)
    ancestry = [[outer], [outer, inner], [outer, inner, left],
                [outer, inner, right]]
    table = [
        dict(opId=index + 1,
             mlirOpName='arith.addf',
             sourceLoc='loc(unknown)',
             controlFlowAncestors=owners)
        for index, owners in enumerate(ancestry)
    ]
    result = planner(table, 4)
    assert set(result['selected_sites']) == {1, 2, 3, 4}
    assert len(result['control_regions']) == 4
    assert all(row['coverage_status'] == 'direct_representative'
               for row in result['control_regions'])


def test_exhausted_control_budget_preserves_uncovered_regions(planner):
    table = [
        dict(opId=i + 1,
             mlirOpName='tt.load',
             controlFlowAncestors=[region(i + 1, 0, 'scf.for')])
        for i in range(10)
    ]
    result = planner(table, 8)
    assert len(result['selected_sites']) == 8
    assert [row['coverage_status']
            for row in result['control_regions']].count('budget_excluded') == 2
    assert len(result['inventory']) == 10


def test_outer_region_prefers_unconditional_position_to_conditional_child(
        planner):
    outer = region(1, 1)
    arm = region(2, 0, 'scf.if', False)
    table = [
        dict(opId=1, mlirOpName='tt.load', controlFlowAncestors=[outer, arm]),
        dict(opId=2, mlirOpName='arith.addi', controlFlowAncestors=[outer])
    ]
    result = planner(table, 1)
    assert result['selected_sites'] == [2]
    assert result['control_regions'][0][
        'coverage_status'] == 'direct_representative'
    assert result['control_regions'][1]['coverage_status'] == 'budget_excluded'
