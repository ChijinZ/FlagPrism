"""The public collector must not stretch raw control clocks into kernel time."""
import importlib
import json


def run(clock=None):
    return {
        'debug_kernel_name': 'same_name',
        'runtime_metadata': {} if clock is None else {'observation_clock': clock},
        'decoded': {'records': [{'record_kind': 'TIMELINE', 'op_id': 1,
                                  'logical_instance_id': 0,
                                  'start_cycle': 100, 'end_cycle': 110}]},
    }


def test_unverified_cycles_never_become_microseconds(tmp_path):
    profile = importlib.import_module('flagtree.profiler.profile')
    assert profile._internal_timeline_events_for_run(
        0, run(), {'name': 'same_name', 'ts': 50, 'dur': 9999}) == []
    path = tmp_path / 'timeline.json'
    original = {'traceEvents': [{'name': 'same_name', 'ph': 'X',
                                 'ts': 50, 'dur': 9999}]}
    path.write_text(json.dumps(original))
    profile._augment_timeline(path, [run()], synthesize_kernel_events=True)
    assert json.loads(path.read_text()) == original


def test_verified_local_clock_stays_in_its_own_frame():
    profile = importlib.import_module('flagtree.profiler.profile')
    clock = {'domain': 'test.counter', 'scope': 'instance_local',
             'alignment': 'instance_local', 'tick_ns': 20, 'origin_tick': 90,
             'conversion_evidence': {'source': 'test_oracle'}}
    event, = profile._internal_timeline_events_for_run(
        7, run(clock), {'name': 'same_name', 'ts': 50, 'dur': 9999, 'pid': 22})
    assert event['ts'] == event['dur'] == .2
    assert event['pid'] != 22
    assert event['args']['semantic'] == 'source_control_interval'
    assert event['args']['storage'] == 'static_site_snapshot'


def test_capture_identity_does_not_collapse_runs():
    profile = importlib.import_module('flagtree.profiler.profile')
    clock = {'domain': 'test.counter', 'scope': 'instance_local',
             'alignment': 'instance_local', 'tick_ns': 20, 'origin_tick': 90,
             'conversion_evidence': {'source': 'test_oracle'}}
    first, = profile._internal_timeline_events_for_run(1, run(clock), None)
    second, = profile._internal_timeline_events_for_run(2, run(clock), None)
    assert first['args']['capture_id'] != second['args']['capture_id']
    assert first['pid'] != second['pid']
