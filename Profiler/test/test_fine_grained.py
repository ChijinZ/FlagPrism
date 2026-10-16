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


def test_counter_report_presents_visits_and_role_without_empty_time_columns(
        view):
    import copy
    data = view.normalize(document())
    row = data['records'][0]
    row.update(semantic='counter',
               storage='source_site_census_v1',
               count=5,
               count_exact=True,
               site_role='primary',
               actor={
                   'kind': 'logical_warp',
                   'id': 0,
                   'writer': 'physical_thread_zero'
               },
               binary_id='0123456789abcdef' * 4,
               clock=None,
               start_tick=None,
               end_tick=None,
               duration_ticks=None)
    before = copy.deepcopy(data)
    rendered = view.render(data)
    assert '<th>Visits</th>' in rendered and '<th>Site role</th>' in rendered
    assert '<th>Start tick</th>' not in rendered
    assert '<th>Retained occurrence</th>' not in rendered
    assert '<td>warp 0</td>' in rendered and '<td>5</td>' in rendered
    assert 'title="' + row['binary_id'] + '"' in rendered
    assert 'data-binary="' + row['binary_id'] + '"' in rendered
    assert data == before


def test_timed_report_retains_actual_clock_and_time_columns(view):
    rendered = view.render(view.normalize(document()))
    assert '<th>Start tick</th>' in rendered and '<th>Clock scope</th>' in rendered
    assert '<td>SM:3/warp:0</td>' in rendered


def test_unassociated_cannot_borrow_source(view):
    record = view.normalize(document(False))['records'][0]
    assert record['source_locations'] == []
    assert record['association_status'] == 'unassociated'


@pytest.mark.parametrize('field', ['source_loc', 'sourceLoc'])
def test_inline_library_operation_keeps_user_callsite_in_public_report(
        view, field):
    data = document()
    event = data['groups'][0]['observations'][0]
    event['source_region_origin'] = {
        field: 'loc(callsite("/installed/standard.py":309:36 at '
        '"reduce"("/user/kernel.py":40:55)))',
        'source_locations': [{
            'file': '/installed/standard.py',
            'line': 309
        }],
    }
    row = view.normalize(data)['records'][0]
    assert {
        'file': '/user/kernel.py',
        'line': 40,
        'column': 55
    } in row['source_locations']
    assert {
        'file': '/installed/standard.py',
        'line': 309,
        'column': 36
    } in row['source_locations']
    assert any(candidate['file'] == '/user/kernel.py'
               and candidate['role'] == 'compiler_location_candidate'
               for candidate in row['source_location_candidates'])
    assert '/user/kernel.py:40:55' in view.render(view.normalize(data))
    event['reconstruction_association'] = 'unassociated'
    assert view.normalize(data)['records'][0]['source_locations'] == []


def test_fused_nested_callsites_preserve_escaped_paths_without_guessing_aliases(
        view):
    data = document()
    data['groups'][0]['observations'][0]['source_region_origin'] = {
        'source_loc':
        'loc(fused[callsite("/lib/a.py":2:3 at '
        'callsite("/lib/b.py":4:5 at "/user/with\\20space.py":6:7)), #missing])'
    }
    row = view.normalize(data)['records'][0]
    assert {(loc['file'], loc['line'], loc['column'])
            for loc in row['source_locations']} == {('/lib/a.py', 2, 3),
                                                    ('/lib/b.py', 4, 5),
                                                    ('/user/with space.py', 6,
                                                     7)}


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


def automatic_capture(capture, invocation, binary, *, runtime_owned=False):
    if not runtime_owned:
        return dict(capture_id=capture,
                    invocation_id=invocation,
                    binary_id=binary)
    return dict(capture_id=capture,
                runtime_metadata=dict(
                    profiler_invocation_id=invocation,
                    profiler_association_evidence=dict(
                        invocation_id=invocation,
                        binary_id=binary,
                        evidence='same_launch_metadata_object')))


def automatic_record(capture, invocation, binary, *, located=True):
    return dict(capture_id=capture,
                invocation_id=invocation,
                binary_id=binary,
                operation='arith.addf',
                association_status='verified',
                semantic='source_control_interval',
                source_locations=[dict(file='ordinary.py', line=4, column=2)]
                if located else [])


def write_automatic_input(tmp_path, captures, records, launches=None):
    import json
    (tmp_path / 'ai').mkdir()
    (tmp_path / 'ai/fine_grained.json').write_text(
        json.dumps(
            dict(captures=captures,
                 records=records,
                 status='dynamic_records_available')))
    if launches is not None:
        (tmp_path / 'ai/launches.json').write_text(json.dumps(launches))


