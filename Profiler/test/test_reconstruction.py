"""Observation identity links survive name changes; clocks never imply a join."""
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture
def reconstruction(monkeypatch):
    package = ModuleType('method_reconstruction_test')
    package.__path__ = [str(Path(__file__).parents[1] / 'python/flagtree_profiler')]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return importlib.import_module(package.__name__ + '.reconstruction')


def event(**changes):
    return dict(id='obs1', source='test', capture_id='capture1',
                semantic='source_control_interval', program=0, site=3,
                invocation_id='launch-1', association_status='verified',
                association_evidence={'source': 'same_launch_metadata_object',
                                      'binary_id': 'binary1'},
                clock={'domain': 'test.counter', 'scope': 'instance_local',
                       'tick_ns': None, 'alignment': 'unverified'},
                start_tick=10, end_tick=20, **changes)


def test_join_never_aligns_clocks(reconstruction):
    launch = dict(id='launch-1', binary_id='binary1', name='source_name')
    document = reconstruction.reconstruct({'observations': [event()]}, [launch],
                [dict(id='binary1')], [dict(id=7, launch_id='launch-1', name='sdk_name')])
    group, = document['groups']
    assert group['native_event_ids'] == [7]
    assert group['time_relation'] == 'separate_clock_frame'
    assert group['observations'][0]['duration_ns'] is None
    assert group['binary_id'] == 'binary1'


def test_binary_mismatch_cannot_link(reconstruction):
    launch = dict(id='launch-1', binary_id='another_binary')
    document = reconstruction.reconstruct({'observations': [event()]}, [launch], [], [])
    group, = document['groups']
    assert group['invocation_id'] is None and group['binary_id'] is None
    assert group['observations'][0]['reconstruction_association'] == 'unassociated'


def test_invalid_observation_preserves_rejection(reconstruction):
    original = event()
    original['end_tick'] = 0
    document = reconstruction.reconstruct({'observations': [original]}, [], [], [])
    assert not document['groups']
    assert document['rejected'][0]['original_record'] == original


def test_shared_clock_requires_matching_invocation_proof(reconstruction):
    raw = event()
    raw['clock'].update(alignment='verified_shared',
                        alignment_evidence={'invocation_id': 'another-launch'})
    launch = dict(id='launch-1', binary_id='binary1')
    document = reconstruction.reconstruct({'observations': [raw]}, [launch], [], [])
    assert document['alignment_sets'] == []
    raw['clock']['alignment_evidence']['invocation_id'] = 'launch-1'
    document = reconstruction.reconstruct({'observations': [raw]}, [launch], [], [])
    frame, = document['alignment_sets']
    assert frame['display_origin_tick'] == 10
    assert document['groups'][0]['time_relation'] == 'verified_shared_control_clock'
