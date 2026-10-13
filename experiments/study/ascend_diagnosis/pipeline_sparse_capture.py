#!/usr/bin/env python3
"""Real per-iteration program0 issue records and matched uninstrumented controls."""
import argparse,os,json,hashlib,random,copy,time,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--shape',default='512x512x4096');p.add_argument('--configs',type=Path);p.add_argument('--tile-m',type=int,default=64);p.add_argument('--tile-n',type=int,default=64);p.add_argument('--bk',default='64,128,256');p.add_argument('--stages',type=int,default=2);p.add_argument('--samples',type=int,default=30);p.add_argument('--batches',type=int,default=3);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'status':'started','shape':[int(x) for x in a.shape.split('x')],'device':4,'config':{'BM':a.tile_m,'BN':a.tile_n,'stages':a.stages},'scope':'exploratory until frozenN/P; real per-iteration program0 scalar issue trace, separate PMU aggregate activities','selected_invocation_policy':'perBK instrumented invocation closest to median matched native task duration, lowestordinal on ties','batches':a.batches,'samples_per_variant_per_batch':a.samples,'raw_invocations':[],'tick_ns':20,'added_barriers':0,'clock_policy':'actor-local origins. Non-scalar wait-clock is issue observation, not engine completion or busy interval.'}
if a.configs:r['config']={'cases_from':str(a.configs)}
try:
 import torch,torch_npu,triton,kernels
 from flagtree import profiler
 torch.set_num_threads(8);torch.npu.set_device(4);M,N,K=r['shape']
 def canonical(index,shape,dtype):
  raw=(a.inputs/f'matmul-{a.shape}-{index}.bin').read_bytes();r.setdefault('input_hashes',{})[str(index)]=hashlib.sha256(raw).hexdigest();return torch.frombuffer(bytearray(raw),dtype=dtype).reshape(shape).clone()
 aa=canonical(0,(M,K),torch.float16);bb=canonical(1,(K,N),torch.float16);bias=canonical(2,(N,),torch.float32);ref=torch.nn.functional.gelu(aa.float()@bb.float()+bias,approximate='tanh');A,B=aa.to('npu:4'),bb.to('npu:4')
 choices={};r['binaries']={};r['validation']={}
 requested=json.load(open(a.configs)) if a.configs else [{'name':f'BK{bk}','BM':a.tile_m,'BN':a.tile_n,'BK':bk,'num_stages':a.stages,'binary':f'sparse-k{bk}-compile/kernel.o'} for bk in [int(x) for x in a.bk.split(',')]]
 r['configs']=requested
 for cfg in requested:
  bk,bm,bn,stages=cfg['BK'],cfg['BM'],cfg['BN'],cfg['num_stages']
  iterations=triton.cdiv(K,bk);fields=48+16*iterations;Bias=torch.cat([bias,torch.zeros(fields*2,dtype=torch.float32)]).to('npu:4');C=torch.empty((M,N),device='npu:4');grid=(triton.cdiv(M,bm),triton.cdiv(N,bn),1);args=(A,B,Bias,C,M,N,K,bm,bn,bk,True)
  template=kernels.matmul.warmup(*args,grid=grid,num_stages=stages,num_warps=4)
  for variant in ['original','instrumented']:
   c=copy.copy(template);c.asm=dict(template.asm);c.module=None;c.function=None;c._run=None
   binary=template.kernel if variant=='original' else (a.workspace/cfg['binary']).read_bytes();c.kernel=binary;c.asm['npubin']=binary
   key=cfg['name']+'-'+variant;choices[key]=(c,grid,args,Bias[N:],C,bk,fields,cfg);r['binaries'][key]={'sha256':hashlib.sha256(binary).hexdigest(),'bytes':len(binary),'metadata':repr(c.metadata)}
   Bias[N:].zero_();c[grid](*args);torch.npu.synchronize();out=C.cpu();assert torch.allclose(out,ref,atol=.002,rtol=.02);values=Bias[N:].cpu().view(torch.int64).tolist()
   assert (values[4]>0) if variant=='instrumented' else not any(values)
   r['validation'][key]={'passed':True,'max_abs_error':float((out-ref).abs().max())}
   for i in range(5):c[grid](*args)
 torch.npu.synchronize();os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1';sid=profiler.start(str(a.output/'profile'),backend='cann',hook='triton',mode='runtime_base:device_id=4:runtime_host_timing_fallback=false')
 for batch in range(a.batches):
  order=list(choices)*a.samples;random.Random(5225+batch).shuffle(order)
  for key in order:
   c,grid,args,tail,C,bk,fields,cfg=choices[key];tail.zero_();torch.npu.synchronize();begin=time.perf_counter_ns();c[grid](*args);torch.npu.synchronize();end=time.perf_counter_ns();out=C.cpu();assert torch.allclose(out,ref,atol=.002,rtol=.02)
   inv={'invocation':len(r['raw_invocations']),'batch':batch,'config':key,'BK':bk,'variant':key.rsplit('-',1)[1],'source_config':cfg,'host_sync_ns':end-begin,'max_abs_error':float((out-ref).abs().max())}
   vals=tail.cpu().view(torch.int64).tolist()
   if inv['variant']=='instrumented':
    headers=[vals[i*16:(i+1)*16] for i in range(3)];loops=[vals[48+i*16:48+(i+1)*16] for i in range(triton.cdiv(K,bk))]
    assert [h[0] for h in headers]==[0,0,0] and [h[1] for h in headers]==[0,0,1] and [h[2] for h in headers]==[0,1,1]
    assert all(h[4]>=h[3]>0 for h in headers)
    assert all(row[0]==i and row[13]>=row[2]>0 and all(row[j]<=row[j+1] for j in range(2,13)) for i,row in enumerate(loops))
    inv.update(actor_headers=headers,loop_records=loops)
   else:assert not any(vals)
   r['raw_invocations'].append(inv)
 profiler.finalize(sid);r['status']='passed'
except Exception as e:r.update(status='failed',error=repr(e),traceback=traceback.format_exc());traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['raw_invocations','traceback','binaries']}));raise SystemExit(r['status']!='passed')
