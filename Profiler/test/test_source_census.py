"""Raw-count, layout, and identity oracles, independent of device scheduling."""
import hashlib
import base64
import importlib
from pathlib import Path
import struct
import sys
from types import ModuleType

import pytest

package = ModuleType('source_census_contract_test')
package.__path__ = [
    str(Path(__file__).parents[1] / 'python/flagtree_profiler')
]
sys.modules[package.__name__] = package
census = importlib.import_module(package.__name__ + '.source_census')
contract = importlib.import_module(package.__name__ + '.observations')


def capture(rows, *, stride=8, actors=None):
    """Rows are programs, each containing the two actual compiler-site counts."""
    actor_list = actors or [dict(kind='logical_warp', id=0)]
    raw = bytearray(32 + len(rows) * len(actor_list) * 2 * stride)
    for program, values in enumerate(rows):
        for actor in range(len(actor_list)):
            for site, count in enumerate(values):
                offset = 32 + (
                    (program * len(actor_list) + actor) * 2 + site) * stride
                struct.pack_into('<II', raw, offset, count, int(bool(count)))
    raw = bytes(raw)
    descriptor = dict(schema=census.SCHEMA,
                      version=1,
                      cell_size=8,
                      byte_order='little',
                      grid=[len(rows), 1, 1],
                      program_count=len(rows),
                      cells_offset=32,
                      site_stride=stride,
                      actor_stride=2 * stride,
                      program_stride=len(actor_list) * 2 * stride,
                      raw_sha256=hashlib.sha256(raw).hexdigest(),
                      actors=actor_list,
                      sites=[
                          dict(site=17,
                               role='context',
                               origin={'operation': 'entry'}),
                          dict(site=41,
                               role='primary',
                               origin={
                                   'operation': 'loop_body',
                                   'file': 'user.py',
                                   'line': 12
                               })
                      ])
    return raw, descriptor


def decode(raw, descriptor, **kwargs):
    return census.decode_source_census(raw,
                                       descriptor,
                                       capture_id='capture',
                                       invocation_id='call',
                                       binary_id='actual-binary',
                                       **kwargs)


@pytest.mark.parametrize('layout,hazard', [('ascend_source_census_v1', True),
                                           ('ascend_source_census_v2', True),
                                           ('ascend_source_census_v3', False),
                                           ('gcu_site_census_v1', False),
                                           ('nvidia_source_census_v1', False)])
@pytest.mark.parametrize('placement', ['record_layout', 'compiler_actor'])
def test_known_legacy_ascend_transport_retracts_exact_without_changing_raw(
        layout, hazard, placement):
    raw, desc = capture([[0, 5]])
    if placement == 'record_layout':
        desc['record_layout'] = layout
    else:
        desc['actors'][0]['compiler_actor'] = dict(runtime_actor_binding=dict(
            layout=layout))
    reader = census.CensusReader(raw, desc)
    assert reader.raw == raw and reader.descriptor == desc
    assert reader.cell(0, 0, 0)['exact'] == (not hazard)
    assert reader.cell(0, 0,
                       0)['zero_execution_status'] == ('unknown' if hazard else
                                                       'not_applicable')
    result = decode(raw, desc)
    assert result['loss']['exact'] == (not hazard)
    assert result['loss']['unknown_loss'] == hazard
    assert result['summary']['unknown_loss'] == hazard
    assert result['observations'][0]['count_exact'] == (not hazard)
    assert result['observations'][0]['unknown_loss'] == hazard
    assert result['observations'][0]['count'] == 5


def test_legacy_visibility_hazard_does_not_reinterpret_saturation_flag():
    raw, desc = capture([[0, 0xffffffff]])
    raw = bytearray(raw)
    struct.pack_into('<II', raw, 40, 0xffffffff, 3)
    raw = bytes(raw)
    desc['raw_sha256'] = hashlib.sha256(raw).hexdigest()
    desc['record_layout'] = 'ascend_source_census_v2'
    result = decode(raw, desc)
    assert result['loss']['overflow_cells'] == 1
    assert result['loss']['unknown_loss'] is True
    assert result['observations'][0]['overflow'] is True
    assert result['observations'][0]['count'] == 0xffffffff


