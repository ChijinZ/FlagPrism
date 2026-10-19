import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);root=Path('/workspace/chijin-timeline-r061-nvidia/runs');rows=[];files={}
for case,folder in [('C1',root/'compute-device-v1/output/device/resume/timeline'),('C2-0',root/'compute-C2-v1/output/device/32-0/capture/timeline'),('C2-1',root/'compute-C2-v1/output/device/32-1/capture/timeline')]:
 for item in json.loads((folder/'index.json').read_text())['captures']:
  path=folder/item['capture_file'];cap=json.loads(path.read_text())
  for field in ['counter_ns_exports','shared_counter_exports']:
   for old in cap.get(field,[]):
    row=dict(old,kind='counter',case=case,invocation_id=item['invocation_id'],source_capture_file=str(path),source_capture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),raw_file=str(folder/cap['raw_file']),canonical_file=str(folder/Path(old['view_file']).parent.parent/'canonical.json'))
    for key in ['trace_file','view_file']:row[key]=str(folder/row[key])
    for key in ['trace_file','view_file','raw_file','canonical_file']:
     x=Path(row[key]);files[str(x)]=dict(bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest())
    rows.append(row)
if len(rows)!=40:raise RuntimeError('Expected 4 actual captures x (8 observer + 2 shared) traces, got '+str(len(rows)))
manifest=a.output/'registered.json';manifest.write_text(json.dumps(rows,indent=2));(a.output/'input-seals.json').write_text(json.dumps(files,indent=2));script=Path('/workspace/chijin-timeline-r059-nvidia/tools-smoke-input-v1/source/verify_perfetto_traces.py')
if hashlib.sha256(script.read_bytes()).hexdigest()!='75e1b08b1dd71256dd442f6ad3bfbffe745ba900026e8f6493e6ef208931a618':raise RuntimeError('Qualified verifier changed')
cmd=[sys.executable,'-I',str(script),'--manifest',str(manifest),'--output',str(a.output/'verified')]
with (a.output/'verify.log').open('xb') as log:
 c=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();owner=dict(argv=cmd,pid=c.pid,startticks=int(f[19]));(a.output/'verifier-owner.json').write_text(json.dumps(owner));owner['returncode']=c.wait(timeout=150);(a.output/'verifier-owner.json').write_text(json.dumps(owner))
if owner['returncode']:raise RuntimeError('Actual pinned TP failed')
result=json.loads((a.output/'verified/result.json').read_text())
if len(result['checks'])!=len(rows):raise RuntimeError('SQL result denominator differs')
for row,check in zip(rows,result['checks']):
 if row['sha256']!=check['sha256'] or check['importer_errors']:raise RuntimeError('Actual trace SHA/importer error differs')
for name,info in files.items():
 x=Path(name)
 if hashlib.sha256(x.read_bytes()).hexdigest()!=info['sha256']:raise RuntimeError('Original input mutated')
(a.output/'result.json').write_text(json.dumps(dict(status='actual_40_new_counter_and_shared_traces_TP_passed',registered=len(rows),verifier_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),result_sha256=hashlib.sha256((a.output/'verified/result.json').read_bytes()).hexdigest(),application_replayed=False,device_executed=False),indent=2))
