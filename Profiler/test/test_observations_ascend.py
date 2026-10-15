import importlib.util
from pathlib import Path
import sys
import types
import pytest

package=types.ModuleType('_ascend_observation_test');package.__path__=[str(Path(__file__).parents[1]/'python/flagtree_profiler')];sys.modules[package.__name__]=package
spec=importlib.util.spec_from_file_location(package.__name__+'.observations_ascend',Path(package.__path__[0])/'observations_ascend.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
UNKNOWN=(1<<64)-1


def test_clock_and_occurrence_are_preserved_with_overflow():
    record=[(2<<32)|7,0,100,130,0,0,UNKNOWN,UNKNOWN]
    result=m.decode_dynamic64([1,1,3,2]+record,capacity=1,actor_slots=1,capture_id='capture',invocation_id='launch',association_evidence={'buffer':'private_per_invocation'})
    event=result['observations'][0]
    assert event['duration_ticks']==30 and event['duration_ns'] is None
    assert event['semantic']=='wait_bracket' and event['iteration'] is None
    assert event['association_status']=='verified' and result['dropped']==2


@pytest.mark.parametrize('header',[[2,0,0,0],[1,2,2,0],[1,1,1,1],[0,0,1,0]])
def test_bad_protocol_header_is_rejected(header):
    with pytest.raises(ValueError):m.decode_dynamic64(header+[0]*8,capacity=1,actor_slots=1,capture_id='capture')


def test_actor_mismatch_and_unknown_semantics_rejected():
    for descriptor,actor in [(5<<32,0),(1<<32,1)]:
        with pytest.raises(ValueError):m.decode_dynamic64([1,1,1,0]+[descriptor,0,100,100,0,actor,UNKNOWN,UNKNOWN],capacity=1,actor_slots=1,capture_id='capture')


def test_empty_log_does_not_fabricate_events_or_infer_actor_execution():
    result=m.decode_dynamic64([0]*12,capacity=1,actor_slots=1,capture_id='capture')
    assert not result['observations'] and result['actors'][0]['state']=='no_records'
    assert result['actors'][0]['execution_status']=='unknown'


def test_same_site_id_on_different_actors_is_disambiguated():
    records=[]
    for actor in range(2):
        records += [1,1,1,0]+[(1<<32)|7,0,100,120,0,actor,UNKNOWN,UNKNOWN]
    manifests=[{'actor_slot':0,'site_id':7,'callee':'cube_signal'}, {'actor_slot':1,'site_id':7,'callee':'vector_signal'}]
    result=m.decode_dynamic64(records,capacity=1,actor_slots=2,capture_id='capture',site_manifest=manifests)
    assert [e['compiler_site']['callee'] for e in result['observations']]==['cube_signal','vector_signal']
    duplicate=m.decode_dynamic64(records,capacity=1,actor_slots=2,capture_id='capture',site_manifest=manifests+[manifests[0]])
    assert duplicate['observations'][0]['compiler_site'] is None
    assert duplicate['observations'][0]['source_mapping_status']=='ambiguous'


@pytest.mark.parametrize('value', [-1, True, 1.5, '0', 1 << 64])
def test_invalid_expected_program_is_rejected(value):
    with pytest.raises(ValueError, match='expected_program'):
        m.decode_dynamic64([0] * 12,
                           capacity=1,
                           actor_slots=1,
                           capture_id='capture',
                           expected_program=value)


def test_record_program_must_agree_with_compiled_selection():
    raw = [1, 1, 1, 0] + [(2 << 32) | 7, 0, 100, 120, 1, 0, UNKNOWN, UNKNOWN]
    with pytest.raises(ValueError, match='program contradicts'):
        m.decode_dynamic64(raw,
                           capacity=1,
                           actor_slots=1,
                           capture_id='capture',
                           expected_program=0)
    old = m.decode_dynamic64(raw,
                             capacity=1,
                             actor_slots=1,
                             capture_id='capture')
    assert old['observations'][0][
        'program_selection_status'] == 'unverified_legacy'
    valid = m.decode_dynamic64(raw,
                               capacity=1,
                               actor_slots=1,
                               capture_id='capture',
                               expected_program=1)
    assert valid['observations'][0][
        'program_selection_status'] == 'consistent_with_expected_program'


@pytest.mark.parametrize(
    'code,callee,semantic',
    [(1, 'llvm.hivm.WAIT.FLAG.IMM', 'existing_readiness_wait_source_control'),
     (2, 'llvm.hivm.SET.FLAG.IMM', 'signal_issue_source_control'),
     (2, 'llvm.hivm.SET.CROSS.CORE', 'existing_readiness_wait_source_control'),
     (1, 'llvm.hivm.SET.FLAG.IMM', 'existing_readiness_wait_source_control'),
     (3, 'llvm.hivm.WAIT.FLAG.IMM', 'loop_header_occurrence')])
def test_authoritative_native_site_contradiction_is_rejected(
        code, callee, semantic):
    raw = [1, 1, 1, 0] + [(code << 32) | 7, 0, 100, 100, 0, 0, UNKNOWN, UNKNOWN
                          ]
    manifest = [{
        'actor_slot': 0,
        'site_id': 7,
        'callee': callee,
        'semantics': semantic
    }]
    with pytest.raises(ValueError,
                       match='semantic contradicts|checkpoint compiler'):
        m.decode_dynamic64(raw,
                           capacity=1,
                           actor_slots=1,
                           capture_id='capture',
                           site_manifest=manifest,
                           expected_program=0)


def test_unknown_and_duplicate_legacy_sites_do_not_gain_semantic_certification(
):
    raw = [1, 1, 1, 0] + [(2 << 32) | 7, 0, 100, 120, 0, 0, UNKNOWN, UNKNOWN]
    unknown = [{
        'actor_slot': 0,
        'site_id': 7,
        'callee': 'unknown_future_primitive'
    }]
    result = m.decode_dynamic64(raw,
                                capacity=1,
                                actor_slots=1,
                                capture_id='capture',
                                site_manifest=unknown)
    assert result['observations'][0]['source_mapping_status'] == 'partial'
    assert result['program_selection']['status'] == 'unverified_legacy'
    known = {
        'actor_slot': 0,
        'site_id': 7,
        'callee': 'llvm.hivm.WAIT.FLAG.IMM',
        'semantics': 'existing_readiness_wait_source_control'
    }
    result = m.decode_dynamic64(raw,
                                capacity=1,
                                actor_slots=1,
                                capture_id='capture',
                                site_manifest=[known, known])
    assert result['observations'][0]['source_mapping_status'] == 'ambiguous'


def test_operation_checkpoint_is_point_observation_with_authoritative_origin():
    raw = [1, 1, 1, 0] + [(4 << 32) | 7, 0, 123, 123, 0, 0, UNKNOWN, UNKNOWN]
    site = {'actor_slot': 0, 'site_id': 7,
            'semantics': 'source_operation_checkpoint',
            'callee': 'ordinary_generated_operation', 'operation_class': 'compiler_call',
            'source_file': '/user/kernel.py', 'line': 19, 'column': 4}
    result = m.decode_dynamic64(raw, capacity=1, actor_slots=1,
                                capture_id='capture', site_manifest=[site])
    event, = result['observations']
    assert event['semantic'] == 'operation_checkpoint'
    assert event['event_kind'] == 'source_operation_occurrence'
    assert event['duration_ticks'] == 0
    assert event['compiler_site'] == site
    assert event['source_mapping_status'] == 'compiler_site_identified'
    raw[7] = 124
    with pytest.raises(ValueError, match='point record'):
        m.decode_dynamic64(raw, capacity=1, actor_slots=1, capture_id='capture')
