import argparse,hashlib,json,subprocess,sys,importlib.util,copy
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);s=Path(__file__).parent/'source';steps=[]
def run(name,cmd,timeout=60):
 with (a.output/(name+'.log')).open('xb') as log:cp=subprocess.run([str(x) for x in cmd],stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 steps.append(dict(name=name,argv=[str(x) for x in cmd],returncode=cp.returncode));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if cp.returncode:raise ValueError(name+' failed')
subprocess.run(['git','init','-q'],cwd=s,check=True,timeout=10)
cpp=['Debugger/lib/Instrumentation/GcuTimeline.cpp','Debugger/include/Debugger/Instrumentation/GcuTimeline.h','Debugger/tools/gcu-timeline/main.cpp']
for i in range(2):
 cp=subprocess.run(['/tmp/chijin-usability-r6-recipe-tests/format-venv/bin/pre-commit','run','clang-format','--files',*cpp],cwd=s,capture_output=True,timeout=40);(a.output/('format-'+str(i)+'.log')).write_bytes(cp.stdout+cp.stderr)
 if i==1 and cp.returncode:raise ValueError('Formatting incomplete')
build=a.output/'build';run('configure',['cmake','-S',s/'Debugger/tools/gcu-timeline','-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DMLIR_DIR=/opt/flagtree-llvm/llvm-fc83c68-gcc9-x64/lib/cmake/mlir']);run('build',['cmake','--build',build,'--target','flagprism-gcu-timeline','--parallel','2'],120);tool=build/'flagprism-gcu-timeline'
for label,flags in [('normal',[]),('optimized',['-O'])]:
 run('origin-fixtures-'+label,[sys.executable,'-I',*flags,s/'Debugger/test/gcu_execution_origins.py','--tool',tool,'--output',a.output/('origins-'+label)])
 run('preservation-'+label,[sys.executable,'-I',*flags,s/'Debugger/test/gcu_execution_preservation.py','--tool',tool])
 run('region-fixtures-'+label,[sys.executable,'-I',*flags,s/'Debugger/test/gcu_llvm_regions.py','--module',s/'Debugger/python/flagtree_debugger/gcu_llvm_regions.py','--tool',tool,'--output',a.output/('regions-'+label)])
f=s/'Debugger/python/flagtree_debugger/gcu_llvm_regions.py';sp=importlib.util.spec_from_file_location('regions',f);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
objects=json.loads((Path(__file__).parent/'objects.json').read_text());registry=json.loads(Path('/tmp/chijin-timeline-r088-gcu/runs/source-partition-v2/output/actual-partition/rows.json').read_text());summaries=[]
for n in (0,4):
 obj=objects[n];cap_path=Path(obj['capture_file']);data=cap_path.read_bytes();cap=json.loads(data);meta=cap['metadata']['compiler_metadata'];original=meta['debug_execution_manifest'];row=next(x for x in registry if x['capture_file']==obj['capture_file']);before=Path(row['original_before_file']);raw=before.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=meta['debug_execution_input_sha256']:raise ValueError('Original input identity differs')
 output=a.output/(str(n)+'.origins.json');run('actual-origins-'+str(n),[tool,'--execution-origins',before,output,str(original['selected_source_regions'])]);origins=json.loads(output.read_text());fields=('id','kind','operation','location')
 if [tuple(x[k] for k in fields) for x in origins['sites']]!=[tuple(x[k] for k in fields) for x in original['sites']]:raise ValueError('Original site identity/order differs')
 enriched=copy.deepcopy(original)
 for old,new in zip(enriched['sites'],origins['sites']):old['source_membership']=new['source_membership']
 graph=Path('/tmp/chijin-timeline-r096-gcu/runs/regions-v1/output')/(str(n)+'.structure.json');report=m.analyze_regions(json.loads(graph.read_text()),enriched);(a.output/(str(n)+'.regions.json')).write_text(json.dumps(report,indent=2))
 summaries.append(dict(object_index=n,capture_sha256=hashlib.sha256(data).hexdigest(),before_sha256=hashlib.sha256(raw).hexdigest(),original_unchanged=cap_path.read_bytes()==data,regions=[dict(site_id=x['site_id'],status=x['status'],reason=x.get('reason'),source_membership=x.get('source_membership'),loop=x.get('loop')) for x in report['regions']]))
(a.output/'result.json').write_text(json.dumps(dict(status='actual_original_membership_and_loop_inspected',source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),objects=summaries,device_executed=False),indent=2))
