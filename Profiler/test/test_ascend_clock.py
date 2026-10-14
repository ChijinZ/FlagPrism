import importlib.util
from pathlib import Path
import struct
import sys
import types
import pytest

package=types.ModuleType('_ascend_clock_test');package.__path__=[str(Path(__file__).parents[1]/'python/flagtree_profiler')];sys.modules[package.__name__]=package
spec=importlib.util.spec_from_file_location(package.__name__+'.ascend_clock',Path(package.__path__[0])/'ascend_clock.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


def packet(tmp_path, *, stream=3, task=6):
    raw=bytearray(128)
    struct.pack_into('<HH',raw,4,stream,task)
    struct.pack_into('<H',raw,20,9) # AIV, physical core4
    struct.pack_into('<HH',raw,28,0,5)
    struct.pack_into('<Q',raw,32,555)
    struct.pack_into('<QQ',raw,112,1000,2000)
    file=tmp_path/'DeviceProf77.bin';file.write_bytes(raw)
    return m.import_deviceprof(file,device_id=4,capture_id='actual-SDK-capture')


def test_packet_sdk_stream_encoding_and_raw_provenance(tmp_path):
    result=packet(tmp_path,stream=0x2009,task=0x8003)
    record=result['records'][0]
    assert (record['stream_id'],record['task_id'])==(3,0x8009)
    assert (record['actor_kind'],record['physical_core'],record['program'])==('AIV',4,5)
    assert record['total_cycles']==555 and record['start_tick']==1000
    assert result['foreground_association']=='unassociated'


def test_containment_without_native_identity_does_not_join_replay(tmp_path):
    result=packet(tmp_path)
    event={'program':5,'actor_slot':1,'start_tick':1200,'end_tick':1400,'invocation_id':'call'}
    assert m.align_same_call([event],result)['status']=='unassociated'


def test_frequency_comes_from_actual_hwts_not_core_mhz(tmp_path):
    file=tmp_path/'info.json.4'
    file.write_text('{"DeviceInfo":[{"id":4,"hwts_frequency":"80","aiv_frequency":"1650"}]}')
    assert m.read_hwts_frequency(file,device_id=4)['tick_ns']==12.5
    with pytest.raises(ValueError):m.read_hwts_frequency(file,device_id=0)


def test_exact_same_call_identity_then_actor_containment(tmp_path):
    result=packet(tmp_path)
    identity={'invocation_id':'call','capture_id':'actual-SDK-capture','device_id':4,'stream_id':3,'task_id':6,'connection_id':91,'scope_id':8,'packet_sha256':result['raw_sha256'],'evidence':{'producer':'actual SDK scope/task connection'},'counter_domain_evidence':{'producer':'raw SDK SYS fields and actual source SYS_CNT instruction'}}
    event={'id':'record','capture_id':'runtime-capture','invocation_id':'call','semantic':'wait_bracket','source':'ascend_llvm_dynamic64','program':5,'actor_slot':1,'start_tick':1200,'end_tick':1400,'clock':{'domain':'ascend.SYS_CNT','scope':'actor_local','alignment':'instance_local','tick_ns':None}}
    aligned=m.align_same_call([event],result,identity=identity)
    assert aligned['status']=='verified_shared'
    assert aligned['observations'][0]['duration_ns'] is None
    assert aligned['observations'][0]['clock']['origin_tick']==1000
    wrong=dict(event,invocation_id='another-replay')
    assert m.align_same_call([wrong],result,identity=identity)['status']=='partial'
    with pytest.raises(ValueError):m.align_same_call([event],result,identity=dict(identity,packet_sha256='another-packet'))


def test_repeated_native_actor_is_ambiguous_even_with_containment(tmp_path):
    result=packet(tmp_path)
    result['records'].append(dict(result['records'][0]))
    identity={'invocation_id':'call','capture_id':'actual-SDK-capture','device_id':4,'stream_id':3,'task_id':6,'connection_id':91,'scope_id':8,'packet_sha256':result['raw_sha256'],'evidence':{'producer':'actual SDK identity'},'counter_domain_evidence':{'producer':'raw SDK SYS fields and actual source SYS_CNT instruction'}}
    event={'program':5,'actor_slot':1,'start_tick':1200,'end_tick':1400,'invocation_id':'call'}
    aligned=m.align_same_call([event],result,identity=identity)
    assert aligned['status']=='partial' and aligned['observations']==[event]


def test_sdk_task_connection_requires_device_and_connection(tmp_path):
    import sqlite3
    root=tmp_path/'actual-capture';device=root/'device_4';(device/'sqlite').mkdir(parents=True);(root/'host/sqlite').mkdir(parents=True)
    (device/'info.json.4').write_text('{"DeviceInfo":[{"id":4,"hwts_frequency":"50"}]}')
    with sqlite3.connect(device/'sqlite/time.db') as db:
        db.execute('CREATE TABLE Time(device_id,dev_cntvct,host_mon)');db.execute('INSERT INTO Time VALUES (4,1000,2000)')
    with sqlite3.connect(device/'sqlite/ascend_task.db') as db:
        db.execute('CREATE TABLE AscendTask(stream_id,task_id,connection_id,start_time,duration)');db.execute('INSERT INTO AscendTask VALUES (3,6,91,4000,20)')
    with sqlite3.connect(root/'host/sqlite/runtime.db') as db:
        db.execute('CREATE TABLE HostTask(device_id,stream_id,task_id,connection_id)')
        db.executemany('INSERT INTO HostTask VALUES (?,?,?,?)',[(0,3,6,91),(4,3,6,92),(4,3,6,91)])
    imported=m.import_sdk_task_capture(root)
    assert imported['tasks'][0]['sdk_host_task']['connection_id']==91
    assert imported['tasks'][0]['sdk_host_task']['device_id']==4
    assert imported['sys_clock_alignment']=='unverified' and imported['tasks'][0]['raw_sys_ticks'] is None


def test_shared_clock_descriptor_is_identical_across_actors(tmp_path):
    result=packet(tmp_path)
    cube=dict(result['records'][0],actor_kind='AIC',subblock=0,start_tick=900,end_tick=2100)
    result['records'].append(cube)
    identity={'invocation_id':'call','capture_id':'actual-SDK-capture','device_id':4,'stream_id':3,'task_id':6,'connection_id':91,'scope_id':8,'packet_sha256':result['raw_sha256'],'evidence':{'producer':'actual SDK same-call binding'},'counter_domain_evidence':{'producer':'SDK SYS fields and source SYS_CNT'}}
    events=[{'id':f'record{actor}','capture_id':'runtime-capture','invocation_id':'call','semantic':'issue','source':'ascend_llvm_dynamic64','program':5,'actor_slot':actor,'start_tick':1200,'end_tick':1400,'clock':{'domain':'ascend.SYS_CNT','scope':'actor_local','alignment':'instance_local','tick_ns':None}} for actor in (0,1)]
    aligned=m.align_same_call(events,result,identity=identity)
    clocks=[event['clock'] for event in aligned['observations']]
    assert clocks[0]==clocks[1] and clocks[0]['origin_tick']==900
    assert clocks[0]['alignment_evidence']['invocation_id']=='call'
    assert len(clocks[0]['alignment_evidence']['verified_actors'])==2
    assert aligned['observations'][0]['clock_alignment_event_evidence']!=aligned['observations'][1]['clock_alignment_event_evidence']
    incomplete=dict(identity);incomplete.pop('counter_domain_evidence')
    assert m.align_same_call(events,result,identity=incomplete)['status']=='unassociated'


def test_actual_sdk_packet_fixture_preserves_raw_unknown_clock_identity():
    import json,hashlib
    fixture=Path(__file__).parent/'fixtures/cann_clock'
    provenance=json.loads((fixture/'provenance.json').read_text())
    imported=m.import_deviceprof(fixture/'actual_program_records.bin')
    assert imported['raw_sha256']==provenance['fixture_sha256']
    assert len(imported['records'])==len(provenance['record_offsets'])
    assert {entry['actor_kind'] for entry in imported['records']}=={'AIC','AIV'}
    assert all(entry['capture_id'] is None and entry['device_id'] is None for entry in imported['records'])
    assert imported['foreground_association']=='unassociated'
