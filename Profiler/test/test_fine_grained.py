"""The public view preserves identity/clock boundaries and usable origins."""
import importlib
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture
def view(monkeypatch):
    package = ModuleType('public_fine_grained_test')
    package.__path__ = [
        str(Path(__file__).parents[1] / 'python/flagtree_profiler')
    ]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return importlib.import_module(package.__name__ + '.fine_grained')


def document(verified=True):
    event = {
        'id': 'actual-record',
        'invocation_id': 'launch-4',
        'reconstruction_association':
        'verified' if verified else 'unassociated',
        'binary_id': 'binary-sha' if verified else None,
        'actor': 'SM:3/warp:0',
        'program': 0,
        'site': 2,
        'semantic': 'source_control_interval',
        'occurrence': 3,
        'start_tick': 10,
        'end_tick': 19,
        'duration_ticks': 9,
        'duration_ns': None,
        'clock': {
            'domain': 'SM.clock',
            'scope': 'SM:3'
        },
        'source_region_origin': {
            'operation':
            'arith.addf',
            'entry': [{
                'child': {
                    'file': '<my_kernel>.py',
                    'line': 14,
                    'column': 7
                }
            }]
        },
        'compiler_site': {
            'kind': 'automatic_compiler_operation'
        }
    }
    return {
        'groups': [{
            'observations': [event],
            'native_event_ids': ['native-1']
        }],
        'captures': [{
            'capture_id': 'c1',
            'loss': {
                'dropped': 2
            }
        }],
        'limits': ['No inferred clock alignment.'],
        'rejected': []
    }


def test_actual_origin_and_clock_are_preserved(view):
    result = view.normalize(document())
    record = result['records'][0]
    assert record['source_locations'] == [{
        'file': '<my_kernel>.py',
        'line': 14,
        'column': 7
    }]
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
    report = {
        'binaries': [{
            'id': 'gcu-binary',
            'compiler_metadata': {
                'debug_automatic_plan': {
                    'max_sites': 8,
                    'selected_sites': [4, 9]
                }
            }
        }, {
            'id': 'asc-binary',
            'compiler_metadata': {
                'flagprism_ascend_handoff': {
                    'compile_id':
                    'compile-5',
                    'artifacts': [{
                        'actor': 'AIV',
                        'metadata': {
                            'module_sha256':
                            'actor-sha',
                            'actors': [{
                                'function': 'compiler_function',
                                'actor_kind': 'AIV'
                            }],
                            'operation_plan': {
                                'max_sites': 8,
                                'inventory': [{
                                    'site_id': 3,
                                    'selected': False
                                }]
                            },
                            'control_plan': {
                                'max_sites':
                                None,
                                'inventory': [{
                                    'site_id':
                                    9,
                                    'selected':
                                    True,
                                    'public_semantic':
                                    'control_checkpoint'
                                }]
                            }
                        }
                    }]
                }
            }
        }]
    }
    plans = view._plans(report, [])['plans']
    assert plans[0]['binary_id'] == 'gcu-binary'
    assert plans[1]['binary_id'] == 'asc-binary'
    assert plans[1]['compile_id'] == 'compile-5'
    assert plans[1]['module_sha256'] == 'actor-sha'
    assert plans[1]['plan']['inventory'][0]['selected'] is False
    assert plans[1]['plan_kind'] == 'operation'
    assert plans[1]['compiler_actors'] == [
        dict(function='compiler_function',
             actor_kind='AIV',
             identity='late_llvm:actor-sha:compiler_function',
             runtime_actor_binding=None)
    ]
    assert plans[2]['plan_kind'] == 'control'
    assert plans[2]['binary_id'] == plans[1]['binary_id']
    assert plans[2]['module_sha256'] == plans[1]['module_sha256']
    assert plans[2]['plan']['inventory'][0]['site_id'] == 9
    assert plans[2]['plan']['max_sites'] is None


@pytest.mark.parametrize('verified', [True, False])
def test_actor_proof_is_preserved_only_for_verified_binary_association(
        view, verified):
    data = document(verified)
    event = data['groups'][0]['observations'][0]
    event['actor'] = 2
    proof = dict(status='verified_compiler_emission_manifest',
                 observed_actor_slot=2,
                 runtime_slot_status='verified_against_raw_record_and_segment')
    compiler_actor = dict(id='late_llvm:module:function',
                          kind='AIV',
                          function='function',
                          binding_proof=proof)
    event['compiler_site']['compiler_actor'] = compiler_actor
    normalized = view.normalize(data)
    row, = normalized['records']
    assert row['actor'] == 2
    assert row['compiler_actor'] == (compiler_actor if verified else None)
    page = view.render(normalized)
    assert ('AIV / function (verified compiler binding)' in page) is verified
    if verified:
        row['compiler_actor']['binding_proof']['observed_actor_slot'] = 1
        assert 'verified compiler binding' not in view.render(normalized)


@pytest.mark.parametrize('function',
                         ['compiler_function', 'different_function'])
def test_plan_binding_requires_the_declared_compiler_function(view, function):
    binding = dict(function=function,
                   actor_kind='AIV',
                   module_sha256='module',
                   compile_id='compile',
                   layout='actor_header4_record8_v1')
    manifest = dict(
        module_sha256='module',
        actors=[dict(function='compiler_function', actor_kind='AIV')],
        runtime_actor_binding=binding,
        control_plan=dict(inventory=[]))
    handoff = dict(compile_id='compile', artifacts=[dict(metadata=manifest)])
    report = {
        'binaries': [
            dict(id='binary',
                 compiler_metadata=dict(flagprism_ascend_handoff=handoff))
        ]
    }
    entry, = view._plans(report, [])['plans']
    actual = entry['compiler_actors'][0]['runtime_actor_binding']
    assert actual == (binding if function == 'compiler_function' else None)


def test_control_checkpoint_names_actual_compiler_structure(view):
    data = document()
    event = data['groups'][0]['observations'][0]
    event['semantic'] = 'control_checkpoint'
    event['compiler_site'] = {
        'semantics': 'loop_header_occurrence',
        'source_file': 'loop.py',
        'line': 9,
        'column': 1
    }
    record = view.normalize(data)['records'][0]
    assert record['operation'] == 'loop_header_occurrence'
    assert record['source_locations'][0]['file'] == 'loop.py'
    assert record['semantic'] == 'control_checkpoint'


def test_automatic_empty_selection_is_incomplete_not_native_only_success(
        view, tmp_path):
    (tmp_path / 'ai').mkdir()
    import json
    (tmp_path / 'ai/fine_grained.json').write_text(json.dumps({'records': []}))
    with pytest.raises(RuntimeError, match='incomplete'):
        view.require_automatic_records(tmp_path, {
            'automatic': True,
            'programs': [0]
        })
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert status['status'] == 'incomplete'
    assert status['request']['programs'] == [0]
