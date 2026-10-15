"""Regression oracles for unsupported clocks, occurrence semantics and evidence."""
import importlib
from pathlib import Path
import sys
from types import ModuleType

import pytest

package = ModuleType('observation_contract_test')
package.__path__ = [
    str(Path(__file__).parents[1] / 'python/flagtree_profiler')
]
sys.modules[package.__name__] = package
contract = importlib.import_module(package.__name__ + '.observations')


def sample(**changes):
    return dict(id='capture:site:7',
                capture_id='capture',
                source='test',
                semantic='issue',
                start_tick=100,
                end_tick=110,
                clock=dict(domain='test.raw', scope='instance_local'),
                **changes)


def test_unknown_clock_preserves_ticks_without_fake_microseconds():
    result = contract.observation(sample())
    assert result['duration_ticks'] == 10
    assert result['duration_ns'] is None
    assert result['relative_start_ns'] is None
    assert result['association_status'] == 'unassociated'


def test_producer_conversion_does_not_stretch_to_launch():
    value = sample()
    value['clock'].update(
        tick_ns=20,
        origin_tick=90,
        conversion_evidence={'source': 'independent_test_oracle'})
    result = contract.observation(value)
    assert result['duration_ns'] == result['relative_start_ns'] == 200
    assert 'kernel_duration' not in result


@pytest.mark.parametrize('clock', [
    dict(domain='test', scope='instance_local', tick_ns=20),
    dict(domain='test', scope='shared', alignment='verified_shared'),
    dict(domain='test', scope='local', tick_ns=float('nan')),
])
def test_unsubstantiated_clock_claims_are_rejected(clock):
    with pytest.raises(ValueError):
        contract.validate_clock(clock)


def test_wrap_requires_evidence_not_a_large_invented_duration():
    with pytest.raises(ValueError):
        contract.interval_ticks(250, 5, {'wrap_bits': 8})
    assert contract.interval_ticks(250, 5, {
        'wrap_bits': 8,
        'wrap_count': 1
    }) == 11


def test_kernel_name_never_proves_association():
    value = sample(association_status='verified', kernel_name='same_name')
    with pytest.raises(ValueError):
        contract.observation(value)


def test_occurrence_is_not_promoted_to_source_iteration():
    result = contract.observation(sample(occurrence=9))
    assert result['occurrence'] == 9
    assert 'iteration' not in result


def test_snapshot_limit_is_preserved_instead_of_claiming_dynamic_history():
    runs = [
        dict(decoded=dict(records=[
            dict(record_kind='TIMELINE',
                 op_id=1,
                 logical_instance_id=0,
                 start_cycle=100,
                 end_cycle=110)
        ]))
    ]
    event, = contract.from_ir_runs(runs)
    assert event['storage'] == 'static_site_snapshot'
    assert event['occurrence'] is None and event['duration_ns'] is None
    assert any('overwrite' in limit for limit in event['limits'])


def test_request_roundtrip_and_invalid_sampling():
    request = contract.ObservationRequest(programs=(0, 2), sample_every=3)
    assert contract.ObservationRequest.from_dict(request.as_dict()) == request
    with pytest.raises(ValueError):
        contract.ObservationRequest(sample_every=0)
    with pytest.raises(ValueError):
        contract.ObservationRequest.from_dict({'kernel_name_guess': 'matmul'})


def test_dynamic_records_keep_site_history_and_verified_invocation():
    runtime = {
        'profiler_invocation_id': 'launch-42',
        'profiler_association_evidence': {
            'source': 'same_launch_metadata_object'
        }
    }
    records = [
        dict(record_kind='DYNAMIC_TIMELINE',
             op_id=3,
             logical_instance_id=0,
             actor_id=0,
             sequence=index,
             attempted_ordinal=index * 3,
             start_cycle=100 + index * 10,
             end_cycle=105 + index * 10) for index in range(3)
    ]
    events = contract.from_ir_runs([{
        'runtime_metadata': runtime,
        'decoded': {
            'records': records
        }
    }])
    assert [event['occurrence'] for event in events] == [0, 1, 2]
    assert [event['attempted_ordinal'] for event in events] == [0, 3, 6]
    assert all(event['association_status'] == 'verified' for event in events)
    assert all(event['storage'] == 'selected_dynamic_append'
               for event in events)
    assert all(event.get('iteration') is None for event in events)
    assert all(event['duration_ns'] is None for event in events)


def test_automatic_request_roundtrip_and_manual_compatibility():
    manual = contract.ObservationRequest()
    assert 'automatic' not in manual.as_dict()
    automatic = contract.ObservationRequest(automatic=True, max_sites=5)
    assert contract.ObservationRequest.from_dict(automatic.as_dict()) == automatic
    assert automatic.as_dict()['max_sites'] == 5


@pytest.mark.parametrize('values', [
    {'automatic': 1}, {'automatic': True, 'sites': (3,)},
    {'max_sites': 0}, {'max_sites': 129}, {'max_sites': True},
])
def test_automatic_request_rejects_ambiguous_or_unbounded_selection(values):
    with pytest.raises(ValueError):
        contract.ObservationRequest(**values)
