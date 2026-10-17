"""Stdlib-only installed-source and raw-reference audit; no product imports."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tarfile


def need(value, message):
    if not value:
        raise RuntimeError(message)


def load(path):
    with tarfile.open(path) as t:
        return {m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}


def identifier(identity, kind, *parts):
    raw = json.dumps([*identity,kind,*parts],ensure_ascii=False,separators=(',',':')).encode()
    return kind+'-'+hashlib.sha256(raw).hexdigest()


p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo',required=True,type=Path)
p.add_argument('--archive',required=True,type=Path)
p.add_argument('--gcu-original',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args();files=load(a.archive);original=load(a.gcu_original)
need(hashlib.sha256(a.gcu_original.read_bytes()).hexdigest()=='ea3fbe96cf5d8c985dd39c2d54a1d2ddaa59c229ad14c3fe85965bac97afb62b','Original GCU identity')
def j(name):return json.loads(files[name])
for package in ['package-gcu-events','package-gcu-events-v2']:
    need(j(package+'/terminal.json')['state']=='build_passed_not_device_qualified','Packaging terminal')
    bridge=j(package+'/native-byte-bridge.json')
    need(bridge['byte_equal'] and len(bridge['native_members'])==7,'Python-only native bridge')
need(j('runs/install-v1/terminal.json')['returncode']==0,'Installed contract job')
need(j('runs/install-v1/output/result.json')['installed_members_byte_verified']==608,'Installed member coverage')
for name in ['timeline_events.py','timeline_events_enflame.py']:
    expected=subprocess.check_output(['git','-C',str(a.repo),'show',
        'a0ef3c904e076e0f4f1743d16fa4399ea4829288:Profiler/python/flagtree_profiler/'+name])
    need(files['installed/'+name]==expected,'Actually installed source: '+name)
all_ids=set();pair_counts=[]
for mode in ['normal','optimized']:
    prefix='runs/install-v1/output/'
    for script,count in [('test_timeline_events.py',16),('test_enflame_timeline_events.py',11),('test_nvidia_machine_map.py',25)]:
        log=files[prefix+script+'-'+mode+'.stderr.log']
        need(('Ran '+str(count)+' tests').encode() in log and b'\nOK\n' in log,'Contract failure: '+script)
    need(b'4 passed' in files[prefix+'public-contract-'+mode+'.stdout.log'],'Public ABI compatibility')
    old=j(prefix+'p01_canonical_v1_reinspection.py-'+mode+'/result.json')
    need((old['captures'],old['raw_endpoint_records'],old['intervals'],old['incomplete_events'])==(26,11456,5720,16) and old['actual_math_launches']==0,'Real v1 compatibility coverage')
    output=prefix+'p01_enflame_canonical_reinspection.py-'+mode+'/'
    result=j(output+'result.json');need(result['actual_math_launches']==0,'Reinspection replayed math')
    mode_ids=set()
    for row in result['captures']:
        k=row['steps'];batch=j(output+'k'+str(k)+'.canonical.json')
        need(hashlib.sha256(files[output+'k'+str(k)+'.canonical.json']).hexdigest()==row['canonical_sha256'],'Canonical SHA')
        document_bytes=original['run-v1/output/k'+str(k)+'/raw/native/capture.observations.json']
        document=json.loads(document_bytes);capture=document['captures'][0]
        raw=base64.b64decode(capture['raw_base64'],validate=True)
        meta=json.loads(original['run-v1/output/metadata-k'+str(k)+'.json'])
        need(batch['schema_version']==2 and batch['complete'] and batch['clock_status']==batch['boundary_status']=='unverified','False raw/time qualification')
        namespace=identifier(('retained-byte-reinspection',),'capture',hashlib.sha256(document_bytes).hexdigest())
        native=capture['runtime_metadata'];assoc=native['profiler_association_evidence']
        invocation=identifier((namespace,),'enflame-invocation',native['profiler_invocation_id'],assoc['scope_id'],sorted(assoc['session_ids']))
        identity=(namespace,invocation,meta['hash'])
        need(tuple(batch['identity'][key] for key in ['capture_id','invocation_id','binary_id'])==identity,'Owning/native identity binding')
        need(batch['raw_artifact']==dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),'Raw identity')
        write,cap,drop,flags,stride,payload,attempted,reserved=struct.unpack_from('<8I',raw)
        observer=batch['observers'][0]
        need(observer['id']==identifier(identity,'observer','enflame.work_item','0',[0,0,0]) and observer['timer_bits']==46 and observer['record_order']=='paired_endpoints' and observer['physical_identity'] is None,'Real work-item identity')
        need((observer['attempted_records'],observer['committed_records'],observer['retained_records'],observer['dropped_records'],observer['filtered_records'],observer['overwritten_records'])==(2*attempted,2*write,2*write,0,0,0),'Exact endpoint-reference count units')
        need(observer['attributes']['enflame.native_association']==assoc,'Native provenance changed')
        records={r['id']:r for r in batch['records']};sites={r['id']:r for r in batch['sites']}
        need(len(records)==2*write and len(batch['events'])==write,'Invented or missing endpoints')
        for event in batch['events']:
            need(event['kind']=='interval' and event['iteration_id'] is None and event['occurrence_basis']=='complete_pair_order','Invented event semantics')
            left,right=[records[key] for key in event['record_ids']]
            seq=left['sequence']//2;offset=32+seq*64
            kind,zero,site,program,begin,end,duration,actor,sequence,ordinal,commit=struct.unpack_from('<HHIQQQQIIQQ',raw,offset)
            need((kind,zero,program,actor,sequence,ordinal,commit)==(7,0,0,0,seq,seq,0x465044594e563031),'Actual native pair')
            need(event['id']==identifier(identity,'event',left['id'],right['id']) and
                 left['id']==identifier(identity,'record',observer['id'],2*seq) and
                 right['id']==identifier(identity,'record',observer['id'],2*seq+1),'Stable raw/event identities')
            need((left['tick'],right['tick'],left['offset'],right['offset'],left['length'],right['length'])==(begin,end,offset+16,offset+24,8,8),'Canonical endpoints differ from physical fields')
            need((event['start_tick'],event['end_tick'])==(begin,end) and duration==end-begin,'Interval duration changed')
            need(sites[event['site_id']]['backend_site_id']==str(site),'Source site binding')
        ids={r['id'] for key in ['observers','records','events'] for r in batch[key]}
        need(mode_ids.isdisjoint(ids),'Local IDs alias captures');mode_ids.update(ids)
        if mode=='normal':pair_counts.append(dict(steps=k,events=write,endpoint_references=2*write))
    if mode=='normal':all_ids=mode_ids
    else:need(all_ids==mode_ids,'Optimized Python changed canonical identity')
need(sum(r['events'] for r in pair_counts)==42,'Real GCU scope')
for job in j('owned-final.json'):
    need(all(row['current_state'] in ['Z','missing'] or not row['same_startticks'] for row in job['owners']),'Owned process live')
out=dict(status='installed_common_v2_and_actual_pair_bytes_audited_not_full_P01',gcu=pair_counts,
         synthetic_new_protocol_methods_each_mode=11,legacy_event_methods_each_mode=16,
         mapper_methods_each_mode=25,public_contracts_each_mode=4,
         legacy_real_captures=26,legacy_real_endpoint_records=11456,legacy_intervals=5720,legacy_orphans=16,
         archive_bytes=a.archive.stat().st_size,archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
         limits=['No new device executions; actual producer evidence remains the original GCU/NVIDIA captures.',
                 'Default GCU collection, clock/async/pipeline qualification and Perfetto remain incomplete.'])
a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
