#!/usr/bin/env python3
"""Raw counter brackets with/without a barrier; no assumed tick conversion."""
import argparse,json,os,time,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--backend',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',type=int,default=2);p.add_argument('--loops',type=int,default=64);p.add_argument('--sync',type=int,default=0);p.add_argument('--nested',action='store_true');p.add_argument('--before',type=int,default=0);p.add_argument('--capture-region',choices=['both','outer','inner'],default='both');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'backend':a.backend,'loops':a.loops,'sync':a.sync,'nested':a.nested,'before':a.before,'capture_region':a.capture_region,'status':'started','semantics':'input-readiness barrier always present; sync changes only the end barrier; counter units retained; not engine busy time','samples':[]}
try:
 import torch
 if a.backend=='cann':import torch_npu;iface=torch.npu;kind='npu'
 elif a.backend=='enflame':import torch_gcu;iface=torch.gcu;kind='gcu'
 else:iface=torch.cuda;kind='cuda'
 import triton
 import triton.language as tl
 if a.backend=='enflame':from triton.language.extra.gcu import libdevice as gd
 else:gd=None
 @triton.jit
 def clock(BACKEND:tl.constexpr,END:tl.constexpr):
  if BACKEND=='enflame':
   if END:return gd.end_clock().to(tl.int32)
   else:return gd.begin_clock().to(tl.int32)
  elif BACKEND=='cann':return tl.inline_asm_elementwise('MOV $0, SYS_CNT',constraints='=l',args=[],dtype=tl.int64,is_pure=False,pack=1).to(tl.int32)
  else:return tl.inline_asm_elementwise('mov.u64 $0, %globaltimer;',constraints='=l',args=[],dtype=tl.int64,is_pure=False,pack=1).to(tl.int32)
 @triton.jit
 def probe(X,Y,T,N:tl.constexpr,LOOPS:tl.constexpr,SYNC:tl.constexpr,BACKEND:tl.constexpr,NESTED:tl.constexpr,BEFORE:tl.constexpr,REGION:tl.constexpr):
  c=tl.arange(0,N);x=tl.load(X+c)
  tl.debug_barrier()
  if REGION!='inner':t0=clock(BACKEND,False)
  else:t0=tl.full((),0,tl.int32)
  if NESTED:
   for i in range(BEFORE):x=x*.999+.001
   if SYNC:tl.debug_barrier()
   if REGION!='outer':t2=clock(BACKEND,False)
   else:t2=tl.full((),0,tl.int32)
   for i in range(LOOPS//2):x=x*.999+.001
   if SYNC:tl.debug_barrier()
   if REGION!='outer':t3=clock(BACKEND,True)
   else:t3=tl.full((),0,tl.int32)
   for i in range(LOOPS//2-BEFORE):x=x*.999+.001
  else:
   t2=tl.full((),0,tl.int32);t3=tl.full((),0,tl.int32)
   for i in range(LOOPS):x=x*.999+0.001
  if SYNC:tl.debug_barrier()
  if REGION!='inner':t1=clock(BACKEND,True)
  else:t1=tl.full((),0,tl.int32)
  tl.store(Y+c,x)
  tl.store(T,t0);tl.store(T+1,t1);tl.store(T+2,t2);tl.store(T+3,t3)
 iface.set_device(a.device);device=f'{kind}:{a.device}'
 x=torch.linspace(-.1,.1,128,device='cpu');ref=x.clone()
 for _ in range(a.loops):ref=ref*.999+.001
 X=x.to(device);Y=torch.empty((128,),dtype=torch.float32,device=device);T=torch.empty((4,),dtype=torch.int32,device=device)
 kwargs={'num_warps':1,'num_stages':1}
 os.environ['TRITON_KERNEL_DUMP']='1'
 os.environ['TRITON_DUMP_DIR']=str((a.output/'compiler_dump').resolve())
 if a.backend=='cann':kwargs['debug']=True
 compiled=probe[(1,)](X,Y,T,128,a.loops,bool(a.sync),a.backend,a.nested,a.before,a.capture_region,**kwargs);iface.synchronize()
 r['correct']=bool(torch.allclose(Y.cpu(),ref,atol=.0005,rtol=.002));r['max_abs_error']=(Y.cpu()-ref).abs().max().item()
 if not r['correct']:raise RuntimeError('reference mismatch')
 asm=a.output/'asm';asm.mkdir();r['metadata']=repr(compiled.metadata)
 for k,v in compiled.asm.items():
  if isinstance(v,(str,bytes)):(asm/k).write_bytes(v.encode() if isinstance(v,str) else v)
 for _ in range(5):probe[(1,)](X,Y,T,128,a.loops,bool(a.sync),a.backend,a.nested,a.before,a.capture_region,**kwargs)
 iface.synchronize()
 from flagtree import profiler
 if a.backend=='cann':os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
 mode=f'runtime_base:runtime_host_timing_fallback=false:device_id={a.device}'+(':vendor_metrics=launch_stats' if a.backend=='cuda' else '')
 sid=profiler.start(str(a.output/'profile'),backend=a.backend,hook='triton',mode=mode)
 try:
  for _ in range(15):
   probe[(1,)](X,Y,T,128,a.loops,bool(a.sync),a.backend,a.nested,a.before,a.capture_region,**kwargs);iface.synchronize();v=T.cpu().tolist();r['samples'].append({'start_low32':v[0]&0xffffffff,'end_low32':v[1]&0xffffffff,'delta_ticks_mod32':(v[1]-v[0])&0xffffffff,'inner_start_low32':v[2]&0xffffffff,'inner_end_low32':v[3]&0xffffffff,'inner_delta_ticks_mod32':(v[3]-v[2])&0xffffffff})
 finally:profiler.finalize(sid)
 r['status']='passed'
except Exception as e:r['status']='failed';r['error']=repr(e);r['traceback']=traceback.format_exc();traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['samples','traceback','metadata']}))
raise SystemExit(0 if r['status']=='passed' else 1)
