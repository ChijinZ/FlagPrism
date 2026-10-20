from pathlib import Path
import argparse,subprocess,json,hashlib,shutil
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);source=Path(__file__).parent/'source';steps=[]
def run(name,argv,timeout=60):
 with (a.output/(name+'.log')).open('xb') as log:c=subprocess.run([str(x) for x in argv],stdout=log,stderr=log,stdin=subprocess.DEVNULL,timeout=timeout)
 steps.append(dict(name=name,argv=[str(x) for x in argv],returncode=c.returncode));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if c.returncode:raise RuntimeError(name+' failed')
config=shutil.which('llvm-config-15')
if not config:raise RuntimeError('Missing upstream LLVM15 development package')
cmake=subprocess.check_output([config,'--cmakedir'],text=True).strip()
formatter=shutil.which('clang-format-15') or shutil.which('clang-format')
if formatter:run('format',[formatter,'-i',source/'AscendExecutionStructure.cpp'])
run('configure',['cmake','-S',source,'-B',a.output/'build','-G','Ninja','-DLLVM_DIR='+cmake,'-DCMAKE_BUILD_TYPE=Release'])
run('build',['cmake','--build',a.output/'build','--target','flagprism-ascend-structure','-j','2'],90)
tool=a.output/'build/flagprism-ascend-structure'
for label,flags in [('normal',[]),('optimized',['-O'])]:run('native-fixtures-'+label,[__import__('sys').executable,'-I',*flags,Path(__file__).parent/'fixtures.py','--tool',tool,'--output',a.output/('fixtures-'+label)])
objects=json.loads(Path('/tmp/chijin-timeline-r091-ascend/runs/source-loop-inventory-v1/output/objects.json').read_text());results=[]
for k in ('q01','q03','q05'):
 obj=next(x for x in objects if x['first_case'].startswith(k))
 for actor in obj['actor_inputs']:
  path=Path(actor['path']);name=k+'-'+actor['actor_kind'];run(name,[tool,path]);data=json.loads((a.output/(name+'.log')).read_text());actual=hashlib.sha256(path.read_bytes()).hexdigest()
  if data['input_sha256']!=actual or actual!=actor['sha256']:raise ValueError('Actor identity differs')
  results.append(dict(case=obj['first_case'],actor=actor['actor_kind'],input_sha256=actual,index_sha256=hashlib.sha256((a.output/(name+'.log')).read_bytes()).hexdigest(),functions=len(data['functions']),blocks=sum(len(f['blocks']) for f in data['functions']),instructions=sum(len(b['instructions']) for f in data['functions'] for b in f['blocks']),loops=sum(len(f['loops']) for f in data['functions'])))
(a.output/'result.json').write_text(json.dumps(dict(status='read_only_actor_structure_indexed',tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((source/'AscendExecutionStructure.cpp').read_bytes()).hexdigest(),actual=results,device_executed=False,SDK_recompiled=False,source_loop_qualified=False),indent=2))
