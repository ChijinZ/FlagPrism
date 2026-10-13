#!/usr/bin/env python3
"""Capture actual scalar issue progression in program0 only; preserve original fences."""
import argparse,re,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--aic',type=Path,required=True);p.add_argument('--aiv',type=Path,required=True);p.add_argument('--n',type=int,required=True);p.add_argument('--k',type=int,required=True);p.add_argument('--bk',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);count=(a.k+a.bk-1)//a.bk
manifest={'shape_K':a.k,'N':a.n,'BK':a.bk,'iterations':count,'recording_program':0,'counter_domain':'SYS_CNT','tick_ns':20,'actor_header_fields':16,'actor_header_records':3,'loop_fields':16,'added_barriers':0,'clock_policy':'Scalar issue positions. After a wait targeting a non-scalar engine, clock does not certify engine readiness/completion. Actor origins independent until shared-domain verification.','selected_invocation_policy':'For each config separately choose instrumented retained invocation closest to median native task duration, tie lowest ordinal; never combine separate invocations into one trace.','loop_events':{'0':'iteration_index','1':'buffer_parity','2':'iteration_entry','3':'A_L1_reuse_wait_instruction_enter','4':'A_L1_reuse_wait_instruction_return','5':'A_GM_to_L1_issue_enter','6':'A_GM_to_L1_issue_return','7':'B_L1_reuse_wait_instruction_enter','8':'B_L1_reuse_wait_instruction_return','9':'B_GM_to_L1_issue_enter','10':'B_GM_to_L1_issue_return','11':'MMA_helper_issue_enter','12':'MMA_helper_issue_return','13':'iteration_exit','14':'L1_A_address','15':'L1_B_address'},'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in [('aic',a.aic),('aiv',a.aiv)]}}
def tick(name):return f'  %{name} = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()\n'
def store(field,value,ptr='%pl_rec',name=None):
 name=name or f'pl_field{field}';return f'  %{name} = getelementptr i64, ptr addrspace(1) {ptr}, i64 {field}\n  store volatile i64 {value}, ptr addrspace(1) %{name}, align 8\n'
def stamp(field,label,ptr='%pl_rec'):
 return tick(label)+store(field,'%'+label,ptr,name=label+'_ptr')
def patch(path,actor):
 text=path.read_text();m=re.search(r'(define dso_local void @([^ (]+)\(([^\n]+)\) \{\n)([\s\S]*?)(\n\})',text);assert m,actor
 name=m[2];signature=m[3];body=m[4];params=re.findall(r'(i\d+|ptr(?: addrspace\(\d+\))?) (%\w+)',signature);assert len(params)==10,params
 observed=body
 header=f'  %pl_bid = call i64 @llvm.hivm.GET.BLOCK.IDX()\n  %pl_tail = getelementptr i8, ptr addrspace(1) %5, i64 {a.n*4}\n'
 if actor=='aic':header+='  %pl_actor_rec = getelementptr i64, ptr addrspace(1) %pl_tail, i64 0\n';sub='0';kind='0'
 else:header+='  %pl_sub = call i64 @llvm.hivm.GET.SUBBLOCKID()\n  %pl_slot = add i64 %pl_sub, 1\n  %pl_actor_off = mul i64 %pl_slot, 16\n  %pl_actor_rec = getelementptr i64, ptr addrspace(1) %pl_tail, i64 %pl_actor_off\n';sub='%pl_sub';kind='1'
 header+=store(0,'%pl_bid','%pl_actor_rec','pl_header_id')+store(1,sub,'%pl_actor_rec','pl_header_sub')+store(2,kind,'%pl_actor_rec','pl_header_kind')+stamp(3,'pl_body_entry','%pl_actor_rec')
 observed=header+observed
 if actor=='aic':
  phi=re.search(r'  (%\d+) = phi i32',observed);assert phi;iteration=phi[1]
  sext=re.search(r'  (%\d+) = sext i32 '+re.escape(iteration)+r' to i64\n',observed);assert sext;iter64=sext[1]
  setup='  %pl_parity = srem i64 '+iter64+', 2\n  %pl_index = mul i64 '+iter64+', 16\n  %pl_offset = add i64 %pl_index, 48\n  %pl_rec = getelementptr i64, ptr addrspace(1) %pl_tail, i64 %pl_offset\n'+store(0,iter64)+store(1,'%pl_parity')+stamp(2,'pl_iter_entry')
  observed=observed.replace(sext[0],sext[0]+setup)
  lines=[l for l in observed.splitlines() if 'call void @nd2nz_half(' in l];assert len(lines)==2
  for index,line in enumerate(lines):
   pos=observed.index(line);prefix=observed[:pos];waits=list(re.finditer(r'  call void @llvm.hivm.WAIT.FLAG\.(?:IMM|REG)\(i64 3, i64 4, [^\n]+',prefix));assert waits;wait=waits[-1][0];wf=3 if index==0 else 7;lf=5 if index==0 else 9
   at=waits[-1].start();observed=observed[:at]+stamp(wf,f'pl_wait{index}_enter')+wait+'\n'+stamp(wf+1,f'pl_wait{index}_return')+observed[at+len(wait):]
   ptr=re.search(r'ptr addrspace\(2\) ([^,]+)',line)[1];ptrname=f'pl_buf{index}'
   observed=observed.replace(line,f'  %{ptrname} = ptrtoint ptr addrspace(2) {ptr} to i64\n'+store(14+index,'%'+ptrname)+stamp(lf,f'pl_load{index}_enter')+line+'\n'+stamp(lf+1,f'pl_load{index}_return'))
  mma=next(l for l in observed.splitlines() if 'call void @mma_tile_half_to_float(' in l);observed=observed.replace(mma,stamp(11,'pl_mma_enter')+mma+'\n'+stamp(12,'pl_mma_return')+stamp(13,'pl_iter_exit'))
  signal='  call void @llvm.hivm.SET.CROSS.CORE(i64 10, i64 33)';assert signal in observed;observed=observed.replace(signal,stamp(5,'pl_signal_enter','%pl_actor_rec')+signal+'\n'+stamp(6,'pl_signal_return','%pl_actor_rec'))
 else:
  wait='  call void @llvm.hivm.WAIT.FLAG.DEV.REG(i64 0)';assert observed.count(wait)==1;observed=observed.replace(wait,stamp(5,'pl_ready_enter','%pl_actor_rec')+wait+'\n'+stamp(6,'pl_ready_return','%pl_actor_rec'))
  load=next(l for l in observed.splitlines() if 'call void @load_gm_to_ubuf_1d_float(ptr addrspace(1) %2' in l);observed=observed.replace(load,stamp(7,'pl_workspace_enter','%pl_actor_rec')+load+'\n'+stamp(8,'pl_workspace_return','%pl_actor_rec'))
 observed=observed.replace('  ret void',stamp(4,'pl_body_exit','%pl_actor_rec')+'  ret void')
 public='define dso_local void @'+name+'('+signature+') {\nentry:\n  %pl_select_bid = call i64 @llvm.hivm.GET.BLOCK.IDX()\n  %pl_selected = icmp eq i64 %pl_select_bid, 0\n  br i1 %pl_selected, label %observe, label %plain\nobserve:\n  call void @'+name+'_observed('+', '.join(t+' '+n for t,n in params)+')\n  ret void\nplain:\n  call void @'+name+'_plain('+', '.join(t+' '+n for t,n in params)+')\n  ret void\n}\n'
 clones='define private void @'+name+'_observed('+signature+') alwaysinline {\n'+observed+'\n}\n'+'define private void @'+name+'_plain('+signature+') alwaysinline {\n'+body+'\n}\n'
 patched=text[:m.start()]+public+clones+text[m.end():]
 assert patched.count('@llvm.hivm.BARRIER(')==text.count('@llvm.hivm.BARRIER(')+body.count('@llvm.hivm.BARRIER(') # second mutually-exclusive identical clone, no new barrier site
 out=a.output/('instrumented-'+actor+'.ll');out.write_text(patched);manifest.setdefault('instrumented_sha256',{})[actor]=hashlib.sha256(patched.encode()).hexdigest()
patch(a.aic,'aic');patch(a.aiv,'aiv');(a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
