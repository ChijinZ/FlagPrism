#!/usr/bin/env python3
"""One fixed uninstrumented GEMM configuration for compiler/SDK PMU diagnosis."""
import argparse,os,json,hashlib
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path);p.add_argument('--kernel-kind',choices=['original','unroll'],default='original');p.add_argument('--unroll',type=int,default=2);p.add_argument('--operator',choices=['gemm','gemm_bias_gelu'],default='gemm_bias_gelu');p.add_argument('--shape',default='512x512x4096');p.add_argument('--bk',type=int,default=64);p.add_argument('--stages',type=int,default=2);p.add_argument('--tile-m',type=int,default=64);p.add_argument('--tile-n',type=int,default=64);p.add_argument('--cv-pipeline',action='store_true');p.add_argument('--lowering',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
if a.lowering:os.environ.update(TRITON_KERNEL_DUMP='1',TRITON_DUMP_DIR=str(a.output/'compiler_dump'))
import torch,torch_npu,triton,kernels,diagnosis_kernels
torch.set_num_threads(8);torch.npu.set_device(4);torch.manual_seed(1729);M,N,K=[int(x) for x in a.shape.split('x')]
if a.input_dir:
 def canonical(index,shape,dtype):return torch.frombuffer(bytearray((a.input_dir/f'matmul-{a.shape}-{index}.bin').read_bytes()),dtype=dtype).reshape(shape).clone()
 aa=canonical(0,(M,K),torch.float16);bb=canonical(1,(K,N),torch.float16);bias=canonical(2,(N,),torch.float32)
else:aa=torch.randn((M,K),dtype=torch.float16)*.1;bb=torch.randn((K,N),dtype=torch.float16)*.1;bias=torch.randn((N,),dtype=torch.float32)*.1
ref=aa.float()@bb.float();ref=torch.nn.functional.gelu(ref+bias,approximate='tanh') if a.operator=='gemm_bias_gelu' else ref
A,B,Bias=aa.to('npu:4'),bb.to('npu:4'),bias.to('npu:4');C=torch.empty((M,N),device='npu:4');kwargs={'num_stages':a.stages,'num_warps':4,'debug':a.lowering};kwargs.update({'enable_dynamic_cv_pipeline':True} if a.cv_pipeline else {})
fn=kernels.matmul if a.kernel_kind=='original' else diagnosis_kernels.matmul_unrolled
args=(A,B,Bias,C,M,N,K,a.tile_m,a.tile_n,a.bk,a.operator=='gemm_bias_gelu')
if a.kernel_kind=='unroll':args=args+(a.unroll,)
c=fn[(triton.cdiv(M,a.tile_m),triton.cdiv(N,a.tile_n),1)](*args,**kwargs);torch.npu.synchronize();out=C.cpu();assert torch.allclose(out,ref,atol=.002,rtol=.02),float((out-ref).abs().max())
r={'status':'passed','scope':'exploratory fixed config, N/P pending','operator':a.operator,'shape':[M,N,K],'config':{'BM':a.tile_m,'BN':a.tile_n,'BK':a.bk,**kwargs},'validation_max_abs_error':float((out-ref).abs().max()),'metadata':repr(c.metadata),'input_hashes':{name:hashlib.sha256(x.numpy().tobytes()).hexdigest() for name,x in [('A',aa),('B',bb),('bias',bias)]},'asm':{}}
d=a.output/'asm';d.mkdir()
for stage,data in c.asm.items():
 if isinstance(data,str):data=data.encode()
 if isinstance(data,bytes):(d/str(stage)).write_bytes(data);r['asm'][str(stage)]=hashlib.sha256(data).hexdigest()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['metadata','asm']}))
