import argparse,copy,hashlib,importlib.util,json,sys
from pathlib import Path
from flagtree.profiler import timeline_events_enflame_native as m
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);steps=[]
spec=importlib.util.spec_from_file_location('flagtree.profiler.old_enflame_native','/tmp/chijin-timeline-r096-gcu/runs/normal-install-v1/output/venv/lib/python3.12/site-packages/flagtree/profiler/timeline_events_enflame_native.py');oldmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldmodule);olddecode=oldmodule.decode_execution_capture
objects=json.loads((Path(__file__).parent/'objects.json').read_text());rows=[]
for n,body in ((0,24),(4,26)):
 cap_path=Path(objects[n]['capture_file']);cap_bytes=cap_path.read_bytes();cap=json.loads(cap_bytes);meta=cap['metadata']['compiler_metadata'];root=cap_path.parent.parent;raw_path=root/cap['raw_file'];raw=raw_path.read_bytes();events=json.loads((root/cap['events_file']).read_text());kwargs=dict(compiler_metadata=meta,identity=events['identity'],association=cap['launch'],grid=cap['owner']['layout']['grid'])
 old=olddecode(raw,**kwargs);plain=m.decode_execution_capture(raw,**kwargs)
 if plain!=old:raise ValueError('Legacy no-membership output changed')
 origins=json.loads(Path('/tmp/chijin-timeline-r097-gcu/runs/origins-v4/output/'+str(n)+'.origins.json').read_text());enriched=copy.deepcopy(meta)
 for original,new in zip(enriched['debug_execution_manifest']['sites'],origins['sites']):
  if any(original[k]!=new[k] for k in ('id','kind','operation','location')):raise ValueError('Site identity differs')
  original['source_membership']=new['source_membership']
 new=m.decode_execution_capture(raw,**dict(kwargs,compiler_metadata=enriched));batch=new['canonical'];oldbatch=old['canonical']
 if new['commands']!=old['commands'] or any(batch[k]!=oldbatch[k] for k in batch if k not in ('sources','sites')):raise ValueError('Source navigation changed timing or runtime data')
 site=next(x for x in batch['sites'] if x['backend_site_id']==str(body));sources={x['id']:x for x in batch['sources']};locations=[sources[k]['location'] for k in site['source_ids']]
 if len(locations)<3 or locations[0]!='loc(unknown)' or site['attributes']['enflame.source_cost_verified']:raise ValueError('Missing original fusion navigation')
 if cap_path.read_bytes()!=cap_bytes or raw_path.read_bytes()!=raw:raise ValueError('Original artifact changed')
 from flagtree.profiler.timeline_unit_enflame import load_counter_unit_proofs
 from flagtree.profiler.timeline_views import derive_counter_ns_views
 from flagtree.profiler.timeline_perfetto import encode_counter_trace
 proofs=load_counter_unit_proofs(root,cap,batch);views=derive_counter_ns_views(batch,proofs);trace_paths=[]
 for view,proof in zip(views,proofs):
  trace=encode_counter_trace(view,batch,proof=proof)
  if json.dumps(locations,ensure_ascii=False,separators=(',',':')).encode() not in trace:raise ValueError('Perfetto trace lost actual member source annotation')
  target=a.output/(str(n)+'-'+proof.observer_id+'.pftrace');target.write_bytes(trace);trace_paths.append(dict(path=str(target),sha256=hashlib.sha256(trace).hexdigest(),bytes=len(trace)))
 if not trace_paths:raise ValueError('No actual clock proof / Perfetto trace')
 rows.append(dict(perfetto_traces=trace_paths,object_index=n,body_site=body,capture_sha256=hashlib.sha256(cap_bytes).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),source_locations=locations,source_op_ids=site['attributes']['enflame.source_member_op_ids'],events=len(batch['events']),records=len(batch['records']),original_unchanged=True,timing_and_runtime_data_unchanged=True,legacy_output_equal=True))
(a.output/'result.json').write_text(json.dumps(dict(status='source_navigation_real_raw_and_legacy_compatibility_checked',source_sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest(),objects=rows,device_executed=False,steps=steps),indent=2))

import zipfile
installed=Path(m.__file__).parents[2];root_install=Path('/tmp/chijin-timeline-r097-gcu/runs/normal-install-v1/output');wheel=next((root_install/'wheel/dist').glob('*.whl'));checked=0
with zipfile.ZipFile(wheel) as archive:
 for name in archive.namelist():
  if name.startswith(('flagtree/','triton/')) and not name.endswith('/'):
   if (installed/name).read_bytes()!=archive.read(name):raise ValueError('Installed wheel member differs '+name)
   checked+=1
native=root_install/'native/flagtree/debugger/_bin/gcu-timeline'
if hashlib.sha256(native.read_bytes()).hexdigest()!='374ab5f9fd07e2c5c7e8ec32f82365fa5c98e5736fd36648b3ee96b7263bf8d4':raise ValueError('Installed native differs')
result=json.loads((a.output/'result.json').read_text());result.update(installed_members=checked,source_commit='726ab3176c74881c92d5098a8de490f49feb21a4',installed_module=str(m.__file__),installed_native_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),install_controller_original_returncode=1,install_controller_failure='actual verification expected unescaped locations instead of JSON array; product unchanged; followup runs actual verifier only')
(a.output/'result.json').write_text(json.dumps(result,indent=2))
