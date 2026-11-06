import os,shutil,json,hashlib,subprocess,sys
from pathlib import Path
root=Path('/root/chijin-journey-capacity-20261106');output=root/'output';source=root/'source'
site=Path('/tmp/chijin-timeline-r098-gcu/runs/normal-install-v3/output/venv/lib/python3.12/site-packages')
stage=output/'python';stage.mkdir(exist_ok=True)
shutil.copytree(site/'flagtree',stage/'flagtree',copy_function=os.link)
updates={
 'debugger/gcu_timeline.py':source/'Debugger/python/flagtree_debugger/gcu_timeline.py',
 'profiler/profile.py':source/'Profiler/python/flagtree_profiler/profile.py',
 'profiler/timeline_enflame.py':source/'Profiler/python/flagtree_profiler/timeline_enflame.py',
 'profiler/timeline_events_enflame_native.py':source/'Profiler/python/flagtree_profiler/timeline_events_enflame_native.py',
 'debugger/_native.cpython-312-x86_64-linux-gnu.so':output/'native/flagtree/debugger/_native.cpython-312-x86_64-linux-gnu.so',
 'debugger/_bin/gcu-timeline':output/'recorder-build/flagprism-gcu-timeline'}
for dest,src in updates.items():
 target=stage/'flagtree'/dest
 if target.exists() or target.is_symlink():target.unlink()
 shutil.copy2(src,target)
receipt={dest:dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest()) for dest,src in updates.items()}
(output/'staging-receipt.json').write_text(json.dumps(receipt,indent=2))
env=os.environ.copy();env.update(PYTHONPATH=str(stage),PYTHONDONTWRITEBYTECODE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0',FLAGTREE_PROFILER_TIMELINE_DOCUMENT_MB='64')
for name,args in [('python-decode',[str(source/'tests/timeline/test_enflame_execution_capacity.py')]),('public-capacity',['-m','pytest','-q',str(source/'tests/timeline/test_public_timeline_contract.py'),'-k','record_capacity or extended']),('native-import',['-c','from flagtree.debugger.native import runtime_binding; print(runtime_binding().__file__)'])]:
 with (output/(name+'.log')).open('w') as log:r=subprocess.run([sys.executable,*args],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 if r.returncode: raise RuntimeError(name+' failed')
print('STAGED_CPU_TESTS_PASSED',stage)
