"""Scoped ordinary-supplement8 sidecar from actual, independently reviewed inputs."""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inp=Path(__file__).parent

def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
contract=json.loads((inp/'contract.json').read_bytes());need(sha(inp/'application-review.md')==contract['application_review_sha256'] and sha(inp/'semantics-review.md')==contract['semantics_review_sha256'],'Independent SDK reviews changed')
for r in contract['resources']:need(sha(r['path'])==r['sha256'],'Reviewed SDK resource changed')
root=Path(contract['partition_root']);need(json.loads((root/'terminal.json').read_bytes())['returncode']==0,'Actual supplemental partition job failed');result=json.loads((root/'output/result.json').read_bytes());need(result['registered']==result['checked']==result['partitioned']==8,'Original supplemental denominator differs');need(result['checker_sha256']==contract['checker_sha256'],'Executed checker identity differs');rows=json.loads((root/'output/rows.json').read_bytes());qualified=[];instances=0;elements=0
for row in rows:
 need(row['status']=='partition_under_reviewed_SDK_model' and sha(row['math_file'])==row['math_sha256'],'Actual supplementary row differs');need(sha(row['host_once_file'])==row['host_once_sha256'] and sha(row['metadata_file'])==row['metadata_sha256'],'Actual launch/once identity changed');math=json.loads(Path(row['math_file']).read_bytes());meta=json.loads(Path(row['metadata_file']).read_bytes());need(meta['hash']==math['compiled_hash'],'Actual compiled launch identity differs')
 if contract['backend']=='gcu':
  need(row['whole_binary_identical'] is True and row['physical_threads']==meta['num_warps'] and meta['arch']=='gcu300' and meta['warp_size']==1,'Reviewed GCU launch/binary ABI differs');need(sha(row['LLVM_file'])==row['LLVM_sha256'],'Actual SDK LLVM view changed');counts={int(k):v for k,v in row['partition']['element_writers'].items()};instances+=len(row['partition']['write_instances']);binary=row['artifacts']['fatbin']['sha256']
  for obj in row['artifacts'].values():need(sha(obj['path'])==obj['sha256'],'Actual frozen GCU compiler object changed')
 else:
  need(meta['arch']=='Ascend910B4-1' and meta['enable_auto_blockify'] is False and meta['parallel_mode']=='simd' and meta['force_simt_only'] is False,'Reviewed Ascend launch ABI differs');bound=row['codegen'];need(sha(bound['file'])==bound['sha256'],'Actual byte-identical codegen receipt changed');need(any(p['whole_binary_identical'] and sha(p['path'])==row['original_npubin_sha256'] for p in bound['proof']['produced']),'Actual original whole binary differs');counts=Counter();binary=row['original_npubin_sha256']
  for part in row['parts']:
   need(sha(part['source_file'])==part['source_sha256'],'Actual actor LLVM input changed');counts.update({int(k):v for k,v in part['partition']['element_writers'].items()})
   for w in part['partition']['write_instances']:
    need(w['source_sizes']==w['sizes'] and w['source_offset']==0 and w['source_byte_address'] is not None and w['source_byte_address']%32==0,'Outside independently reviewed source window');need(w['source_strides'] in ([1],[16,1],[32,1]) and w['strides'][-1]==1 and max(w['sizes'])<=256,'Outside reviewed supplemental transfer dimensions');instances+=1
 need(len(counts)==row['elements'] and all(counts[i]==1 for i in range(row['elements'])),'Physical State writer partition changed');elements+=row['elements'];qualified.append(dict(id=row['id'],math_sha256=row['math_sha256'],binary_sha256=binary,elements=row['elements'],metadata_sha256=row['metadata_sha256'],state_writer_qualified=True,native_timing_boundary_qualified=False))
need(len(qualified)==8 and elements==17140,'Reviewed supplemental State scope differs');summary=dict(status='ordinary_supplementary8_actual_State_writer_under_reviewed_SDK_ABI',backend=contract['backend'],qualified=8,scope='q07/q08 x two shapes x two configurations; retained ordinary calls only',State_write_instances=instances,State_elements=elements,state_writer_qualified=True,SDK_ABI_binding_qualified=True,profile_objects_qualified=False,native_timing_boundary_qualified=False,pipeline_or_whole_goal_qualified=False,device_executed=False,application_replayed=False,contract_sha256=sha(inp/'contract.json'),application_review_sha256=contract['application_review_sha256'],semantics_review_sha256=contract['semantics_review_sha256'],partition_rows_sha256=sha(root/'output/rows.json'),qualification_rows=qualified);(a.output/'result.json').write_text(json.dumps(summary,indent=2))