@pytest.mark.parametrize('stride', [8, 64])
def test_inactive_program_zero_selects_actual_active_instance_and_retains_raw(
        stride):
    raw, desc = capture([[1, 0], [1, 0], [1, 5], [1, 2]], stride=stride)
    result = decode(
        raw,
        desc,
        association_evidence={'source': 'same_launch_metadata_object'})
    assert result['summary']['selected_program'] == 2
    assert result['summary']['primary_observed_programs'] == 2
    assert [(row['site'], row['count'])
            for row in result['observations']] == [(17, 1), (41, 5)]
    row = result['observations'][1]
    assert row['program'] == 2 and row['actor'] == dict(kind='logical_warp',
                                                        id=0)
    assert row['semantic'] == 'counter' and row['occurrence'] is None
    assert row['duration_ticks'] is None and row['duration_ns'] is None
    assert row['clock'] is None and row['mask_activity'] == 'unobserved'
    reader = census.CensusReader(raw, desc)
    assert reader.cell(3, 0, 1)['count'] == 2
    assert reader.cell(0, 0, 1)['visited'] is False


def test_two_calls_keep_exact_runtime_counts_without_expanding_fake_intervals(
):
    calls = [decode(*capture([[1, 0], [1, count]])) for count in (2, 5)]
    assert [len(call['observations']) for call in calls] == [2, 2]
    assert [call['observations'][1]['count'] for call in calls] == [2, 5]
    assert all(call['observations'][1]['association_status'] == 'unassociated'
               for call in calls)


def test_context_only_is_not_primary_detail_or_evidence_of_body_execution():
    result = decode(*capture([[1, 0], [1, 0]]))
    assert result['observations'] == []
    assert result['summary']['status'] == 'no_primary_visits'
    assert result['summary']['observed_programs'] == 2


def test_actor_namespaces_are_kept_separate_not_summed():
    raw, desc = capture([[1, 2]],
                        actors=[
                            dict(kind='logical_warp', id=0),
                            dict(kind='logical_warp', id=1)
                        ])
    events = decode(raw, desc)['observations']
    assert [(event['actor']['id'], event['count']) for event in events
            if event['site'] == 41] == [(0, 2), (1, 2)]


@pytest.mark.parametrize('flags,count', [(4, 2), (0, 2), (1, 0), (3, 2),
                                         (2, 0)])
