"""Finite current96 State sidecar; preserve all prior unqualified receipts."""
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inp=Path(__file__).parent

def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
contract=json.loads((inp/'contract.json').read_bytes())
for name,key in [('application-review.md','application_review_sha256'),('semantics-review.md','semantics_review_sha256'),('compiler-review.md','compiler_review_sha256')]:need(sha(inp/name)==contract[key],'Independent reviewed scope changed')
for resource in contract['resources']:need(sha(resource['path'])==resource['sha256'],'Reviewed actual SDK resource changed')
root=Path('/tmp/chijin-timeline-r089-ascend');job=root/'runs/profile-State-v4';inventory=root/'runs/profile-inventory-v1'
for r in [job,inventory]:need(json.loads((r/'terminal.json').read_bytes())['returncode']==0,'Actual CPU job not successful')
need(sha(root/'profile-State-input-v4/ascend_state_writer_partition.py')==contract['checker_sha256'],'Actual executed checker differs')
result=json.loads((job/'output/actual-profile/result.json').read_bytes());need(result['registered']==result['checked']==result['partitioned']==96 and result['distinct_successful_parts']==40,'Actual profile denominator differs')
need(result['checker_sha256']==contract['checker_sha256'] and sha(inventory/'output/current-rows.json')==result['registration_sha256'],'Actual registration identity differs')
registered=json.loads((inventory/'output/current-rows.json').read_bytes());rows=json.loads((job/'output/actual-profile/rows.json').read_bytes());bycase={x['case']:x for x in registered};need(len(bycase)==len(rows)==96,'Actual current96 registry differs');qualified=[];instances=0;elements=0;actors=Counter()
for row in rows:
 original=bycase[row['case']];need(row['status']=='partition_under_existing_SDK_model' and original['status']=='bound_actual_profile_codegen','Actual partition not verified')
 for key in ['stage','capture_sha256','math_sha256','binary_sha256','ttir_sha256','bcmlir_sha256','grid','elements','State_index','compiler_identity','mix_mode','bs_task_type']:need(row[key]==original[key],'Actual original/profile row differs')
 for pathkey,hashkey in [('capture_file','capture_sha256'),('math_file','math_sha256')]:need(sha(row[pathkey])==row[hashkey],'Original capture/math changed')
 cap=json.loads(Path(row['capture_file']).read_bytes());meta=cap['metadata']['compiler_metadata'];need(meta['arch']=='Ascend910B4-1' and meta['enable_auto_blockify'] is False and meta['parallel_mode']=='simd' and meta['force_simt_only'] is False,'Actual reviewed launcher ABI differs')
 need(meta['ascend_compiler_identity']==contract['compiler_identity'],'Actual SDK compiler identity differs');need((meta['mix_mode'],meta['bs_task_type'])==(('mix',32) if original['has_cube'] else ('aiv',10)),'Actual physical actor/task type differs')
 actual={(j['actor_kind'],s['path'],s['sha256']) for j in original['jobs'] for s in j['inputs']};need(actual=={(x['actor'],x['source_file'],x['source_sha256']) for x in row['parts']},'Actual codegen actor/input binding differs')
 for j in original['jobs']:
  for f in j['input_files']:need(sha(f['path'])==f['sha256'],'Actual codegen input or linked library changed')
 counts=Counter()
 for part in row['parts']:
  actors[part['actor']]+=1;need(sha(part['source_file'])==part['source_sha256'],'Actual LLVM actor input changed');need(part['subblocks']==(2 if part['actor']=='AIV' and original['has_cube'] else 1),'Actual physical actor multiplicity differs');counts.update({int(k):v for k,v in part['partition']['element_writers'].items()})
  for w in part['partition']['write_instances']:
   need(w['source_sizes']==w['sizes'] and w['source_offset']==0 and w['source_byte_address'] is not None and w['source_byte_address']%32==0,'Outside reviewed source window');need(w['source_strides'] in ([1],[16,1],[32,1]) and w['strides'][-1]==1 and max(w['sizes'])<=256,'Outside reviewed transfer dimensions');instances+=1
 need(len(counts)==row['elements'] and all(counts[i]==1 for i in range(row['elements'])),'Actual physical writers overlap or omit State');elements+=row['elements'];qualified.append(dict(case=row['case'],stage=row['stage'],capture_sha256=row['capture_sha256'],math_sha256=row['math_sha256'],binary_sha256=row['binary_sha256'],grid=row['grid'],State_elements=row['elements'],state_writer_qualified=True,native_timing_boundary_qualified=False))
need(instances==1143 and elements==183048 and actors==Counter(AIV=96,AIC=36),'Actual independently reviewed finite extent differs')
summary=dict(status='current96_actual_Ascend_State_writer_under_reviewed_SDK_ABI',qualified=96,State_write_instances=instances,State_elements=elements,actor_parts=dict(actors),state_writer_qualified=True,SDK_ABI_binding_qualified=True,native_timing_boundary_qualified=False,pipeline_or_whole_goal_qualified=False,device_executed=False,application_replayed=False,SDK_recompiled=False,checker_sha256=contract['checker_sha256'],contract_sha256=sha(inp/'contract.json'),application_review_sha256=contract['application_review_sha256'],semantics_review_sha256=contract['semantics_review_sha256'],compiler_review_sha256=contract['compiler_review_sha256'],partition_rows_sha256=sha(job/'output/actual-profile/rows.json'),qualification_rows=qualified)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
