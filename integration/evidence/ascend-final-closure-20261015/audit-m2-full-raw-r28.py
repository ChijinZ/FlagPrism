"""Independent offline audit of retained real captures; does not execute tool code."""
from pathlib import Path
import hashlib,json,tarfile,base64,struct,collections
base=Path('artifacts/method-run/ascend')
archives=[('m2-semantic-r28-evidence.tgz','5a18249352bbc73566d114fa0a27416c40d9a09b83cd7a31d76ac54bc608341e')]
result=[]
for name,expected in archives:
 archive=base/name;assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
 destination=base/(name.removesuffix('.tgz')+'-extracted')
 if not destination.exists():
  destination.mkdir()
  with tarfile.open(archive) as t:t.extractall(destination,filter='data')
 counts=collections.Counter();actors=collections.Counter();all_events=0;all_buffers=0;result_files=[]
 for path in destination.rglob('manifest.json'):
  manifest=json.loads(path.read_text())
  if 'capture_id' not in manifest or not isinstance(manifest.get('files'),dict):continue
  root=path.parent
  for relative,meta in manifest['files'].items():
   fp=(root/relative).resolve();assert fp.is_relative_to(root.resolve())
   raw=fp.read_bytes();assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256'],str(fp)
   counts['manifest_files']+=1
  counts['bundles']+=1
  obs=root/'ai/observations.json'
  if not obs.exists():continue
  payload=json.loads(obs.read_text());events=payload['observations'];bycapture=collections.defaultdict(dict)
  for event in events:
   key=(event['actor_slot'],event['occurrence']);assert key not in bycapture[event['capture_id']]
   bycapture[event['capture_id']][key]=event
   assert event['association_status']=='verified'
   assert event['clock']['alignment']=='instance_local' and event['clock']['scope']=='actor_local'
   assert event['clock']['tick_ns']==20.0
   ticks=(event['end_tick']-event['start_tick'])%(1<<64)
   assert ticks==event['duration_ticks'] and event['duration_ns']==ticks*20
   actors[str(event['actor_slot'])]+=1
  for capture in payload['captures']:
   assert capture['capture_status']=='decoded' and not capture.get('decode_error')
   assert capture['dropped']==0 and not capture.get('counter_saturated')
   raw=base64.b64decode(capture['raw_base64'],validate=True)
   assert hashlib.sha256(raw).hexdigest()==capture['raw_sha256']
   assert len(raw)%8==0
   words=struct.unpack('<'+'Q'*(len(raw)//8),raw)
   assert len(words)%3==0 and (len(words)//3-4)%8==0
   capacity=(len(words)//3-4)//8;retained=0
   for actor in range(3):
    offset=actor*(4+capacity*8);version,cursor,attempted,dropped=words[offset:offset+4]
    if version==0:assert cursor==attempted==dropped==0;continue
    assert version==1 and cursor==attempted and dropped==0 and cursor<=capacity
    for index in range(cursor):
     record=list(words[offset+4+index*8:offset+4+(index+1)*8]);event=bycapture[capture['capture_id']][(actor,record[1])]
     assert record==event['original_record'];assert event['start_tick']==record[2] and event['end_tick']==record[3]
     assert record[5]==actor and record[4]==event['program'] and (record[0]&0xffffffff)==event['site']
     retained+=1
   assert retained==len(bycapture[capture['capture_id']]);all_buffers+=1
  all_events+=len(events);counts['detailed_bundles']+=1
 for path in destination.rglob('result.json'):
  d=json.loads(path.read_text())
  if 'plan' in d:
   counts['result_files']+=1;counts['mode_'+d['plan']['mode']]+=1
   assert d['status']==('passed_math' if d['plan']['mode']=='off' else 'passed_math_and_native'),str(path)
   if d['plan']['mode']!='off':assert d['device_task_identity_status']=='verified',str(path)
   result_files.append({'path':str(path.relative_to(destination)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':d['plan']['mode'],'operator':d['plan']['operator']})
 summary={'archive':name,'sha256':expected,'counts':dict(counts),'observations':all_events,'raw_buffers':all_buffers,'actors':dict(actors),'results':result_files,'status':'independent_raw_hash_record_identity_and_local_duration_audit_passed','limits':['Does not certify shared clock origin or exclusive source cost.','Hardware mathematical outcomes are recorded assertions; original numerical execution occurred in Docker.']}
 result.append(summary);print(name,dict(counts),'events',all_events,'buffers',all_buffers,flush=True)
 (base/'m2-root-full-raw-audit-r28.json').write_text(json.dumps(result,indent=2)+'\n')
