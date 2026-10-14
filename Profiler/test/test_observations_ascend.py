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
    for descriptor,actor in [(4<<32,0),(1<<32,1)]:
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
