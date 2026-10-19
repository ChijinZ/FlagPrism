"""Actual public GEMM and SDK-translated buffer address check; two real calls."""
import argparse, pathlib, json, ctypes
from contextlib import nullcontext

p = argparse.ArgumentParser()
p.add_argument('--output', type=pathlib.Path, required=True)
p.add_argument('--two-streams',
               action='store_true',
               help='Submit the two real GEMMs on distinct nondefault streams')
a = p.parse_args()
a.output.mkdir(parents=True)
import torch
import torch_gcu
import triton
import triton.language as tl
import flagtree.profiler as profiler
from flagtree.debugger import api
from flagtree.profiler.timeline_events_enflame_native import decode_execution_capture

torch.gcu.set_device(0)
lib = ctypes.CDLL('/opt/tops/lib/libtopsrt.so')
query = lib.topsPointerGetAttribute
query.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
query.restype = ctypes.c_int
snapshots = []
original = api._infer_runtime_metadata


def observe(metadata, args):
    result = original(metadata, args)
    pointers = []
    for i, arg in enumerate(args):
        if not callable(getattr(arg, 'data_ptr', None)): continue
        host = int(arg.data_ptr())
        device = ctypes.c_uint64()
        status = query(ctypes.byref(device), 3, ctypes.c_void_p(host))
        if status or not device.value:
            raise RuntimeError('Actual SDK pointer translation failed ' +
                               str(status))
        pointers.append(
            dict(position=i, host_pointer=host, device_pointer=device.value))
    snapshots.append(pointers)
    return result


@triton.jit(do_not_specialize=['K'])
def tiled_product(A, B, C, M: tl.constexpr, N: tl.constexpr, K,
                  BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
    rows = tl.program_id(0) * BM + tl.arange(0, BM)
    cols = tl.program_id(1) * BN + tl.arange(0, BN)
    inner = tl.arange(0, BK)
    result = tl.full((BM, BN), 0, tl.float32)
    for tile in range(tl.cdiv(K, BK)):
        kk = tile * BK + inner
        left = tl.load(A + rows[:, None] * K + kk[None, :],
                       (rows[:, None] < M) & (kk[None, :] < K), 0)
        right = tl.load(B + kk[:, None] * N + cols[None, :],
                        (kk[:, None] < K) & (cols[None, :] < N), 0)
        result += tl.dot(left, right)
    tl.store(C + rows[:, None] * N + cols[None, :], result,
             (rows[:, None] < M) & (cols[None, :] < N))


inputs = []
for k in [96, 224]:
    left = torch.linspace(-.5, .5, 64 * k).reshape(64, k).to(torch.float16)
    right = torch.linspace(.5, -.25, k * 64).reshape(k, 64).to(torch.float16)
    inputs.append(
        dict(k=k,
             left=left,
             right=right,
             x=left.to('gcu'),
             y=right.to('gcu'),
             out=torch.full((4100, ), -17.25, device='gcu')))
streams = [torch.gcu.Stream(device=0) for _ in inputs] if a.two_streams else []
if streams:
    torch.gcu.synchronize(
        0)  # Finish input setup before either independent stream.
api._infer_runtime_metadata = observe
session = profiler.start(str(a.output / 'public'), detail='timeline')
try:
    for index, row in enumerate(inputs):
        with torch.gcu.stream(streams[index]) if streams else nullcontext():
            tiled_product[(2, 2)](row['x'],
                                  row['y'],
                                  row['out'],
                                  64,
                                  64,
                                  row['k'],
                                  32,
                                  32,
                                  32,
                                  num_warps=4,
                                  num_stages=1)
finally:
    api._infer_runtime_metadata = original
    (a.output / 'sdk-pointer-bindings.json').write_text(
        json.dumps(snapshots, indent=2))
    profiler.finalize(session)
for row in inputs:
    if not torch.allclose(row['out'][:4096].cpu().reshape(64, 64),
                          row['left'].float() @ row['right'].float(),
                          rtol=2e-3,
                          atol=2e-3):
        raise RuntimeError('Public GEMM math changed')
    if not torch.equal(row['out'][4096:].cpu(), torch.full(
        (4, ), -17.25)) or not torch.equal(row['x'].cpu(),
                                           row['left']) or not torch.equal(
                                               row['y'].cpu(), row['right']):
        raise RuntimeError('Inputs/tail changed')
root = a.output / 'public/timeline'
index = json.loads((root / 'index.json').read_text())
checks = []
if len(index['captures']) != 2 or len(snapshots) != 2:
    raise RuntimeError('Unexpected actual call count')
for snapshot, item, row in zip(snapshots, index['captures'], inputs):
    from flagtree.profiler.timeline_capture_store import load_capture_file
    c = load_capture_file(root / item['capture_file'])
    metadata = c['metadata']['compiler_metadata']
    batch = json.loads((root / c['events_file']).read_text())
    raw = (root / c['raw_file']).read_bytes()
    decoded = decode_execution_capture(raw,
                                       compiler_metadata=metadata,
                                       identity=batch['identity'],
                                       association=c['launch'],
                                       grid=c['owner']['layout']['grid'])
    if metadata['debug_execution_manifest'].get(
            'buffer_address_encoding') != 'gcu_ptr2int_i64_v1':
        raise RuntimeError('Timeline lacks full-width device addresses')
    addresses = {
        cmd[role]['address']
        for cmd in decoded['commands']
        for role in ['destination', 'source', 'secondary_source']
    }
    matched = [x for x in snapshot if x['device_pointer'] in addresses]
    (a.output / ('commands-K' + str(row['k']) + '.json')).write_text(
        json.dumps(decoded['commands'], indent=2))
    if len(matched) < 2:
        raise RuntimeError(
            'Actual SDK-translated addresses do not match native records ' +
            repr(dict(expected=snapshot, observed=sorted(addresses))))
    if streams and c['owner']['stream'] != int(
            streams[len(checks)].gcu_stream):
        raise RuntimeError('Captured invocation belongs to another stream')
    checks.append(
        dict(k=row['k'],
             binary_id=c['owner']['binary_id'],
             math_passed=True,
             matched_device_pointer_arguments=matched,
             intervals=len(batch['events']),
             positive_intervals=sum(e['end_tick'] > e['start_tick']
                                    for e in batch['events']),
             counter_ns_status=c['counter_ns_status']['status']))
if checks[0]['binary_id'] != checks[1]['binary_id'] or checks[0][
        'intervals'] >= checks[1]['intervals']:
    raise RuntimeError('Runtime-K structure changed incorrectly')
(a.output / 'result.json').write_text(
    json.dumps(dict(
        status=
        'public_GCU_GEMM_real_math_and_full_width_SDK_address_bindings_passed_not_dependency_qualification',
        calls=2,
        checks=checks),
               indent=2))
