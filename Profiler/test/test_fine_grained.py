"""The public view preserves identity/clock boundaries and usable origins."""
import importlib
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture
def view(monkeypatch):
    package = ModuleType('public_fine_grained_test')
    package.__path__ = [str(Path(__file__).parents[1] / 'python/flagtree_profiler')]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return importlib.import_module(package.__name__ + '.fine_grained')


def document(verified=True):
    event = {'id': 'actual-record', 'invocation_id': 'launch-4',
             'reconstruction_association': 'verified' if verified else 'unassociated',
             'binary_id': 'binary-sha' if verified else None,
             'actor': 'SM:3/warp:0', 'program': 0, 'site': 2,
             'semantic': 'source_control_interval', 'occurrence': 3,
             'start_tick': 10, 'end_tick': 19, 'duration_ticks': 9,
             'duration_ns': None, 'clock': {'domain': 'SM.clock', 'scope': 'SM:3'},
             'source_region_origin': {'operation': 'arith.addf', 'entry': [
                 {'child': {'file': '<my_kernel>.py', 'line': 14, 'column': 7}}]},
             'compiler_site': {'kind': 'automatic_compiler_operation'}}
    return {'groups': [{'observations': [event], 'native_event_ids': ['native-1']}],
            'captures': [{'capture_id': 'c1', 'loss': {'dropped': 2}}],
            'limits': ['No inferred clock alignment.'], 'rejected': []}


def test_actual_origin_and_clock_are_preserved(view):
    result = view.normalize(document())
    record = result['records'][0]
    assert record['source_locations'] == [{'file': '<my_kernel>.py', 'line': 14, 'column': 7}]
    assert record['operation'] == 'arith.addf'
    assert record['invocation_id'] == 'launch-4'
    assert record['duration_ticks'] == 9 and record['duration_ns'] is None
    assert record['occurrence'] == 3
    assert result['captures'][0]['loss']['dropped'] == 2
    html = view.render(result)
    assert '&lt;my_kernel&gt;.py:14:7' in html
    assert '<my_kernel>' not in html
    assert 'observation_plan.json' in html


def test_unassociated_cannot_borrow_source(view):
    record = view.normalize(document(False))['records'][0]
    assert record['source_locations'] == []
    assert record['association_status'] == 'unassociated'


def test_empty_is_not_success(view):
    data = document()
    data['groups'] = []
    assert view.normalize(data)['status'] == 'no_internal_dynamic_records'


def test_backend_plans_keep_distinct_binary_and_actor_provenance(view):
    report = {'binaries': [
        {'id': 'gcu-binary', 'compiler_metadata': {'debug_automatic_plan':
            {'max_sites': 8, 'selected_sites': [4, 9]}}},
        {'id': 'asc-binary', 'compiler_metadata': {'flagprism_ascend_handoff':
            {'compile_id': 'compile-5', 'artifacts': [
                {'actor': 'AIV', 'metadata': {'module_sha256': 'actor-sha',
                 'operation_plan': {'max_sites': 8, 'inventory': [{'site_id': 3, 'selected': False}]}}}]}}}
    ]}
    plans = view._plans(report, [])['plans']
    assert plans[0]['binary_id'] == 'gcu-binary'
    assert plans[1]['binary_id'] == 'asc-binary'
    assert plans[1]['compile_id'] == 'compile-5'
    assert plans[1]['module_sha256'] == 'actor-sha'
    assert plans[1]['plan']['inventory'][0]['selected'] is False
