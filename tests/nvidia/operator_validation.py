"""Six Study math contracts and preselected held-out RMSNorm via formal bundles."""
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
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler import language as pl
from flagtree.profiler.native import runtime_binding
import reference_workloads as workloads

pl.enable_semantic('triton')


@triton.jit
def rmsnorm(X, W, Y, R: tl.constexpr, N: tl.constexpr, BLOCK: tl.constexpr):
    row = tl.program_id(0)
    column = tl.arange(0, BLOCK)
    pl.enter_scope('rms_source_control')
    value = tl.load(X + row * N + column, column < N, 0)
    scale = tl.rsqrt(tl.sum(value * value, 0) / N + 1.e-5)
    weight = tl.load(W + column, column < N, 0)
    result = value * scale * weight
    pl.exit_scope('rms_source_control')
    tl.store(Y + row * N + column, result, column < N)


output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
inputs = Path(os.environ['METHOD_CANONICAL_INPUTS'])
state = {
    'status':
    'running',
    'cases': [],
    'source_contract':
    'Study fixed canonical input bytes and original tolerances',
    'heldout_preselection': {
        'operator': 'RMSNorm',
        'shapes': [[32, 256], [256, 1024], [127, 769]],
        'configs': [1, 4],
        'oracle': 'CPU float32 x*rsqrt(mean(x*x)+1e-5)*weight',
        'atol': 0.0005,
        'rtol': 0.002
    },
    'tool_baseline':
    os.environ['METHOD_BASELINE'],
    'compiler_baseline':
    '57d348b08455ff9a03902016c0fd6054ab44343e+policy-patch',
    'compiler_path':
    libtriton.__file__,
    'compiler_sha256':
    hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest(),
    'native_path':
    runtime_binding().__file__,
    'native_sha256':
    hashlib.sha256(Path(runtime_binding().__file__).read_bytes()).hexdigest(),
    'device':
    torch.cuda.get_device_name(0),
    'pid':
    os.getpid(),
    'visible_devices':
    os.environ.get('CUDA_VISIBLE_DEVICES')
}
(output / 'result.json').write_text(json.dumps(state, indent=2))


def read(family, shape, index, dimensions, dtype, hashes):
    path = inputs / f'{family}-{"x".join(map(str, shape))}-{index}.bin'
    raw = path.read_bytes()
    hashes.append({
        'file': path.name,
        'sha256': hashlib.sha256(raw).hexdigest()
    })
    return torch.frombuffer(bytearray(raw),
                            dtype=dtype).reshape(dimensions).clone()


