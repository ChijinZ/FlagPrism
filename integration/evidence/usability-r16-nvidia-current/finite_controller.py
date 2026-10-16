"""Finite one-shot original NVIDIA cohort revalidation, no automatic retries."""
import ctypes,hashlib,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'usability_qualification';sys.path.insert(0,str(H));sys.path.insert(0,str(R))
import auth_r16
from auth_r16 import require
import check_unseen_metadata_r11 as gate
gate.verify_authorization=auth_r16.verify # only obsolete ce00 namespace authorization is adapted
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(p):return json.loads(Path(p).read_text())
class Terminated(RuntimeError):pass
def on_signal(number,frame):raise Terminated('controller signal '+str(number))
def exclusive_write(p,x):
 with p.open('x') as stream:stream.write(json.dumps(x,indent=2,sort_keys=True)+'\n')
def verify_ready(ready,freeze_path,controller_path):
 expected=dict(backend='nvidia',device=0,authorized=True,owner='qualification_r16_nvidia',container='chijin-study-pro6000',cpu_freeze_sha256=sha(freeze_path),controller_sha256=sha(controller_path))
 require(all(type(ready.get(k)) is type(v) and ready.get(k)==v for k,v in expected.items()),'root GPU_READY identity/hash binding required')
def identity(pid):
 p=Path('/proc')/str(pid);s=(p/'stat').read_text().split(') ',1)[1].split()
 return dict(pid=pid,pgid=os.getpgid(pid),start_ticks=s[19],argv_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest())
def descendants(pid):
 found={pid};changed=True
 while changed:
  changed=False
  for p in Path('/proc').glob('[0-9]*/stat'):
   try:
    s=p.read_text().split(') ',1)[1].split();child=int(p.parent.name)
    if int(s[1]) in found and child not in found:found.add(child);changed=True
   except (OSError,ValueError):pass
 return found-{pid}
def run(argv,folder,env,budget):
 folder.mkdir(parents=True,exist_ok=False);started=time.monotonic();owned={}
 with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
  p=subprocess.Popen(argv,stdout=out,stderr=err,env=env,start_new_session=True)
  stamp=identity(p.pid);write(folder/'process.json',dict(**stamp,argv=argv,outer_timeout_s=budget,started_unix=time.time()))
  timed=False;interrupted=None
  try:
   while p.poll() is None:
    for pid in descendants(p.pid):
     try:owned[pid]=identity(pid)
     except (OSError,ProcessLookupError):pass
    if time.monotonic()-started>budget:timed=True;break
    time.sleep(.1)
  except BaseException as error:interrupted=error
  finally:
   if timed or interrupted is not None:
    for pid in descendants(p.pid)|{p.pid}:
     try:owned[pid]=identity(pid)
     except (OSError,ProcessLookupError):pass
    # Cleanup cannot itself be interrupted. Signal only byte-identity verified owned PIDs.
    saved={s:signal.signal(s,signal.SIG_IGN) for s in [signal.SIGTERM,signal.SIGINT]}
    try:
     for sig in [signal.SIGTERM,signal.SIGKILL]:
      for pid,old in owned.items():
       try:
        now=identity(pid)
        if now['start_ticks']==old['start_ticks'] and now['pgid']==old['pgid'] and now['argv_sha256']==old['argv_sha256']:os.kill(pid,sig)
       except (OSError,ProcessLookupError):pass
      try:p.wait(timeout=2)
      except subprocess.TimeoutExpired:pass
      time.sleep(.1)
    finally:
     for s,h in saved.items():signal.signal(s,h)
   code=p.wait()
 # As subreaper, wait for already-dead adopted owned children; no unrelated signals.
 reaped=[]
 for pid in owned:
  try:
   got,status=os.waitpid(pid,os.WNOHANG)
   if got:reaped.append(got)
  except ChildProcessError:pass
 remaining=[]
 for pid,old in owned.items():
  try:
   now=identity(pid)
   if now['start_ticks']==old['start_ticks']:remaining.append(now)
  except (OSError,ProcessLookupError):pass
 terminal=dict(returncode=code,timed_out=timed,interrupted=None if interrupted is None else str(interrupted),host_process_wall_s=time.monotonic()-started,owned_descendants_reaped=reaped,owned_remaining=remaining)
 write(folder/'terminal.json',terminal);require(not remaining,'owned process remains')
 if interrupted is not None:raise interrupted
 return terminal
