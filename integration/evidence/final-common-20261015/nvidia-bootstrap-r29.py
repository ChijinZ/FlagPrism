import json,pathlib,hashlib
source=pathlib.Path('/workspace/FlagPrism-method-nvidia')
freeze=json.loads((source/'_method_source_freeze_r29.json').read_text())
for name,sha in freeze['files'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha,name
print(json.dumps({'canonical_git_commit':freeze['canonical_git_commit'],'exact_source_files':len(freeze['files']),'source_freeze_sha256':hashlib.sha256((source/'_method_source_freeze_r29.json').read_bytes()).hexdigest()},indent=2),flush=True)
import sys,os,importlib.util,json,hashlib,pathlib
source=pathlib.Path('/workspace/FlagPrism-method-nvidia');compiler=pathlib.Path('/workspace/FlagTree-method-nvidia')
sys.path.insert(0,str(compiler/'python'))
import triton,flagtree
for name,relative in [('debugger','Debugger/python/flagtree_debugger'),('profiler','Profiler/python/flagtree_profiler')]:
 package=source/relative;spec=importlib.util.spec_from_file_location('flagtree.'+name,package/'__init__.py',submodule_search_locations=[str(package)])
 module=importlib.util.module_from_spec(spec);sys.modules['flagtree.'+name]=module;setattr(flagtree,name,module);spec.loader.exec_module(module)
from flagtree.debugger.native import runtime_binding,compiler_binding
from flagtree.profiler.native import runtime_binding as profiler_binding
import triton._C.libtriton as core
native=runtime_binding();assert native is not None
assert pathlib.Path(native.__file__).is_relative_to(source),native.__file__
assert hasattr(compiler_binding(),'prepare_late_observation_abi')
paths={'compiler':core.__file__,'debugger_native':native.__file__,'profiler_native':profiler_binding().__file__}
print(json.dumps({'paths':paths,'sha256':{k:hashlib.sha256(pathlib.Path(v).read_bytes()).hexdigest() for k,v in paths.items()},'no_gpu_kernel_execution':True},indent=2),flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
