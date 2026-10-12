#!/usr/bin/env python3
"""Extract observed measurements without filling missing fields or joining clocks."""
import argparse,collections,csv,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('roots',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
rows=[];native=[];ir=[];inventory=[]
for root in a.roots:
 for f in sorted(root.rglob('result.json')):
  d=json.loads(f.read_text());case=f.parent; identity={'dataset':str(root),'case':str(case.relative_to(root)),'backend':d['backend'],'operator':d['operator'],'shape':'x'.join(map(str,d['shape'])),'variant':d['variant'],'phase':d['phase'],'status':d['status']}
  inventory.append({**identity,'device':d.get('device'),'validation':d.get('validation'),'post_profile_validation':d.get('post_profile_validation'),'error':d.get('error')})
  if d['status']!='passed':continue
  if d['phase']=='baseline':
   for i,sample in enumerate(d.get('samples',[])): rows.append({**identity,'sample':i,**sample})
  for stage,info in d.get('asm',{}).items():
   if stage not in ['ttir','ttgir','gcuir','ttadapter','bcmlir','llir']:continue
   content=(case/info['file']).read_text(errors='replace')
   # MLIR operation names only; no semantic equivalence or dynamic counts inferred.
   if stage=='llir':continue
   names=[]
   for line in content.splitlines():
    line=line.strip()
    if line.startswith('#') or line.startswith('^'):continue
    m=re.match(r'(?:%[^=]+?=\s*)?(?:"([A-Za-z_][\w]*\.[\w]+)"|([A-Za-z_][\w]*\.[\w]+))(?:\s|\()',line)
    if m:names.append(m.group(1) or m.group(2))
   for name,count in sorted(collections.Counter(names).items()): ir.append({**identity,'stage':stage,'operation':name,'static_text_count':count,'ir_sha256':info['sha256']})
  events=case/'profile/ai/events.jsonl'
  if events.exists():
   for line in events.read_text().splitlines():
    e=json.loads(line)
    native.append({**identity,'source':e.get('source',e.get('original_record',{}).get('source')),'kind':e.get('kind'),'name':e.get('name'),'start_ns':e.get('start_ns'),'end_ns':e.get('end_ns'),'duration_us':e.get('duration_us'),'correlation_key':e.get('correlation_key'),'scope_id':e.get('scope_id'),'device_id':e.get('device_id'),'stream_id':e.get('stream_id'),'timing_status':e.get('timing_status')})
  vendor=case/'profile.vendor.json'
  if vendor.exists():
   v=json.loads(vendor.read_text())
   for e in v.get('associations',[]):
    rt=e.get('runtime_event',{});m=e.get('metrics',{})
    native.append({**identity,'source':e.get('source'),'state':e.get('state'),'kind':m.get('activity.kind'),'name':rt.get('op_name'),'start_ns':rt.get('start_time_ns') or None,'end_ns':rt.get('end_time_ns') or None,'duration_us':m.get('task_duration_us'),'start_cycle':m.get('start_cycle'),'end_cycle':m.get('end_cycle'),'duration_cycle':m.get('duration_cycle'),'op_id':m.get('op_id'),'op_name':m.get('mlir_op'),'source_loc':m.get('source_loc'),'reported_count':m.get('count'),'scope_id':rt.get('scope_id'),'device_id':rt.get('device_id'),'stream_id':rt.get('stream_id')})
def write(name,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (a.output/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
write('baseline_samples.csv',rows);write('profile_records.csv',native);write('static_ir_operations.csv',ir)
(a.output/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(json.dumps({'cases':len(inventory),'statuses':dict(collections.Counter(x['status'] for x in inventory)),'baseline_samples':len(rows),'profile_records':len(native),'static_ir_count_rows':len(ir)}))
