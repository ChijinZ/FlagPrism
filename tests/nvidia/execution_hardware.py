"""Non-name-based mapping against real NVIDIA compiler artifacts and CPU oracle."""
import json
import importlib.util
import os
from pathlib import Path
import sys
if os.environ.get('METHOD_COMPILER_SOURCE'):
    sys.path.insert(0, str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import torch
import triton
import triton.language as tl
if os.environ.get('METHOD_COMPILER_SOURCE'):
    assert Path(triton.__file__).is_relative_to(Path(os.environ['METHOD_COMPILER_SOURCE'])), triton.__file__

source = Path(os.environ['METHOD_SOURCE'])
spec = importlib.util.spec_from_file_location('execution_nvidia', source / 'Profiler/python/flagtree_profiler/execution_nvidia.py')
mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapper)
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)

@triton.jit
def vector(X, Y, N: tl.constexpr, B: tl.constexpr):
    indices = tl.program_id(0) * B + tl.arange(0, B)
    tl.store(Y + indices, tl.load(X + indices, indices < N, 0) * 2, indices < N)

@triton.jit
def reduction(X, Y, N: tl.constexpr, B: tl.constexpr):
    indices = tl.arange(0, B)
    values = tl.load(X + indices, indices < N, 0)
    tl.store(Y, tl.sum(values, 0))

@triton.jit
def matrix(A, B, C, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr):
    rows = tl.arange(0, 16)
    cols = tl.arange(0, 16)
    kk = tl.arange(0, 32)
    a = tl.load(A + rows[:, None] * K + kk[None, :], (rows[:, None] < M) & (kk[None, :] < K), 0)
    b = tl.load(B + kk[:, None] * N + cols[None, :], (kk[:, None] < K) & (cols[None, :] < N), 0)
    c = tl.dot(a, b)
    tl.store(C + rows[:, None] * N + cols[None, :], c, (rows[:, None] < M) & (cols[None, :] < N))


def save(compiled, name):
    metadata = compiled.metadata._asdict()
    metadata = {key: value for key, value in metadata.items() if isinstance(value, (str, int, float, bool, type(None)))}
    result = mapper.build_execution_mapping(compiled.asm, metadata, binary_id=compiled.hash)
    assert result['status'] == 'partial'
    assert result['source_associations'] == []
    assert result['organization']['threads-per-warp'] == 32
    assert result['layouts'], result
    path = output / name
    path.mkdir()
    (path / 'mapping.json').write_text(json.dumps(result, indent=2))
    for kind in ('ttir', 'ttgir', 'llir', 'ptx'):
        (path / kind).write_text(compiled.asm[kind])
    return result

for n, warps in [(127, 1), (513, 4), (1027, 8)]:
    x = torch.arange(n, dtype=torch.float32, device='cuda') / 128
    y = torch.empty_like(x)
    compiled = vector[(triton.cdiv(n, 256),)](x, y, n, 256, num_warps=warps)
    torch.testing.assert_close(y.cpu(), x.cpu() * 2)
    mapping = save(compiled, f'vector-{n}-w{warps}')
    assert any(layout['kind'] == 'blocked' for layout in mapping['layouts'])
    result = torch.empty((), dtype=torch.float32, device='cuda')
    compiled = reduction[(1,)](x, result, n, triton.next_power_of_2(n), num_warps=warps)
    torch.testing.assert_close(result.cpu(), x.cpu().sum(), rtol=1e-5, atol=1e-5)
    mapping = save(compiled, f'reduction-{n}-w{warps}')
    assert any(site['opcode'] == 'tt.reduce' for site in mapping['sites'])

a = torch.arange(16 * 32, device='cuda', dtype=torch.float16).reshape(16, 32) / 256
b = torch.arange(32 * 16, device='cuda', dtype=torch.float16).reshape(32, 16) / 256
c = torch.empty((16, 16), device='cuda', dtype=torch.float32)
compiled = matrix[(1,)](a, b, c, 16, 16, 32, num_warps=4)
torch.testing.assert_close(c.cpu(), a.cpu().float() @ b.cpu().float(), rtol=1e-5, atol=1e-5)
mapping = save(compiled, 'matrix')
assert any(layout['kind'] == 'nvidia_mma' for layout in mapping['layouts']), mapping['layouts']
print('PASS REAL_TTGIR_MAPPING 3 vector + 3 reduction + matrix; source coverage partial', flush=True)
