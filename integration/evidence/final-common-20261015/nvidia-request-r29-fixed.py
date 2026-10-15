import json,pathlib,hashlib
source=pathlib.Path('/workspace/FlagPrism-method-nvidia')
freeze=json.loads((source/'_method_source_freeze_r29.json').read_text())
for name,sha in freeze['files'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha,name
print(json.dumps({'canonical_git_commit':freeze['canonical_git_commit'],'exact_source_files':len(freeze['files']),'source_freeze_sha256':hashlib.sha256((source/'_method_source_freeze_r29.json').read_bytes()).hexdigest()},indent=2),flush=True)
import sys,importlib.util,runpy
source=pathlib.Path('/workspace/FlagPrism-method-nvidia');compiler=pathlib.Path('/workspace/FlagTree-method-nvidia')
sys.path.insert(0,str(compiler/'python'))
import triton,flagtree
package=source/'Debugger/python/flagtree_debugger'
spec=importlib.util.spec_from_file_location('flagtree.debugger',package/'__init__.py',submodule_search_locations=[str(package)])
module=importlib.util.module_from_spec(spec);sys.modules['flagtree.debugger']=module;setattr(flagtree,'debugger',module);spec.loader.exec_module(module)
assert 'flagtree.profiler' not in sys.modules
sys.argv=[str(source/'tests/nvidia/request_hardware.py'),'/workspace/method-final-r29-public-request']
runpy.run_path(sys.argv[0],run_name='__main__')
from flagtree.profiler.native import runtime_binding as pb
from flagtree.debugger.native import runtime_binding as db
import triton._C.libtriton as core
paths={'compiler':core.__file__,'debugger_native':db().__file__,'profiler_native':pb().__file__}
print(json.dumps({'functional_check':'public request actual three launches, no performance','paths':paths,'sha256':{k:hashlib.sha256(pathlib.Path(v).read_bytes()).hexdigest() for k,v in paths.items()}},indent=2),flush=True)
