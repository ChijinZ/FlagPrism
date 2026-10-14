"""Real compiler location chains: unknown, callsite, and fused candidates."""
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import triton._C.libtriton as core
import flagtree

source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler.native import compiler_binding
from flagtree.profiler.source_origins_nvidia import capture_scope_origins

text = '''module {
 tt.func @sites() {
  proton.record start "unknown" loc(unknown)
  proton.record end "unknown" loc(unknown)
  proton.record start "inline" loc(callsite("callee.py":10:2 at "caller.py":20:3))
  proton.record end "inline" loc(callsite("callee.py":12:2 at "caller.py":20:3))
  proton.record start "fused" loc(fused["a.py":1:0, "b.py":2:1])
  proton.record end "fused" loc(fused["a.py":3:0, "b.py":4:1])
  tt.return
 } loc("function.py":99:0)
}'''
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(text)
context = core.ir.context()
core.ir.load_dialects(context)
compiler_binding().load_dialects(context)
module = core.ir.parse_mlir_module(str(path), context)
module.context = context
names = dict(compiler_binding().get_scope_id_names(module))
origins = compiler_binding().get_scope_id_origins(module)
values, sources = capture_scope_origins(origins, binary_id='compiler-fixture')
by_name = {names[int(key)]: value for key, value in values.items()}
assert by_name['unknown']['status'] == 'unknown'
assert by_name['inline']['entry'][0]['kind'] == 'callsite'
assert by_name['inline']['entry'][0]['callee']['file'] == 'callee.py'
assert by_name['inline']['entry'][0]['caller']['file'] == 'caller.py'
assert by_name['fused']['status'] == 'multiple_candidates'
assert len(by_name['fused']['entry'][0]['candidates']) == 2
path.with_suffix('.origins.json').write_text(
    json.dumps({
        'origins': values,
        'sources': sources
    }, indent=2))
print('PASS REAL_COMPILER_UNKNOWN_INLINE_CALLSITE_AND_FUSED_LOCATION_CHAINS',
      flush=True)
