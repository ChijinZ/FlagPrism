import argparse,ast,copy,hashlib,importlib.util,json,runpy,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);s=Path(__file__).parent/'source';steps=[]
def run(name,cmd):
 with (a.output/(name+'.log')).open('xb') as log:cp=subprocess.run([str(x) for x in cmd],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 steps.append(dict(name=name,argv=[str(x) for x in cmd],returncode=cp.returncode));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if cp.returncode:raise ValueError(name+' failed')
subprocess.run(['git','init','-q'],cwd=s,check=True,timeout=10)
files=['Profiler/python/flagtree_profiler/timeline_events_enflame_native.py','tests/timeline/test_enflame_source_members.py','Debugger/python/flagtree_debugger/gcu_llvm_regions.py','Debugger/test/gcu_llvm_regions.py','Debugger/test/gcu_execution_origins.py']
before={n:ast.dump(ast.parse((s/n).read_text()),include_attributes=False) for n in files}
for hook in ('ruff','yapf','check-ast'):
 for i in range(2):
  cp=subprocess.run(['/tmp/chijin-usability-r6-recipe-tests/format-venv/bin/pre-commit','run',hook,'--files',*files],cwd=s,capture_output=True,timeout=60);(a.output/(hook+'-'+str(i)+'.log')).write_bytes(cp.stdout+cp.stderr)
  if i==1 and cp.returncode:raise ValueError('Formatting failed '+hook)
for n in files:
 if ast.dump(ast.parse((s/n).read_text()),include_attributes=False)!=before[n]:raise ValueError('Formatting changed AST '+n)
for name in ['Debugger/lib/Instrumentation/GcuTimeline.cpp','Debugger/include/Debugger/Instrumentation/GcuTimeline.h','Debugger/tools/gcu-timeline/main.cpp']:
 (s/name).write_bytes((Path('/tmp/chijin-timeline-r097-gcu/origins-input-v4/source')/name).read_bytes())
fixture=Path(__file__).parent/'fixture_runner.py'
fixture.write_text("import importlib.util,runpy,sys\nfrom pathlib import Path\ns=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('flagtree.profiler.timeline_events_enflame_native',s/'Profiler/python/flagtree_profiler/timeline_events_enflame_native.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);sys.argv=[str(s/'tests/timeline/test_enflame_source_members.py')];runpy.run_path(sys.argv[0],run_name='__main__')\n")
for label,flags in [('normal',[]),('optimized',['-O'])]:run('navigation-'+label,[sys.executable,'-I',*flags,fixture,s])
from flagtree.profiler.timeline_events_enflame_native import decode_execution_capture as olddecode
spec=importlib.util.spec_from_file_location('flagtree.profiler.timeline_events_enflame_native',s/'Profiler/python/flagtree_profiler/timeline_events_enflame_native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
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
 rows.append(dict(object_index=n,body_site=body,capture_sha256=hashlib.sha256(cap_bytes).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),source_locations=locations,source_op_ids=site['attributes']['enflame.source_member_op_ids'],events=len(batch['events']),records=len(batch['records']),original_unchanged=True,timing_and_runtime_data_unchanged=True,legacy_output_equal=True))
(a.output/'result.json').write_text(json.dumps(dict(status='source_navigation_real_raw_and_legacy_compatibility_checked',source_sha256=hashlib.sha256((s/files[0]).read_bytes()).hexdigest(),objects=rows,device_executed=False,steps=steps),indent=2))
