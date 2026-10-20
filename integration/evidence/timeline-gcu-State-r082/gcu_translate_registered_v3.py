"""Finite translation of all original LLVM-dialect operation bodies, no device replay."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inputs=Path(__file__).parent
root=Path('/tmp/chijin-timeline-r078-gcu/runs/state-inventory-v1/output');inventory=json.loads((root/'inventory.json').read_bytes());bound=Path('/tmp/chijin-timeline-r081-gcu/runs/original-compile-v2/output/rows.json');bindings=json.loads(bound.read_bytes());rows=[];seen={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for index,(row,bind) in enumerate(zip(inventory['rows'],bindings)):
 if (row['id'],row['variant'],row['math_sha256'])!=(bind['id'],bind['variant'],bind['math_sha256']) or not bind['codegen']['whole_binary_identical']:raise ValueError('Original binary binding differs')
 entry=next(x for x in row['artifacts'] if x['kind']=='llir');source=root/entry['retained_file']
 if sha(source)!=entry['sha256'] or sha(Path(row['math_file']))!=row['math_sha256']:raise ValueError('Original source/report changed')
 key=entry['sha256']
 if key in seen:result_file=seen[key]
 else:
  output=a.output/('row-'+str(index));command=[sys.executable,'-I',str(inputs/'row.py'),'--row-index',str(index),'--output',str(output)]
  with (a.output/(str(index)+'.stdout')).open('xb') as stdout,(a.output/(str(index)+'.stderr')).open('xb') as stderr:
   child=subprocess.Popen(command,stdout=stdout,stderr=stderr)
   try:code=child.wait(timeout=35)
   finally:
    if child.poll() is None:child.kill()
    child.wait(timeout=10)
  if code:raise RuntimeError('Preserve actual input translation failure at '+str(index))
  result_file=output/'result.json';seen[key]=result_file
 result=json.loads(result_file.read_bytes())
 if result['exit']!=0 or result['source_sha256']!=key:raise ValueError('Translation receipt differs')
 rows.append(dict(id=row['id'],variant=row['variant'],math_sha256=row['math_sha256'],source_sha256=key,whole_binary_sha256=bind['codegen']['original_fatbin_sha256'],translation_result=str(result_file),translation_result_sha256=sha(result_file),LLVM_file=str(result_file.parent/'functions.ll'),LLVM_sha256=result['output_sha256']))
 (a.output/'rows.json').write_text(json.dumps(rows,indent=2))
summary=dict(status='registered_original_LLVM_dialect_semantic_translation',checked=len(rows),registered=len(inventory['rows']),distinct_translations=len(seen),function_operation_lines_unchanged=True,vendor_final_IR=False,vendor_final_native=False,state_writer_qualified=False,device_executed=False,application_replayed=False)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if len(rows)!=len(inventory['rows']):raise ValueError('Registration differs')
