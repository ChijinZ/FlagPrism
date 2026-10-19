"""Finish current compact report rendering on already losslessly compacted copies."""
import argparse,hashlib,json
from pathlib import Path
from flagtree.profiler import bundle_metadata as module
from flagtree.profiler import _report as reports,execution_view
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=Path('/tmp/chijin-timeline-r076-gcu/runs/budget-closure-v3/output');previous=json.loads((base/'result.json').read_text());rows=[]
if previous['completed']!=36:raise RuntimeError('Incomplete metadata compaction predecessor')
for row in previous['results']:
 number=row['number'];source=Path(row['source']);target=base/'retained'/row['group']/(str(number)+'-'+source.parent.name)
 ledger=json.loads((base/'ledgers'/(str(number)+'.json')).read_text())
 for name,value in ledger['after'].items():
  if sha(target/name)!=value['sha256']:raise RuntimeError('Predecessor copy changed')
 original={name:module.load_bundle_json(target,name) for name in module.FILES}
 reports.write_timeline_page(target);execution_view.write_view(target,{},compact_html=True)
 reports.write_manifest(target,original['report/report.json'])
 after={str(p.relative_to(target)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in target.rglob('*') if p.is_file()}
 if set(after)!=set(ledger['after']):raise RuntimeError('Report refresh changed inventory')
 allowed={'report/index.html','report/execution.html','manifest.json'}
 for name,value in ledger['after'].items():
  if name not in allowed and after[name]!=value:raise RuntimeError('Report refresh changed evidence')
 for name,value in original.items():
  if module.load_bundle_json(target,name)!=value:raise RuntimeError('Report refresh changed logical metadata')
 for name,value in ledger['before'].items():
  if sha(source/name)!=value['sha256']:raise RuntimeError('Original evidence changed')
 size=sum(v['bytes'] for v in after.values());item=dict(row,compact_bytes=size,within_budget=size<=64*1024*1024,metadata_compaction_predecessor=str(base/'result.json'),metadata_compaction_predecessor_sha256=sha(base/'result.json'),current_report_renderer_used=True,retained=str(target))
 d=a.output/'ledgers';d.mkdir(exist_ok=True);(d/(str(number)+'.json')).write_text(json.dumps(dict(before=ledger['after'],after=after),sort_keys=True))
 pages=a.output/'pages'/str(number);pages.mkdir(parents=True)
 for name in ['index.html','execution.html']:(pages/name).write_bytes((target/'report'/name).read_bytes())
 rows.append(item);(a.output/'result.json').write_text(json.dumps(dict(status='in_progress',completed=len(rows),results=rows),indent=2))
summary=dict(status='all_36_registered_budget_failures_losslessly_recovered_with_current_report_rendering' if all(r['within_budget'] for r in rows) else 'some_registered_budget_failures_remain',completed=len(rows),registered_count=36,within_budget=sum(r['within_budget'] for r in rows),max_compact_bytes=max(r['compact_bytes'] for r in rows),original_first_attempt_failures_preserved=True,device_executed=False,application_replayed=False,results=rows)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if summary['within_budget']!=36:raise RuntimeError('Budget failures remain after current full report compaction')
