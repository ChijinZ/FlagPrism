#!/usr/bin/env python3
"""Late HIVM probe for the existing fused kernel; preserve the original launch ABI.
Counter records use extra, allocated space after the bias vector. All clocks
remain SYS_CNT ticks. Each actor's intervals are interpreted locally.
"""
# EXPERIMENTAL / FAILED: final-HIVM roundtrip crashed before any device launch.
# This file is not an implemented profiling backend or a Study measurement source.
import argparse,json,os,re,subprocess,time,traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--before',type=int,default=0);p.add_argument('--budget',type=int,default=4096);p.add_argument('--device',type=int,default=4);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--compile-only',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
r={'status':'started','before':a.before,'budget':a.budget,'semantics':'actor-local SYS_CNT brackets; probe perturbation recorded; no cross-core subtraction'}
try:
 import torch,torch_npu,triton
 import kernels
 torch.npu.set_device(a.device);device=f'npu:{a.device}'
 def inp(i,shape,dtype):return torch.frombuffer(bytearray((a.input_dir/f'matmul-32x32x32-{i}.bin').read_bytes()),dtype=dtype).reshape(shape).clone()
 ca,cb,bias=inp(0,(32,32),torch.float16),inp(1,(32,32),torch.float16),inp(2,(32,),torch.float32)
 ref=torch.nn.functional.gelu(ca.float()@cb.float()+bias,approximate='tanh')
 extra=torch.full((512,),-559038737,dtype=torch.int32,device='cpu').view(torch.float32)
 A,B,Bias,C=ca.to(device),cb.to(device),torch.cat([bias,extra]).to(device),torch.empty((32,32),dtype=torch.float32,device=device)
 os.environ['TRITON_KERNEL_DUMP']='1';os.environ['TRITON_DUMP_DIR']=str((a.output/'dump').resolve())
 compiled=kernels.matmul.warmup(A,B,Bias,C,32,32,32,16,16,16,True,grid=(2,2),num_stages=1,num_warps=4,debug=True)
 files=list((a.output/'dump').rglob('kernel.npuir.mlir'))
 if not files:files=list(Path('../fusion-lowering').rglob('kernel.npuir.mlir'))
 if not files:raise RuntimeError('No late HIVM diagnostic produced')
 raw=files[0].read_text();parts=[];active=False;depth=0;current=[]
 for line in raw.splitlines():
  if line.startswith('func.func @matmul_mix_'):active=True;current=[];depth=0
  if active:
   current.append(line);depth+=line.count('{')-line.count('}')
   if depth==0:parts.append(chr(10).join(current));active=False
 src=chr(10).join(parts);(a.output/'original.hivm.mlir').write_text(src)
 split=src.index('func.func @matmul_mix_aiv');cube,vec=src[:split],src[split:]
 def setup():return '''
  %study_bid = hivm.hir.get_block_idx -> i64
  %study_bidx = arith.index_cast %study_bid : i64 to index
  %study_stride = arith.constant 16 : index
  %study_n = arith.constant 32 : index
  %study_base0 = arith.muli %study_bidx, %study_stride : index
  %study_base = arith.addi %study_base0, %study_n : index
'''
 def tick(name):return f'  %{name} = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l" : () -> i64\n'
 def stores(names,vector=False):
  text=setup();base='study_base'
  if vector:
   text+='  %study_sub = hivm.hir.get_sub_block_idx -> i64\n  %study_sidx = arith.index_cast %study_sub : i64 to index\n  %study_six = arith.constant 6 : index\n  %study_four = arith.constant 4 : index\n  %study_s_off = arith.muli %study_sidx, %study_six : index\n  %study_v_off = arith.addi %study_s_off, %study_four : index\n  %study_vbase = arith.addi %study_base, %study_v_off : index\n';base='study_vbase'
  for i,name in enumerate(names):
   text+=f'  %study_i{i} = arith.constant {i} : index\n  %study_o{i} = arith.addi %{base}, %study_i{i} : index\n  %study_lo{i} = arith.trunci %{name} : i64 to i32\n  %study_f{i} = arith.bitcast %study_lo{i} : i32 to f32\n  memref.store %study_f{i}, %arg5[%study_o{i}] : memref<?xf32, #hivm.address_space<gm>>\n'
  return text
 def delay(tag,n):
  if not n:return ''
  return f'''  %study_{tag}_zero = arith.constant 0 : index
  %study_{tag}_one = arith.constant 1 : index
  %study_{tag}_n = arith.constant {n} : index
  scf.for %study_{tag}_i = %study_{tag}_zero to %study_{tag}_n step %study_{tag}_one {{
    llvm.inline_asm has_side_effects asm_dialect = att "NOP", "" : () -> ()
  }}
'''
 # Start after scalar setup, before the existing matrix loop.
 pos=cube.index('  scf.for ');cube=cube[:pos]+tick('study_t0')+cube[pos:]
 signal='  hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 0'
 if signal not in cube:raise RuntimeError('Expected producer signal not found')
 fence='  hivm.hir.set_flag[<PIPE_FIX>, <PIPE_S>, <EVENT_ID7>]\n  hivm.hir.wait_flag[<PIPE_FIX>, <PIPE_S>, <EVENT_ID7>]\n'
 cube=cube.replace(signal,fence+tick('study_t1')+delay('pre',a.before)+signal+'\n'+delay('post',a.budget-a.before))
 cube=cube.replace('  return',stores(['study_t0','study_t1'])+'  hivm.hir.pipe_barrier[<PIPE_ALL>]\n  return')
 wait='  hivm.hir.sync_block_wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 0'
 vec=vec.replace(wait,tick('study_w0')+wait+'\n'+tick('study_w1')+tick('study_e0'))
 vec=vec.replace('  return','  hivm.hir.pipe_barrier[<PIPE_ALL>]\n'+tick('study_e1')+stores(['study_w0','study_w1','study_e0','study_e1'],True)+'  hivm.hir.pipe_barrier[<PIPE_ALL>]\n  return')
 patched='module {\n'+cube+vec+'\n}\n';ir=a.output/'instrumented.hivm.mlir';ir.write_text(patched)
 binary=a.output/'kernel'
 cmd=['/usr/local/Ascend/cann-9.0.0/bin/bishengir-compile',str(ir),'--target=Ascend910B4-1','--enable-hivm-compile=true','--disable-hivm-tensor-compile','-o',str(binary)]
 q=subprocess.run(cmd,capture_output=True,text=True,timeout=120);(a.output/'compile.log').write_text(q.stdout+q.stderr);r['compile_command']=cmd
 if q.returncode:raise RuntimeError(f'HIVM recompile failed ({q.returncode}); inspect compile.log')
 if not binary.exists():raise RuntimeError('Compiler output missing')
 r['binary_bytes']=binary.stat().st_size
 if not a.compile_only:
  compiled.kernel=binary.read_bytes();compiled.asm['npubin']=compiled.kernel
  # A warmup object has not initialized a module handle; the new binary is loaded once.
  r['samples']=[]
  from flagtree import profiler
  os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
  sid=profiler.start(str(a.output/'profile'),backend='cann',hook='triton',mode=f'runtime_base:device_id={a.device}:runtime_host_timing_fallback=false')
  try:
   for i in range(15):
    compiled[(2,2)](A,B,Bias,C,32,32,32,16,16,16,True)
    torch.npu.synchronize()
    if not torch.allclose(C.cpu(),ref,atol=.002,rtol=.02):raise RuntimeError('Instrumented output incorrect')
    vals=Bias.cpu()[32:].view(torch.int32).tolist();r['samples'].append(vals[:64])
  finally:profiler.finalize(sid)
 r['status']='passed'
except Exception as e:r['status']='failed';r['error']=repr(e);r['traceback']=traceback.format_exc();traceback.print_exc()
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['samples','traceback']}))
raise SystemExit(0 if r['status']=='passed' else 1)
