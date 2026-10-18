"""Real math plus controlled host decode/guard faults, never unsafe device writes."""
import argparse
import importlib
import json
import os
from pathlib import Path
from unittest.mock import patch

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler
from flagtree.profiler.timeline_runtime import TimelineReadback, retained_owner_statuses
from flagtree.profiler.timeline_reexport import reexport_bundle


@triton.jit
def update(x, out, state, N: tl.constexpr):
    i = tl.program_id(0) * 256 + tl.arange(0, 256)
    active = i < N
    value = tl.load(x + i, active, 0)
    tl.store(out + i, value * 3 + 1, active)
    old = tl.load(state + i, active, 0)
    tl.store(state + i, old + 1, active)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    module = importlib.import_module('flagtree.profiler.profile')
    n = 1027
    cpu = torch.arange(n + 7, dtype=torch.int32) % 17
    x = cpu.npu()
    outputs = []

    def launch():
        out = torch.full_like(x, -1234)
        state = torch.zeros_like(x)
        update[(5, )](x, out, state, n, enable_auto_blockify=False)
        outputs.append((out, state))

    decode_base = args.output / 'decode-fault'
    session = profiler.start(str(decode_base),
                             backend='cann',
                             detail='timeline')
    collector = module._active_sessions[session]['timeline_hook']
    original_decode = collector._decode_timeline_original
    visits = []

    def fail_first(identity, directory, deadline):
        visits.append(identity)
        if len(visits) == 1:
            raise ValueError('controlled first decode failure')
        return original_decode(identity, directory, deadline)

    launch()
    launch()
    failed = False
    with patch.object(collector, '_decode_timeline_original', fail_first):
        try:
            profiler.finalize(session)
        except RuntimeError:
            failed = True
    directory = Path(collector._timeline_directory)
    originals = sorted(directory.glob('captures/*.input.json'))
    if not failed or len(originals) != 2 or len(
            visits) != 2 or retained_owner_statuses():
        raise RuntimeError(
            'Decode failure lost later raw or retained completed owners')
    restored = reexport_bundle(directory)
    if len(restored['captures']) != 2:
        raise RuntimeError(
            'Public offline recovery did not recover both calls')

    guard_base = args.output / 'guard-fault'
    session = profiler.start(str(guard_base),
                             backend='cann',
                             detail='timeline')
    collector = module._active_sessions[session]['timeline_hook']
    transport = collector.timeline_pool.transport
    original_read = transport.read_raw

    def bad_guard(owner):
        actual = original_read(owner)
        guard = bytes([actual.guard[0] ^ 1]) + actual.guard[1:]
        return TimelineReadback(actual.raw, guard,
                                ('controlled_guard_check_failure', ))

    launch()
    failed = False
    with patch.object(transport, 'read_raw', bad_guard):
        try:
            profiler.finalize(session)
        except RuntimeError:
            failed = True
    directory = Path(collector._timeline_directory)
    originals = sorted(directory.glob('captures/*.input.json'))
    if not failed or len(originals) != 1 or retained_owner_statuses():
        raise RuntimeError(
            'Guard failure lost bytes or retained completed storage')
    capture = json.loads(originals[0].read_text())
    if capture['owner']['readback_integrity']['status'] != 'invalid':
        raise RuntimeError('Injected readback integrity failure was hidden')
    if (directory / capture['readback_guard']['file']).read_bytes() == bytes(
        [165]) * 128:
        raise RuntimeError('Actual failed readback guard was not retained')
    try:
        reexport_bundle(directory)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            'Invalid guard obtained canonical export qualification')

    session = profiler.start(str(args.output / 'next-valid'),
                             backend='cann',
                             detail='timeline')
    try:
        launch()
    finally:
        profiler.finalize(session)
    for out, state in outputs:
        torch.testing.assert_close(out[:n].cpu(), (cpu * 3 + 1)[:n],
                                   rtol=0,
                                   atol=0)
        if not bool((state[:n].cpu() == 1).all()) or not bool(
            (state[n:].cpu() == 0).all()) or not bool(
                (out[n:].cpu() == -1234).all()):
            raise RuntimeError(
                'Fault recovery replayed or changed the user kernel')
    if not torch.equal(x.cpu(), cpu) or retained_owner_statuses():
        raise RuntimeError('Input or owner lifetime changed')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='real_math_host_fault_recovery_passed',
            user_kernel_calls=4,
            decode_calls_salvaged=2,
            guard_fault='host readback mutation after real device completion',
            invalid_guard_rejected=True,
            application_replayed=False,
            limits=
            'Controlled host fault injection, not a hardware failure recovery test'
        ),
                   indent=2))


if __name__ == '__main__':
    main()
