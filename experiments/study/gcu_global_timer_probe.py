#!/usr/bin/env python3
"""Use the installed SDK read-only global_timer through an external device call."""
import argparse,hashlib,json,os,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--shim',type=Path);p.add_argument('--adapt',action='store_true');p.add_argument('--compile-only',action='store_true');p.add_argument('--library',default='/opt/tops/lib/krt/gcu300_api_profile.bc');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'status':'started','device':1,'library':a.library,'library_sha256':hashlib.sha256(Path(a.library).read_bytes()).hexdigest(),'semantics':'SDK tops::global_timer only; no direct MMIO access or counter reset/configuration'}
try:
 import torch,torch_gcu,triton
 import triton.language as tl
 from triton.language import core
 if a.adapt:
  from gcu_global_timer_adapter import install
  install(a.output/'adapter',a.shim);os.environ['TRITON_CACHE_DIR']=str(a.output/'cache')
 @core.extern
 def timer(_semantic=None):
  return core.extern_elementwise('', '', [], {(): ('_ZN4tops12global_timerEv',core.dtype('int64'))},is_pure=False,_semantic=_semantic)
 @triton.jit
 def probe(X,Y,T,N:tl.constexpr,ADAPT:tl.constexpr):
  pid=tl.program_id(0);c=tl.arange(0,N)
  b0=tl.extra.gcu.libdevice.begin_clock() if ADAPT else timer();x=tl.load(X+pid*N+c);e=tl.exp(x-tl.max(x,0));d=tl.sum(e,0);o0=tl.extra.gcu.libdevice.begin_clock() if ADAPT else timer();y=e/d
  tl.store(Y+pid*N+c,y);tl.debug_barrier();o1=tl.extra.gcu.libdevice.end_clock() if ADAPT else timer();b1=tl.extra.gcu.libdevice.end_clock() if ADAPT else timer()
  tl.store(T+pid*8+0,b0.to(tl.int32));tl.store(T+pid*8+1,b1.to(tl.int32));tl.store(T+pid*8+2,o0.to(tl.int32));tl.store(T+pid*8+3,o1.to(tl.int32));tl.store(T+pid*8+4,pid);tl.store(T+pid*8+5,0);tl.store(T+pid*8+6,1);tl.store(T+pid*8+7,0)
 torch.gcu.set_device(1);X=torch.zeros((32,256),device='gcu:1');Y=torch.empty_like(X);T=torch.zeros((32,8),dtype=torch.int32,device='gcu:1')
 k=probe.warmup(X,Y,T,256,a.adapt,grid=(32,),num_warps=4,num_stages=1,extern_libs={} if a.adapt else {'study_global_timer':a.library});r['metadata']=repr(k.metadata)
 for key,value in k.asm.items():
  if isinstance(value,str):(a.output/(key+'.txt')).write_text(value)
  elif isinstance(value,bytes):(a.output/(key+'.bin')).write_bytes(value)
 if not a.compile_only:
  r['samples']=[]
  for i in range(5):
   probe[(32,)](X,Y,T,256,a.adapt,num_warps=4,num_stages=1,extern_libs={} if a.adapt else {'study_global_timer':a.library});torch.gcu.synchronize();assert torch.allclose(Y.cpu(),torch.full((32,256),1/256));v=T.cpu().tolist();assert all(x[4]==j and x[6]==1 for j,x in enumerate(v));r['samples'].append(v)
 r['status']='passed'
except Exception as e:r.update(status='failed',error=repr(e),traceback=traceback.format_exc());traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['samples','metadata','traceback']}));raise SystemExit(r['status']!='passed')
