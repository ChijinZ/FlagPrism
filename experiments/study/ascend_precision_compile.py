#!/usr/bin/env python3
"""Compile real AIV softmax with SDK-equivalent hardware PMU window gates."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--gate-sdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--narrow',action='store_true');p.add_argument('--shared-stop-fence',action='store_true');p.add_argument('--dependent-end',action='store_true');p.add_argument('--branch-end',action='store_true');p.add_argument('--scope',choices=['body','output','empty'],required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);o=a.output.resolve()
s=a.source.read_text();sdk=a.gate_sdk.read_text()
for x in ['GET.CTRL','SET.CTRL','SBITSET0','SBITSET1']:assert '@llvm.hivm.'+x in sdk
start='  %st_body0 = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()' if a.scope=='body' else '  %st_output0 = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()'
end='  %st_body1 = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()'
def tick(n):return f'  %{n} = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()\n'
def prep(on,prefix):return f'  %{prefix}_ctrl = call i64 @llvm.hivm.GET.CTRL()\n  %{prefix}_bit = call i64 @llvm.hivm.SBITSET{int(on)}(i64 %{prefix}_ctrl, i64 0)\n'
def gate(on,prefix):
 if a.narrow:return ('' if a.shared_stop_fence and not on and a.scope!='empty' else '  call void @llvm.hivm.BARRIER(i64 6)\n')+tick(prefix+'0')+f'  call void @llvm.hivm.SET.CTRL(i64 %{prefix}_bit)\n'+tick(prefix+'1')+'  call void @llvm.hivm.BARRIER(i64 6)\n'
 return '  call void @llvm.hivm.BARRIER(i64 6)\n'+tick(prefix+'0')+f'  %{prefix}_ctrl = call i64 @llvm.hivm.GET.CTRL()\n  %{prefix}_bit = call i64 @llvm.hivm.SBITSET{int(on)}(i64 %{prefix}_ctrl, i64 0)\n  call void @llvm.hivm.SET.CTRL(i64 %{prefix}_bit)\n'+tick(prefix+'1')+'  call void @llvm.hivm.BARRIER(i64 6)\n'
# SDK gates carry PIPE_ALL fences; raw endpoint halos bound the SET.CTRL instructions.
if a.narrow:
 s=s.replace(start,prep(True,'pmu_start')+start)
 if a.scope=='empty':s=s.replace(start,prep(False,'pmu_stop')+start)
 else:
  needle='  call void @llvm.hivm.BARRIER(i64 6)\n'+end;assert s.count(needle)==1;s=s.replace(needle,prep(False,'pmu_stop')+needle)
if a.scope=='empty':s=s.replace(start,gate(True,'pmu_start')+gate(False,'pmu_stop')+start)
else:s=s.replace(start,gate(True,'pmu_start')+start).replace(end,end+'\n'+gate(False,'pmu_stop'))
if a.dependent_end:
 assert a.narrow and a.shared_stop_fence and a.scope!='empty'
 s=s.replace(end,'  %st_body1 = call i64 asm sideeffect "MOV $0, $1\\0AMOV $0, SYS_CNT", "=&l,l"(i64 %pmu_stop_bit)')
if a.branch_end:
 assert a.narrow and a.shared_stop_fence and not a.dependent_end and a.scope!='empty'
 branch='  %pmu_clock_condition = icmp ne i64 %pmu_stop_bit, 0\n  br i1 %pmu_clock_condition, label %pmu_clock_true, label %pmu_clock_false\n\npmu_clock_true:\n  call void asm sideeffect "NOP\\0ANOP", ""()\n  br label %pmu_clock_join\n\npmu_clock_false:\n  call void asm sideeffect "NOP", ""()\n  br label %pmu_clock_join\n\npmu_clock_join:\n  %st_body1 = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()'
 s=s.replace(end,branch)
for i,name in enumerate(['pmu_start0','pmu_start1','pmu_stop0','pmu_stop1'],9):
 store=f'  %pmu_p{i} = getelementptr i64, ptr addrspace(1) %st_rec, i64 {i}\n  store volatile i64 %{name}, ptr addrspace(1) %pmu_p{i}, align 8\n'
 # Only public rows has this named record, preserving other helper return sites.
 s=s.replace('  store volatile i64 %st_compute1, ptr addrspace(1) %st_p8, align 8\n','  store volatile i64 %st_compute1, ptr addrspace(1) %st_p8, align 8\n'+store)
for name,ret,args in [('GET.CTRL','i64',''),('SET.CTRL','void','i64'),('SBITSET0','i64','i64, i64'),('SBITSET1','i64','i64, i64')]:
 if not re.search(r'(declare|define) [^\n]*@llvm\.hivm\.'+re.escape(name)+r'\(',s):s+='\ndeclare '+ret+' @llvm.hivm.'+name+'('+args+')\n'
ll=o/'kernel.ll';ll.write_text(s)
cmd=['/usr/local/Ascend/cann-9.0.0/bin/bisheng',str(ll),'-o',str(o/'kernel.o'),'--cce-aicore-arch=dav-c220-vec','--cce-aicore-only','-O2','-cce-bitcode-is-aicore','-Wno-override-module','-cce-link-aicore-ll-module','/usr/local/Ascend/cann-9.0.0/tools/bishengir/lib/meta_op.aiv.bc','-mllvm','-cce-aicore-dcci-insert-for-scalar=false','--cce-aicore-input-parameter-size=1536']
r=subprocess.run(cmd,capture_output=True,timeout=45);(o/'compile.log').write_bytes(r.stdout+r.stderr);receipt={'status':'compiled' if r.returncode==0 and (o/'kernel.o').exists() else 'failed','command':cmd,'scope':a.scope,'narrow_halo':a.narrow,'shared_stop_fence':a.shared_stop_fence,'dependent_end_clock':a.dependent_end,'branch_end_clock':a.branch_end,'branch_end_semantics':'Fresh prepared stop-word controls branch through distinct sideeffect NOP blocks before common SYS clock at join; branch/optional NOP probe overhead before end clock at after-selected-final-barrier site','dependent_end_semantics':'SYS end clock first consumes fresh prepared off-word through scalar MOV; adds instrumentation dependency before reading SYS_CNT at original after-final-barrier site; no math/output change','stop_barrier_policy':'Original final PIPE_ALL also serves SDK stop prebarrier; source end clock and immediate gate halos between barrier and SET.CTRL' if a.shared_stop_fence and a.scope!='empty' else ('Empty gate retains full SDK before/after fences; no source final-barrier sharing' if a.scope=='empty' else 'SDK adds another PIPE_ALL after source end clock'),'control_preparation':('Empty: on/off words freshly prepared before empty gate, no helper between snapshots and gates' if a.scope=='empty' else 'fresh start word before start fence; fresh stop word after store helper before original final PIPE_ALL; no helper/CTRL mutations between snapshot and its gate') if a.narrow else 'fresh GET.CTRL/SBITSET inside halos','source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'gate_sdk_sha256':hashlib.sha256(a.gate_sdk.read_bytes()).hexdigest(),'llvm_sha256':hashlib.sha256(s.encode()).hexdigest(),'pmu_tick_halos':[9,10,11,12],'comparison':'hardware profiling window bounded by SYS_CNT before/after SET.CTRL; new PIPE_ALL gates perturb execution; PMU gating halo is wider than source bracket'}
if (o/'kernel.o').exists():receipt['binary_sha256']=hashlib.sha256((o/'kernel.o').read_bytes()).hexdigest()
(o/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(r.returncode)
