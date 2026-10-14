"""Real CUDA smoke against an explicitly supplied freshly built package/native."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
if os.environ.get('METHOD_COMPILER_SOURCE'):
    sys.path.insert(0,
                    str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import torch
import triton
import triton.language as tl
if os.environ.get('METHOD_COMPILER_SOURCE'):
    assert Path(triton.__file__).is_relative_to(
        Path(os.environ['METHOD_COMPILER_SOURCE'])), triton.__file__
import flagtree

root = Path(os.environ['METHOD_SOURCE'])
package = root / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler.native import runtime_binding

native = runtime_binding()
print(json.dumps(
    {
        'pid':
        os.getpid(),
        'torch':
        torch.__version__,
        'triton':
        triton.__version__,
        'triton_path':
        triton.__file__,
        'native_path':
        native.__file__,
        'native_sha256':
        hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        'profiler_path':
        profiler.__file__,
        'device':
        torch.cuda.get_device_name(0),
        'visible_devices':
        os.environ.get('CUDA_VISIBLE_DEVICES'),
        'source_commit':
        os.environ['METHOD_BASELINE']
    },
    indent=2),
      flush=True)


@triton.jit
def add(X, Y, Z, N: tl.constexpr, B: tl.constexpr):
    offsets = tl.program_id(0) * B + tl.arange(0, B)
    tl.store(
        Z + offsets,
        tl.load(X + offsets, offsets < N, 0) +
        tl.load(Y + offsets, offsets < N, 0), offsets < N)


n = 1027
x = torch.arange(n, device='cuda', dtype=torch.float32)
y = torch.ones_like(x)
z = torch.empty_like(x)
add[(triton.cdiv(n, 256), )](x, y, z, n, 256)
torch.cuda.synchronize()
output = Path(sys.argv[1])
session = profiler.start(str(output), backend='cupti', hook='triton')
for _ in range(3):
    add[(triton.cdiv(n, 256), )](x, y, z, n, 256)
torch.cuda.synchronize()
profiler.finalize(session)
torch.testing.assert_close(z.cpu(), x.cpu() + y.cpu())
files = list(output.rglob('*'))
print('BUNDLE_FILES',
      [str(p.relative_to(output)) for p in files if p.is_file()],
      flush=True)
events = [
    json.loads(line)
    for line in (output / 'ai/events.jsonl').read_text().splitlines()
]
kernels = [r for r in events if r['kind'] == 'kernel']
assert len(kernels) == 3, len(kernels)
assert all(r['scope_id'] > 0 and r['correlation_id'] > 0
           and r['process_id'] == os.getpid() for r in kernels)
assert len({r['scope_id'] for r in kernels}) == 3
assert all(r['end_ns'] > r['start_ns'] for r in kernels)
assert all(r['launch_id'] and r['binary_id'] and r['argument_signature']
           for r in kernels)
print('PASS CUDA_REAL_KERNELS', len(kernels), flush=True)

# Same binary/name on independent streams, with overlapping session lifetime.
streams = [torch.cuda.Stream(), torch.cuda.Stream()]
zs = [torch.empty_like(x), torch.empty_like(x)]
for i in range(2):
    with torch.cuda.stream(streams[i]):
        add[(triton.cdiv(n, 256), )](x, y, zs[i], n, 256)
torch.cuda.synchronize()
outer_path = output.with_name(output.name + '-outer')
inner_path = output.with_name(output.name + '-inner')
outer = profiler.start(str(outer_path), backend='cupti', hook='triton')
with torch.cuda.stream(streams[0]):
    add[(triton.cdiv(n, 256), )](x, y, zs[0], n, 256)
inner = profiler.start(str(inner_path), backend='cupti', hook='triton')
for i in range(2):
    with torch.cuda.stream(streams[i]):
        add[(triton.cdiv(n, 256), )](x, y, zs[i], n, 256)
torch.cuda.synchronize()
profiler.finalize(inner)
with torch.cuda.stream(streams[1]):
    add[(triton.cdiv(n, 256), )](x, y, zs[1], n, 256)
torch.cuda.synchronize()
profiler.finalize(outer)
outer_events = [
    json.loads(line)
    for line in (outer_path / 'ai/events.jsonl').read_text().splitlines()
]
inner_events = [
    json.loads(line)
    for line in (inner_path / 'ai/events.jsonl').read_text().splitlines()
]
assert len(outer_events) == 4, len(outer_events)
assert len(inner_events) == 2, len(inner_events)
assert len({e['stream_id'] for e in outer_events}) == 2
assert len({e['correlation_key'] for e in outer_events}) == 4
assert {e['correlation_domain']
        for e in outer_events
        }.isdisjoint({e['correlation_domain']
                      for e in kernels})
assert {e['scope_id']
        for e in inner_events} < {e['scope_id']
                                  for e in outer_events}
assert all(e['launch_id'] for e in outer_events + inner_events)
for value in zs:
    torch.testing.assert_close(value.cpu(), x.cpu() + y.cpu())
print('PASS SAME_NAME_MULTISTREAM_NESTED_SESSIONS',
      len(outer_events),
      len(inner_events),
      flush=True)