def test_bad_cell_in_unselected_program_is_rejected(flags, count):
    raw, desc = capture([[1, 2], [1, 0]])
    changed = bytearray(raw)
    struct.pack_into('<II', changed, 56, count, flags)
    raw = bytes(changed)
    desc['raw_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match='count/flags'):
        decode(raw, desc)


def test_saturation_remains_one_lower_bound_counter_and_marks_capture_inexact(
):
    raw, desc = capture([[1, census.UINT32_MAX]])
    changed = bytearray(raw)
    struct.pack_into('<II', changed, 40, census.UINT32_MAX, 3)
    raw = bytes(changed)
    desc['raw_sha256'] = hashlib.sha256(raw).hexdigest()
    result = decode(raw, desc)
    assert result['loss']['exact'] is False and result['loss'][
        'overflow_cells'] == 1
    assert result['observations'][1]['count_exact'] is False


@pytest.mark.parametrize('change', [
    {
        'site_stride': 4
    },
    {
        'actor_stride': 8
    },
    {
        'program_stride': 8
    },
    {
        'cells_offset': 33
    },
    {
        'program_count': 99
    },
    {
        'version': True
    },
    {
        'grid': [True, 1, 1]
    },
    {
        'byte_order': 'big'
    },
    {
        'raw_sha256': '0' * 64
    },
    {
        'sites': [{
            'site': 1,
            'role': 'primary'
        }, {
            'site': 1,
            'role': 'context'
        }]
    },
    {
        'actors': [{
            'kind': 'physical_sm',
            'id': 0
        }]
    },
])
def test_invalid_layout_does_not_decode_as_valid_counts(change):
    raw, desc = capture([[1, 2], [1, 0]])
    desc.update(change)
    with pytest.raises(ValueError):
        decode(raw, desc)


def test_truncation_and_budgets_are_checked_without_sampling_or_partial_results(
):
    raw, desc = capture([[1, 2], [1, 0]])
    with pytest.raises(ValueError, match='byte budget'):
        decode(raw, desc, max_bytes=len(raw) - 1)
    with pytest.raises(ValueError, match='cell budget'):
        decode(raw, desc, max_cells=3)
    raw = raw[:-1]
    desc['raw_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match='truncated'):
        decode(raw, desc)


def test_bound_descriptor_and_caller_identity_cannot_disagree():
    raw, desc = capture([[1, 2]])
    desc['binary_id'] = 'another-binary'
    with pytest.raises(ValueError, match='identity'):
        decode(raw, desc)
    desc.pop('binary_id')
    with pytest.raises(ValueError, match='evidence binary'):
        decode(raw, desc, association_evidence={'binary_id': 'another-binary'})


def test_descriptor_mutation_cannot_change_previously_validated_reader():
    raw, desc = capture([[1, 2]])
    reader = census.CensusReader(raw, desc)
    desc['sites'][1]['site'] = 99
    reader.descriptor['sites'][1]['site'] = 100
    reader.summary['selected_program'] = 99
    assert reader.cell(0, 0, 1)['site'] == 41
    assert reader.summary['selected_program'] == 0


def test_census_request_is_explicit_and_legacy_serialization_stays_stable():
    old = contract.ObservationRequest()
    assert 'program_policy' not in old.as_dict()
    request = contract.ObservationRequest(semantics=('counter', ),
                                          programs=None,
                                          automatic=True,
                                          program_policy='all_grid_census')
    assert contract.ObservationRequest.from_dict(request.as_dict()) == request
    assert contract.ObservationRequest.from_dict(old.as_dict()) == old


def test_ir_adapter_retains_full_raw_and_never_emits_legacy_snapshot_records():
    raw, descriptor = capture([[1, 0], [1, 5]])
    run = dict(source_census={'descriptor': descriptor},
               raw_base64=base64.b64encode(raw).decode('ascii'),
               runtime_metadata=dict(capture_id='capture',
                                     profiler_invocation_id='call',
                                     profiler_association_evidence=dict(
                                         binary_id='actual-binary')),
               decoded={'records': [dict(record_kind='TIMELINE', op_id=999)]})
    rows = contract.from_ir_runs([run])
    assert [(row['program'], row['site'], row['count'])
            for row in rows] == [(1, 17, 1), (1, 41, 5)]
    metadata = contract.ir_source_census_metadata(run, capture_id='capture')
    assert metadata['summary']['program_count'] == 2
    assert 'raw_base64' not in metadata and run[
        'raw_base64'] == base64.b64encode(raw).decode('ascii')


def test_ir_adapter_uses_actual_explicit_compiler_budget_without_raising_defaults(
):
    raw, descriptor = capture([[1, 2]])
    raw += bytes(8388608 + 8 - len(raw))
    descriptor.update(raw_sha256=hashlib.sha256(raw).hexdigest(),
                      max_census_bytes=len(raw),
                      max_census_cells=1048576)
    request = contract.ObservationRequest(semantics=('counter', ),
                                          programs=None,
                                          program_policy='all_grid_census',
                                          max_census_bytes=len(raw))
    run = dict(source_census={'descriptor': descriptor},
               raw_base64=base64.b64encode(raw).decode('ascii'),
               runtime_metadata=dict(capture_id='capture',
                                     profiler_invocation_id='call',
                                     profiler_association_evidence={
                                         'binary_id': 'actual-binary'
                                     },
                                     source_census_request=request.as_dict()))
    assert contract.decode_ir_source_census(
        run)['observations'][1]['count'] == 2
    del run['runtime_metadata']['source_census_request']
    with pytest.raises(ValueError, match='byte budget'):
        contract.decode_ir_source_census(run)
    # The ordinary reader still requires an explicit caller override.
    with pytest.raises(ValueError, match='byte budget'):
        census.CensusReader(raw, descriptor)


def test_ir_adapter_rejects_descriptor_budget_conflicting_with_compiler_request(
):
    raw, descriptor = capture([[1, 2]])
    request = contract.ObservationRequest(semantics=('counter', ),
                                          programs=None,
                                          program_policy='all_grid_census')
    descriptor.update(max_census_bytes=request.max_census_bytes + 8,
                      max_census_cells=request.max_census_cells)
    run = dict(source_census={'descriptor': descriptor},
               raw_base64=base64.b64encode(raw).decode('ascii'),
               runtime_metadata=dict(capture_id='capture',
                                     profiler_invocation_id='call',
                                     profiler_association_evidence={
                                         'binary_id': 'actual-binary'
                                     },
                                     source_census_request=request.as_dict()))
    with pytest.raises(ValueError, match='request limits disagree'):
        contract.decode_ir_source_census(run)


@pytest.mark.parametrize('changes', [
    {
        'programs': (0, )
    },
    {
        'semantics': ('source_control_interval', )
    },
    {
        'sample_every': 2
    },
    {
        'max_census_cells': True
    },
    {
        'max_census_bytes': 7
    },
])
def test_exact_census_request_rejects_fixed_instance_sampling_and_invalid_budgets(
        changes):
    values = dict(semantics=('counter', ),
                  programs=None,
                  program_policy='all_grid_census')
    values.update(changes)
    with pytest.raises(ValueError):
        contract.ObservationRequest(**values)


@pytest.mark.parametrize('placement', ['record_layout', 'compiler_actor'])
def test_direct_v3_reader_charges_complete_shared_physical_storage(placement):
    _, desc = capture([[0, 0]])
    raw = bytes(256)
    desc.update(raw_sha256=hashlib.sha256(raw).hexdigest(),
                cells_offset=64,
                actor_stride=64,
                program_stride=192,
                sites=desc['sites'][:1])
    if placement == 'record_layout':
        desc['record_layout'] = 'ascend_source_census_v3'
    else:
        desc['actors'][0]['compiler_actor'] = dict(runtime_actor_binding=dict(
            layout='ascend_source_census_v3'))
    with pytest.raises(ValueError, match='physical cell budget'):
        census.CensusReader(raw, desc, max_cells=1)
    assert census.CensusReader(raw, desc,
                               max_cells=32).cell(0, 0, 0)['exact'] is True
    with pytest.raises(ValueError, match='byte budget'):
        census.CensusReader(raw, desc, max_cells=32, max_bytes=255)


def test_legacy_derived_retag_is_idempotent_and_scoped_to_actual_capture():
    original = dict(
        captures=[
            dict(
                capture_id='legacy',
                runtime_metadata=dict(record_layout='ascend_source_census_v2'))
        ],
        groups=[
            dict(observations=[
                dict(capture_id='legacy', semantic='counter',
                     count_exact=True),
                dict(capture_id='other', semantic='counter', count_exact=True)
            ])
        ])
    derived = census.derive_transport_visibility(original)
    assert original['groups'][0]['observations'][0]['count_exact'] is True
    assert derived['groups'][0]['observations'][0]['count_exact'] is False
    assert derived['groups'][0]['observations'][1]['count_exact'] is True
    assert census.derive_transport_visibility(derived) == derived
