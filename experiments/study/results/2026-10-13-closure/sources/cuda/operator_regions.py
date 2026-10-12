#!/usr/bin/env python3
"""Actual operator region probes. Generic nested capture vs backend clock contract.
Separate replay modes preserve logical program IDs; they are not the same launch.
"""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--backend',choices=['cuda','enflame','cann'],required=True);p.add_argument('--operator',choices=['gemm_bias_gelu','softmax'],required=True);p.add_argument('--shape',required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--capture',choices=['none','nested','body','output'],default='nested');p.add_argument('--device',type=int,default=0);p.add_argument('--tile',type=int,default=16);p.add_argument('--rows',type=int,default=1);p.add_argument('--samples',type=int,default=15);p.add_argument('--end-barrier',type=int,choices=[0,1],default=1);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'schema_version':1,'request_id':'logical-region-intervals-v1','backend':a.backend,'operator':a.operator,'shape':list(map(int,a.shape.split('x'))),'capture':a.capture,'tile':a.tile,'rows':a.rows,'end_barrier':a.end_barrier,'status':'started','samples':[],'input_hashes':[],'limits':['Instrumented actor-local brackets; not unperturbed busy time.','Separate captures are different physical invocations.','No counter-to-ns conversion assumed except CUDA globaltimer native ns.']}
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
 def matmul_regions(A,B,Bias,C,T,M:tl.constexpr,N:tl.constexpr,K:tl.constexpr,BM:tl.constexpr,BN:tl.constexpr,BK:tl.constexpr,MODE:tl.constexpr,BACKEND:tl.constexpr,END_BARRIER:tl.constexpr):
  p0=tl.program_id(0);p1=tl.program_id(1);record=(p0*tl.cdiv(N,BN)+p1)*8
  if MODE=='nested' or MODE=='body':s0=clock(BACKEND,False)
  else:s0=tl.full((),0,tl.int32)
  m=p0*BM+tl.arange(0,BM);n=p1*BN+tl.arange(0,BN);k=tl.arange(0,BK);acc=tl.full((BM,BN),0,tl.float32)
  for base in range(tl.cdiv(K,BK)):
   kk=base*BK+k
   av=tl.load(A+m[:,None]*K+kk[None,:],(m[:,None]<M)&(kk[None,:]<K),0)
   bv=tl.load(B+kk[:,None]*N+n[None,:],(kk[:,None]<K)&(n[None,:]<N),0)
   acc+=tl.dot(av,bv)
  if MODE=='nested' or MODE=='output':s1=clock(BACKEND,False)
  else:s1=tl.full((),0,tl.int32)
  bias=tl.load(Bias+n,n<N,0);z=acc+bias[None,:];u=.7978845608028654*(z+.044715*z*z*z);acc=.5*z*(1+(2/(1+tl.exp(-2*u))-1))
  tl.store(C+m[:,None]*N+n[None,:],acc,(m[:,None]<M)&(n[None,:]<N))
  if END_BARRIER:tl.debug_barrier()
  if MODE=='nested' or MODE=='output':e1=clock(BACKEND,True)
  else:e1=tl.full((),0,tl.int32)
  if MODE=='nested' or MODE=='body':e0=clock(BACKEND,True)
  else:e0=tl.full((),0,tl.int32)
  if MODE!='none':
   tl.store(T+record,s0);tl.store(T+record+1,e0);tl.store(T+record+2,s1);tl.store(T+record+3,e1);tl.store(T+record+4,p0.to(tl.int32));tl.store(T+record+5,p1.to(tl.int32));tl.store(T+record+6,1);tl.store(T+record+7,0)
 @triton.jit
 def softmax_regions(X,Y,T,R:tl.constexpr,N:tl.constexpr,BLOCK:tl.constexpr,ROWS:tl.constexpr,MODE:tl.constexpr,BACKEND:tl.constexpr,END_BARRIER:tl.constexpr):
  pid=tl.program_id(0);record=pid*8
  if MODE=='nested' or MODE=='body':s0=clock(BACKEND,False)
  else:s0=tl.full((),0,tl.int32)
  row=pid*ROWS+tl.arange(0,ROWS);col=tl.arange(0,BLOCK);valid=(row[:,None]<R)&(col[None,:]<N)
  x=tl.load(X+row[:,None]*N+col[None,:],valid,float('-inf'));e=tl.exp(x-tl.max(x,1)[:,None]);denom=tl.sum(e,1)
  if MODE=='nested' or MODE=='output':s1=clock(BACKEND,False)
  else:s1=tl.full((),0,tl.int32)
  y=e/denom[:,None];tl.store(Y+row[:,None]*N+col[None,:],y,valid)
  if END_BARRIER:tl.debug_barrier()
  if MODE=='nested' or MODE=='output':e1=clock(BACKEND,True)
  else:e1=tl.full((),0,tl.int32)
  if MODE=='nested' or MODE=='body':e0=clock(BACKEND,True)
  else:e0=tl.full((),0,tl.int32)
  if MODE!='none':
   tl.store(T+record,s0);tl.store(T+record+1,e0);tl.store(T+record+2,s1);tl.store(T+record+3,e1);tl.store(T+record+4,pid.to(tl.int32));tl.store(T+record+5,0);tl.store(T+record+6,1);tl.store(T+record+7,0)
 iface.set_device(a.device);device=f'{kind}:{a.device}'
 def inp(family,i,shape,dtype):
  raw=(a.input_dir/f'{family}-{a.shape}-{i}.bin').read_bytes();r['input_hashes'].append(hashlib.sha256(raw).hexdigest());return torch.frombuffer(bytearray(raw),dtype=dtype).reshape(shape).clone()
 if a.operator=='gemm_bias_gelu':
  M,N,K=r['shape'];ca=inp('matmul',0,(M,K),torch.float16);cb=inp('matmul',1,(K,N),torch.float16);bias=inp('matmul',2,(N,),torch.float32);ref=torch.nn.functional.gelu(ca.float()@cb.float()+bias,approximate='tanh');A,B,Bias=ca.to(device),cb.to(device),bias.to(device);grid=(triton.cdiv(M,a.tile),triton.cdiv(N,a.tile));count=grid[0]*grid[1]
 else:
  R,N=r['shape'];cx=inp('rows',0,(R,N),torch.float32);ref=torch.softmax(cx,-1);X=cx.to(device);grid=(triton.cdiv(R,a.rows),);count=grid[0]
 Y=torch.empty(ref.shape,dtype=torch.float32,device=device);T=torch.full((count,8),-1,dtype=torch.int32,device='cpu').to(device)
 kwargs={'num_warps':4,'num_stages':1}
 if a.backend=='cann':kwargs['debug']=True;os.environ['TRITON_KERNEL_DUMP']='1';os.environ['TRITON_DUMP_DIR']=str((a.output/'compiler_dump').resolve())
 def launch():
  if a.operator=='gemm_bias_gelu':return matmul_regions[grid](A,B,Bias,Y,T,M,N,K,a.tile,a.tile,16,a.capture,a.backend,bool(a.end_barrier),**kwargs)
  return softmax_regions[grid](X,Y,T,R,N,triton.next_power_of_2(N),a.rows,a.capture,a.backend,bool(a.end_barrier),**kwargs)
 compiled=launch();iface.synchronize();tol={'atol':.002,'rtol':.02} if a.operator=='gemm_bias_gelu' else {'atol':.0005,'rtol':.002};actual=Y.cpu();r['correct']=bool(torch.allclose(actual,ref,**tol));r['max_abs_error']=(actual-ref).abs().max().item();r['grid']=grid;r['programs']=count;r['metadata']=repr(compiled.metadata);r['runtime']={'torch':torch.__version__,'triton':triton.__version__,'torch_file':torch.__file__,'triton_file':triton.__file__};r['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();r['asm']={};adir=a.output/'asm';adir.mkdir()
 for k,v in compiled.asm.items():
  if isinstance(v,(str,bytes)):
   raw=v.encode() if isinstance(v,str) else v;(adir/k).write_bytes(raw);r['asm'][k]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 if not r['correct']:raise RuntimeError('CPU output mismatch')
 for _ in range(10):launch()
 iface.synchronize()
 from flagtree import profiler
 if a.backend=='cann':os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
 mode=f'runtime_base:runtime_host_timing_fallback=false:device_id={a.device}'+(':vendor_metrics=launch_stats' if a.backend=='cuda' else '')
 sid=profiler.start(str(a.output/'profile'),backend=a.backend,hook='triton',mode=mode)
 try:
  for i in range(a.samples):
   launch();iface.synchronize();values=T.cpu().tolist()
   if a.capture!='none':
    for j,v in enumerate(values):
     expected=[j//grid[1],j%grid[1]] if len(grid)==2 else [j,0]
     if v[4:6]!=expected or v[6]!=1:raise RuntimeError(f'Missing/incorrect program record {j}: {v}')
   r['samples'].append({'invocation_id':i,'program_records':values})
 finally:profiler.finalize(sid)
 actual=Y.cpu();r['post_profile_correct']=bool(torch.allclose(actual,ref,**tol));assert r['post_profile_correct']
 r['status']='passed';r['unit']='globaltimer_ns' if a.backend=='cuda' else ('SYS_CNT_ticks' if a.backend=='cann' else 'SDK_counter_units_unverified');r['clock_record_width_bits']=32;r['interval_decode']='unsigned modular subtraction modulo 2^32, not subtraction of signed tensor values';r['identity']='Triton program coordinates stored in dedicated per-program slots, linked to the locally enumerated serial launch; not inferred by kernel name'
except Exception as e:r['status']='failed';r['error']=repr(e);r['traceback']=traceback.format_exc();traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['samples','traceback','asm','metadata']}));raise SystemExit(0 if r['status']=='passed' else 1)
