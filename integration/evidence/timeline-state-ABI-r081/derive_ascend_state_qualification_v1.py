"""Derive a scoped sidecar from unchanged checked original receipts and reviewed SDK ABI."""
import argparse, hashlib, json
from pathlib import Path
from collections import Counter
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inputs=Path(__file__).parent

def need(value,message):
 if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
contract=json.loads((inputs/'contract.json').read_bytes())
for entry in contract['resources']:
 need(sha(Path(entry['path']))==entry['sha256'],'Reviewed SDK/receipt resource changed: '+entry['path'])
review=inputs/'ABI-review.md';need(sha(review)==contract['review_sha256'],'Independent SDK ABI review changed')
root=Path('/tmp/chijin-timeline-r081-ascend/runs/state-partition-v1');need(json.loads((root/'terminal.json').read_bytes())['returncode']==0,'Original partition execution failed');result=json.loads((root/'output/result.json').read_bytes());need(result['checked']==result['registered']==result['partitioned']==32,'Partition registration differs')
wrapper=json.loads((inputs/'wrappers.json').read_bytes());need(len(wrapper['rows'])==20 and len(wrapper['definitions'])==2,'Reviewed wrapper scope differs')
for entry in wrapper['rows']:
 need(sha(Path(entry['source_path']))==entry['source_sha256'],'Actual original codegen LLVM changed')
 text=Path(entry['source_path']).read_text();body=wrapper['definitions'][entry['wrapper_sha256']]
 need(hashlib.sha256(body.encode()).hexdigest()==entry['wrapper_sha256'] and text.count(body)==1,'Actual descriptor wrapper changed')
 need(entry['meta_op'] and all(m['sha256']=='d5c10fbdcb1a976e888a2ddb2bcccd0b66febc10e959e044d141ad2760b63fa0' for m in entry['meta_op']),'Reviewed original library differs')
rows=json.loads((root/'output/rows.json').read_bytes());qualified=[];instances=0;empty=0
for row in rows:
 need(row['status']=='partition_under_inspected_transfer_and_actor_ABI_model','Original partition unverified');need(sha(Path(row['math_file']))==row['math_sha256'],'Original math receipt changed');counts=Counter()
 for part in row['parts']:
  counts.update({int(k):v for k,v in part['partition']['element_writers'].items()})
  for item in part['partition']['write_instances']:
   sizes=item['sizes'];need(item['source_sizes']==sizes and item['source_offset']==0 and item['source_byte_address'] is not None and item['source_byte_address']%32==0,'Outside reviewed source descriptor model');need(item['source_strides']==([1] if len(sizes)==1 else [32,1]),'Outside reviewed source row strides');need(len(sizes) in (1,2) and max(sizes)<=256 and (len(sizes)==1 or sizes[1]<=32),'Outside reviewed finite transfer sizes');need(item['strides'][-1]==1,'Outside reviewed contiguous destination dimension');instances+=1;empty+=int(0 in sizes)
 need(len(counts)==row['elements'] and all(counts[i]==1 for i in range(row['elements'])),'Actual physical element partitions overlap or omit')
 need(any(w['npubin_sha256']==row['npubin_sha256'] for w in wrapper['rows']),'Original byte-bound binary absent')
 qualified.append(dict(id=row['id'],variant=row['variant'],math_sha256=row['math_sha256'],npubin_sha256=row['npubin_sha256'],launch_metadata_sha256=row['launch_metadata_sha256'],elements=row['elements'],state_writer_qualified=True))
need(len(qualified)==32,'Scope must remain original 32 ordinary reports')
summary=dict(status='ordinary32_actual_State_physical_writer_qualification',qualified=len(qualified),transfer_instances=instances,zero_extent_noop_instances=empty,state_writer_qualified=True,scope='original ordinary 24 primary plus 8 runtime-K reports only',profile_objects_qualified=False,supplemental_objects_qualified=False,whole_goal_qualified=False,device_executed=False,mathematical_application_replayed=False,review_sha256=sha(review),contract_sha256=sha(inputs/'contract.json'),original_partition_rows_sha256=sha(root/'output/rows.json'),qualification_rows=qualified)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
