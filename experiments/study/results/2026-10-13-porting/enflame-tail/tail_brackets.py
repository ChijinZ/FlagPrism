"""GCU real softmax max/sum actor-local issue/dependency brackets, no added sync."""
import argparse,os,json,hashlib,traceback
from pathlib import Path
os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD']='0'
p=argparse.ArgumentParser();p.add_argument('--warps',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=15);p.add_argument('--shape',default='127x769');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
os.environ['TRITON_CACHE_DIR']=str(a.output/'cache')
from gcu_global_timer_adapter import install
install(a.output/'adapter',Path('/workspace/flagprism-study-closure-20261013/sdk-clock/global-timer-shim.ll'),True)
import torch,torch_gcu,triton
import triton.language as tl
from triton.language.extra.gcu import libdevice as gd
from flagtree import profiler
@triton.jit
def softmax_reduce_trace(X,Y,T,R:tl.constexpr,N:tl.constexpr,BLOCK:tl.constexpr):
 pid=tl.program_id(0);row=pid+tl.arange(0,1);c=tl.arange(0,BLOCK);valid=(row[:,None]<R)&(c[None,:]<N);x=tl.load(X+row[:,None]*N+c[None,:],valid,float('-inf'))
 s0=tl.full((),0,tl.int32)
 if pid==0:s0=gd.begin_clock().to(tl.int32)
 mx=tl.max(x,1)
 e0=tl.full((),0,tl.int32)
 if pid==0:e0=gd.end_clock().to(tl.int32)
 e=tl.exp(x-mx[:,None])
 s1=tl.full((),0,tl.int32)
 if pid==0:s1=gd.begin_clock().to(tl.int32)
 den=tl.sum(e,1)
 e1=tl.full((),0,tl.int32)
 if pid==0:e1=gd.end_clock().to(tl.int32)
 y=e/den[:,None]
 tl.store(Y+row[:,None]*N+c[None,:],y,valid)
 if pid==0:
  tl.store(T+pid*8,s0);tl.store(T+pid*8+1,e0);tl.store(T+pid*8+2,s1);tl.store(T+pid*8+3,e1)
  tl.store(T+pid*8+4,pid);tl.store(T+pid*8+5,0);tl.store(T+pid*8+6,1);tl.store(T+pid*8+7,0)
r={'scope':'actorlocal source reduction brackets; instructionissue/dependency sequence, not engine busy or independent physical completion','unit':'SDK_global_timer_ticks','cross_actor_alignment':'unverified','num_warps':a.warps,'grid':[int(a.shape.split('x')[0])],'rows':1,'samples':[],'status':'started','new_barriers':0}
try:
 torch.gcu.set_device(0);R,N=map(int,a.shape.split('x'));BLOCK=triton.next_power_of_2(N);raw=Path('/workspace/chijin-study-canonical-inputs-r007')/f'rows-{a.shape}-0.bin';raw=raw.read_bytes();r['input_sha256']=hashlib.sha256(raw).hexdigest();cx=torch.frombuffer(bytearray(raw),dtype=torch.float32).reshape(R,N).clone();ref=torch.softmax(cx,-1)
 X=cx.to('gcu');Y=torch.empty_like(X);T=torch.full((R,8),-1,dtype=torch.int32).to('gcu')
 def launch():return softmax_reduce_trace[(R,)](X,Y,T,R,N,BLOCK,num_warps=a.warps,num_stages=1)
 k=launch();torch.gcu.synchronize();r['correct']=bool(torch.allclose(Y.cpu(),ref,atol=.0005,rtol=.002));assert r['correct']
 r['recording_program']=0;r['reference_device']=str(ref.device);assert ref.device.type=='cpu';r['metadata']=repr(k.metadata);r['asm']={};(a.output/'asm').mkdir()
 for name,v in k.asm.items():
  if isinstance(v,(str,bytes)):
   b=v.encode() if isinstance(v,str) else v;(a.output/'asm'/name).write_bytes(b);r['asm'][name]=hashlib.sha256(b).hexdigest()
 for _ in range(5):launch()
 torch.gcu.synchronize()
 sid=profiler.start(str(a.output/'profile'),backend='enflame',hook='triton',mode='runtime_base:runtime_host_timing_fallback=false:device_id=0')
 try:
  for i in range(a.samples):
   launch();torch.gcu.synchronize();v=T.cpu().tolist()
   assert v[0][4]==0 and v[0][6]==1 and all(all(x==-1 for x in row) for row in v[1:])
   r['samples'].append({'invocation':i,'records':v})
 finally:profiler.finalize(sid)
 r['post_correct']=bool(torch.allclose(Y.cpu(),ref,atol=.0005,rtol=.002));assert r['post_correct'];r['status']='passed'
except Exception:r['status']='failed';r['error']=traceback.format_exc();traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2));print(r['status'],flush=True)
raise SystemExit(0 if r['status']=='passed' else 1)
