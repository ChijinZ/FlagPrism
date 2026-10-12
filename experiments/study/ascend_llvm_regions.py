#!/usr/bin/env python3
"""Launch original-ABI late-LLVM probes; retain actor-local native tick intervals."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=32);p.add_argument('--operator',choices=['gemm_bias_gelu','softmax'],default='gemm_bias_gelu');p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--completion',action='store_true');p.add_argument('--native-profile',action='store_true');p.add_argument('--samples',type=int,default=15);p.add_argument('--instrumented',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'status':'started','operator':a.operator,'shape':[a.n,a.n,a.n] if a.operator=='gemm_bias_gelu' else [32,256],'device':4,'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest(),'completion_fences':a.completion,'instrumented':a.instrumented,'counter_unit':'SYS_CNT native ticks','global_body':None,'samples':[]}
try:
 import torch,torch_npu,triton,kernels
 torch.npu.set_device(4);device='npu:4'
 def inp(i,shape,dtype):
  path=a.input_dir/f'matmul-{a.n}x{a.n}x{a.n}-{i}.bin';r.setdefault('input_sha256',{})[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();return torch.frombuffer(bytearray(path.read_bytes()),dtype=dtype).reshape(shape).clone()
 if a.operator=='gemm_bias_gelu':
  n=a.n;blocks=(n//16)**2
  ca,cb,bias=inp(0,(n,n),torch.float16),inp(1,(n,n),torch.float16),inp(2,(n,),torch.float32)
  ref=torch.nn.functional.gelu(ca.float()@cb.float()+bias,approximate='tanh')
  A,B=ca.to(device),cb.to(device);Bias=torch.cat([bias,torch.zeros((blocks*3*32,),dtype=torch.float32)]).to(device);C=torch.empty((n,n),device=device)
  compiled=kernels.matmul.warmup(A,B,Bias,C,n,n,n,16,16,16,True,grid=(n//16,n//16),num_stages=1,num_warps=4)
  grid=(n//16,n//16,1);launchargs=(A,B,Bias,C,n,n,n,16,16,16,True);tail=Bias[n:];records=blocks*3
 else:
  path=a.input_dir/'rows-32x256-0.bin';r['input_sha256']={path.name:hashlib.sha256(path.read_bytes()).hexdigest()}
  cx=torch.frombuffer(bytearray(path.read_bytes()),dtype=torch.float32).reshape(32,256).clone();ref=torch.softmax(cx,-1)
  X=cx.to(device);Y=torch.empty((8192+1024,),device=device);V=torch.empty((256,),device=device);C=Y[:8192].reshape(32,256);tail=Y[8192:];records=32
  compiled=kernels.rows.warmup(X,V,V,Y,32,256,256,1,'softmax',grid=(32,),num_stages=1,num_warps=4)
  grid=(32,1,1);launchargs=(X,V,V,Y,32,256,256,1,'softmax')
 compiled.kernel=a.binary.read_bytes();compiled.asm['npubin']=compiled.kernel
 sid=None
 if a.native_profile:
  from flagtree import profiler
  os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
  sid=profiler.start(str(a.output/'profile'),backend='cann',hook='triton',mode='runtime_base:device_id=4:runtime_host_timing_fallback=false')
 for i in range(a.samples+3):
  tail.zero_();torch.npu.synchronize();start=time.perf_counter_ns();compiled[grid](*launchargs);torch.npu.synchronize();elapsed=time.perf_counter_ns()-start
  out=C.cpu();assert torch.allclose(out,ref,atol=.002,rtol=.02),float((out-ref).abs().max())
  rec={'invocation':i,'host_synchronized_ns':elapsed,'max_abs_error':float((out-ref).abs().max())}
  if a.instrumented:
   vals=tail.cpu().view(torch.int64).reshape(-1,16).tolist();rec['actors']=[]
   for slot,v in enumerate(vals[:records]):
    if not v[4]:continue
    assert (v[0]==slot if a.operator=='softmax' else v[0]==slot//3 and (v[1] if v[2] else 0)==(slot%3-1 if slot%3 else 0)),(slot,v)
    actor={'program_id':v[0],'subblock_id':v[1],'actor':'AIV' if v[2] else 'AIC','raw_record':v,'body':[v[3],v[4]]}
    if a.operator=='softmax':actor.update(output=[v[7],v[4]],input_transfer=[v[5],v[6]],normalization_compute=[v[7],v[8]],output_store=[v[8],v[4]])
    elif v[2]:actor.update(output=[v[5],v[4]],readiness_wait=[v[5],v[6]],workspace_transfer=[v[6],v[7]],epilogue_with_bias_load=[v[7],v[8]],output_store=[v[8],v[4]])
    else:actor.update(producer_signal=[v[5],v[6]])
    rec['actors'].append(actor)
   assert len(rec['actors'])==records,len(rec['actors'])
  if i>=3:r['samples'].append(rec)
 if sid is not None:profiler.finalize(sid)
 r['status']='passed';r['semantics']=('AIC/AIV actor-local projections. AIV output begins before original readiness wait and includes workspace+bias input, GELU and output store through original PIPE_ALL barrier; added PIPE_MTE2 barrier splits workspace transfer.' if a.operator=='gemm_bias_gelu' else 'AIV body includes input load, reductions, exp, divide and output store through original PIPE_ALL barrier; output begins after denominator scalar load before final divide. Original flags delimit completed input transfer and vector compute.')+' Probes perturb timing; no cross-actor subtraction or engine busy time.'
 if a.completion:r['semantics']+=' Additional PIPE_ALL fences before transfer and compute end clocks enforce completion of outstanding engine work, with synchronization perturbation included.'
 if not a.instrumented:r['semantics']='Unmodified source recompile control; no internal counter records. CPU correctness and optional native aclprof whole-task timing are retained.'
except Exception as e:r.update(status='failed',error=repr(e),traceback=traceback.format_exc());traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['samples','traceback']}));raise SystemExit(r['status']!='passed')
