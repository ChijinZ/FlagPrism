"""Real inlining preserves scope IDs, emitted boundaries, and captured source hashes."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import torch
import triton
import triton.language as tl
import triton._C.libtriton as libtriton
import flagtree
source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location('flagtree.profiler', package / '__init__.py', submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler import language as pl
from flagtree.profiler.observations import ObservationRequest
from flagtree.profiler.native import runtime_binding, compiler_binding
from triton.language.core import builtin, _unwrap_if_constexpr
from flagtree.profiler.flags import get_instrumentation_on
pl.enable_semantic('triton')
print(json.dumps({'compiler_path': libtriton.__file__, 'compiler_sha256': hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest(), 'native_path': runtime_binding().__file__, 'native_sha256': hashlib.sha256(Path(runtime_binding().__file__).read_bytes()).hexdigest(), 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'pid': os.getpid()}, indent=2), flush=True)

@triton.jit
def scoped(value):
    pl.enter_scope('same_helper_region')
    result = value + 1
    pl.exit_scope('same_helper_region')
    return result

@builtin
def legacy_record(is_start: tl.constexpr, _semantic=None):
    if get_instrumentation_on():
        # The original three-argument compiler API remains valid and unknown.
        compiler_binding().create_proton_record(_semantic.builder.get_op_builder(),
                                               _unwrap_if_constexpr(is_start), 'legacy_no_location')

@triton.jit
def kernel(X, Y, N: tl.constexpr, B: tl.constexpr):
    i = tl.program_id(0) * B + tl.arange(0, B)
    value = tl.load(X+i, i<N, 0)
    value = scoped(value)
    value = scoped(value)
    legacy_record(True)
    tl.store(Y+i, value, i<N)
    legacy_record(False)

output = Path(sys.argv[1])
binary_ids=set()
for n in (257, 513):
    x=torch.arange(n,device='cuda',dtype=torch.float32)
    y=torch.empty_like(x)
    destination=output/str(n)
    session=profiler.start(str(destination),backend='instrumentation',hook='instrumentation',
                           observation_request=ObservationRequest(programs=(0,),max_events_per_instance=4))
    compiled=kernel[(triton.cdiv(n,256),)](x,y,n,256,num_warps=4,num_stages=1)
    profiler.finalize(session)
    binary_ids.add(compiled.hash)
    torch.testing.assert_close(y.cpu(),x.cpu()+2)
    doc=json.loads((destination/'ai/observations.json').read_text())
    all_observations=doc['observations']
    assert len(all_observations)==3,all_observations
    observations=[event for event in all_observations if event['scope_name']=='same_helper_region']
    assert len(observations)==2
    assert len({event['site'] for event in observations})==2
    legacy=[event for event in all_observations if event['scope_name']=='legacy_no_location']
    assert len(legacy)==1 and legacy[0]['compiler_site']['origin']['status']=='unknown',legacy
    capture=doc['captures'][0]
    files={item['sha256']:base64.b64decode(item['content']) for item in capture['scope_origin_sources'] if item['status']=='captured'}
    for event in observations:
        site=event['compiler_site']
        assert site['binary_id']==compiled.hash and site['scope_id']==event['site']
        origin=site['origin']
        assert origin['status']=='source_region_origin',origin
        assert origin['entry'] and origin['exit']
        own_files=[item for item in origin['source_capture'] if item.get('source_sha256') in files and item['file']==__file__]
        assert own_files, origin
        for item in own_files:
            data=files[item['source_sha256']]
            assert hashlib.sha256(data).hexdigest()==item['source_sha256']
            assert 0<item['line']<=len(data.splitlines())
    (destination/'scope-origin-check.json').write_text(json.dumps({'binary_id':compiled.hash,'scopes':capture['scope_id_origins'],'source_files':[{k:v for k,v in item.items() if k!='content'} for item in capture['scope_origin_sources']]},indent=2))
    print('PASS INLINED_SAME_NAME_DISTINCT_SCOPE_IDS_AND_REAL_SOURCE',n,flush=True)
assert len(binary_ids)==2,binary_ids
print('PASS SAME_SOURCE_DIFFERENT_BINARY_SOURCE_ORIGIN_IDENTITY',flush=True)
