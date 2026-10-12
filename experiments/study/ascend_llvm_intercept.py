#!/usr/bin/env python3
"""Capture/instrument generated pre-link LLVM inside the original compiler pipeline."""
import json, os, re, subprocess, sys
from pathlib import Path
w=Path(os.environ['STUDY_ASCEND_OUTPUT']);w.mkdir(parents=True,exist_ok=True)
args=sys.argv[1:]
with (w/'bisheng-argv.jsonl').open('a') as f:f.write(json.dumps(args)+'\n')
def tick(name):return f'  %{name} = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()\n'
def instrument(text,kind):
 # Modify only the public kernel, preserving wrapper functions and implicit SSA IDs.
 pattern=r'(define dso_local void @matmul_mix_'+kind+r'\([^\n]+\) \{\n)([\s\S]*?)(\n\})'
 m=re.search(pattern,text);assert m,kind
 body=m[2];names=['st_body0','st_body1'];body=tick(names[0])+body
 if kind=='aic':
  signal='  call void @llvm.hivm.SET.CROSS.CORE(i64 10, i64 33)'
  assert signal in body
  before=int(os.environ.get('STUDY_ASCEND_BEFORE','0'));budget=int(os.environ.get('STUDY_ASCEND_BUDGET','0'));assert 0<=before<=budget
  def aux(n):return '  call void asm sideeffect "'+r'\0A'.join(['NOP']*n)+'", ""()\n' if n else ''
  fence='  call void @llvm.hivm.BARRIER(i64 6)\n' if os.environ.get('STUDY_ASCEND_PRODUCER_FENCE')=='1' else ''
  body=body.replace(signal,fence+tick('st_signal0')+aux(before)+signal+'\n'+tick('st_signal1')+aux(budget-before))
  names += ['st_signal0','st_signal1'];sub='0';actor='0'
 else:
  wait='  call void @llvm.hivm.WAIT.FLAG.DEV.REG(i64 0)'
  assert wait in body
  body=body.replace(wait,tick('st_output0')+wait+'\n'+tick('st_ready'))
  load=next(l for l in body.splitlines() if 'call void @load_gm_to_ubuf_1d_float(ptr addrspace(1) %2' in l)
  body=body.replace(load,load+f'\n  call void @llvm.hivm.BARRIER(i64 {6 if os.environ.get("STUDY_ASCEND_COMPLETION")=="1" else 4})\n'+tick('st_transfer1'))
  stwait='  call void @llvm.hivm.WAIT.FLAG.IMM(i64 1, i64 5, i64 0)'
  assert stwait in body
  body=body.replace(stwait,stwait+'\n'+('  call void @llvm.hivm.BARRIER(i64 6)\n' if os.environ.get('STUDY_ASCEND_COMPLETION')=='1' else '')+tick('st_compute1'))
  names+=['st_output0','st_ready','st_transfer1','st_compute1'];sub='%st_sub';actor='1'
  body=body.replace('  ret void','  %st_sub = call i64 @llvm.hivm.GET.SUBBLOCKID()\n  ret void')
 body=body.replace('  ret void',tick('st_body1')+'  %st_bid = call i64 @llvm.hivm.GET.BLOCK.IDX()\n  %st_b3 = mul i64 %st_bid, 3\n'+('  %st_a = add i64 %st_sub, 1\n  %st_slot = add i64 %st_b3, %st_a\n' if kind=='aiv' else '  %st_slot = add i64 %st_b3, 0\n')+f'  %st_bytes = mul i64 %st_slot, 128\n  %st_off = add i64 %st_bytes, {int(os.environ.get("STUDY_ASCEND_N","32"))*4}\n  %st_rec = getelementptr i8, ptr addrspace(1) %5, i64 %st_off\n'+''.join(f'  %st_p{i} = getelementptr i64, ptr addrspace(1) %st_rec, i64 {i}\n  store volatile i64 {v}, ptr addrspace(1) %st_p{i}, align 8\n' for i,v in enumerate(['%st_bid',sub,actor]+['%'+n for n in names]))+'  ret void')
 return text[:m.start()]+m[1]+body+m[3]+text[m.end():]
def instrument_rows(text):
 m=re.search(r'(define dso_local void @rows\([^\n]+\) \{\n)([\s\S]*?)(\n\})',text);assert m
 body=tick('st_body0')+m[2]
 load=next(l for l in body.splitlines() if '  call void @load_gm_to_ubuf_2d_float(' in l)
 body=body.replace(load,tick('st_load0')+load)
 wait='  call void @llvm.hivm.WAIT.FLAG.IMM(i64 4, i64 1, i64 0)'
 assert body.count(wait)==1;body=body.replace(wait,wait+'\n'+('  call void @llvm.hivm.BARRIER(i64 6)\n' if os.environ.get('STUDY_ASCEND_COMPLETION')=='1' else '')+tick('st_load1'))
 div=next(l for l in body.splitlines() if '  call void @vdiv_vs_1d_float(' in l)
 body=body.replace(div,tick('st_output0')+div)
 wait='  call void @llvm.hivm.WAIT.FLAG.IMM(i64 1, i64 5, i64 0)'
 assert body.count(wait)==1;body=body.replace(wait,wait+'\n'+('  call void @llvm.hivm.BARRIER(i64 6)\n' if os.environ.get('STUDY_ASCEND_COMPLETION')=='1' else '')+tick('st_compute1'))
 vals=['%st_bid','0','1','%st_body0','%st_body1','%st_load0','%st_load1','%st_output0','%st_compute1']
 stores=''.join(f'  %st_p{i} = getelementptr i64, ptr addrspace(1) %st_rec, i64 {i}\n  store volatile i64 {v}, ptr addrspace(1) %st_p{i}, align 8\n' for i,v in enumerate(vals))
 body=body.replace('  ret void',tick('st_body1')+'  %st_bid = call i64 @llvm.hivm.GET.BLOCK.IDX()\n  %st_bytes = mul i64 %st_bid, 128\n  %st_off = add i64 %st_bytes, 32768\n  %st_rec = getelementptr i8, ptr addrspace(1) %6, i64 %st_off\n'+stores+'  ret void')
 return text[:m.start()]+m[1]+body+m[3]+text[m.end():]
for a in args:
 p=Path(a)
 if p.is_file() and p.suffix=='.ll':
  original=p.read_text();(w/(p.name+'.original')).write_text(original)
  if os.environ.get('STUDY_ASCEND_INSTRUMENT')=='1' and ('@matmul_mix_' in original or 'define dso_local void @rows(' in original):
   patched=instrument_rows(original) if 'define dso_local void @rows(' in original else instrument(original,'aic' if '.mix_aic.' in p.name else 'aiv');p.write_text(patched);(w/(p.name+'.instrumented')).write_text(patched)
r=subprocess.run(['/usr/local/Ascend/cann-9.0.0/bin/bisheng',*args]);sys.exit(r.returncode)
