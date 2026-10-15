"""Independent retained-data audit; never imports or executes profiler code."""
from pathlib import Path
import json,hashlib,base64,struct,collections
base=Path('artifacts/method-run/ascend/round2');root=base/'origin-source-manifest-extracted';p=root/'round2-origin-mix-r1';bundle=p/'capture';manifest=json.loads((bundle/'manifest.json').read_text());count=0
for relative,meta in manifest['files'].items():
 f=(bundle/relative).resolve();assert f.is_relative_to(bundle.resolve());raw=f.read_bytes();assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256'];count+=1
payload=json.loads((bundle/'ai/observations.json').read_text());bycapture=collections.defaultdict(dict);actors=collections.Counter()
for e in payload['observations']:
 key=(e['actor_slot'],e['occurrence']);assert key not in bycapture[e['capture_id']];bycapture[e['capture_id']][key]=e;assert e['program_selection_status']=='consistent_with_expected_program' and e['expected_program']==e['program']==0;assert e['clock']['tick_ns']==20 and e['clock']['alignment']=='instance_local' and e['clock']['scope']=='actor_local';assert e['relative_start_ns'] is None and e['duration_ns']==(e['end_tick']-e['start_tick'])*20;actors[str(e['actor_slot'])]+=1
buffers=records=0
for c in payload['captures']:
 assert c['capture_status']=='decoded' and c['dropped']==0 and not c.get('decode_error');raw=base64.b64decode(c['raw_base64'],validate=True);assert len(raw)==49248 and hashlib.sha256(raw).hexdigest()==c['raw_sha256'];words=struct.unpack('<6156Q',raw);retained=0
 for actor in range(3):
  offset=actor*(4+256*8);version,cursor,attempted,dropped=words[offset:offset+4];assert version==1 and cursor==attempted and dropped==0 and cursor<=256
  for i in range(cursor):
   rec=list(words[offset+4+i*8:offset+4+(i+1)*8]);e=bycapture[c['capture_id']][(actor,rec[1])];assert rec==e['original_record'] and rec[4]==0 and rec[5]==actor;assert rec[2]==e['start_tick'] and rec[3]==e['end_tick'];retained+=1
 assert retained==len(bycapture[c['capture_id']]);records+=retained;buffers+=1
assert buffers==4 and records==232 and dict(actors)=={'0':192,'1':20,'2':20}
d=json.loads((p/'result.json').read_text());h=d['compiler_metadata']['flagprism_ascend_handoff'];remote_prefix='/tmp/flagprism-method-ascend/'
def sidecar(name):assert name.startswith(remote_prefix);return root/name[len(remote_prefix):]
source=h['source_snapshot']['ir'].encode();assert sidecar(h['output']+'/source.mlir').read_bytes()==source;assert hashlib.sha256(source).hexdigest()==h['source_snapshot']['ir_sha256']==h['sdk_ir_capture']['receipt']['source_ir_sha256'];assert h['compile_id']==h['sdk_ir_capture']['receipt']['compile_id'];sizes=[]
for a in h['artifacts']:
 raw=a['manifest_text'].encode();assert raw==sidecar(a['manifest_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==a['manifest_sha256'];assert json.dumps(json.loads(raw),sort_keys=True,separators=(',',':'))==json.dumps(a['metadata'],sort_keys=True,separators=(',',':'));assert hashlib.sha256(a['llir'].encode()).hexdigest()==a['sha256']==a['metadata']['module_sha256'];assert a['metadata']['compile_id']==a['driver_job']['compile_id']==h['compile_id'] and a['driver_job']['exit_code']==0;sizes.append(len(raw))
assert d['status']=='passed_math_and_native' and d['device_task_identity_status']=='verified' and len(d['device_task_samples'])==3
result={'state':'passed_independent_data_only_audit','archive_sha256':hashlib.sha256((base/'round2-origin-source-manifest-evidence.tgz').read_bytes()).hexdigest(),'bundles':1,'manifest_entries_sha_and_bytes':count,'raw_buffers':buffers,'raw_records':records,'actor_record_counts':dict(actors),'unchanged_original_record_identity_ticks':True,'local_duration_formula_20ns':True,'program0_consistency':True,'actual_source_bytes':len(source),'actual_manifest_bytes':sizes,'same_enclosing_compile_and_actor_llvm':True,'measured_native_tasks':3,'max_abs_error':d['max_abs_error'],'boundary':'Data-only SHA/byte/schema audit, not a new GPU experiment or timing-accuracy certificate.'};(base/'origin-local-independent-data-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
