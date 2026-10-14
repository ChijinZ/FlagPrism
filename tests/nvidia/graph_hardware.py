"""Native CUPTI graph replay keeps graph identity and missing launch metadata explicit."""
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
import flagtree
source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location('flagtree.profiler', package / '__init__.py', submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler.native import runtime_binding
print(json.dumps({'native_path': runtime_binding().__file__, 'native_sha256': hashlib.sha256(Path(runtime_binding().__file__).read_bytes()).hexdigest(), 'compiler_path': triton.__file__, 'pid': os.getpid()}, indent=2), flush=True)
@triton.jit
def add(X,Y,B:tl.constexpr):
    i=tl.arange(0,B)
    tl.store(Y+i,tl.load(X+i)+1)
x=torch.arange(256,device='cuda',dtype=torch.float32)
y=torch.empty_like(x)
z=torch.empty_like(x)
stream=torch.cuda.Stream()
with torch.cuda.stream(stream):
    add[(1,)](x,y,256)
    add[(1,)](y,z,256)
torch.cuda.synchronize()
output=Path(sys.argv[1])
for creation in ('before','during'):
    session=None
    if creation=='during':session=profiler.start(str(output/creation),backend='cupti',hook='triton')
    graph=torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph,stream=stream):
        add[(1,)](x,y,256)
        add[(1,)](y,z,256)
    if creation=='before':session=profiler.start(str(output/creation),backend='cupti',hook='triton')
    for replay in range(2):
        with profiler.scope(f'replay-{replay}'):
            graph.replay()
    torch.cuda.synchronize()
    profiler.finalize(session)
    torch.testing.assert_close(z.cpu(),x.cpu()+2)
    events=[json.loads(line) for line in (output/creation/'ai/events.jsonl').read_text().splitlines()]
    kernels=[event for event in events if event['kind']=='kernel' and event['metrics']['activity.graph_id']>0]
    assert len(kernels)==4, kernels
    assert len({event['scope_id'] for event in kernels})==2, kernels
    assert len({event['correlation_key'] for event in kernels})==2, kernels
    assert all(event['metrics']['activity.graph_id']>0 and event['end_ns']>event['start_ns'] for event in kernels)
    if creation == 'before':
        assert all(event['metrics'].get('activity.graph_instance_count_status') == 'unknown_graph_created_before_capture' for event in kernels)
        summary=json.loads((output/creation/'ai/summary.json').read_text())
        assert 'Graph created before CUPTI capture' in json.dumps(summary), summary
    else:
        assert all('activity.graph_instance_count_status' not in event['metrics'] for event in kernels)
    # Graph replay has no per-kernel LazyDict launch metadata. Do not attach
    # capture-time source/binary/arguments to replay based on name or order.
    assert all(event.get('launch_id') is None and event.get('binary_id') is None for event in kernels), kernels
    (output/creation/'graph-check.json').write_text(json.dumps({'creation':creation,'kernel_count':len(kernels),'graph_ids':sorted({event['metrics']['activity.graph_id'] for event in kernels}),'correlation_ids':sorted({event['correlation_id'] for event in kernels}),'source_association':'unavailable_per_kernel_graph_replay'},indent=2))
    print('PASS NATIVE_GRAPH_CREATED',creation,'KERNELS',len(kernels),flush=True)
