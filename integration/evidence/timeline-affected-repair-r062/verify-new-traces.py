"""Bounded CPU-only cohort import; one durable verifier receipt per trace."""
import argparse,concurrent.futures,hashlib,importlib.util,json,os,subprocess,sys,threading,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
base=Path('/workspace/chijin-timeline-r062-nvidia')
data=base/'imported/ascend/data'
manifest=json.loads((data/'manifest.json').read_text())
if manifest['backend']!='ascend' or len(manifest['captures'])!=60 or manifest['missing_original_counter_exports']:raise RuntimeError('Wrong affected60 actual captures')
for name,seal in manifest['files'].items():
 p=data/name
 if p.stat().st_size!=seal['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=seal['sha256']:raise RuntimeError('Transferred original bytes changed')
rows=[]
for old in manifest['traces']:
 row=dict(old)
 for name in ['trace_file','view_file','raw_file','canonical_file','inputs_file']:
  if name in row:row[name]=str(data/row[name])
 rows.append(row)
source=Path('/workspace/chijin-timeline-r059-nvidia/tools-smoke-input-v1/source');backend='ascend'
source_sha={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ['verify_perfetto_traces.py','verify_dependency_traces.py']}
if source_sha!={'verify_perfetto_traces.py':'75e1b08b1dd71256dd442f6ad3bfbffe745ba900026e8f6493e6ef208931a618','verify_dependency_traces.py':'0d72cf3a882ea4b9d3bd1fe6c7172066fa486f708db8d2787ae47aef15147e03'}:raise RuntimeError('Qualified verifier bytes changed')
config={}
reused={}
def key_for(row):
 fields={name:hashlib.sha256(Path(row[name]).read_bytes()).hexdigest() for name in ['trace_file','view_file','raw_file','canonical_file','inputs_file'] if name in row}
 return hashlib.sha256(json.dumps(dict(kind=row['kind'],files=fields),sort_keys=True).encode()).hexdigest()
spec=importlib.util.spec_from_file_location('owned_deadline','/workspace/chijin-timeline-r020-style/input/_deadline.py');deadline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=deadline;spec.loader.exec_module(deadline)
lock=threading.Lock();records=[];started=time.monotonic();stop_new_after=250
(a.output/'registered.json').write_text(json.dumps(dict(backend=backend,part=config.get('part'),rows=rows,source_sha256=source_sha,application_replayed=False,device_executed=False),indent=2))
def verify(pair):
 i,row=pair;key=key_for(row);report=dict(index=i,proof_key=key,backend=backend,stage=row['stage'],case=row['case'],kind=row['kind'],trace_sha256=row['sha256'],source_capture_file=row['source_capture_file'],source_capture_sha256=row['source_capture_sha256'])
 if key in reused:report.update(status='reused_exact_input_actual_TP_success',**reused[key]);return report
 if time.monotonic()-started>stop_new_after:report['status']='not_started_budget';return report
 folder=a.output/f'{i:04d}';folder.mkdir();manifest=folder/'manifest.json';manifest.write_text(json.dumps([row]));script=source/('verify_dependency_traces.py' if row['kind']=='dependency' else 'verify_perfetto_traces.py');cmd=[sys.executable,'-I',str(script),'--manifest',str(manifest),'--output',str(folder/'verified')]
 with (folder/'stdout.log').open('xb') as out,(folder/'stderr.log').open('xb') as err:
  child=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True);f=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split();owner=dict(pid=child.pid,pgid=int(f[2]),startticks=int(f[19]),argv=cmd);(folder/'launch.json').write_text(json.dumps(owner));report['pid']=child.pid;report['startticks']=int(f[19])
  try:report['returncode']=child.wait(timeout=75)
  except subprocess.TimeoutExpired:
   deadline._stop_worker(child);report.update(status='verifier_timeout',returncode=child.poll())
  else:
   if report['returncode']:report.update(status='verifier_failed',error=(folder/'stderr.log').read_text(errors='replace')[-2000:])
   else:
    result=json.loads((folder/'verified/result.json').read_text())
    if len(result['checks'])!=1 or result['checks'][0]['sha256']!=row['sha256']:raise RuntimeError('Verifier returned a different trace')
    report.update(status='actual_TP_passed',result_file=str(folder/'verified/result.json'),result_row=0,result_sha256=hashlib.sha256((folder/'verified/result.json').read_bytes()).hexdigest())
 (folder/'terminal.json').write_text(json.dumps(report,indent=2));return report
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 futures=[pool.submit(verify,pair) for pair in enumerate(rows)]
 for future in concurrent.futures.as_completed(futures):
  record=future.result();records.append(record)
  with (a.output/'progress.jsonl').open('a') as output:output.write(json.dumps(record)+'\n')
  if len(records)%32==0:(a.output/'current.json').write_text(json.dumps(dict(completed=len(records),total=len(rows),failed=sum(r['status'] not in ['actual_TP_passed','reused_exact_input_actual_TP_success'] for r in records))))
records.sort(key=lambda r:r['index']);good=[r for r in records if r['status'] in ['actual_TP_passed','reused_exact_input_actual_TP_success']]
result=dict(status='actual_TP_cohort_passed' if len(good)==len(rows) else 'actual_TP_cohort_incomplete',backend=backend,part=config.get('part'),registered=len(rows),passed=len(good),fresh_TP=sum(r['status']=='actual_TP_passed' for r in records),reused=sum(r['status']=='reused_exact_input_actual_TP_success' for r in records),failed=[r for r in records if r not in good],elapsed_s=time.monotonic()-started,application_replayed=False,device_executed=False,source_sha256=source_sha,checks=records,limits='actual repaired affected60 exports only; not final source-boundary, ordinary-overlap, or new UI qualification')
(a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['checks','failed']}))
if len(good)!=len(rows):raise SystemExit(1)
