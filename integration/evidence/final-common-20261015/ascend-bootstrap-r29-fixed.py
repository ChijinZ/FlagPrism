from pathlib import Path
import hashlib,json,sys
source=Path('/tmp/flagprism-method-ascend/source');freeze=json.loads((source/'_method_code_freeze_r29.json').read_text())
for name,sha in freeze['files'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha,name
import torch,torch_npu,triton,flagtree,importlib.util
built=Path('/tmp/flagprism-method-ascend/compiler-python')
for component,directory in [('debugger','Debugger/python/flagtree_debugger'),('profiler','Profiler/python/flagtree_profiler')]:
 name='flagtree.'+component;package=source/directory;compiled=built/'flagtree'/component
 spec=importlib.util.spec_from_file_location(name,package/'__init__.py',submodule_search_locations=[str(compiled),str(package)])
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);setattr(flagtree,component,module)
for prefix,package in [('Profiler/python/flagtree_profiler',flagtree.profiler),('Debugger/python/flagtree_debugger',flagtree.debugger)]:
 actual=Path(package.__file__).parent
 for name,sha in freeze['files'].items():
  p=Path(name)
  if p.is_relative_to(prefix) and p.suffix=='.py':
   relative=p.relative_to(prefix)
   possibilities=[Path(folder)/relative for folder in package.__path__]
   selected=next(path for path in possibilities if path.is_file())
   assert hashlib.sha256(selected.read_bytes()).hexdigest()==sha,name
from flagtree.profiler.native import runtime_binding as pb
from flagtree.debugger.native import runtime_binding as db
import triton._C.libtriton as core
paths={'profiler':flagtree.profiler.__file__,'debugger':flagtree.debugger.__file__,'compiler':core.__file__,'profiler_native':pb().__file__,'debugger_native':db().__file__}
print(json.dumps({'canonical_runtime_code_commit':freeze['canonical_runtime_code_commit'],'exact_code_files':len(freeze['files']),'paths':paths,'native_sha256':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in paths.items() if k in ['compiler','profiler_native','debugger_native']}},indent=2),flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
