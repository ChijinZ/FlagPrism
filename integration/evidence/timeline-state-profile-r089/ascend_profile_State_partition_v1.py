"""Existing actual profile LLVM State partitions, no SDK or math replay."""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
from collections import Counter
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inp=Path(__file__).parent
spec=importlib.util.spec_from_file_location('ascend_state',inp/'ascend_state_writer_partition.py');checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
root=Path('/tmp/chijin-timeline-r089-ascend/runs/profile-inventory-v1');need(json.loads((root/'terminal.json').read_bytes())['returncode']==0,'Actual input inventory job failed');registration=root/'output/current-rows.json';registered=json.loads(registration.read_bytes());need(len(registered)==96 and all(r['status']=='bound_actual_profile_codegen' for r in registered),'Current96 identity inventory incomplete');rows=[];cache={}
for item in registered:
 row={k:item[k] for k in ['stage','case','capture_file','capture_sha256','math_file','math_sha256','binary_sha256','ttir_sha256','bcmlir_sha256','State_index','grid','elements','bs_task_type','mix_mode','compiler_identity']};row.update(state_writer_qualified=False)
 try:
  need(sha(item['capture_file'])==item['capture_sha256'] and sha(item['math_file'])==item['math_sha256'],'Original actual capture/math changed');parts=[];counts=Counter()
  for job in item['jobs']:
   actor=job['actor_kind'];subblocks=item['bs_task_type']%10 if actor=='AIV' and item['has_cube'] else 1
   for source in job['inputs']:
    path=Path(source['path']);need(sha(path)==source['sha256'],'Actual codegen LLVM input changed');text=path.read_text();functions=[m[0] for m in re.finditer(r'^define dso_local void @[^\n]+\{\n.*?^}',text,re.M|re.S)];need(functions,'Actual profile actor function absent')
    for original in functions:
     body='\n'.join(re.sub(r', !dbg !\d+(?=,|$)','',line) for line in original.splitlines());body_sha=hashlib.sha256(body.encode()).hexdigest();parameters=checker._parse(body)[0];ptrs=[v for v,t in parameters.items() if t.startswith('ptr')];need(len(ptrs)-len(item['formals'])==2,'Actual profile pointer prefix differs');state=ptrs[2+item['State_index']];key=(body_sha,state,tuple(parameters)[-3:],tuple(item['grid']),subblocks,item['elements'])
     if key not in cache:cache[key]=checker.analyze(body,state_parameter=state,grid_parameters=list(parameters)[-3:],grid=item['grid'],subblocks=subblocks,elements=item['elements'])
     answer=cache[key];counts.update(answer['element_writers']);parts.append(dict(actor=actor,source_file=str(path),source_sha256=source['sha256'],original_function_sha256=hashlib.sha256(original.encode()).hexdigest(),analysis_function_sha256=body_sha,normalization_only='navigation_debug_location_attachments',State_formal=state,grid_parameters=list(parameters)[-3:],subblocks=subblocks,partition=answer))
  need(len(counts)==item['elements'] and all(counts[k]==1 for k in range(item['elements'])),'Actual profile actors overlap or omit State elements');row.update(status='partition_under_existing_SDK_model',parts=parts)
 except (ValueError,KeyError,StopIteration) as error:
  detail=[];tb=error.__traceback__
  while tb is not None:
   if tb.tb_frame.f_code.co_filename==str(inp/'ascend_state_writer_partition.py') and 'op' in tb.tb_frame.f_locals:detail.append(str(tb.tb_frame.f_locals['op']))
   tb=tb.tb_next
  row.update(status='unverified',error=str(error),necessary_instruction_context=detail[-1:])
 rows.append(row);(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
(a.output/'result.json').write_text(json.dumps(dict(status='current96_actual_Ascend_State_partition',registered=96,checked=len(rows),partitioned=sum(r['status']!='unverified' for r in rows),distinct_successful_parts=len(cache),registration_sha256=sha(registration),checker_sha256=sha(inp/'ascend_state_writer_partition.py'),failures=[r for r in rows if r['status']=='unverified'],state_writer_qualified=False,SDK_ABI_binding_qualified=False,native_timing_boundary_qualified=False,device_executed=False,SDK_recompiled=False,application_replayed=False),indent=2))
