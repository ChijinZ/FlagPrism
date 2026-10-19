import argparse,hashlib,json,struct,sys,subprocess,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
if not a.child:
 a.output.mkdir(parents=True);steps=[]
 for name,flags in [('normal',[]),('optimized',['-O'])]:
  cmd=[sys.executable,'-I',*flags,__file__,'--output',str(a.output/name),'--child']
  with (a.output/(name+'.log')).open('xb') as log:
   c=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();row=dict(name=name,argv=cmd,pid=c.pid,startticks=int(f[19]));steps.append(row);row['returncode']=c.wait(timeout=45)
  (a.output/'steps.json').write_text(json.dumps(steps))
  if row['returncode']:raise RuntimeError(name+' failed')
 (a.output/'result.json').write_text(json.dumps(dict(status='actual_retained_legacy_identity_and_new_raw_faults_passed',modes=[json.loads((a.output/name/'result.json').read_text()) for name in ['normal','optimized']],steps=steps),indent=2));raise SystemExit(0)
a.output.mkdir();from flagtree.profiler.timeline_events_ascend import canonicalize_ascend_capture
old=Path('/tmp/chijin-timeline-r055-qualification-ascend-v2/runs/profile-first-v1');new=Path('/tmp/chijin-timeline-r060-ascend/runs/participation-device-v1/output/device');checks=[]
for label,root,legacy in [('legacy-vector',old/'q01-s0-c0-cold/capture/timeline',True),('legacy-mixed',old/'q05-s0-c0-cold/capture/timeline',True),('new-vector',new/'vector/capture/timeline',False),('new-mixed',new/'mixed/capture/timeline',False)]:
 before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()};row=json.loads((root/'index.json').read_text())['captures'][0];capture=json.loads((root/row['capture_file']).read_text());original=json.loads((root/'captures'/(row['invocation_id']+'.input.json')).read_text());raw=(root/original['raw_file']).read_bytes()
 def decode(data):return canonicalize_ascend_capture(data,owner=original['owner'],metadata=original['metadata']['compiler_metadata'],association=original['launch'])
 batch=decode(raw)
 if batch!=json.loads((root/capture['events_file']).read_text()):raise RuntimeError('Actual canonical bytes changed: '+label)
 tests=[]
 if not legacy:
  stride=original['owner']['layout']['scratch_size'];mut=bytearray(raw)
  if label=='new-vector':
   flags=struct.unpack_from('<Q',mut,stride+56)[0];struct.pack_into('<Q',mut,stride+56,(flags&255)|(2<<8))
   if decode(bytes(mut))['complete']:raise RuntimeError('Missing second vector writer falsely complete')
   tests.append('higher_expected_count_stays_incomplete');mut=bytearray(raw);mut[2*stride+64]=1
  else:
   mut[2*stride:3*stride]=bytes(stride)
   if decode(bytes(mut))['complete']:raise RuntimeError('Lost expected actor falsely complete')
   tests.append('removed_expected_actor_stays_incomplete');mut=bytearray(raw);flags=struct.unpack_from('<Q',mut,stride+56)[0];struct.pack_into('<Q',mut,stride+56,(flags&255)|(1<<8))
  try:decode(bytes(mut))
  except ValueError:tests.append('invalid_unselected_or_conflicting_raw_rejected')
  else:raise RuntimeError('Actual invalid topology accepted: '+label)
 after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
 if before!=after:raise RuntimeError('Original changed')
 checks.append(dict(label=label,complete=batch['complete'],observers=len(batch['observers']),events=len(batch['events']),files_unchanged=len(before),canonical_equal=True,fault_checks=tests))
(a.output/'result.json').write_text(json.dumps(dict(checks=checks),indent=2))
