"""Dedicated causal clock calibration using real two-CTA producer/consumer math.

Not a public profiling, async-operator, scale or full epoch qualification. The
four reads constrain relative clock offset by release/acquire causality. Every
spin is bounded; no sleep, application replay, global timer fitting or driver
setting changes. Final instruction/control ordering still requires inspection.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time


def need(value, message):
    if not value:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    registration = dict(target='cuda:120', device=0, grid=2, block=128,
        num_warps=32, rounds=64, max_spins=100000, explicit_math_launches=3,
        producer_math='v = 0.75 * v + 0.125',
        consumer_math='y = 0.5 * published_v + 0.25',
        rtol=2e-6, atol=2e-6, spin_timeout_is_failure=True,
        scale_hypothesis_only='1 ns/tick; separate scale evidence required',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save(a.output/'registration.json', registration)
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def exchange(X, Payload, Y, Ready, Ack, T, SM, State, Error,
                 ROUNDS: tl.constexpr, MAX_SPINS: tl.constexpr,
                 BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        lane = tl.arange(0, BLOCK)
        completed = 0
        old_state = tl.load(State + pid)
        previous = tl.full((), 0, tl.int64)
        if pid == 0:
            value = tl.load(X + lane)
            r = 0
            failed = 0
            while (r < ROUNDS) & (failed == 0):
                value = value * 0.75 + 0.125
                tl.store(Payload + lane, value)
                # Dedicated calibration synchronization, never injected into
                # user math: publish only after all CTA payload stores finish.
                tl.debug_barrier()
                begin = tl.inline_asm_elementwise('mov.u64 $0, %globaltimer;',
                    constraints='=l', args=[], dtype=tl.uint64,
                    is_pure=False, pack=1).to(tl.int64)
                sm_begin = tl.inline_asm_elementwise('mov.u32 $0, %smid;',
                    constraints='=r', args=[], dtype=tl.int32,
                    is_pure=False, pack=1)
                tl.atomic_xchg(Ready, begin, sem='release', scope='gpu')
                reply = tl.atomic_add(Ack, 0, sem='acquire', scope='gpu')
                spins = 0
                while (reply <= previous) & (reply != -1) & (spins < MAX_SPINS):
                    reply = tl.atomic_add(Ack, 0, sem='acquire', scope='gpu')
                    spins += 1
                if (reply == -1) | (reply <= previous):
                    tl.store(Error + pid, 1)
                    tl.atomic_xchg(Ready, -1, sem='release', scope='gpu')
                    failed = 1
                else:
                    finish = tl.inline_asm_elementwise('mov.u64 $0, %globaltimer;',
                        constraints='=l', args=[], dtype=tl.uint64,
                        is_pure=False, pack=1).to(tl.int64)
                    sm_finish = tl.inline_asm_elementwise('mov.u32 $0, %smid;',
                        constraints='=r', args=[], dtype=tl.int32,
                        is_pure=False, pack=1)
                    tl.store(T + r * 4, begin)
                    tl.store(T + r * 4 + 3, finish)
                    tl.store(SM + r * 4, sm_begin)
                    tl.store(SM + r * 4 + 3, sm_finish)
                    previous = reply
                    completed += 1
                r += 1
        else:
            r = 0
            failed = 0
            while (r < ROUNDS) & (failed == 0):
                token = tl.atomic_add(Ready, 0, sem='acquire', scope='gpu')
                spins = 0
                while (token <= previous) & (token != -1) & (spins < MAX_SPINS):
                    token = tl.atomic_add(Ready, 0, sem='acquire', scope='gpu')
                    spins += 1
                if (token == -1) | (token <= previous):
                    tl.store(Error + pid, 2)
                    tl.atomic_xchg(Ack, -1, sem='release', scope='gpu')
                    failed = 1
                else:
                    receive = tl.inline_asm_elementwise('mov.u64 $0, %globaltimer;',
                        constraints='=l', args=[], dtype=tl.uint64,
                        is_pure=False, pack=1).to(tl.int64)
                    sm_receive = tl.inline_asm_elementwise('mov.u32 $0, %smid;',
                        constraints='=r', args=[], dtype=tl.int32,
                        is_pure=False, pack=1)
                    value = tl.load(Payload + lane) * 0.5 + 0.25
                    tl.store(Y + r * BLOCK + lane, value)
                    tl.debug_barrier()
                    # The result controls the end observation; actual final
                    # machine ordering is audited rather than assumed from IR.
                    if tl.sum(value, 0) > 0:
                        respond = tl.inline_asm_elementwise('mov.u64 $0, %globaltimer;',
                            constraints='=l', args=[], dtype=tl.uint64,
                            is_pure=False, pack=1).to(tl.int64)
                        sm_respond = tl.inline_asm_elementwise('mov.u32 $0, %smid;',
                            constraints='=r', args=[], dtype=tl.int32,
                            is_pure=False, pack=1)
                        tl.store(T + r * 4 + 1, receive)
                        tl.store(T + r * 4 + 2, respond)
                        tl.store(SM + r * 4 + 1, sm_receive)
                        tl.store(SM + r * 4 + 2, sm_respond)
                        tl.atomic_xchg(Ack, respond, sem='release', scope='gpu')
                    else:
                        tl.store(Error + pid, 3)
                        tl.atomic_xchg(Ack, -1, sem='release', scope='gpu')
                        failed = 1
                    previous = token
                    if failed == 0:
                        completed += 1
                r += 1
        tl.store(State + pid, old_state + completed)

    torch.cuda.set_device(0)
    props = torch.cuda.get_device_properties(0)
    need((props.major, props.minor) == (12, 0), 'Wrong registered target')
    need(props.max_threads_per_multi_processor < 2 * 32 * 32,
         'Registered one-CTA-per-SM occupancy condition absent')
    rounds, block = registration['rounds'], registration['block']
    x_cpu = torch.linspace(0.25, 1.25, block, dtype=torch.float32)
    x = x_cpu.cuda()
    payload = torch.full((block+3,), -777., device='cuda')
    y = torch.full((rounds*block+3,), -777., device='cuda')
    ready = torch.zeros((), dtype=torch.int64, device='cuda')
    ack = torch.zeros((), dtype=torch.int64, device='cuda')
    stamps = torch.full((rounds*4+4,), -1, dtype=torch.int64, device='cuda')
    smids = torch.full((rounds*4+4,), -1, dtype=torch.int32, device='cuda')
    state = torch.zeros(2, dtype=torch.int32, device='cuda')
    error = torch.zeros(2, dtype=torch.int32, device='cuda')
    inputs = (x, payload, y, ready, ack, stamps, smids, state, error)
    config = dict(ROUNDS=rounds, MAX_SPINS=registration['max_spins'],
                  BLOCK=block, num_warps=32)
    compiled = exchange.warmup(*inputs, **config, grid=(2,))
    compiled._init_handles()
    need(state.cpu().tolist() == [0, 0], 'Compile-only executed real math')
    need(compiled.metadata.num_warps == 32, 'Actual launch occupancy changed')
    artifacts = []
    for kind, data in compiled.asm.items():
        if isinstance(data, str):
            data = data.encode()
        if not isinstance(data, bytes):
            continue
        path = a.output/('exchange.'+kind)
        path.write_bytes(data)
        artifacts.append(dict(path=path.name, bytes=len(data),
                              sha256=hashlib.sha256(data).hexdigest()))
    save(a.output/'compiled-artifacts.json', artifacts)
    expected, v = [], x_cpu.clone()
    for _ in range(rounds):
        v = v * 0.75 + 0.125
        expected.append(v * 0.5 + 0.25)
    expected = torch.stack(expected)
    calls = []
    for trial in range(registration['explicit_math_launches']):
        ready.zero_(); ack.zero_(); error.zero_()
        stamps.fill_(-1); smids.fill_(-1); y.fill_(-777.)
        torch.cuda.synchronize()
        host_before = time.monotonic_ns()
        actual = exchange[(2,)](*inputs, **config)
        torch.cuda.synchronize()
        host_after = time.monotonic_ns()
        raw = stamps.cpu().tolist(); sm = smids.cpu().tolist()
        output = y.cpu(); errors = error.cpu().tolist(); states = state.cpu().tolist()
        row = dict(trial=trial, host_before_ns=host_before,
            host_after_ns=host_after, ticks=[raw[i:i+4] for i in range(0,rounds*4,4)],
            smids=[sm[i:i+4] for i in range(0,rounds*4,4)],
            errors=errors, state=states,
            binary_sha256=hashlib.sha256(actual.asm['cubin']).hexdigest(),
            output_sha256=hashlib.sha256(output.numpy().tobytes()).hexdigest())
        calls.append(row); save(a.output/'calls.json', calls)
        need(errors == [0, 0], 'Bounded clock handshake timed out or math failed')
        need(actual is compiled, 'Changed actual binary during calibration')
        need(states == [rounds*(trial+1)]*2, 'Requested math/replay count changed')
        need(torch.allclose(output[:rounds*block].reshape(rounds,block), expected,
                            rtol=2e-6, atol=2e-6), 'Published/consumed math incorrect')
        need(torch.equal(x.cpu(), x_cpu), 'Input changed')
        need(output[rounds*block:].tolist() == [-777.]*3 and
             payload.cpu()[block:].tolist() == [-777.]*3, 'Math tail corrupted')
        need(raw[rounds*4:] == [-1]*4 and sm[rounds*4:] == [-1]*4,
             'Timestamp/SM tail corrupted')
        offset_intervals = []
        for ticks, ids in zip(row['ticks'], row['smids']):
            aa, bb, cc, dd = ticks
            need(all(0 < n < 2**63 for n in ticks), 'Invalid actual getter')
            need(aa < dd and bb <= cc, 'Local clock regressed')
            need(ids[0] == ids[3] and ids[1] == ids[2] and ids[0] != ids[1],
                 'Did not observe two stable, distinct actual SMs')
            # If device clock b = clock a + delta, causality gives
            # b_reply-a_receive <= delta <= b_receive-a_publish.
            offset_intervals.append((cc-dd, bb-aa))
        lo = max(n[0] for n in offset_intervals)
        hi = min(n[1] for n in offset_intervals)
        row['causal_offset_tick_interval'] = [lo, hi]
        row['zero_offset_consistent'] = lo <= 0 <= hi
        row['offset_interval_width_ticks'] = hi-lo
        row['distinct_sm_pairs'] = sorted({(n[0],n[1]) for n in row['smids']})
        row['exact_math_input_tail_and_once_passed'] = True
        diffs = [abs(v-u) for ticks in row['ticks'] for u,v in zip(ticks,ticks[1:]) if v!=u]
        row['observed_delta_gcd_ticks'] = math.gcd(*diffs)
        save(a.output/'calls.json', calls)
        need(lo <= hi, 'No fixed offset is consistent with causal observations')
    save(a.output/'result.json', dict(
        status='real_causal_clock_constraints_acquired_not_yet_machine_audited',
        registration=registration, device=str(props), device_uuid=str(props.uuid),
        installed_python=os.path.realpath(os.sys.executable),
        cuda_runtime=torch.version.cuda, torch=torch.__version__,
        calls=calls, artifacts=artifacts,
        limits=['Four-read ordering must be checked in final machine object',
                'Bounds apply to the observed SM pairs and acquisition window',
                'Raw tick offset constraints are not an absolute endpoint error certificate',
                'Separate target clock scale and quantization evidence required',
                'Dedicated calibration synchronization is not injected into user kernels']))


if __name__ == '__main__':
    main()
