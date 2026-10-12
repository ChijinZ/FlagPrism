"""Research-only late LLVM call adapter to the installed read-only SDK helper."""
import hashlib,json,re
from pathlib import Path

def guard_record_staging(text, symbol):
 # Each scalar record is staged in local memory then copied to GM by thread 0.
 # Move staging into that existing branch, preserving endpoint placement.
 split=text.index('\n',text.rfind('callee = @'+symbol))+1;prefix,tail=text[:split],text[split:]
 pattern=r'(?m)^(?P<store> +"llvm.store"\(%[0-9]+, %[0-9]+\)[^\n]*: \(i32, !llvm.ptr\) -> \(\)\n)(?P<mid>(?:[^\n]*\n){0,3}?)(?P<fence> +"llvm.call"\(\)[^\n]*callee = @tops_mfence[^\n]*\n)(?P<br> +"llvm.cond_br"[^\n]*\n)(?P<label> +\^bb[0-9]+:[^\n]*\n)'
 def move(m):return m['mid']+m['fence']+m['br']+m['label']+m['store']+m['fence']
 patched,count=re.subn(pattern,move,tail);assert count in [4,8],count
 return prefix+patched,count

def install(output, shim=None, leader_records=False):
 from triton.backends.enflame import compiler
 original=compiler.make_llir
 root=Path(output);root.mkdir(parents=True,exist_ok=True)
 def adapted(mod,metadata,options):
  before=str(original(mod,metadata,options))
  begin_calls=before.count('callee = @tops_clock_begin');end_calls=before.count('callee = @tops_clock_end')
  before_ids=re.findall(r'(%[0-9]+) = \"llvm.call\"\(\)[^\n]*callee = @tops_clock_(?:begin|end)',before)
  assert 'callee = @tops_clock_begin' in before and 'callee = @tops_clock_end' in before
  after,count=re.subn(r'(?m)^    "llvm.func"[^\n]*sym_name = "tops_clock_end"[^\n]*\n    \}\) : \(\) -> \(\)\n','',before)
  assert count==1,count
  after=after.replace('tops_clock_begin','_ZN4tops12global_timerEv').replace('tops_clock_end','_ZN4tops12global_timerEv')
  assert 'tops_clock_begin' not in after and 'tops_clock_end' not in after
  staging_count=0
  if leader_records:after,staging_count=guard_record_staging(after,'_ZN4tops12global_timerEv')
  if shim:
   after=after.replace('_ZN4tops12global_timerEv','study_sdk_global_timer')
   after,count=re.subn(r', targets = \[(?:[^\[\]\n]|\[[^\[\]\n]*\])*\]', '', after, count=1);assert count==1
   after=compiler.toolkit.gcu_compiler_opt(after,'--gcu-attach-target=arch=gcu300 l='+str(shim))
  final_symbol='study_sdk_global_timer' if shim else '_ZN4tops12global_timerEv'
  after_calls=after.count('callee = @'+final_symbol);assert after_calls==begin_calls+end_calls
  after_ids=re.findall(r'(%[0-9]+) = \"llvm.call\"\(\)[^\n]*callee = @'+final_symbol,after);assert before_ids==after_ids,(before_ids,after_ids)
  (root/'original.llir.mlir').write_text(before);(root/'global-timer.llir.mlir').write_text(after)
  (root/'adapter.json').write_text(json.dumps({'sdk_symbol':'_ZN4tops12global_timerEv','leader_record_staging':leader_records,'leader_guarded_staging_stores':staging_count,'before_begin_calls':begin_calls,'before_end_calls':end_calls,'after_helper_calls':after_calls,'endpoint_ssa_order':before_ids,'calls':after.count('callee = @study_sdk_global_timer' if shim else 'callee = @_ZN4tops12global_timerEv'),'original_sha256':hashlib.sha256(before.encode()).hexdigest(),'adapted_sha256':hashlib.sha256(after.encode()).hexdigest(),'scope':'Replace clock callees and attach installed-SDK read-only helper. With leader_records, move scalar T staging into existing thread0 publication branches and retain a compiler memory fence after staging. Source math, arguments, record addresses and clock call positions remain fixed. No invented MMIO addresses or MMIO writes; SDK read-only implementation preserved.'},indent=2))
  return after
 compiler.make_llir=adapted
