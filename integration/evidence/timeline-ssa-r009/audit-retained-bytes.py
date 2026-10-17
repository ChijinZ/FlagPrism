"""Independent audit of retained physical bytes and canonical references only."""
from pathlib import Path
import base64
import hashlib
import json
import struct
import tarfile

root=Path(__file__).resolve().parent
archive=root/'ssa-boundaries-final-original-evidence.tgz'
with tarfile.open(archive) as t:
    files={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}

files['owned-terminal-status.json']=(root/'owned-terminal-v2-status.json').read_bytes()

def need(value,message):
    if not value:
        raise RuntimeError(message)

def j(name):
    return json.loads(files[name])

def identifier(identity,kind,*parts):
    data=json.dumps([*identity,kind,*parts],ensure_ascii=False,separators=(',',':')).encode()
    return kind+'-'+hashlib.sha256(data).hexdigest()

for name in ('native-bc460c8','native-4280bab','native-a9ea010'):
    receipt=j(name+'/terminal.json')
    need(receipt['state']=='build_passed_not_device_qualified','Native build not successful')
    log=files[name+'/native-wheel-build.stdout.log']
    need(b'Building CXX object' in log and b'libtriton.so' in log,'Changed source not actually compiled/linked')
need(j('runs/install-v1/terminal.json')['returncode']==1,'First ABI negative failure was lost')
need(b'Unknown boundary ABI accepted: unknown-plan' in files['runs/install-v1/output/boundary-native-contract.stderr.log'],'Wrong first failure')
need(j('runs/install-v3/terminal.json')['returncode']==0,'Fixed independent install failed')
for mode in ('normal','optimized'):
    for name,count in [('test_timeline_events.py',15),('test_timeline_runtime.py',16),('test_timeline_storage.py',7)]:
        text=files[f'runs/install-v3/output/{name}-{mode}.stderr.log']
        need(f'Ran {count} tests'.encode() in text and b'\nOK\n' in text,'CPU contract')
    need(b'3 passed' in files[f'runs/install-v3/output/public-contract-{mode}.stdout.log'],'Public negative contract')
need(b'3 passed' in files['runs/install-v3/output/legacy-automatic-hook.stdout.log'],'Legacy hook')
repo=root.parents[3]/'FlagPrism-method'
for name in ('ordinary_timeline_workload.py','p01_nvidia_public_timeline.py'):
    need(files['check-input-v3/'+name]==(repo/'tests/timeline'/name).read_bytes(),'Actual executed test source')
