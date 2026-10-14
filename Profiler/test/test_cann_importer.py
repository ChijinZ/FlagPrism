"""Offline semantic regression using real msprof op actor fixtures."""
import importlib.util
import json
from pathlib import Path
import pytest

MODULE = Path(__file__).parents[1] / 'python/flagtree_profiler/cann.py'
spec = importlib.util.spec_from_file_location('cann_import_test', MODULE)
cann = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cann)
FIXTURE = Path(__file__).parent / 'fixtures/cann_pmu'


def test_real_fixture_preserves_actor_replay_raw_and_units():
    doc = cann.import_msprof(FIXTURE, replay_id='replay-A')
    pipe = [g for g in doc['counter_groups'] if g['name'] == 'PipeUtilization']
    assert [g['actor'] for g in pipe] == ['0:cube0', '0:vector0', '0:vector1']
    assert all(g['replay_id'] == 'replay-A' and g['activity_overlap'] == 'allowed' for g in pipe)
    for g in pipe:
        for metric in g['metrics']:
            original = g['raw_row'][metric['name']]
            assert metric['value'] == (None if original == 'NA' else float(original))
    assert next(m for m in pipe[0]['metrics'] if m['name'] == 'aic_cube_time(us)')['unit'] == 'us'
    assert next(m for m in pipe[0]['metrics'] if m['name'] == 'aic_cube_ratio')['unit'] == 'ratio'
    assert all('start_ns' not in g and g['source_launch_association'] == 'unassociated' for g in pipe)
    assert json.loads(json.dumps(doc)) == doc
    assert all(len(item['sha256']) == 64 and not Path(item['path']).is_absolute() for item in doc['raw_inputs'])


@pytest.mark.parametrize('value', ['inf', '-inf', 'NaN', 'broken'])
def test_nonfinite_and_invalid_are_rejected(tmp_path, value):
    (tmp_path/'PipeUtilization.csv').write_text(f'block_id,sub_block_id,aic_cube_ratio\n0,cube0,{value}\n')
    with pytest.raises(ValueError, match='PipeUtilization.csv:2:aic_cube_ratio'):
        cann.import_msprof(tmp_path)


def test_multiple_capture_directories_stay_separate(tmp_path):
    for folder in ['OPPROF_A', 'OPPROF_B']:
        (tmp_path/folder).mkdir()
        (tmp_path/folder/'PipeUtilization.csv').write_bytes((FIXTURE/'PipeUtilization.csv').read_bytes())
    doc = cann.import_msprof(tmp_path, replay_id='application-replay')
    assert {g['capture_id'] for g in doc['counter_groups']} == {'OPPROF_A', 'OPPROF_B'}


def test_collector_refuses_output_reuse_and_nonindependent_replay(tmp_path):
    with pytest.raises(FileExistsError):
        cann.collect_msprof(['python', 'app.py'], tmp_path)
    with pytest.raises(ValueError, match='independent'):
        cann.collect_msprof(['python', 'app.py'], tmp_path/'new', replay_mode='same_invocation')


def test_actual_device_comes_from_sdk_metadata_not_application_name():
    document=cann.import_msprof(FIXTURE)
    assert document['actual_device_ids']==[4]
    assert all(group['actual_device_id']==4 for group in document['counter_groups'])


@pytest.mark.parametrize('options',[{'expected_device_id':-1},{'timeout':0},{'metrics':()}])
def test_bad_collector_configuration_is_rejected_before_start(tmp_path,options):
    with pytest.raises(ValueError):cann.collect_msprof(['python','app.py'],tmp_path/'new',**options)