def case(operator, shape, variant):
    label = f'{operator}-{"x".join(map(str, shape))}-v{variant}'
    hashes = []
    if operator.startswith('gemm'):
        m, n, k = shape
        a = read('matmul', shape, 0, (m, k), torch.float16, hashes)
        b = read('matmul', shape, 1, (k, n), torch.float16, hashes)
        bias = read('matmul', shape, 2, (n, ), torch.float32, hashes)
        reference = a.float() @ b.float()
        if operator == 'gemm_bias_gelu':
            reference = torch.nn.functional.gelu(reference + bias,
                                                 approximate='tanh')
        da, db, dbias = a.cuda(), b.cuda(), bias.cuda()
        result = torch.empty((m, n), device='cuda', dtype=torch.float32)
        bm, bn, bk, stages, warps = (16 if variant == 0 else
                                     32), 16, 16, variant + 1, 4
        grid = (triton.cdiv(m, bm), triton.cdiv(n, bn))

        def launch():
            return workloads.matmul[grid](da,
                                          db,
                                          dbias,
                                          result,
                                          m,
                                          n,
                                          k,
                                          bm,
                                          bn,
                                          bk,
                                          operator == 'gemm_bias_gelu',
                                          num_stages=stages,
                                          num_warps=warps)

        atol, rtol = 0.002, 0.02
        config = {
            'BM': bm,
            'BN': bn,
            'BK': bk,
            'num_stages': stages,
            'num_warps': warps
        }
    elif operator == 'transpose':
        m, n = shape
        x = read('transpose', shape, 0, (m, n), torch.float32, hashes)
        reference = x.T.contiguous()
        dx = x.cuda()
        result = torch.empty((n, m), device='cuda')
        bm, bn = (16 if variant == 0 else 32), 16
        grid = (triton.cdiv(m, bm), triton.cdiv(n, bn))

        def launch():
            return workloads.transpose[grid](dx,
                                             result,
                                             m,
                                             n,
                                             bm,
                                             bn,
                                             num_stages=1,
                                             num_warps=4)

        atol, rtol = 0., 0.
        config = {'BM': bm, 'BN': bn, 'num_stages': 1, 'num_warps': 4}
    else:
        r, n = shape
        x = read('rows', shape, 0, (r, n), torch.float32, hashes)
        w = read('rows', shape, 1, (n, ), torch.float32, hashes)
        bias = read('rows', shape, 2, (n, ), torch.float32, hashes)
        if operator == 'softmax': reference = torch.softmax(x, -1)
        elif operator == 'layernorm':
            reference = torch.nn.functional.layer_norm(x, (n, ), w, bias,
                                                       1.e-5)
        elif operator == 'rmsnorm':
            reference = x * torch.rsqrt((x * x).mean(-1, keepdim=True) +
                                        1.e-5) * w
        else:
            reference = x.sum(-1)
        dx, dw, dbias = x.cuda(), w.cuda(), bias.cuda()
        result = torch.empty(reference.shape, device='cuda')
        rows = variant + 1
        block = triton.next_power_of_2(n)
        warps = (1 if variant == 0 else 4) if operator == 'rmsnorm' else 4
        if operator == 'rmsnorm':
            grid = (r, )

            def launch():
                return rmsnorm[grid](dx,
                                     dw,
                                     result,
                                     r,
                                     n,
                                     block,
                                     num_stages=1,
                                     num_warps=warps)
        else:
            grid = (triton.cdiv(r, rows), )

            def launch():
                return workloads.rows[grid](dx,
                                            dw,
                                            dbias,
                                            result,
                                            r,
                                            n,
                                            block,
                                            rows,
                                            operator,
                                            num_stages=1,
                                            num_warps=warps)

        atol, rtol = 0.0005, 0.002
        config = {
            'ROWS': 1 if operator == 'rmsnorm' else rows,
            'BLOCK': block,
            'num_stages': 1,
            'num_warps': warps
        }
    compiled = launch()
    for _ in range(5):
        launch()
    torch.cuda.synchronize()
    assert reference.device.type == 'cpu'
    torch.testing.assert_close(result.cpu(), reference, atol=atol, rtol=rtol)
    session = profiler.start(str(output / label),
                             backend='cupti',
                             hook='triton',
                             metadata={
                                 'operator': operator,
                                 'parameters': {
                                     'shape': list(shape),
                                     'config': config
                                 },
                                 'validation': {
                                     'oracle': 'CPU float32',
                                     'atol': atol,
                                     'rtol': rtol
                                 }
                             })
    for _ in range(3):
        launch()
    torch.cuda.synchronize()
    profiler.finalize(session)
    actual = result.cpu()
    torch.testing.assert_close(actual, reference, atol=atol, rtol=rtol)
    events = [
        json.loads(line)
        for line in (output / label /
                     'ai/events.jsonl').read_text().splitlines()
    ]
    kernels = [event for event in events if event['kind'] == 'kernel']
    assert len(kernels) == 3, (label, len(kernels))
    assert len({event['scope_id'] for event in kernels}) == 3
    assert all(event['launch_id'] and event['binary_id']
               and event['argument_signature'] for event in kernels)
    return {
        'operator': operator,
        'shape': list(shape),
        'config': config,
        'grid': list(grid),
        'status': 'passed',
        'input_hashes': hashes,
        'binary_id': compiled.hash,
        'atol': atol,
        'rtol': rtol,
        'max_abs_error': (actual - reference).abs().max().item(),
        'native_kernel_count': len(kernels),
        'bundle': label,
        'native_duration_us': [event['duration_us'] for event in kernels]
    }


try:
    for operator in [
            'gemm', 'gemm_bias_gelu', 'softmax', 'layernorm', 'reduce_sum',
            'transpose', 'rmsnorm'
    ]:
        shapes = [(128, 128, 128), (512, 512, 512),
                  (257, 193, 320)] if operator.startswith('gemm') else (
                      [(256, 256), (1024, 1024),
                       (513,
                        257)] if operator == 'transpose' else [(32, 256),
                                                               (256, 1024),
                                                               (127, 769)])
        for shape in shapes:
            for variant in (0, 1):
                result = case(operator, shape, variant)
                state['cases'].append(result)
                (output / 'result.json').write_text(json.dumps(state,
                                                               indent=2))
                print('PASS', operator, shape, result['config'], flush=True)
    state['status'] = 'passed'
finally:
    (output / 'result.json').write_text(json.dumps(state, indent=2))
print('PASS FORMAL_NATIVE_AND_CPU_ORACLE', len(state['cases']), flush=True)
