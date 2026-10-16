"""Bounded CPU controls tests, intended identically under normal Python and -O."""
import copy,ctypes,json,os,signal,sys,tempfile,threading
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path[:0]=[str(R),str(R/'usability_qualification')]
import auth_r16 as auth
import finite_controller as c
import check_unseen_metadata_r11 as gate
def require(v,m):
 if not v:raise RuntimeError(m)
def rejected(label,fn):
 try:fn()
 except Exception as e:return dict(mutation=label,rejected=True,error_type=type(e).__name__,reason=str(e))
 raise RuntimeError('accepted mutation '+label)
mode='optimized' if sys.flags.optimize else 'normal';F=c.load(R/'cpu-freeze.json');auth.verify(None,F);neg=[]
for key in ['python','venv','wheel_sha256','unseen_manifest_sha256','device','product_revision','backend']:
 bad=copy.deepcopy(F);bad[key]='invalid';neg.append(rejected('caller_'+key,lambda:auth.verify(None,bad)))
with tempfile.TemporaryDirectory(prefix='auth-cpu-fixture-') as tmp:
 d=Path(tmp);fixture=d/'fixture';fixture.write_text('frozen bytes');oldroot=auth.ROOT;auth.ROOT=d
 minimal=dict(python=sys.executable,venv=sys.prefix,backend='nvidia',device=0,immutable_files={str(fixture):c.sha(fixture)})
 c.write(d/'cpu-freeze.json',minimal);auth.verify(None,minimal)
 for key in ['python','venv','backend','device']:
  bad=copy.deepcopy(minimal);bad[key]='invalid';c.write(d/'cpu-freeze.json',bad)
  neg.append(rejected('policy_'+key,lambda:auth.verify(None,bad)))
 c.write(d/'cpu-freeze.json',minimal);fixture.write_text('changed bytes');neg.append(rejected('actual_frozen_file_bytes',lambda:auth.verify(None,minimal)));auth.ROOT=oldroot
ready=dict(backend='nvidia',device=0,authorized=True,owner='qualification_r16_nvidia',container='chijin-study-pro6000',cpu_freeze_sha256=c.sha(R/'cpu-freeze.json'),controller_sha256=c.sha(R/'finite_controller.py'))
c.verify_ready(ready,R/'cpu-freeze.json',R/'finite_controller.py')
for key in ready:
 bad=copy.deepcopy(ready);bad[key]='invalid';neg.append(rejected('gpu_ready_'+key,lambda:c.verify_ready(bad,R/'cpu-freeze.json',R/'finite_controller.py')))
with tempfile.TemporaryDirectory(prefix='exclusive-cpu-test-') as tmp:
 p=Path(tmp)/'start';c.exclusive_write(p,{});neg.append(rejected('one_shot_exclusive',lambda:c.exclusive_write(p,{})))
O=Path('/workspace/chijin-r11-independent-qualification');E=c.load(O/'unseen/eligibility.json');M=c.load(R/'usability_qualification/private_r11/manifest.json');p=next(p for p in (O/'unseen/profile').glob('*/*/receipt.json') if len(c.load(p)['calls'])==2);a=c.load(p);b=next(x['receipt'] for x in E['results'] if all(x[k]==a[k] for k in ['case','shape_index','config_index']));l=[json.loads(s) for s in p.with_name('startup-ledger.jsonl').read_text().splitlines()];t=c.load(p.with_name('terminal.json'));gate.validate_receipts(M,b,a,l,t)
for mutation in ['state','canary','tolerance','witness','runtime','ledger','terminal','seed']:
 aa,bb,ll,tt=copy.deepcopy((a,b,l,t))
 if mutation=='state':aa['calls'][0]['program_state_counts'][0]+=1
 if mutation=='canary':aa['calls'][0]['canaries']=False
 if mutation=='tolerance':aa['calls'][0]['atol']*=10
 if mutation=='witness':aa['calls'][0]['non_idempotence_witness_max_abs']=0
 if mutation=='runtime':aa['calls'][0]['runtime_input_sha256']='0'*64
 if mutation=='ledger':ll.append(ll[0])
 if mutation=='terminal':tt['returncode']=1
 if mutation=='seed':aa['output_initial_sha256']='0'*64
 neg.append(rejected(mutation,lambda:gate.validate_receipts(M,bb,aa,ll,tt)))
require(ctypes.CDLL(None).prctl(36,1,0,0,0)==0,'subreaper')
for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,c.on_signal)
cleanup=[]
for kind in ['timeout','SIGTERM','SIGINT']:
 folder=R/('cpu-control-final-'+mode+'-'+kind)
 argv=[sys.executable,'-B','-I','-c','import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-B","-I","-c","import time; time.sleep(30)"]); time.sleep(30)']
 timer=None
 if kind!='timeout':timer=threading.Timer(.5,lambda:os.kill(os.getpid(),getattr(signal,kind)));timer.start()
 continued=False
 try:
  result=c.run(argv,folder,dict(os.environ),.5 if kind=='timeout' else 5)
  continued=True
 except c.Terminated:result=c.load(folder/'terminal.json')
 require(kind=='timeout' or not continued,'signal cancellation continued to subsequent call')
 if timer:timer.join()
 require(not result['owned_remaining'] and result['returncode']!=0,'CPU owned cleanup failed')
 cleanup.append(dict(kind=kind,next_call_reached=continued,**result))
c.write(R/('SAFE_CONTROLS_'+mode+'.json'),dict(status='pass',mode=mode,authorization_version=auth.VERSION,negative_count=len(neg),all_rejected=True,negatives=neg,owned_sleep_subprocess_cleanup=cleanup,device_initialization=False,kernel_launch=False))
print(mode+': '+str(len(neg))+' negatives rejected; timeout/SIGTERM/SIGINT owned-child cleanup/reap and cancellation propagation passed; no device work')
