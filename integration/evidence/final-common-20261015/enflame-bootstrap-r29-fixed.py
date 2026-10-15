import pathlib,hashlib,json,sys
source=pathlib.Path('/workspace/method-enflame-20261014/i3-source')
freeze=json.loads((source/'_method_source_freeze_r29.json').read_text())
for name,sha in freeze['files'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha,name
import torch,torch_gcu,triton,flagtree.profiler,flagtree.debugger
from flagtree.profiler.native import runtime_binding as pbind
from flagtree.debugger.native import runtime_binding as dbind
import triton._C.libtriton as core
runtime=pathlib.Path('/workspace/method-enflame-20261014/i3-runtime')
assert pathlib.Path(flagtree.profiler.__file__).resolve().is_relative_to(runtime)
assert pathlib.Path(flagtree.debugger.__file__).resolve().is_relative_to(runtime)
for prefix,package in [('Profiler/python/flagtree_profiler','profiler'),('Debugger/python/flagtree_debugger','debugger')]:
 for name,sha in freeze['files'].items():
  path=pathlib.Path(name)
  if path.is_relative_to(prefix) and path.suffix=='.py':assert hashlib.sha256((runtime/'flagtree'/package/path.relative_to(prefix)).read_bytes()).hexdigest()==sha,name
paths={'profiler':flagtree.profiler.__file__,'debugger':flagtree.debugger.__file__,'compiler':core.__file__,'profiler_native':pbind().__file__,'debugger_native':dbind().__file__}
print(json.dumps({'canonical_git_commit':freeze['canonical_git_commit'],'exact_source_files':len(freeze['files']),'paths':paths,'native_sha256':{k:hashlib.sha256(pathlib.Path(v).read_bytes()).hexdigest() for k,v in paths.items() if k in ['compiler','profiler_native','debugger_native']}},indent=2),flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
