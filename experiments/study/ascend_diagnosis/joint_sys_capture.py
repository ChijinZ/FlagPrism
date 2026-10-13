#!/usr/bin/env python3
"""One sparse source-clock call for SDK application replay; no nested profiler/fences."""
import argparse,os,json,time,hashlib,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--config',choices=['P32_K32','R_K32_K256'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output/f'run-{os.getpid()}-{time.time_ns()}';out.mkdir(parents=True,exist_ok=False);bk=32 if a.config=='P32_K32' else 256
r={'status':'started','pid':os.getpid(),'config':a.config,'operator':'gemm_bias_gelu','shape':[512,512,4096],'tile':[32,32,bk],'requested_stages':4,'device':4,'matmul_calls_in_app':1,'added_barriers':0,'counter_domain':'SYS_CNT','tick_ns':20,'native_collection':'External SDK only; application replay; no FlagPrism session in this app','clock_association_target':'3 actual program0 actor source windows and raw SDK task_start/end_SYS from same single invocation','selection':'all source captures retained; unique raw-packet match required, no joining replays'}
try:
 import torch,torch_npu,triton,kernels
 torch.set_num_threads(8);torch.npu.set_device(4)
 def inp(i,shape,dtype):
  raw=(a.inputs/f'matmul-512x512x4096-{i}.bin').read_bytes();r.setdefault('input_sha256',{})[str(i)]=hashlib.sha256(raw).hexdigest();return torch.frombuffer(bytearray(raw),dtype=dtype).reshape(shape).clone()
 aa,bb,bias=inp(0,(512,4096),torch.float16),inp(1,(4096,512),torch.float16),inp(2,(512,),torch.float32);ref=torch.nn.functional.gelu(aa.float()@bb.float()+bias,approximate='tanh');A,B=aa.to('npu:4'),bb.to('npu:4');fields=48+16*(4096//bk);Bias=torch.cat([bias,torch.zeros(fields*2,dtype=torch.float32)]).to('npu:4');C=torch.empty((512,512),device='npu:4');tail=Bias[512:]
 args=(A,B,Bias,C,512,512,4096,32,32,bk,True);grid=(16,16,1);c=kernels.matmul.warmup(*args,grid=grid,num_stages=4,num_warps=4);binary=(a.workspace/f'sparse-{a.config}-compile/kernel.o').read_bytes();r['binary_sha256']=hashlib.sha256(binary).hexdigest();c.kernel=binary;c.asm['npubin']=binary
 tail.zero_();torch.npu.synchronize();c[grid](*args);torch.npu.synchronize();actual=C.cpu();assert torch.allclose(actual,ref,atol=.002,rtol=.02);values=tail.cpu().view(torch.int64).tolist();headers=[values[i*16:(i+1)*16] for i in range(3)];loops=[values[48+i*16:48+(i+1)*16] for i in range(4096//bk)]
 assert [h[0] for h in headers]==[0,0,0] and [h[1] for h in headers]==[0,0,1] and [h[2] for h in headers]==[0,1,1]
 assert all(h[4]>=h[3]>0 for h in headers) and all(row[0]==i and row[13]>=row[2]>0 for i,row in enumerate(loops))
 r.update(status='passed',actor_headers=headers,loop_records=loops,max_abs_error=float((actual-ref).abs().max()))
except Exception as e:r.update(status='failed',error=repr(e),traceback=traceback.format_exc());traceback.print_exc()
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['actor_headers','loop_records','traceback']}));raise SystemExit(r['status']!='passed')
