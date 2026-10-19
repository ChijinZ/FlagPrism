import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);source=Path(__file__).parent/'source';steps=[]
def run(name,cmd,timeout=170):
 with (a.output/(name+'.log')).open('xb') as log:
  c=subprocess.Popen([str(x) for x in cmd],stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();r=dict(name=name,argv=[str(x) for x in cmd],pid=c.pid,startticks=int(f[19]));steps.append(r);(a.output/'steps.json').write_text(json.dumps(steps));r['returncode']=c.wait(timeout=timeout);(a.output/'steps.json').write_text(json.dumps(steps))
 if r['returncode']:raise RuntimeError(name+' failed')
run('cmake-configure',['cmake','-S',source/'Profiler/llvm','-B',a.output/'build','-DLLVM_DIR=/usr/lib/llvm-15/lib/cmake/llvm'],40)
run('cmake-build',['cmake','--build',a.output/'build','--target','FlagPrismAscendLateObserver','-j2'])
plugin=a.output/'build/FlagPrismAscendLateObserver.so'
run('clock-marker-probe',[sys.executable,'-I',source/'tests/timeline/ascend_clock_marker_probe.py','--plugin',plugin,'--output',a.output/'clock-markers'],60)
results=[]
for manifest in (a.output/'clock-markers').glob('*/*.json'):
 m=json.loads(manifest.read_text())
 if 'runtime_actor_binding' not in m:continue
 binding=m['runtime_actor_binding'];expected='llvm.hivm.GET.SUBBLOCKDIM' if binding['actor_kind']=='AIV' else 'constant_one_cube_actor'
 if binding.get('runtime_participation')!=dict(version=1,header_word=7,count_shift=8,basis=expected):raise RuntimeError('Missing actual participation manifest')
 text=(manifest.parent/'output.ll').read_text()
 if binding['actor_kind']=='AIV' and 'call i64 @llvm.hivm.GET.SUBBLOCKDIM()' not in text:raise RuntimeError('Missing actual getter emission')
 results.append(dict(actor=binding['actor_kind'],manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),binding=binding['runtime_participation']))
if len(results)!=4:raise RuntimeError('Expected two actual opt inputs per actor')
(a.output/'result.json').write_text(json.dumps(dict(status='actual_normal_CMake_plugin_build_and_opt_manifest_checks_passed_not_device',plugin=str(plugin),plugin_sha256=hashlib.sha256(plugin.read_bytes()).hexdigest(),source_sha256={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()},checks=results,steps=steps),indent=2))
