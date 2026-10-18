"""Actual compiler handoff/derive/copy faults with default API math and recovery.

Faults are explicit host-side fixtures; no malformed binary is sent to a GPU.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import torch
import triton
import triton.language as tl
from triton.backends import backends
from flagtree import profiler
from flagtree.profiler.hooks.hook import HookManager
from flagtree.profiler.hooks.timeline_late import LateTimelineHook
from flagtree.profiler.timeline_nvidia_late_compile import LateCompileError


def need(value, message):
    if not value:
        raise RuntimeError(message)


@triton.jit
def affine(X, Y, Calls, N: tl.constexpr, B: tl.constexpr):
    pid = tl.program_id(0)
    offset = pid * B + tl.arange(0, B)
    value = tl.load(X + offset, offset < N, 0.0)
    output = value * 0.75 + 0.125
    tl.store(Y + offset, output, offset < N)
    tl.atomic_add(Calls + pid, 1, sem='relaxed')


def check(cpu, x, y, calls, grid):
    need(
        torch.allclose(y[:cpu.numel()].cpu().double(),
                       cpu.double() * 0.75 + 0.125,
                       rtol=2e-6,
                       atol=2e-6), 'Original affine math')
    need(torch.equal(y[cpu.numel():].cpu(), torch.full((7, ), 1234.)),
         'Original tail guard')
    need(torch.equal(x.cpu(), cpu), 'Original input')
    need(calls.cpu().tolist() == [1] * grid + [0], 'Hidden application replay')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.cuda.set_device(0)
    torch.manual_seed(37051)
    cpu = torch.randn(1003)
    x = cpu.cuda()
    first = torch.full((1010, ), 1234., device='cuda')
    second = torch.full_like(first, 1234.)
    calls_a = torch.zeros(3, dtype=torch.int32, device='cuda')
    calls_b = torch.zeros(5, dtype=torch.int32, device='cuda')
    bundle = a.output / 'profile'
    session = profiler.start(str(bundle), detail='timeline')
    hooks = [
        hook for hook in HookManager.active_hooks
        if isinstance(hook, LateTimelineHook)
    ]
    need(len(hooks) == 1, 'Missing actual default late hook')
    hook = hooks[0]
    affine[(2, )](x, first, calls_a, 1003, 512, num_warps=4)
    check(cpu, x, first, calls_a, 2)
    manager = backends['nvidia'].compiler.instrumentation.manager
    transform = manager['optimized_llvm']
    manager['optimized_llvm'] = lambda text, metadata: transform(
        'intentional invalid LLVM handoff fixture', metadata)
    try:
        try:
            affine[(4, )](x, second, calls_b, 1003, 256, num_warps=8)
        except LateCompileError as error:
            compile_error = str(error)
        else:
            raise RuntimeError(
                'Injected native compiler failure did not reach the real tool')
        need(calls_b.cpu().tolist() == [0] * 5,
             'Failed compilation launched the kernel')
        need(torch.equal(second.cpu(), torch.full((1010, ), 1234.)),
             'Failed compilation touched user output')
    finally:
        manager['optimized_llvm'] = transform
    affine[(4, )](x, second, calls_b, 1003, 256, num_warps=8)
    check(cpu, x, second, calls_b, 4)
    original_decode = hook._decode_timeline_original
    attempted = []

    def fail_first(identity, directory, deadline):
        attempted.append(identity)
        if len(attempted) == 1:
            raise RuntimeError('controlled late derived-output failure')
        return original_decode(identity, directory, deadline)

    hook._decode_timeline_original = fail_first
    try:
        profiler.finalize(session)
    except RuntimeError as error:
        need(
            isinstance(error.__cause__, RuntimeError) and str(
                error.__cause__) == 'controlled late derived-output failure',
            'Finalization lost the original error cause')
        derive_error = str(error)
    else:
        raise RuntimeError('Injected derived failure did not surface')
    directory = Path(hook._timeline_directory)
    inputs = sorted((directory / 'captures').glob('*.input.json'))
    need(
        len(inputs) == 2 and not hook.timeline_pool.invocation_ids,
        'One derived failure prevented raw salvage/release of the other call')
    retained = json.loads(
        (directory / 'compiler-attempts/index.json').read_text())['artifacts']
    receipts = [
        json.loads((directory / row['file']).read_text()) for row in retained
        if row['file'].endswith('/compile-receipt.json')
    ]
    need(
        receipts and any(row['state'] == 'failed' and row['returncode'] != 0
                         for row in receipts),
        'Failed native compiler receipt was not retained with actual process identity'
    )
    for row in receipts:
        need(
            type(row['pid']) is int and type(row['startticks']) is int
            and row['argv'],
            'Retained compiler process identity is incomplete')
    raw_hashes = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob('*.raw')
    }
    hook._decode_timeline_original = original_decode
    original_copy = hook._retain_compiler_attempts

    def copy_failure(*args):
        raise OSError('controlled compiler-receipt copy failure')

    hook._retain_compiler_attempts = copy_failure
    try:
        hook.flush_timeline(hook._late_base)
    except OSError as error:
        need(
            str(error) == 'controlled compiler-receipt copy failure',
            'Copy failure was hidden')
        copy_error = str(error)
    else:
        raise RuntimeError(
            'Injected compiler receipt copy failure did not surface')
    need(not hook.timeline_pool.invocation_ids,
         'Copy failure retained already durable device buffers')
    hook._retain_compiler_attempts = original_copy
    for path, digest in raw_hashes.items():
        need(
            hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest,
            'Recovery changed original raw')
    hook.flush_timeline(hook._late_base)
    check(cpu, x, first, calls_a, 2)
    check(cpu, x, second, calls_b, 4)
    final = a.output / 'recovered-timeline'
    shutil.copytree(directory, final)
    temporary = hook._late_base.parent
    need(
        temporary.name.startswith('flagprism-session-')
        and directory.parent == temporary,
        'Unexpected recovery staging ownership')
    shutil.rmtree(temporary)
    index = json.loads((final / 'index.json').read_text())
    need(
        len(index['captures']) == 2 and not index['failures']
        and not index['pending_decode'] and not index['retained_owners'],
        'Recovery did not complete final bundle')
    need(not directory.exists(),
         'Recovered bundle still depends on temporary staging')
    ledger = json.loads(
        (final / 'compiler-attempts/index.json').read_text())['artifacts']
    for row in ledger:
        data = (final / row['file']).read_bytes()
        need(
            len(data) == row['bytes']
            and hashlib.sha256(data).hexdigest() == row['sha256'],
            'Compiler artifact changed after temporary staging cleanup')
    traces = 0
    for item in index['captures']:
        capture = json.loads((final / item['capture_file']).read_text())
        need(
            capture['capture_status'] == 'raw_complete'
            and capture['counter_ns_status']['status'] == 'counter_unit_only',
            'Recovered default time view is unavailable')
        traces += len(capture['counter_ns_exports'])
    need(traces == 16, 'Expected two real calls with eight thread views each')
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_default_math_compile_derive_copy_faults_and_durable_receipt_recovery_passed_not_full_pipeline',
            compiler_failure=compile_error,
            derived_failure=derive_error,
            copy_failure=copy_error,
            successful_kernel_launches=2,
            failed_compile_kernel_launches=0,
            original_calls_unchanged_after_recovery=True,
            recovery_path=
            "documented retained-hook flush then durable bundle copy; finalized session IDs are no-ops",
            retained_compiler_receipts=len(receipts),
            retained_compiler_artifacts=len(ledger),
            traces=traces),
                   indent=2))


if __name__ == '__main__':
    main()
