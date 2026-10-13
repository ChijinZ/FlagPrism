#!/usr/bin/env python3
"""Uninstrumented paired kernel/task timing with serial, randomized invocations."""
import argparse,os,json,time,hashlib,random,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--shape',default='512x512x4096');p.add_argument('--input-dir',type=Path);p.add_argument('--configs',type=Path);p.add_argument('--prediction',default='Compiler-aware granularity intervention; compare original frozen-port config with explicitly controlled target changes.');p.add_argument('--operator',choices=['gemm','gemm_bias_gelu'],default='gemm');p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=30);p.add_argument('--batches',type=int,default=3);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'status':'started','scope':'exploratory, N/P freeze pending','shape':[int(x) for x in a.shape.split('x')],'operator':a.operator,'device':4,'samples_per_config_per_batch':a.samples,'batches':a.batches,'raw_invocations':[],'prediction':a.prediction,'source_hashes':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['compare_native.py','diagnosis_kernels.py']}}
try:
 import torch,torch_npu,triton,kernels,diagnosis_kernels
 from flagtree import profiler
 torch.set_num_threads(8);torch.npu.set_device(4);torch.manual_seed(1729);M,N,K=r['shape']
 if a.input_dir:
  def canonical(index,shape,dtype):return torch.frombuffer(bytearray((a.input_dir/f'matmul-{a.shape}-{index}.bin').read_bytes()),dtype=dtype).reshape(shape).clone()
  aa=canonical(0,(M,K),torch.float16);bb=canonical(1,(K,N),torch.float16);bias=canonical(2,(N,),torch.float32)
 else:aa=torch.randn((M,K),dtype=torch.float16)*.1;bb=torch.randn((K,N),dtype=torch.float16)*.1;bias=torch.randn((N,),dtype=torch.float32)*.1
 r['input_hashes']={name:hashlib.sha256(x.numpy().tobytes()).hexdigest() for name,x in [('A',aa),('B',bb),('bias',bias)]}
 reference=aa.float()@bb.float();reference=torch.nn.functional.gelu(reference+bias,approximate='tanh') if a.operator=='gemm_bias_gelu' else reference
 A,B,Bias=aa.to('npu:4'),bb.to('npu:4'),bias.to('npu:4');C=torch.empty((M,N),device='npu:4');compiled={};configs={};r['compile_artifacts']={}
 requested=json.load(open(a.configs)) if a.configs else [{'name':f'b64-k{bk}-s{stages}','BM':64,'BN':64,'BK':bk,'num_stages':stages,'num_warps':4,'kernel':'original'} for bk in [64,128] for stages in [1,2]]
 r['configs']=requested
 for cfg in requested:
  bm,bn,bk=cfg['BM'],cfg['BN'],cfg['BK'];key=cfg['name'];grid=(triton.cdiv(M,bm),triton.cdiv(N,bn),1);args=(A,B,Bias,C,M,N,K,bm,bn,bk,a.operator=='gemm_bias_gelu');kwargs={'num_stages':cfg['num_stages'],'num_warps':cfg.get('num_warps',4)}
  fn=kernels.matmul if cfg.get('kernel','original')=='original' else diagnosis_kernels.matmul_unrolled
  if cfg.get('kernel')=='unroll':args=args+(cfg['UNROLL'],)
  kwargs.update(cfg.get('backend_options',{}))
  c=fn[grid](*args,**kwargs);torch.npu.synchronize();out=C.cpu();assert torch.allclose(out,reference,atol=.002,rtol=.02),float((out-reference).abs().max())
  d=a.output/'asm'/key;d.mkdir(parents=True);r['compile_artifacts'][key]={'validation_max_abs_error':float((out-reference).abs().max()),'metadata':repr(c.metadata),'hashes':{}}
  for stage,data in c.asm.items():
   if isinstance(data,str):data=data.encode()
   if isinstance(data,bytes):(d/str(stage)).write_bytes(data);r['compile_artifacts'][key]['hashes'][str(stage)]=hashlib.sha256(data).hexdigest()
  configs[key]=(fn,grid,args,kwargs);compiled[key]=c
  for i in range(10):fn[grid](*args,**kwargs)
 torch.npu.synchronize();os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
 sid=profiler.start(str(a.output/'profile'),backend='cann',hook='triton',mode='runtime_base:device_id=4:runtime_host_timing_fallback=false')
 for batch in range(a.batches):
  order=list(configs)*a.samples;random.Random(914+batch).shuffle(order)
  for index,key in enumerate(order):
   fn,grid,args,kwargs=configs[key];torch.npu.synchronize();begin=time.perf_counter_ns();fn[grid](*args,**kwargs);torch.npu.synchronize();end=time.perf_counter_ns();out=C.cpu();assert torch.allclose(out,reference,atol=.002,rtol=.02)
   r['raw_invocations'].append({'invocation':len(r['raw_invocations']),'batch':batch,'index':index,'config':key,'host_sync_ns':end-begin,'max_abs_error':float((out-reference).abs().max())})
 profiler.finalize(sid);r['status']='passed'
except Exception as e:r.update(status='failed',error=repr(e),traceback=traceback.format_exc());traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['raw_invocations','traceback','compile_artifacts']}));raise SystemExit(r['status']!='passed')
