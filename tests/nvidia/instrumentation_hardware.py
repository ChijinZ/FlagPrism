"""Real Triton dynamic loop tracing against a fresh full compiler/native build."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

compiler_source = Path(os.environ['METHOD_COMPILER_SOURCE'])
sys.path.insert(0, str(compiler_source / 'python'))
import torch
import triton
import triton.language as tl
import flagtree
import triton._C.libtriton as libtriton
assert Path(triton.__file__).is_relative_to(compiler_source), triton.__file__
assert Path(
    libtriton.__file__).is_relative_to(compiler_source), libtriton.__file__
source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler import language as pl
from flagtree.profiler.hooks.instrumentation import InstrumentationHook
from flagtree.profiler.observations_nvidia import decode_proton_ring
from flagtree.profiler.observations import observation
from flagtree.profiler.native import runtime_binding, compiler_binding

native = runtime_binding()
print(json.dumps(
    {
        'compiler_path':
        libtriton.__file__,
        'compiler_sha256':
        hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest(),
        'compiler_source_baseline':
        '57d348b08455ff9a03902016c0fd6054ab44343e+recorded-policy-patch',
        'native_path':
        native.__file__,
        'native_sha256':
        hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        'profiler_path':
        profiler.__file__,
        'pid':
        os.getpid(),
        'torch':
        torch.__version__,
        'triton':
        triton.__version__,
        'device':
        torch.cuda.get_device_name(0)
    },
    indent=2),
      flush=True)
# Explicitly opt into the supported simple Triton loop subset; the inherited
# frontend defaults to Gluon and does not establish arbitrary pipeline fidelity.
pl.enable_semantic('triton')
InstrumentationHook.enable_host_buffer = True


@triton.jit(do_not_specialize=["loops"])
def loop_kernel(X, Y, loops, B: tl.constexpr):
    indices = tl.arange(0, B)
    values = tl.load(X + indices)
    result = tl.full((B, ), 0, tl.float32)
    for iteration in range(loops):
        pl.enter_scope('loop_body')
        result = result + values
        pl.exit_scope('loop_body')
    tl.store(Y + indices, result)


output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
x = torch.arange(256, dtype=torch.float32, device='cuda') / 128
y = torch.empty_like(x)
mode = profiler.mode.Default(sampling_strategy='selective',
                             sampling_options='0',
                             granularity='warp',
                             buffer_size=256)
binary_ids = set()
for loops in (0, 1, 3, 7, 23):
    base = output / f'loop-{loops}'
    session = profiler.start(str(base),
                             backend='instrumentation',
                             mode=mode,
                             hook='instrumentation')
    compiled = loop_kernel[(1, )](x, y, loops, 256, num_warps=4, num_stages=1)
    binary_ids.add(compiled.hash)
    torch.cuda.synchronize()
    assert InstrumentationHook.host_buffer is not None
    data = bytes(InstrumentationHook.host_buffer.tolist())
    (output / f'loop-{loops}.bin').write_bytes(data)
    ir_path = output / f'loop-{loops}.ttgir'
    ir_path.write_text(compiled.asm['ttgir'])
    context = libtriton.ir.context()
    libtriton.ir.load_dialects(context)
    libtriton.nvidia.load_dialects(context)
    compiler_binding().load_dialects(context)
    module = libtriton.ir.parse_mlir_module(str(ir_path), context)
    module.context = context
    names = dict(compiler_binding().get_scope_id_names(module))
    assert 'loop_body' in names.values(), names
    decoded = decode_proton_ring(data,
                                 capture_id=f'loop-{loops}',
                                 scopes=names)
    decoded['observations'] = [
        observation(value) for value in decoded['observations']
    ]
    (output / f'loop-{loops}-observations.json').write_text(
        json.dumps(decoded, indent=2))
    for kind in ('ttir', 'ttgir', 'llir', 'ptx'):
        (output / f'loop-{loops}.{kind}').write_text(compiled.asm[kind])
    profiler.finalize(session)
    exported = json.loads((base / 'ai/observations.json').read_text())
    assert len(exported['captures']) == 1
    assert len(exported['observations']) == len(decoded['observations'])
    capture = exported['captures'][0]
    assert capture['raw_sha256'] == hashlib.sha256(data).hexdigest()
    assert capture['decoded']['dropped_records'] == decoded['dropped_records']
    assert all(
        record['association_status'] == 'verified' and record['invocation_id']
        and record['scope_name'] == 'loop_body'
        and record['duration_ns'] is None
        for record in exported['observations'])
    torch.testing.assert_close(y.cpu(), x.cpu() * loops, rtol=1e-5, atol=1e-5)
    assert 'scf.for' in compiled.asm['ttir'] or 'scf.while' in compiled.asm[
        'ttir']
    assert 'mov.u64' in compiled.asm['ptx'] and '%clock64' in compiled.asm[
        'ptx']
    assert '%clock_hi' not in compiled.asm['ptx']
    actual = decoded['observations']
    # A scope interval needs two records; the selected warp has the entire ring.
    expected = min(loops, 16)
    assert len(actual) == expected, (loops, len(actual), decoded['losses'],
                                     decoded['unpaired_records'])
    assert decoded['dropped_records'] == max(0,
                                             loops * 2 - 32), decoded['losses']
    assert all(value['program'] == 0 and value['actor'].endswith('/warp:0')
               and value['duration_ns'] is None for value in actual)
    print('PASS REAL_TRITON_LOOP',
          loops,
          'intervals',
          len(actual),
          'dropped_records',
          decoded['dropped_records'],
          flush=True)
print('PASS FRESH_COMPILER_CLOCK64_AND_SELECTED_WARP_RING', flush=True)

assert len(binary_ids) == 1, binary_ids
