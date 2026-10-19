"""Seal minimal original bytes for CPU-only TP validation; never replay kernels."""
import argparse,hashlib,json,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
base=Path('/tmp/chijin-timeline-r062-ascend')
prepare=base/'runs/prepare-v1/output'
registration=json.loads((prepare/'registration-v2.json').read_text())
if len(registration['calls'])!=60 or registration['base_registration_sha256']!='a56d8bc209848393deaa1a12a2b901a4ad77799b1f9d36588fdc660c05d4c5e0':raise RuntimeError('Original affected registration differs')
receipts=[]
for i,call in enumerate(registration['calls']):
 r=base/'runs'/f'{i:03d}'
 terminal=json.loads((r/'terminal.json').read_text())
 f=r/'output/result.json'
 if not f.exists():f=r/'output/result-v2-retained.json'
 receipt=json.loads(f.read_text())
 if receipt['status']!='affected_registered_call_passed' or receipt['registered_call']!=call:raise RuntimeError('Registered actual call incomplete or differs')
 if terminal['returncode']!=0 and not (i==0 and terminal['returncode']==1 and receipt.get('application_replayed') is False):raise RuntimeError('Unexpected failed original controller')
 receipts.append(dict(index=i,case=call['id'],phase=call['phase'],controller_returncode=terminal['returncode'],receipt_file=str(f),receipt_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(a.output/'registered-call-receipts.json').write_text(json.dumps(receipts,indent=2))
config=dict(backend='ascend',stages=[('affected60',str(base/'runs'))])
backend=config['backend'];blobroot=a.output/'data/blobs';blobroot.mkdir(parents=True)
files={};rows=[];captures=[];missing=[];sealed_paths={}
def seal(path,expected=None):
 path=Path(path).resolve()
 if str(path) in sealed_paths:
  name=sealed_paths[str(path)]
  if expected is not None and files[name]['sha256']!=expected:raise RuntimeError('Conflicting expected original SHA')
  return name
 data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
 if expected is not None and digest!=expected:raise RuntimeError('Original artifact SHA changed: '+str(path))
 name=str(path) if config.get('local_only') else 'blobs/'+digest;dest=a.output/'data'/name
 if not config.get('local_only') and not dest.exists():dest.write_bytes(data)
 files[name]=dict(sha256=digest,bytes=len(data));sealed_paths[str(path)]=name
 return name
for stage,path in config['stages']:
 root=Path(path)
 if not root.is_dir():raise RuntimeError('Missing registered qualification stage: '+path)
 for indexfile in sorted(root.glob('[0-9][0-9][0-9]/output/capture/timeline/index.json')):
  timeline=indexfile.parent;case=indexfile.parents[3].name
  for indexrow in json.loads(indexfile.read_text())['captures']:
   capfile=timeline/indexrow['capture_file'];original=capfile.read_bytes();cap=json.loads(original);capture_id=cap['owner']['invocation_id'];canonical=timeline/cap['events_file'];raw=timeline/cap['raw_file']
   exports=cap.get('counter_ns_exports',[]);deps=cap.get('observed_dependency_exports',[])
   if not exports:missing.append(dict(stage=stage,case=case,invocation_id=capture_id,reason='no_original_counter_export'))
   captures.append(dict(stage=stage,case=case,invocation_id=capture_id,source_capture_file=str(capfile),source_capture_sha256=hashlib.sha256(original).hexdigest(),counter_exports=len(exports),dependency_exports=len(deps),canonical_complete=json.loads(canonical.read_text()).get('complete')))
   for kind,items in [('counter',exports),('dependency',deps)]:
    for export in items:
     trace=timeline/export['trace_file'];view=timeline/export['view_file'];canonical_file=timeline/Path(export['view_file']).parent.parent/'canonical.json'
     row=dict(kind=kind,backend=backend,stage=stage,case=case,invocation_id=capture_id,observer_id=export['observer_id'],source_capture_file=str(capfile),source_capture_sha256=hashlib.sha256(original).hexdigest(),source_trace_file=str(trace),sha256=export['sha256'])
     row.update(trace_file=seal(trace,export['sha256']),view_file=seal(view),raw_file=seal(raw,cap['raw_sha256']),canonical_file=seal(canonical_file))
     if kind=='dependency':row['inputs_file']=seal(timeline/Path(export['receipt_file']).parent/'inputs.json')
     rows.append(row)
if len(captures)!=60 or missing:raise RuntimeError('Expected all60 actual primary captures with ns exports')
manifest=dict(schema_version=1,application_replayed=False,device_executed=False,backend=backend,captures=captures,traces=rows,files=files,missing_original_counter_exports=missing,scope='new affected60 views; SQL import alone does not prove native source boundaries or UI acceptance')
(a.output/'data/manifest.json').write_text(json.dumps(manifest,sort_keys=True,separators=(',',':')))
if config.get('local_only'):
 result=dict(status='minimal_actual_byte_inputs_prepared_no_TP_or_device_run',backend=backend,captures=len(captures),traces=len(rows),counter_traces=sum(r['kind']=='counter' for r in rows),dependency_traces=sum(r['kind']=='dependency' for r in rows),blob_bytes=0,archive=None,chunks=[],missing_original_counter_exports=missing)
 (a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));raise SystemExit(0)
archive=a.output/'audit-inputs.tgz'
with tarfile.open(archive,'w:gz',compresslevel=1) as t:
 for name in ['manifest.json',*sorted(files)]:t.add(a.output/'data'/name,arcname=name,recursive=False)
chunkroot=a.output/'chunks';chunkroot.mkdir();chunks=[]
with archive.open('rb') as f:
 index=0
 while True:
  data=f.read(3*1024*1024)
  if not data:break
  name=f'{index:03d}.part';(chunkroot/name).write_bytes(data);chunks.append(dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));index+=1
result=dict(status='minimal_actual_byte_inputs_prepared_no_TP_or_device_run',backend=backend,captures=len(captures),traces=len(rows),counter_traces=sum(r['kind']=='counter' for r in rows),dependency_traces=sum(r['kind']=='dependency' for r in rows),blob_bytes=sum(x['bytes'] for x in files.values()),archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),chunks=chunks,missing_original_counter_exports=missing)
(a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