def main():
 require(Path('/.dockerenv').exists(),'server Docker only');require(ctypes.CDLL(None).prctl(36,1,0,0,0)==0,'subreaper initialization')
 for s in [signal.SIGTERM,signal.SIGINT]:signal.signal(s,on_signal)
 ready=load(R/'GPU_READY.json');verify_ready(ready,R/'cpu-freeze.json',Path(__file__))
 F=load(R/'cpu-freeze.json');auth_r16.verify(H,F);M=load(H/'private_r11/manifest.json');app=H/'private_r11/unseen_r11.py'
 require(not (R/'execution-start.json').exists(),'one-shot already started')
 exclusive_write(R/'execution-start.json',dict(**identity(os.getpid()),cpu_freeze_sha256=sha(R/'cpu-freeze.json'),gpu_ready_sha256=sha(R/'GPU_READY.json'),started_unix=time.time()))
 env=dict(os.environ)
 for k in list(env):
  if k=='PYTHONPATH' or k=='FLAGTREE_BACKEND' or k.startswith(('FLAGPRISM_','PROTON_','TRITON_PROTON_')):env.pop(k)
 env['PYTHONDONTWRITEBYTECODE']='1'
 original=load('/workspace/chijin-r11-independent-qualification/unseen/eligibility.json')
 results=R/'matrix';rows=[];profiles=[]
 for spec in M['cases']:
  for si in [0,1]:
   for ci in [0,1]:
    key=f"{spec['case']}-s{si}-c{ci}";folder=results/'baseline'/key
    env['TRITON_CACHE_DIR']=str(folder/'cache')
    argv=[sys.executable,'-B','-I',str(app),'--backend','nvidia','--device','cuda:0','--case',spec['case'],'--shape-index',str(si),'--config-index',str(ci),'--receipt',str(folder/'receipt.json'),'--startup-ledger',str(folder/'startup-ledger.jsonl')]
    t=run(argv,folder,env,300);require(t['returncode']==0 and not t['timed_out'],'ordinary process failed');a=load(folder/'receipt.json')
    old=next(x['receipt'] for x in original['results'] if all(x[k]==a[k] for k in ['case','shape_index','config_index']))
    gate.validate_receipts(M,old,a,[loadline(x) for x in (folder/'startup-ledger.jsonl').read_text().splitlines()],t)
    require(Path(a['triton_path']).resolve().is_relative_to(Path(F['venv']).resolve()),'ordinary import escaped venv')
    a['cold_timeout_s']=min(300,max(120,3*a['calls'][0]['compile_launch_sync_wall_s']))
    row=dict(case=spec['case'],shape_index=si,config_index=ci,category=spec['category'],status='pass',receipt=a,receipt_sha256=sha(folder/'receipt.json'),terminal=t)
    rows.append(row);write(results/'baseline-progress.json',dict(status='running',results=rows))
 eligibility=dict(status='pass',results=rows,source_sha256=M['source_sha256'],profiler_invoked=False,expected=24,resolved=len(rows))
 write(results/'eligibility.json',eligibility);write(results/'eligibility-seal.json',dict(sha256=sha(results/'eligibility.json'),manifest_sha256=sha(H/'private_r11/manifest.json')))
 for row in rows:
  spec=next(s for s in M['cases'] if s['case']==row['case']);key=f"{row['case']}-s{row['shape_index']}-c{row['config_index']}"
  env['TRITON_CACHE_DIR']=str(results/'profile-cache'/key)
  for rep in ['cold','warm']:
   folder=results/'profile'/key/rep
   argv=[sys.executable,'-B','-I','-m','flagtree.profiler.cli','--detail','auto','--device','0','-n',str(folder/'bundle'),str(app),'--backend','nvidia','--device','cuda:0','--case',row['case'],'--shape-index',str(row['shape_index']),'--config-index',str(row['config_index']),'--receipt',str(folder/'receipt.json'),'--startup-ledger',str(folder/'startup-ledger.jsonl')]
   t=run(argv,folder,env,240+row['receipt']['cold_timeout_s'])
   require(t['returncode']==0 and not t['timed_out'],'public CLI process failed')
   q=gate.verify(folder/'bundle',folder/'receipt.json',results/'eligibility.json',H/'private_r11/manifest.json',R/'cpu-freeze.json',folder/'terminal.json',folder/'startup-ledger.jsonl',folder/'derived-gate')
   write(folder/'qualification.json',q);profiles.append(dict(case=row['case'],shape_index=row['shape_index'],config_index=row['config_index'],repetition=rep,status=q['status'],verification=q,terminal=t));write(results/'profile-progress.json',dict(results=profiles))
   require(q['status']=='pass','complete original raw gate failed; finite profile phase stopped')
 write(R/'terminal.json',dict(status='pass',ordinary=len(rows),profiles=len(profiles),ended_unix=time.time(),owned_remaining=[]))
def loadline(x):return json.loads(x)
if __name__=='__main__':
 try:main()
 except Exception as error:
  write(R/'terminal.json',dict(status='fail',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),ended_unix=time.time()))
  raise