@pytest.mark.parametrize('runtime_owned', [False, True])
@pytest.mark.parametrize('second_binary', ['binary-A', 'binary-B'])
def test_valid_kernel_cannot_mask_empty_capture(view, tmp_path, runtime_owned,
                                                second_binary):
    import json
    captures = [
        automatic_capture('c-A',
                          'launch-A',
                          'binary-A',
                          runtime_owned=runtime_owned),
        automatic_capture('c-B',
                          'launch-B',
                          second_binary,
                          runtime_owned=runtime_owned)
    ]
    write_automatic_input(tmp_path, captures,
                          [automatic_record('c-A', 'launch-A', 'binary-A')])
    with pytest.raises(RuntimeError, match='incomplete'):
        view.require_automatic_records(tmp_path, {'automatic': True})
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert status['status'] == 'incomplete'
    a, b = status['captures']
    assert a['status'] == 'complete' and a['source_linked_records'] == 1
    assert b['capture_id'] == 'c-B' and b['invocation_id'] == 'launch-B'
    assert b['status'] == 'incomplete' and b['source_linked_records'] == 0


@pytest.mark.parametrize('runtime_owned', [False, True])
def test_every_invocation_of_same_binary_needs_its_own_capture(
        view, tmp_path, runtime_owned):
    import json
    captures = [
        automatic_capture('c-A',
                          'launch-A',
                          'binary',
                          runtime_owned=runtime_owned),
        automatic_capture('c-B',
                          'launch-B',
                          'binary',
                          runtime_owned=runtime_owned)
    ]
    records = [
        automatic_record('c-A', 'launch-A', 'binary'),
        automatic_record('c-B', 'launch-B', 'binary')
    ]
    launches = [
        dict(id='launch-A', binary_id='binary'),
        dict(id='launch-B', binary_id='binary')
    ]
    write_automatic_input(tmp_path, captures, records, launches)
    view.require_automatic_records(tmp_path, {'automatic': True})
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert status['status'] == 'complete'
    assert len(status['captures']) == 2
    assert all(row['source_linked_records'] == 1 for row in status['captures'])


def test_expected_launch_without_capture_is_incomplete(view, tmp_path):
    import json
    write_automatic_input(tmp_path,
                          [automatic_capture('c-A', 'launch-A', 'binary')],
                          [automatic_record('c-A', 'launch-A', 'binary')], [
                              dict(id='launch-A', binary_id='binary'),
                              dict(id='launch-B', binary_id='binary')
                          ])
    with pytest.raises(RuntimeError,
                       match='invocation_has_no_internal_capture'):
        view.require_automatic_records(tmp_path, {'automatic': True})
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert status['captures'][-1]['invocation_id'] == 'launch-B'


@pytest.mark.parametrize('mismatch',
                         ['capture', 'invocation', 'binary', 'source'])
def test_record_cannot_borrow_identity_or_source_from_another_capture(
        view, tmp_path, mismatch):
    import json
    record = automatic_record('c-A', 'launch-A', 'binary')
    if mismatch == 'source':
        record['source_locations'] = []
    else:
        record[{
            'capture': 'capture_id',
            'invocation': 'invocation_id',
            'binary': 'binary_id'
        }[mismatch]] = 'another'
    write_automatic_input(tmp_path,
                          [automatic_capture('c-A', 'launch-A', 'binary')],
                          [record])
    with pytest.raises(RuntimeError, match='incomplete'):
        view.require_automatic_records(tmp_path, {'automatic': True})
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert status['captures'][0]['source_linked_records'] == 0


def test_partial_automatic_html_names_the_missing_capture(view, tmp_path):
    import json
    data = view.normalize(document())
    data['records'][0]['capture_id'] = 'c-A'
    data['captures'] = [
        automatic_capture('c-A', 'launch-4', 'binary-sha'),
        automatic_capture('c-B', 'launch-5', 'binary-sha')
    ]
    (tmp_path / 'ai').mkdir()
    (tmp_path / 'report').mkdir()
    (tmp_path / 'ai/fine_grained.json').write_text(json.dumps(data))
    html = tmp_path / 'report/fine_grained.html'
    html.write_text(view.render(data))
    with pytest.raises(RuntimeError, match='incomplete'):
        view.require_automatic_records(tmp_path, {'automatic': True})
    rendered = html.read_text()
    assert 'Automatic capture coverage' in rendered
    assert 'c-B' in rendered and 'launch-5' in rendered
    assert 'incomplete_automatic_capture' in rendered
    assert '../ai/selection_status.json' in rendered


def test_raw_capture_references_preserve_automatic_gate_and_loss(
        view, tmp_path):
    import json
    refs = importlib.import_module(view.__package__ + '.export_refs')
    capture = automatic_capture('c-A',
                                'launch-A',
                                'binary-A',
                                runtime_owned=True)
    capture.update(raw_base64='retained-raw-' * 1024,
                   raw_sha256='raw-digest',
                   dropped=7,
                   counter_saturated=True)
    records = [automatic_record('c-A', 'launch-A', 'binary-A')]
    write_automatic_input(tmp_path, [capture], records)
    path = tmp_path / 'ai/fine_grained.json'
    original = {'captures': [capture], 'observations': []}
    (tmp_path / 'ai/observations.json').write_text(json.dumps(original))
    before = json.loads(path.read_text())
    path.write_text(
        json.dumps(refs.compact(before, original, fields={'raw_base64'})))
    view.require_automatic_records(tmp_path, {'automatic': True})
    exported = json.loads(path.read_text())
    restored = refs.restore(exported, original)
    assert restored['records'] == records
    assert restored['captures'] == [capture]
    assert restored['automatic_selection_status']['status'] == 'complete'
    assert '$observation_ref' in exported['captures'][0]['raw_base64']
    assert exported['captures'][0]['dropped'] == 7
    assert exported['captures'][0]['counter_saturated'] is True


