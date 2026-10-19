import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from collections import Counter
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
source=Path('/workspace/chijin-timeline-r061-nvidia/compute-install-input-v1/source');env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0',CUDA_VISIBLE_DEVICES='0',TRITON_CACHE_DIR=str(a.output/'cache'),TMPDIR=str(a.output/'tmp'));(a.output/'tmp').mkdir();env.pop('PYTHONPATH',None);steps=[]
cmd=[sys.executable,'-I',str(source/'tests/timeline/p01_review_recovery.py'),'--backend','nvidia','--device','0','--output',str(a.output/'device')]
with (a.output/'device.log').open('xb') as log:
 c=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();steps.append(dict(argv=cmd,pid=c.pid,startticks=int(f[19])));(a.output/'steps.json').write_text(json.dumps(steps));steps[0]['returncode']=c.wait(timeout=180);(a.output/'steps.json').write_text(json.dumps(steps))
if steps[0]['returncode']:raise RuntimeError('Real C1 functional run failed')
from flagtree.profiler import timeline_unit_nvidia_late as units
from flagtree.profiler import timeline_nvidia_late_boundaries as boundaries
def inspect(root,before):
 hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()};rows=[]
 for item in json.loads((root/'index.json').read_text())['captures']:
  cap=json.loads((root/item['capture_file']).read_text());plan=cap['owner']['plan'];bid=cap['owner']['binary_id'];machine=units.load_late_machine_map(root,cap);base=root/'machine'/bid;ptxrow=next(r for r in cap['metadata']['timeline_artifacts'] if r['retained_file'].endswith('.ptx'));ptx=(root/ptxrow['retained_file']).read_bytes()
  report=boundaries.derive_native_boundaries(machine_map=machine,sass_lines=(base/'lines.stdout').read_bytes(),sass_json=(base/'json.stdout').read_bytes(),ptx=ptx,plan=plan)
  loop_sites=[s for s in plan['sites'] if s['kind']=='compute_issue_bracket' and s['member_count']==2]
  if len(loop_sites)!=1:raise RuntimeError('Expected retained two-operation recurrence source group')
  site=loop_sites[0]['site_id'];entry=next(r for r in report['source_issue_sites'] if r['site_id']==site)
  if before:
   if entry['status']!='unverified':raise RuntimeError('Historical empty compute bracket incorrectly accepted')
  else:
   if plan.get('compute_operand_fence_version')!=1 or entry['status']!='source_issue_control_order_checked' or entry['native_opcode']!='FFMA' or not entry['begin_reader_pc']<entry['native_pc']<entry['end_reader_pc']:raise RuntimeError('Loaded release object does not bracket actual recurrence FMA: '+str(entry))
   if b', debug' in ptx or b'debug,' in ptx:raise RuntimeError('Device executable used debug PTX')
  batch=json.loads((root/cap['events_file']).read_text());canonical_site=next(s['id'] for s in batch['sites'] if s['backend_site_id']==str(site));counts=Counter(e['observer_id'] for e in batch['events'] if e['site_id']==canonical_site and e['kind']=='interval')
  if not before and (not batch['complete'] or not counts or any(n!=3 for n in counts.values())):raise RuntimeError('Actual three-step runtime loop interval sequence incomplete: '+str(counts))
  rows.append(dict(invocation_id=item['invocation_id'],binary_id=bid,capture_file=item['capture_file'],capture_sha256=hashes[item['capture_file']],loop_site_id=site,loop_intervals_per_observer=dict(counts),source_issue_report=report,old_empty_bracket_rejected=before,PTX_sha256=hashlib.sha256(ptx).hexdigest(),machine_map=machine))
 if hashes!={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}:raise RuntimeError('Retained files mutated')
 return dict(root=str(root),original_files_unchanged=len(hashes),captures=rows)
old=inspect(Path('/workspace/chijin-timeline-r058-nvidia/runs/device-recovery-v1/output/device/resume/timeline'),True);new=inspect(a.output/'device/resume/timeline',False)
(a.output/'result.json').write_text(json.dumps(dict(status='loaded_release_C1_FMA_bracket_and_runtime_loop_regression_passed_not_source_exclusive_cost',math=json.loads((a.output/'device/result.json').read_text()),old=old,new=new,performance_measured=False),indent=2))
