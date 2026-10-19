"""Bounded CPU-only cohort import; one durable verifier receipt per trace."""
import argparse,concurrent.futures,hashlib,importlib.util,json,os,subprocess,sys,threading,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
config=json.loads((Path(__file__).parent/'config.json').read_text());base=Path('/workspace/chijin-timeline-r059-nvidia');smoke=base/'runs/tools-smoke-v1/output';all_rows=json.loads((base/'runs/q04-audit-v1/output/all-traces.json').read_text());source=base/'tools-smoke-input-v1/source';backend=config['backend']
rows=sorted([r for r in all_rows if r['backend']==backend],key=lambda r:(r['stage'],r['case'],r['kind'],r['observer_id'],r['sha256']))
if backend=='nvidia':rows=rows[:len(rows)//2] if config['part']==0 else rows[len(rows)//2:]
checks={r['file']:r for r in json.loads((smoke/'input-sha-checks.json').read_text())};checks.update(json.loads((base/'runs/q04-audit-v1/output/extra-input-sha-checks.json').read_text()))
source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')};prior=json.loads((smoke/'result.json').read_text())
if source_sha!=prior['source_sha256']:raise RuntimeError('Verifier bytes changed after actual smoke')
def key_for(row):
 fields={}
 for name in ['trace_file','view_file','raw_file','canonical_file','inputs_file']:
  if name in row:
   path=row[name]
   if path not in checks:raise RuntimeError('Unsealed verifier input')
   fields[name]=checks[path]['sha256']
 return hashlib.sha256(json.dumps(dict(kind=row['kind'],files=fields),sort_keys=True).encode()).hexdigest()
reused={}
for name in ['counter-normal','dependency-normal']:
 old_rows=json.loads((smoke/(name+'.json')).read_text());result=json.loads((smoke/name/'result.json').read_text())
 if len(old_rows)!=len(result['checks']):raise RuntimeError('Smoke receipt denominator differs')
 for i,(row,check) in enumerate(zip(old_rows,result['checks'])):
  if check['sha256']!=row['sha256'] or check['importer_errors']:raise RuntimeError('Smoke trace SHA/errors differ')
  reused[key_for(row)]=dict(result_file=str(smoke/name/'result.json'),result_row=i)
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
result=dict(status='actual_TP_cohort_passed' if len(good)==len(rows) else 'actual_TP_cohort_incomplete',backend=backend,part=config.get('part'),registered=len(rows),passed=len(good),fresh_TP=sum(r['status']=='actual_TP_passed' for r in records),reused=sum(r['status']=='reused_exact_input_actual_TP_success' for r in records),failed=[r for r in records if r not in good],elapsed_s=time.monotonic()-started,application_replayed=False,device_executed=False,source_sha256=source_sha,checks=records,limits='historical retained views only; not current mechanism/default completeness/source-boundary/UI qualification')
(a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['checks','failed']}))
if len(good)!=len(rows):raise SystemExit(1)
