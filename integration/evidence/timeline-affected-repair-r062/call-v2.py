"""One original registered affected call; no mathematical implementation here."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);root=Path('/tmp/chijin-timeline-r062-ascend');prepare=root/'runs/prepare-v1/output';registration=json.loads((prepare/'registration-v2.json').read_text());index=int(a.output.parent.name);call=registration['calls'][index];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
 with (a.output/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True)
if sha(__file__) != registration['verifier_script_sha256']:raise RuntimeError('Bound repaired verifier script changed')
if sha(prepare/'product-freeze.json')!=registration['product_freeze_sha256'] or sha(call['registration_file'])!=call['registration_sha256'] or sha(call['ordinary']['file'])!=call['ordinary']['sha256']:raise RuntimeError('Original registration/ordinary/product freeze changed')
helper=Path('/tmp/chijin-timeline-r052-private/input-v2/matrix.py');spec=importlib.util.spec_from_file_location('original_matrix',helper);matrix=importlib.util.module_from_spec(spec);spec.loader.exec_module(matrix);matrix.check_prepare();matrix.verify_product_freeze(prepare/'product-freeze.json','ascend')
if call['phase']!='cold':
 previous=root/'runs'/f'{index-1:03d}'/'output/result.json'
 if not previous.exists():previous=previous.with_name('result-v2-retained.json')
 if not previous.is_file() or json.loads(previous.read_text())['status']!='affected_registered_call_passed':raise RuntimeError('Previous cold/warm call has no success receipt; do not implicitly retry')
source=Path(call['source']);manifest=source/('prepare_manifest.json' if call['case']!='q08' else 'prepare-manifest.json');expected=json.loads(manifest.read_text())
for name,digest in expected['files_sha256'].items():
 if sha(source/name)!=digest:raise RuntimeError('Original application source changed')
cache=root/'cache'/call['id']
if call['phase']=='cold' and cache.exists():raise RuntimeError('Cold cache already exists')
cache.mkdir(parents=True,exist_ok=True);freeze=json.loads((prepare/'product-freeze.json').read_text());env=dict(os.environ,**freeze['environment'],TRITON_CACHE_DIR=str(cache));env.pop('PYTHONPATH',None);tmp=a.output/'tmp';tmp.mkdir();env['TMPDIR']=str(tmp)
command=[sys.executable,'-m','flagtree.profiler.cli','--backend','cann','--detail','timeline','--device','4','--compile-timeout',str(call['compile_budget']),'--export-timeout','60','-n',str(a.output/'capture'),str(source/'launch.py'),'--backend','ascend']
if call['case']!='q08':command+=['--torch-device','npu:4']
command+=['--case',call['case'],'--shape',str(call['shape']),'--config',str(call['config'])]
if call['case']!='q08':command+=['--runtime-k','3']
command+=['--result',str(a.output/'math.json')];started=time.monotonic_ns()
with (a.output/'application.stdout').open('xb') as out,(a.output/'application.stderr').open('xb') as err:
 child=subprocess.Popen(command,env=env,stdout=out,stderr=err,start_new_session=True);f=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split();owner=dict(argv=command,pid=child.pid,pgid=int(f[2]),startticks=int(f[19]),script_sha256=sha(__file__),registration_sha256=sha(prepare/'registration-v2.json'),registered_call=call,device='npu:4',application_wait_seconds=260);save('application-owner.json',owner)
 try:code=child.wait(timeout=260)
 except subprocess.TimeoutExpired:
  deadline=Path('/tmp/chijin-timeline-r019/input/Profiler/python/flagtree_profiler/_deadline.py');spec=importlib.util.spec_from_file_location('owned_cleanup',deadline);cleanup=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cleanup;spec.loader.exec_module(cleanup);cleanup._stop_worker(child);save('application-terminal.json',dict(owner,returncode=child.returncode,outcome='timeout_not_completion_proof'));raise
save('application-terminal.json',dict(owner,returncode=code,wall_ns=time.monotonic_ns()-started))
if code:raise RuntimeError('Actual registered CLI failed; originals and not-started denominator preserved')
report=json.loads((a.output/'math.json').read_text());reference=json.loads(Path(call['ordinary']['file']).read_text());fields=['shape','config','input_sha256','source_sha256']+(['runtime_k'] if call['case']!='q08' else [])
if not all(report[k]==reference[k] for k in fields):raise RuntimeError('Original math/input/config reference differs')
if len(list(a.output.glob('*.host-once.json')))!=1:raise RuntimeError('Host-once receipt count differs')
spec=importlib.util.spec_from_file_location('old_capture_summary',Path('/tmp/chijin-timeline-r055-qualification-ascend-v2/driver.py'));summary=importlib.util.module_from_spec(spec);spec.loader.exec_module(summary);artifacts=summary.capture_summary(a.output);timeline=a.output/'capture/timeline';catalog=json.loads((timeline/'index.json').read_text())
if len(catalog['captures'])!=1 or catalog.get('retained_owners') or catalog.get('pending_decode') or catalog.get('failures'):raise RuntimeError('Actual public capture is not finalized/complete')
if artifacts['bundle_bytes']>67108864 or sum(r['bytes'] for r in artifacts['trace_files'])>16777216:raise RuntimeError('Frozen bundle/trace budget exceeded')
checks=[]
for item in catalog['captures']:
 cap=json.loads((timeline/item['capture_file']).read_text());batch=json.loads((timeline/cap['events_file']).read_text());sites={s['id']:s for s in batch['sites']};positive={e['site_id'] for e in batch['events'] if e['kind']=='interval' and e['end_tick']>e['start_tick'] and 'ascend.native_operation' not in sites[e['site_id']]['attributes']}
 if not batch['complete'] or len(positive)<2 or not cap.get('counter_ns_exports'):raise RuntimeError('Actual default capture lacks complete multi-source positive intervals/ns')
 guard=cap['readback_guard']
 if (timeline/guard['file']).read_bytes()!=bytes([165])*128:raise RuntimeError('Actual device allocation guard changed')
 if (timeline/cap['raw_file']).stat().st_size+128>8388608:raise RuntimeError('Frozen raw+guard budget exceeded')
 checks.append(dict(invocation_id=item['invocation_id'],capture_file=item['capture_file'],capture_sha256=sha(timeline/item['capture_file']),raw_sha256=cap['raw_sha256'],canonical_complete=batch['complete'],positive_source_sites=sorted(positive),observer_count=len(batch['observers']),ns_exports=len(cap['counter_ns_exports'])))
primary={str((timeline/item['capture_file']).resolve()) for item in catalog['captures']}
artifacts['auxiliary_input_snapshots_excluded']=len([c for c in artifacts['captures'] if str(Path(c['metadata']).resolve()) not in primary])
artifacts['captures']=[c for c in artifacts['captures'] if str(Path(c['metadata']).resolve()) in primary]
if len(artifacts['captures'])!=len(primary):raise RuntimeError('Indexed actual capture missing from original summary')
if any(not c['raw_sha256_matches'] or not c['observed_range_loss_free'] or c['unknown_reserved_slot_count'] or c['missing_selected_positive_writer_programs'] for c in artifacts['captures']):raise RuntimeError('Original observed/default selection/raw checks failed')
save('result.json',dict(status='affected_registered_call_passed',registered_call=call,math_input_config_matches=True,host_once=True,checks=checks,artifacts=artifacts,source_boundary_qualified=False,SQL_UI_qualification_inferred=False,old_partial_files_unchanged=True))
