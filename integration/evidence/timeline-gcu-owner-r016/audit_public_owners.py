"""Audit actual GCU default raw references and recovery evidence using stdlib."""
import argparse,hashlib,json,struct,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
with tarfile.open(a.archive) as tar:
 def read(name):return tar.extractfile(name).read()
 names={m.name for m in tar.getmembers()}
 roots=['runs/public-timeline-v1/output/api-cold/timeline','runs/public-timeline-v1/output/api-warm/timeline','runs/public-cli-v1/output/capture/timeline','runs/owner-recovery-v1/output/recovered-originals','runs/owner-recovery-v1/output/after-failure/timeline']
 rows=[];all_ids=set();total_refs=0;total_events=0
 for root in roots:
  index=json.loads(read(root+'/index.json'))
  if index['retained_owners'] or index['pending_decode'] or index['failures']:raise RuntimeError('Accepted trace pending or failed')
  for item in index['captures']:
   capture=json.loads(read(root+'/'+item['capture_file']));raw=read(root+'/'+capture['raw_file']);batch=json.loads(read(root+'/'+capture['events_file']))
   digest=hashlib.sha256(raw).hexdigest()
   if digest!=batch['raw_artifact']['sha256'] or len(raw)!=batch['raw_artifact']['bytes'] or not batch['complete']:raise RuntimeError('Raw binding or completeness mismatch')
   if batch['clock_status']!='unverified' or batch['boundary_status']!='unverified':raise RuntimeError('Unproved qualification')
   ids={r['id'] for r in batch['records']}|{e['id'] for e in batch['events']}
   if ids&all_ids:raise RuntimeError('Cross-invocation identity collision')
   all_ids.update(ids)
   for endpoint in batch['records']:
    if endpoint['length']!=8 or struct.unpack_from('<Q',raw,endpoint['offset'])[0]!=endpoint['tick']:raise RuntimeError('Endpoint not actual raw field')
   counts=[sum(e['observer_id']==o['id'] for e in batch['events']) for o in batch['observers']]
   if not all(n>=2 for n in counts):raise RuntimeError('Host-only observer coverage')
   positive=sum(e['end_tick']>e['start_tick'] for e in batch['events'])
   rows.append(dict(root=root,invocation_id=batch['identity']['invocation_id'],raw_sha256=digest,raw_bytes=len(raw),events_per_observer=counts,positive_intervals=positive,endpoints=len(batch['records'])))
   total_refs+=len(batch['records']);total_events+=len(batch['events'])
 if len(rows)!=13 or total_refs!=576 or total_events!=288:raise RuntimeError('Actual default capture counts changed')
 recheck=json.loads(read('runs/cpu-v5-recheck/output/result.json'))
 if recheck['versions']!=[2,2,2,2] or recheck['installed_members_byte_verified']!=450 or any(r['returncode'] for r in recheck['tests']):raise RuntimeError('Independent install/CPU evidence mismatch')
 recovered=json.loads(read('runs/owner-recovery-v1/output/result.json'))
 if recovered['recovery_transport_actions']!=0:raise RuntimeError('Recovery reentered transport')
 for relative,digest in recovered['original_sha256'].items():
  if hashlib.sha256(read('runs/owner-recovery-v1/output/recovered-originals/'+relative)).hexdigest()!=digest:raise RuntimeError('Recovered originals changed')
 for name in ['public-timeline-v1','public-cli-v1','owner-recovery-v1','cpu-v5-recheck']:
  terminal=json.loads(read('runs/'+name+'/terminal.json'))
  if terminal['state']!='terminal' or terminal['returncode']!=0:raise RuntimeError('Job did not terminate successfully')
 statuses=json.loads(read('owned-status-r016-final.json'))
 if any(o['state'] not in ['missing','pid_reused','Z'] for o in statuses['owners']):raise RuntimeError('Selected owned handle live')
 result=dict(status='actual_public_raw_and_ownership_byte_audit_passed_not_full_P01',archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),archive_bytes=a.archive.stat().st_size,archive_members=len(tar.getmembers()),default_captures=len(rows),raw_endpoint_references=total_refs,intervals=total_events,positive_intervals=sum(r['positive_intervals'] for r in rows),selected_owned_handle_checks=len(statuses['owners']),independent_install=recheck,captures=rows,limitations=['No product imported or math replayed on workstation','No clock/epoch, source-boundary, allocation-guard, async reuse, Perfetto or independent-math qualification'])
a.output.write_text(json.dumps(result,indent=2)+'\n')
