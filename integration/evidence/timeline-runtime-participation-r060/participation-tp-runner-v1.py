import argparse,hashlib,json,subprocess,sys,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);root=Path(__file__).parent;archive=root/'inputs.tgz'
if hashlib.sha256(archive.read_bytes()).hexdigest()!='c017d82e9b2201b0cb5940349db0f0d04ffc6519ceb01fc8ab09679a842369eb':raise RuntimeError('Archive bytes differ')
data=a.output/'inputs';data.mkdir()
with tarfile.open(archive) as t:
 for m in t:
  if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise RuntimeError('Unsafe input archive')
  p=data/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
manifest=json.loads((data/'manifest.json').read_text());seals={}
for name,info in manifest['files'].items():
 p=data/name;raw=p.read_bytes()
 if len(raw)!=info['bytes'] or hashlib.sha256(raw).hexdigest()!=info['sha256']:raise RuntimeError('Original blob seal differs')
 seals[str(p)]=info
rows=manifest['traces']
for row in rows:
 for key in ['trace_file','view_file','raw_file','canonical_file','inputs_file']:
  if key in row:row[key]=str(data/row[key])
(a.output/'all-traces.json').write_text(json.dumps(rows,indent=2));(a.output/'sealed-inputs.json').write_text(json.dumps(seals,indent=2));source=Path('/workspace/chijin-timeline-r059-nvidia/tools-smoke-input-v1/source');expected={'counter':('verify_perfetto_traces.py','75e1b08b1dd71256dd442f6ad3bfbffe745ba900026e8f6493e6ef208931a618',8),'dependency':('verify_dependency_traces.py','0d72cf3a882ea4b9d3bd1fe6c7172066fa486f708db8d2787ae47aef15147e03',2)};steps=[];checks=[]
for kind,(name,digest,count) in expected.items():
 script=source/name
 if hashlib.sha256(script.read_bytes()).hexdigest()!=digest:raise RuntimeError('Previously qualified verifier changed')
 selected=[r for r in rows if r['kind']==kind]
 if len(selected)!=count:raise RuntimeError('Registered denominator differs')
 registered=a.output/(kind+'.json');registered.write_text(json.dumps(selected));cmd=[sys.executable,'-I',str(script),'--manifest',str(registered),'--output',str(a.output/kind)]
 with (a.output/(kind+'.log')).open('xb') as log:
  c=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();step=dict(kind=kind,argv=cmd,pid=c.pid,startticks=int(f[19]));steps.append(step);step['returncode']=c.wait(timeout=60)
 (a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if step['returncode']:raise RuntimeError('Actual TP failed '+kind)
 resultfile=a.output/kind/'result.json';result=json.loads(resultfile.read_text())
 if len(result['checks'])!=count:raise RuntimeError('Actual result denominator differs')
 checks.append(dict(kind=kind,count=count,result_file=str(resultfile),sha256=hashlib.sha256(resultfile.read_bytes()).hexdigest()))
(a.output/'result.json').write_text(json.dumps(dict(status='actual_new_participation_trace_TP_passed',registered=10,counter=8,dependency=2,checks=checks,application_replayed=False,device_executed=False,steps=steps),indent=2))
