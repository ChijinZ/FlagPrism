"""Automatic selection acts on real metadata identities, never operator names."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def planner():
    path = Path(__file__).parents[1] / 'python/flagtree_debugger/automatic_plan.py'
    spec = importlib.util.spec_from_file_location('automatic_plan_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.plan_operations


def test_bounded_structure_classes_and_input_unchanged(planner):
    names = ['arith.constant', 'tt.load', 'arith.addf', 'tt.dot', 'scf.for', 'tt.store']
    table = [{'opId': i + 1, 'mlirOpName': name} for i, name in enumerate(names)]
    result = planner(table, 3)
    assert set(result['selected_sites']) == {2, 3, 4}
    assert result['candidate_count'] == 4
    assert all('selected' not in row for row in table)
    assert len(result['inventory']) == 6


def test_no_observers_is_actionable_failure(planner):
    with pytest.raises(ValueError, match='no instrumentable internal operations'):
        planner([{'opId': 1, 'mlirOpName': 'arith.constant'}], 8)


def test_selection_covers_tail_of_ir(planner):
    table = [{'opId': i, 'mlirOpName': 'arith.addf'} for i in range(1, 30)]
    result = planner(table, 4)
    assert 29 in result['selected_sites']
    assert len(result['selected_sites']) == 4