@pytest.mark.parametrize('role,exact,expected', [
    ('primary', True, True),
    ('context', True, False),
    ('primary', False, False),
])
def test_census_gate_requires_source_linked_exact_primary_count(
        view, tmp_path, role, exact, expected):
    capture = automatic_capture('c-A', 'launch-A', 'binary-A')
    record = automatic_record('c-A', 'launch-A', 'binary-A')
    record.update(storage='source_site_census_v1',
                  semantic='counter',
                  site_role=role,
                  count=5,
                  count_exact=exact,
                  overflow=not exact)
    write_automatic_input(tmp_path, [capture], [record])
    request = dict(automatic=True, program_policy='all_grid_census')
    if expected:
        view.require_automatic_records(tmp_path, request)
    else:
        with pytest.raises(RuntimeError, match='incomplete'):
            view.require_automatic_records(tmp_path, request)


@pytest.mark.parametrize('backend', ['gcu', 'ascend'])
def test_census_gate_checks_overflow_in_programs_not_expanded_for_display(
        view, tmp_path, backend):
    capture = automatic_capture('c-A', 'launch-A', 'binary-A')
    census = {'loss': {'overflow_cells': 1, 'exact': False}}
    if backend == 'ascend':
        capture = automatic_capture('c-A',
                                    'launch-A',
                                    'binary-A',
                                    runtime_owned=True)
        capture['runtime_metadata']['ascend_source_census'] = census
    else:
        capture['source_census'] = census
    record = automatic_record('c-A', 'launch-A', 'binary-A')
    record.update(storage='source_site_census_v1',
                  semantic='counter',
                  site_role='primary',
                  count=5,
                  count_exact=True,
                  overflow=False)
    write_automatic_input(tmp_path, [capture], [record])
    with pytest.raises(RuntimeError, match='source_census_count_overflow'):
        view.require_automatic_records(
            tmp_path, dict(automatic=True, program_policy='all_grid_census'))


def test_census_coverage_counts_located_context_without_accepting_it_as_body(
        view, tmp_path):
    import json
    capture = automatic_capture('c-A', 'launch-A', 'binary-A')
    rows = []
    for role in ('context', 'primary'):
        row = automatic_record('c-A', 'launch-A', 'binary-A')
        row.update(storage='source_site_census_v1',
                   semantic='counter',
                   site_role=role,
                   count=2,
                   count_exact=True,
                   overflow=False)
        rows.append(row)
    write_automatic_input(tmp_path, [capture], rows)
    view.require_automatic_records(tmp_path, {'automatic': True})
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert status['captures'][0]['source_linked_records'] == 2
    assert status['captures'][0]['status'] == 'complete'


def test_capture_html_links_complete_raw_without_inlining_it(view):
    data = view.normalize(document())
    data['captures'] = [{
        'capture_id': 'capture-raw',
        'dropped': 7,
        'raw_base64': 'unique-base64-' * 4096,
        'runtime_metadata': {
            'large': 'unique-runtime-' * 4096
        }
    }]
    html = view.render(data)
    assert 'unique-base64-' not in html
    assert 'unique-runtime-' not in html
    assert '../ai/observations.json' in html
    assert 'capture-raw' in html and 'dropped' in html


def test_candidate_status_distinguishes_retention_selection_and_scope_identity(
        view):
    capture = dict(capture_id='capture',
                   binary_id='binary',
                   invocation_id='launch',
                   automatic_plan={
                       'inventory': [
                           dict(scope_id=2,
                                selected=True,
                                candidate_ordinal=0,
                                candidate_class='control_region',
                                operation='scf.if'),
                           dict(scope_id=3,
                                selected=True,
                                candidate_ordinal=1,
                                candidate_class='control_computation',
                                operation='arith.addi'),
                           dict(scope_id=None,
                                selected=False,
                                candidate_ordinal=2,
                                selection_reason='site_budget_excluded'),
                           dict(scope_id=None,
                                selected=True,
                                candidate_ordinal=3)
                       ]
                   })
    record = automatic_record('capture', 'launch', 'binary')
    record['site'] = 2
    other = dict(record, capture_id='other', site=3)
    other_binary = dict(record, binary_id='other', site=3)
    rows = view.candidate_observation_status([capture],
                                             [record, other, other_binary])
    assert [row['status'] for row in rows] == [
        'observed_retained_records', 'selected_no_retained_records',
        'site_budget_excluded', 'unbound_scope_identity'
    ]
    assert [row['retained_records'] for row in rows] == [1, 0, 0, 0]
    data = view.normalize(document())
    data['candidate_observation_status'] = rows
    html = view.render(data)
    assert all(row['status'] in html for row in rows)
    assert 'control_region' in html and 'control_computation' in html
    assert 'conditional body' in html
    assert 'notexecuted' not in html
