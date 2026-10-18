"""Development tests: unchanged ordinary elementwise/reduction sources, real CUDA."""
import argparse, ctypes, hashlib, importlib.util, json, subprocess, time, types, sys
from pathlib import Path
import torch, triton, triton.language as tl
from triton._C.libtriton import llvm
from triton.backends.nvidia.compiler import get_ptxas


@triton.jit
def nonlinear(X, Y, N: tl.constexpr, B: tl.constexpr):
    x = tl.program_id(0) * B + tl.arange(0, B)
    value = tl.load(X + x, x < N, 0.)
    value = tl.exp(-value * value) * 0.75 + value * 0.125
    tl.store(Y + x, value, x < N)


@triton.jit
def row_softmax(X, Y, N: tl.constexpr, B: tl.constexpr):
    row = tl.program_id(0)
    x = tl.arange(0, B)
    value = tl.load(X + row * N + x, x < N, -float('inf'))
    shifted = value - tl.max(value, 0)
    exp = tl.exp(shifted)
    output = exp / tl.sum(exp, 0)
    tl.store(Y + row * N + x, output, x < N)


p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--tool', type=Path, required=True)
p.add_argument('--module-root', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
source = a.module_root
pkg = types.ModuleType('generic_late')
pkg.__path__ = [str(source)]
sys.modules[pkg.__name__] = pkg
for name in ('timeline_nvidia_late_compile', 'timeline_nvidia_late_raw'):
    spec = importlib.util.spec_from_file_location('generic_late.' + name,
                                                  source / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if name.endswith('compile'): compiler = mod
    else: decoder = mod
native = a.tool
hook = compiler.LateLLVMTransform(native, a.output / 'compile-attempts')
lib = ctypes.CDLL('libcuda.so.1')
ptr = ctypes.c_void_p
u = ctypes.c_uint


def bind(name, args):
    fn = getattr(lib, name)
    fn.argtypes = args
    fn.restype = ctypes.c_int
    return fn


load_module = bind('cuModuleLoadData', [ctypes.POINTER(ptr), ptr])
get_function = bind('cuModuleGetFunction',
                    [ctypes.POINTER(ptr), ptr, ctypes.c_char_p])
unload = bind('cuModuleUnload', [ptr])
launch = bind(
    'cuLaunchKernel',
    [ptr, u, u, u, u, u, u, u, ptr,
     ctypes.POINTER(ptr),
     ctypes.POINTER(ptr)])


def need(value, message):
    if not value: raise RuntimeError(message)


torch.cuda.set_device(0)
need(torch.cuda.get_device_capability() == (12, 0), 'Wrong actual target')
llvm.init_targets()
torch.manual_seed(35049)
results = []
for name, kernel, n, b, warps in [('nonlinear', nonlinear, 1003, 512, 4),
                                  ('row_softmax', row_softmax, 769, 1024, 8)]:
    folder = a.output / name
    folder.mkdir()
    cpu = torch.randn((n if name == 'nonlinear' else 2 * n, ),
                      dtype=torch.float32)
    reference = torch.exp(-cpu.double() * cpu.double()) * 0.75 + cpu.double(
    ) * 0.125 if name == 'nonlinear' else torch.softmax(
        cpu.double().reshape(2, n), 1).flatten()
    x = cpu.cuda()
    y = torch.full((cpu.numel() + 7, ), 1234., device='cuda')
    ordinary = kernel.warmup(x, y, n, b, grid=(2, ), num_warps=warps)
    frozen = dict(name=name,
                  N=n,
                  B=b,
                  num_warps=warps,
                  grid=[2, 1, 1],
                  rtol=1e-5,
                  atol=1e-6,
                  input_sha256=hashlib.sha256(
                      cpu.numpy().tobytes()).hexdigest(),
                  ordinary_llir_sha256=hashlib.sha256(
                      ordinary.asm['llir'].encode()).hexdigest(),
                  reference_sha256=hashlib.sha256(
                      reference.numpy().tobytes()).hexdigest())
    (folder / 'frozen-before-profile.json').write_text(
        json.dumps(frozen, indent=2))
    kernel[(2, )](x, y, n, b, num_warps=warps)
    torch.cuda.synchronize()
    need(
        torch.allclose(y[:cpu.numel()].cpu().double(),
                       reference,
                       rtol=1e-5,
                       atol=1e-6), 'Ordinary math failed')
    need(torch.equal(y[cpu.numel():].cpu(), torch.full((7, ), 1234.)),
         'Ordinary tail changed')
    y.fill_(1234.)
    metadata = dict(profile_scratch_size=0,
                    profile_scratch_align=1,
                    shared=ordinary.metadata.shared,
                    num_warps=warps)
    ir = hook(ordinary.asm['llir'], metadata)
    plan = metadata['flagprism_late_manifest']
    (folder / 'manifest.json').write_text(json.dumps(plan, indent=2))
    ptx = llvm.translate_to_asm(ir, 'nvptx64-nvidia-cuda', 'sm_120a', '+ptx88',
                                [], True, False)
    ptx_path = folder / 'late.ptx'
    ptx_path.write_text(ptx)
    tool = Path(
        get_ptxas(triton.runtime.driver.active.get_current_target().arch).path)
    argv = [
        str(tool), '-lineinfo', '-v', '--gpu-name=sm_120a',
        str(ptx_path), '-o',
        str(folder / 'late.cubin')
    ]
    with (folder / 'ptxas.stdout').open('xb') as out, (
            folder / 'ptxas.stderr').open('xb') as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err)
        fields = Path('/proc/' + str(child.pid) + '/stat').read_text().rsplit(
            ')', 1)[1].split()
        receipt = dict(argv=argv,
                       pid=child.pid,
                       startticks=int(fields[19]),
                       tool_sha256=hashlib.sha256(
                           tool.read_bytes()).hexdigest())
        (folder / 'assembly.json').write_text(json.dumps(receipt, indent=2))
        receipt['returncode'] = child.wait(timeout=30)
        (folder / 'assembly.json').write_text(json.dumps(receipt, indent=2))
        need(receipt['returncode'] == 0, 'Actual ptxas failed')
    cubin = (folder / 'late.cubin').read_bytes()
    image = ctypes.create_string_buffer(cubin)
    module = ptr()
    need(
        load_module(ctypes.byref(module), ctypes.cast(image, ptr)) == 0,
        'Actual module load failed')
    try:
        function = ptr()
        need(
            get_function(ctypes.byref(function), module,
                         kernel.__name__.encode()) == 0,
            'Actual function lookup failed')
        stride = plan['segment_words']
        guard = 16
        canary = 0x5A5A1234
        allocation = torch.full((2 * stride + guard * 2, ),
                                canary,
                                dtype=torch.int64,
                                device='cuda')
        raw = allocation[guard:-guard]
        raw.zero_()
        args = [
            ctypes.c_uint64(v)
            for v in (x.data_ptr(), y.data_ptr(), 0, raw.data_ptr())
        ]
        need(plan['scratch_arg'] == 3, 'Unexpected ordinary hidden ABI')
        params = (ptr * len(args))(
            *[ctypes.cast(ctypes.byref(v), ptr) for v in args])
        stream = torch.cuda.current_stream()
        dims = plan['block_dimensions']
        need(
            launch(function, 2, 1, 1, *dims, ordinary.metadata.shared,
                   ptr(stream.cuda_stream), params, None) == 0,
            'Actual launch failed')
        stream.synchronize()
        host = allocation.cpu()
        all_bytes = host.numpy().tobytes()
        (folder / 'allocation.bin').write_bytes(all_bytes)
        (folder / 'allocation-metadata.json').write_text(
            json.dumps(dict(guard_words=guard,
                            word_count=host.numel(),
                            grid=[2, 1, 1],
                            shared_bytes=ordinary.metadata.shared,
                            slots=[[0, 0], [1, 1]]),
                       indent=2))
        need(
            host[:guard].tolist() == host[-guard:].tolist() ==
            [canary] * guard, 'Raw guard changed')
        need(
            torch.allclose(y[:cpu.numel()].cpu().double(),
                           reference,
                           rtol=1e-5,
                           atol=1e-6), 'Instrumented math failed')
        need(torch.equal(y[cpu.numel():].cpu(), torch.full((7, ), 1234.)),
             'Original tail changed')
        need(torch.equal(x.cpu(), cpu), 'Original input changed')
        decoded = decoder.decode_late_raw(plan,
                                          all_bytes[guard * 8:-guard * 8],
                                          slots=[(0, 0), (1, 1)])
        (folder / 'decoded.json').write_text(json.dumps(decoded, indent=2))
        need(decoded['complete'], 'New generic math raw incomplete')
        events = [
            e for p in decoded['programs'] for actor in p['observers']
            for e in actor['events']
        ]
        row = dict(name=name,
                   ordinary_launches=1,
                   instrumented_launches=1,
                   math=True,
                   guards=True,
                   inputs=True,
                   raw_bytes=decoded['raw_bytes'],
                   actors=plan['actors'],
                   events=len(events),
                   positive_brackets=sum(e['end_tick'] > e['begin_tick']
                                         for e in events),
                   kinds=sorted(set(e['kind'] for e in events)))
        need(row['positive_brackets'] > 0, 'No real positive intervals')
        results.append(row)
        (a.output / 'result.json').write_text(
            json.dumps(dict(
                status=
                'actual_ordinary_generic_math_and_late_driver_not_public_api',
                results=results),
                       indent=2))
    finally:
        need(unload(module) == 0, 'Actual module unload failed')
