"""CPU-only lossless closure of the registered 15+21 over-budget bundles."""
import argparse,hashlib,json,shutil,time
from pathlib import Path
from flagtree.profiler import bundle_metadata as module
from flagtree.profiler import _report as report_module
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
limit=64*1024*1024
registrations=[]
for label,root,total,failed in [('original-six','/tmp/chijin-timeline-r052-qualification-profile-v1',72,15),('supplement-two','/tmp/chijin-timeline-r054-supplement-profile-v1',24,21)]:
 index=Path(root)/'runs/profile-first-v1/profile-attempts.json';data=json.loads(index.read_text());rows=data['results']
 if len(rows)!=total:raise RuntimeError('Changed registered denominator')
 selected=[r for r in rows if r['artifacts']['bundle_bytes']>limit]
 if len(selected)!=failed:raise RuntimeError('Changed original budget-failure denominator')
 for r in selected:registrations.append(dict(group=label,id=r['id'],source=str(Path(r['directory'])/'capture'),registered_bytes=r['artifacts']['bundle_bytes'],index=str(index),index_sha256=sha(index)))
(a.output/'registrations.json').write_text(json.dumps(registrations,indent=2))
required=sum(sum(p.stat().st_size for p in Path(r['source']).rglob('*') if p.is_file()) for r in registrations)
if shutil.disk_usage(a.output).free < required+256*1024*1024:raise RuntimeError('Insufficient free space for retained copies')
results=[]
for number,row in enumerate(registrations):
 source=Path(row['source']);target=a.output/'retained'/row['group']/(str(number)+'-'+source.parent.name)
 if any(p.is_symlink() for p in source.rglob('*')):raise RuntimeError('Unexpected symlink in retained bundle')
 before={str(p.relative_to(source)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in source.rglob('*') if p.is_file()}
 shutil.copytree(source,target)
 original={name:module.load_bundle_json(target,name) for name in module.FILES}
 module.compact_timeline_metadata(target)
 for name,value in original.items():
  if module.load_bundle_json(target,name)!=value:raise RuntimeError('Logical metadata changed: '+name)
 report_module.write_manifest(target,original['report/report.json'])
 allowed={'manifest.json','ai/binaries.json','report/report.json'}
 after={str(p.relative_to(target)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in target.rglob('*') if p.is_file()}
 if set(before)-set(after) or set(after)-set(before) not in (set(),{module.CATALOG}):raise RuntimeError('Unexpected compaction file inventory change')
 for name,value in before.items():
  if name not in allowed and after[name]!=value:raise RuntimeError('Original evidence modified: '+name)
  if sha(source/name)!=value['sha256']:raise RuntimeError('Source original modified')
 size=sum(v['bytes'] for v in after.values());item=dict(row,number=number,original_bytes=sum(v['bytes'] for v in before.values()),compact_bytes=size,budget_bytes=limit,within_budget=size<=limit,logical_metadata_equal=True,unchanged_files=len(before)-len(allowed),originals_unchanged=True,device_executed=False,application_replayed=False)
 ledger=a.output/'ledgers';ledger.mkdir(exist_ok=True);(ledger/(str(number)+'.json')).write_text(json.dumps(dict(before=before,after=after),sort_keys=True))
 results.append(item);(a.output/'result.json').write_text(json.dumps(dict(status='in_progress',registered_count=len(registrations),completed=len(results),results=results),indent=2));print(json.dumps(item),flush=True)
summary=dict(status='registered_budget_failures_losslessly_compacted' if all(r['within_budget'] for r in results) else 'retained_budget_failures_remain',registered_count=len(registrations),completed=len(results),within_budget=sum(r['within_budget'] for r in results),max_compact_bytes=max(r['compact_bytes'] for r in results),original_first_attempt_failures_preserved=True,device_executed=False,application_replayed=False,results=results)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if summary['within_budget']!=36:raise RuntimeError('Some registered original budget failures remain')