base='runs/device-public-v2/output/'
phases=['api-cold','api-warm','recovered-raw.timeline','api-after-failure','api-overflow','cli','types']
raw_count=intervals=orphans=groups=overwritten=0
seen_invocations=set();phase_functions=[]
for name in phases:
    prefix=('runs/type-math-v2/output/public/timeline/' if name=='types' else base+name+('/' if name.endswith('.timeline') else '/timeline/'))
    idx=j(prefix+'index.json')
    need(idx['status']=='partial_clock_unverified','False clock certification')
    need(len(idx['captures'])==(5 if name=='types' else 1 if name=='api-overflow' else 4),'Actual request count')
    handles=[]
    for item in idx['captures']:
        capture=j(prefix+item['capture_file']);owner=capture['owner']
        identity=tuple(owner[k] for k in ('capture_id','invocation_id','binary_id'))
        need(identity[1] not in seen_invocations,'Reused invocation identity')
        seen_invocations.add(identity[1]);handles.append(owner['function'])
        need(owner['plan'].get('timeline_boundary_version')==1 and owner['plan'].get('timeline_boundary_strategy')=='llvm_ssa_pending_machine_audit','False or missing compiler boundary strategy')
        need(owner['state']=='raw_ready' and owner['submission_outcome']=='returned','Writer completion')
        raw=files[prefix+capture['raw_file']]
        need(hashlib.sha256(raw).hexdigest()==capture['raw_sha256'],'Original raw SHA')
        input_name=prefix+str(Path(capture['raw_file']).with_suffix('.input.json'))
        input_document=j(input_name)
        need(input_document['capture_status']=='raw_persisted_pending_decode','False predecode completeness')
        need(input_document['owner']==owner and input_document['metadata']==capture['metadata'],'Input snapshot changed')
        canonical=j(prefix+capture['events_file']);decoded=j(prefix+capture['decoded_file']);facts=j(prefix+capture['async_file'])
        need(canonical['clock_status']=='unverified' and canonical['boundary_status']=='unverified','Raw pairing certified timing')
        need(tuple(canonical['identity'][k] for k in ('capture_id','invocation_id','binary_id'))==identity,'Canonical identity')
        need(canonical['raw_artifact']==dict(sha256=capture['raw_sha256'],bytes=len(raw)),'Canonical raw binding')
        layout=owner['layout'];stride=layout['scratch_size'];grid=layout['grid']
        need(len(raw)==layout['raw_bytes']==len(layout['slots'])*stride,'Compact extent')
        record_map={r['id']:r for r in canonical['records']}
        observer_map={o['id']:o for o in canonical['observers']}
        site_map={s['id']:s for s in canonical['sites']}
        physical={};expected_pairs=[];expected_orphans=[]
        for slot,program in layout['slots']:
            magic,pid,sm,size=struct.unpack_from('<4I',raw,slot*stride)
            need((magic,pid,size)==(0x46505432,program,32768),'Physical header')
            coordinates=[program%grid[0],(program//grid[0])%grid[1],program//(grid[0]*grid[1])]
            for warp in range(4):
                words=struct.unpack_from('<I',raw,slot*stride+16+warp*4)[0]
                need(words!=0xffffffff and words%4==0,'Unexpected saturated/misaligned physical counter')
                written=words//4;first=max(0,written-512);overwritten+=first
                oid=identifier(identity,'observer','nvidia.recording_warp',str(warp),coordinates)
                observer=observer_map[oid]
                need(observer['retained_records']==min(written,512) and observer['written_records']==written and observer['overwritten_records']==first,'Observer physical counts')
                need(observer['physical_identity']=={'nvidia.finalize_smid':sm},'Header SM was reinterpreted')
                stack=[]
                for seq in range(first,written):
                    offset=slot*stride+32+warp*8192+(seq%512)*16
                    tag,lo,hi,absolute=struct.unpack_from('<4I',raw,offset)
                    need(seq==absolute,'Physical record absolute sequence')
                    site=identifier((identity[2],),'site',str(tag&0x7fffffff))
                    rid=identifier(identity,'record',oid,seq)
                    expected=dict(id=rid,observer_id=oid,site_id=site,phase='exit' if tag>>31 else 'entry',tick=(hi<<32|lo),sequence=seq,offset=offset,length=16)
                    need(record_map[rid]==expected,'Canonical record differs from physical payload')
                    physical[rid]=expected
                    backend_id=identifier(identity,'record',program,warp,seq)
                    need(canonical['backend_record_map']['nvidia.cp_async.groups.v1'][backend_id]==rid,'Mechanism record correspondence')
                    if expected['phase']=='entry':
                        stack.append(expected)
                    elif stack and stack[-1]['site_id']==site:
                        begin=stack.pop();expected_pairs.append((begin['id'],rid))
                    else:
                        need(not observer['complete'],'Complete physical stream has orphan')
                        expected_orphans.extend((r['id'],'entry') for r in stack);stack=[]
                        expected_orphans.append((rid,'exit'))
                expected_orphans.extend((r['id'],'entry') for r in stack)
        need(set(physical)==set(record_map),'Canonical silently added/dropped records')
        actual_pairs=[];actual_orphans=[]
        for event in canonical['events']:
            refs=event['record_ids'];points=[physical[k] for k in refs]
            need(event['id']==identifier(identity,'event',*refs),'Event namespace')
            need(event['semantic']==site_map[event['site_id']]['semantic'] and event['iteration_id'] is None,'Changed source/iteration semantic')
            if event['kind']=='interval':
                need(len(points)==2 and event['start_tick']==points[0]['tick'] and event['end_tick']==points[1]['tick'],'Actual interval endpoints')
                actual_pairs.append(tuple(refs));intervals+=1
            else:
                need(event['kind']=='incomplete' and len(points)==1,'Unexpected event type')
                p=points[0]
                need((event['start_tick'],event['end_tick'])==((p['tick'],None) if p['phase']=='entry' else (None,p['tick'])),'Synthesized orphan endpoint')
                actual_orphans.append((refs[0],p['phase']));orphans+=1
        need(set(actual_pairs)==set(expected_pairs) and set(actual_orphans)==set(expected_orphans),'Canonical pairing differs from physical nesting')
        need(not facts['time_arrow_verified'],'False time arrow')
        if name=='api-overflow':
            need(not canonical['complete'] and not facts['groups'] and not facts['dependencies'],'Loss inferred async generations')
        else:
            need(canonical['complete'] and decoded['complete'],'Normal capture incomplete')
        for source in capture['metadata']['scope_origin_sources']:
            if source.get('status')=='captured':
                need(source['encoding']=='base64' and hashlib.sha256(base64.b64decode(source['content'])).hexdigest()==source['sha256'],'Retained source snapshot')
        for artifact in capture['metadata']['timeline_artifacts']:
            if artifact['retained_file'].endswith('.llir'):
                llvm=files[prefix+artifact['retained_file']].decode()
                getters=[line for line in llvm.splitlines() if '%globaltimer' in line]
                need(getters and all('~{memory}' in line and 'asm sideeffect' in line for line in getters),'Getter missing actual LLVM memory clobber')
            need(hashlib.sha256(files[prefix+artifact['retained_file']]).hexdigest()==artifact['sha256'],'Compiled artifact')
        raw_count+=len(physical);groups+=len(facts['groups'])
    phase_functions.append(handles)
    if not name.endswith('.timeline'):
        manifest_prefix='runs/type-math-v2/output/public/' if name=='types' else base+name+'/'
        manifest=j(manifest_prefix+'manifest.json')
        for file,entry in manifest['files'].items():
            payload=files[manifest_prefix+file]
            need(len(payload)==entry['bytes'] and hashlib.sha256(payload).hexdigest()==entry['sha256'],'Bundle manifest')
need(phase_functions[0]==phase_functions[1],'Cold/warm loaded function identity changed')
for name in ['api-cold','api-warm','api-export-failure','api-after-failure','api-overflow','cli','legacy-auto']:
    need(base+name+'-math/host-once.txt' in files and base+name+'-math/math-passed.txt' in files,'Original once/math proof')
need(len(j(base+'legacy-auto/ai/observations.json')['captures'])==4,'Legacy count lost')
for job in j('owned-terminal-status.json'):
    need(all(p['state'] in ('missing','Z','pid_reused') for p in job['owned']),'Owned process still live')
types=j('runs/type-math-v2/output/result.json')
need(types['actual_math_launches']==5 and all(v['exact_cpu_math'] and v['state']==[1,1,1] for v in types['math']),'Five-type math requests')
need(files['type-input-v2/p01_nvidia_boundary_math.py']==(repo/'tests/timeline/p01_nvidia_boundary_math.py').read_bytes(),'Actual type test source differs')
for mode in ('normal','optimized'):
    contract=j('runs/install-v3/output/boundary-native-contract-'+mode+'/result.json')
    need(contract['anchors']==34 and contract['dependent_counter_reads']==17 and len(contract['rejected'])==4 and contract['legacy_path_unchanged'],'Compiler boundary/legacy contract')
objects=j('runs/ssa-object-inspection-v2/output/objects.json')
need(len(objects)==7,'Missing final objects')
for obj in objects:
    path=str(Path(obj['cubin']).relative_to('/workspace/chijin-timeline-r009'))
    need(hashlib.sha256(files[path]).hexdigest()==obj['sha256'],'Disassembled different cubin')
    for step in obj['steps']:
        need(step['returncode']==0 and '--no-dataflow' not in step['argv'],'Disassembly/CFG failed or downgraded')
        for stream in ('stdout','stderr'):
            blob=files['runs/ssa-object-inspection-v2/output/'+str(obj['index'])+'-'+step['kind']+'.'+stream]
            need(hashlib.sha256(blob).hexdigest()==step[stream+'_sha256'],'Changed actual disassembler output')
    meta,functions=j('runs/ssa-object-inspection-v2/output/'+str(obj['index'])+'-json.stdout')
    need(meta['SM']['version']=={'major':12,'minor':0},'Wrong actual machine target')
    need(all(not ins.get('opcode','').startswith('MEMBAR') for f in functions for ins in f['sass-instructions']),'Unexpected hardware membar')
out=dict(status='compiler_dependencies_and_canonical_raw_independently_audited_not_full_P01',captures=len(seen_invocations),physical_records=raw_count,
         paired_intervals=intervals,incomplete_endpoints=orphans,logical_groups=groups,overwritten_records=overwritten,
         canonical_cpu_methods_each_mode=15,boundary_cpu_rejections_each_mode=4,type_math_calls=5,final_objects_byte_bound=7,warm_loaded_functions_reused=True,
         archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
         limits=['Unverified physical clock/epoch and final machine boundaries','No Perfetto/P01/independent qualification acceptance'])
(root/'ssa-v2-root-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
