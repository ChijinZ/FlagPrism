"""Build/run a DI-only CPU prototype; always revalidate with the actual SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from flagtree.profiler._deadline import _stop_worker

p = argparse.ArgumentParser()
p.add_argument('--output',type=Path,required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
source = Path(__file__).parent
build = a.output/'build'
steps=[]
commands=[
 ('configure',['cmake','-S',str(source),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DMLIR_DIR=/opt/flagtree-llvm/llvm-fc83c68-gcc9-x64/lib/cmake/mlir'],30),
 ('build',['cmake','--build',str(build),'--parallel','2'],90),
 ('bridge',[str(build/'scope-bridge'),'/tmp/chijin-timeline-r061-gcu/runs/final-inspect-v1/output/32-8/input.llir',str(a.output/'with-scope.mlir')],20),
 ('SDK-validate',['/opt/triton_gcu/bin/gcu-compiler-opt',str(a.output/'with-scope.mlir'),'--mlir-print-debuginfo','-o',str(a.output/'SDK-roundtrip.mlir')],20),
]
for name,command,timeout in commands:
 with (a.output/(name+'.stdout')).open('xb') as out,(a.output/(name+'.stderr')).open('xb') as err:
  child=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True)
  try:child.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   _stop_worker(child)
   raise RuntimeError('Owned CPU prototype timed out: '+name)
 steps.append(dict(name=name,argv=command,returncode=child.returncode))
 (a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if child.returncode:break
files=[dict(path=q.name,bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest()) for q in sorted(a.output.iterdir()) if q.is_file()]
(a.output/'result.json').write_text(json.dumps(dict(status='CPU_vendor_DI_bridge_prototype',steps=steps,files=files,application_replayed=False,device_executed=False,product_or_SDK_modified=False,actual_native_mapping_qualified=False),indent=2))
if len(steps)!=4 or any(r['returncode'] for r in steps):raise RuntimeError('DI bridge prototype is incomplete; preserve diagnostics')
