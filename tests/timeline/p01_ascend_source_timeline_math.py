"""Real Ascend producer development probe, not deferred-owner qualification.

Ordinary kernels contain no profiler annotations. The generic development hook
uses an explicit post-launch synchronization, so it cannot qualify concurrent
capture, preserved inter-stream ordering, source boundaries or clock units.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import debugger
from flagtree.debugger import api
from flagtree.profiler.observations import ObservationRequest


@triton.jit
def recurrence(x, out, state, iterations, N: tl.constexpr):
    index = tl.program_id(0) * 256 + tl.arange(0, 256)
    active = index < N
    value = tl.load(x + index, active, 0)
    count = tl.load(iterations)
    for iteration in range(count):
        value = value * 1.001 + 0.01
    tl.store(out + index, value, active)
    previous = tl.load(state + index, active, 0)
    tl.store(state + index, previous + 1, active)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(4)
    n = 1027
    cpu = torch.linspace(-0.5, 0.5, n + 7, dtype=torch.float32)
    x = cpu.npu()
    captures, retained = [], []
    capacity = 128
    grid = (triton.cdiv(n, 256), 1, 1)
    programs = [0, grid[0] - 1]
    raw_bytes = len(programs) * 3 * (64 + capacity * 64)

    def prepare(metadata, stream, launch_metadata, kernel_args):
        actual = api._build_launch_metadata_dict(metadata)
        if actual.get('debug_record_layout') != 'ascend_source_timeline_v1':
            raise ValueError('Unexpected producer layout')
        storage = torch.empty(raw_bytes + 128, dtype=torch.uint8, device=x.device)
        retained.append(storage)  # Hold through errors and any in-flight writer.
        storage.zero_()
        storage[:64].fill_(0xa5)
        storage[-64:].fill_(0xa5)
        pointer = int(storage.data_ptr()) + 64
        if pointer % 64:
            raise RuntimeError('Actual allocation is not cache-line aligned')

        def finalize(error):
            if error is not None:
                return
            # launch_context has explicitly completed this development launch.
            data = storage.cpu().numpy().tobytes()
            raw = data[64:-64]
            ordinal = len(captures)
            (args.output / f'capture-{ordinal}.raw').write_bytes(raw)
            (args.output / f'capture-{ordinal}.metadata.json').write_text(
                json.dumps(actual, indent=2, default=str))
            if data[:64] != bytes([0xa5]) * 64 or data[-64:] != bytes([0xa5]) * 64:
                raise RuntimeError('Timeline allocation guard changed')
            actors = []
            for slot, program in enumerate(programs):
                for actor in range(3):
                    base = (slot * 3 + actor) * (64 + capacity * 64)
                    header = struct.unpack_from('<8Q', raw, base)
                    if not any(header):
                        continue
                    magic, committed, attempted, dropped, pid, who, block, flags = header
                    if (magic != 0x46505441314c4f47 or committed > capacity
                            or attempted != committed + dropped or dropped
                            or pid != program or who != actor or flags != 1):
                        raise RuntimeError('Invalid producer header')
                    intervals = []
                    for record in range(committed):
                        pair = struct.unpack_from('<8Q', raw, base + 64 + record * 64)
                        descriptor, sequence, start, end, p, a, physical, tag = pair
                        if (sequence != record or descriptor >> 32 != 1 or not descriptor & 0xffffffff
                                or p != program or a != actor or physical != block or end < start
                                or tag != (0x46505441434f4d31 ^ descriptor ^ sequence ^ p ^ a ^ physical)):
                            raise RuntimeError('Invalid committed device pair')
                        intervals.append(dict(site=descriptor & 0xffffffff, start=start, end=end))
                    actors.append(dict(program=program, actor=actor, physical_block=block,
                                       committed=committed, intervals=intervals))
            if not actors:
                raise RuntimeError('Device producer wrote no records')
            captures.append(dict(raw_sha256=hashlib.sha256(raw).hexdigest(), actors=actors))
        return api.PreparedKernelLaunch(kernel_args=(pointer,), finalize=finalize, synchronize=True)

    results = []
    for profiled in (False, True):
        if profiled:
            request = ObservationRequest(programs=None, program_policy='runtime_first_last',
                                         automatic=True, max_sites=8, max_events_per_instance=capacity)
            debugger.activate(auto_collect=True, record_capacity=capacity,
                              observation_request=request.as_dict())
            debugger.register_launch_prepare_hook(prepare)
        try:
            for k in (3, 7):
                out = torch.full_like(x, 1234)
                state = torch.zeros(n + 7, dtype=torch.int32, device=x.device)
                count = torch.tensor([k], dtype=torch.int32, device=x.device)
                kernel = recurrence[grid](x, out, state, count, n, enable_auto_blockify=False)
                torch.npu.synchronize()
                expected = cpu[:n].clone()
                for _ in range(k):
                    expected = expected * 1.001 + 0.01
                torch.testing.assert_close(out[:n].cpu(), expected, rtol=1e-5, atol=1e-6)
                if not torch.equal(x.cpu(), cpu) or not bool((state[:n].cpu() == 1).all()):
                    raise RuntimeError('Input or mathematical side effect changed')
                if not bool((state[n:].cpu() == 0).all()) or not bool((out[n:].cpu() == 1234).all()):
                    raise RuntimeError('Mathematical tail changed')
                results.append(dict(profiled=profiled, k=k, binary=kernel.hash))
        finally:
            if profiled:
                debugger.deactivate()
    if results[0]['binary'] != results[1]['binary'] or results[2]['binary'] != results[3]['binary']:
        raise RuntimeError('Runtime K unexpectedly changed binary')
    (args.output / 'result.json').write_text(json.dumps(dict(
        status='real_device_raw_producer_probe_not_P01', calls=results, captures=captures,
        source_boundaries='unverified', clock_units='unverified', concurrent_owner='not_tested'), indent=2))


if __name__ == '__main__':
    main()
