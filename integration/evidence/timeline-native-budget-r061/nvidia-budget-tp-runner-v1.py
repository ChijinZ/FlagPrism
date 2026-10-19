import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);root=Path('/workspace/chijin-timeline-r061-nvidia/runs/budget-pipeline-v1/output/device/profile/timeline');rows=[];seals={}
for item in json.loads((root/'index.json').read_text())['captures']:
 capfile=root/item['capture_file'];cap=json.loads(capfile.read_text())
 for field,kind in [('counter_ns_exports','counter'),('observed_dependency_exports','dependency')]:
  for export in cap.get(field,[]):
   row=dict(export,kind=kind,source_capture_file=str(capfile),source_capture_sha256=hashlib.sha256(capfile.read_bytes()).hexdigest(),raw_file=str(root/cap['raw_file']),canonical_file=str(root/Path(export['view_file']).parent.parent/'canonical.json'))
   for k in ['trace_file','view_file']:row[k]=str(root/export[k])
   if kind=='dependency':row['inputs_file']=str(root/Path(export['receipt_file']).parent/'inputs.json')
   for k in ['trace_file','view_file','raw_file','canonical_file','inputs_file']:
    if k in row:
     p=Path(row[k]);seals[str(p)]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
   rows.append(row)
if len(rows)!=20:raise RuntimeError('Wrong registered denominator')
(a.output/'registered.json').write_text(json.dumps(rows,indent=2));(a.output/'input-seals.json').write_text(json.dumps(seals,indent=2));source=Path('/workspace/chijin-timeline-r059-nvidia/tools-smoke-input-v1/source');results=[]
for kind,name,expected,count in [('counter','verify_perfetto_traces.py','75e1b08b1dd71256dd442f6ad3bfbffe745ba900026e8f6493e6ef208931a618',16),('dependency','verify_dependency_traces.py','0d72cf3a882ea4b9d3bd1fe6c7172066fa486f708db8d2787ae47aef15147e03',4)]:
 script=source/name
 if hashlib.sha256(script.read_bytes()).hexdigest()!=expected:raise RuntimeError('Qualified verifier changed')
 selected=[r for r in rows if r['kind']==kind]
 if len(selected)!=count:raise RuntimeError('Wrong kind denominator')
 manifest=a.output/(kind+'.json');manifest.write_text(json.dumps(selected,indent=2));cmd=[sys.executable,'-I',str(script),'--manifest',str(manifest),'--output',str(a.output/kind)]
 with (a.output/(kind+'.log')).open('xb') as log:
  c=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();owner=dict(kind=kind,argv=cmd,pid=c.pid,startticks=int(f[19]));(a.output/(kind+'-owner.json')).write_text(json.dumps(owner));owner['returncode']=c.wait(timeout=150);(a.output/(kind+'-owner.json')).write_text(json.dumps(owner))
 if owner['returncode']:raise RuntimeError('Actual '+kind+' TP failed')
 output=a.output/kind/'result.json';result=json.loads(output.read_text())
 if len(result['checks'])!=count:raise RuntimeError('Wrong verified denominator')
 results.append(dict(kind=kind,count=count,result_file=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
for name,info in seals.items():
 if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=info['sha256']:raise RuntimeError('Original bytes changed')
(a.output/'result.json').write_text(json.dumps(dict(status='actual_new_budget_pipeline_TP_passed',registered=20,counter=16,dependency=4,results=results,application_replayed=False,device_executed=False),indent=2))
