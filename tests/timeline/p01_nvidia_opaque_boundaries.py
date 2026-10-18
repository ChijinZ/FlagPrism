"""Real register-dependency primitive, not the automatic profiler or qualification.

A device-loaded runtime zero keeps math unchanged while creating actual PTX
bit/predicate dependencies. Only final machine inspection can establish that
those dependencies survived. No hardware completion barrier is inserted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def save(path, document):
    path.write_text(json.dumps(document, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--strategy',
                        choices=['vector_predicate', 'scalar_control_call'],
                        default='vector_predicate')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import torch
    import triton
    import triton.language as tl
    from flagtree.profiler.timeline_nvidia_machine import find_nvdisasm, _run_tool

    @triton.jit
    def entry(value, zero):
        if value.dtype == tl.int64:
            bits = value.to(tl.uint64, bitcast=True)
            wide_zero = zero.to(tl.uint64) | (zero.to(tl.uint64) << 32)
            forwarded, stamp = tl.inline_asm_elementwise(
                '{ .reg .b64 mask;\n'
                '// flagprism_opaque_primitive_begin64\n'
                'mov.u64 $1, %globaltimer;\n'
                'and.b64 mask, $1, $3;\n'
                'xor.b64 $0, $2, mask;\n}',
                constraints='=l,=l,l,l',
                args=[bits, wide_zero],
                dtype=(tl.uint64, tl.uint64),
                is_pure=False,
                pack=1)
        else:
            bits = value.to(tl.uint32, bitcast=True)
            forwarded, stamp = tl.inline_asm_elementwise(
                '{ .reg .b32 low, mask;\n'
                '// flagprism_opaque_primitive_begin32\n'
                'mov.u64 $1, %globaltimer;\n'
                'cvt.u32.u64 low, $1;\n'
                'and.b32 mask, low, $3;\n'
                'xor.b32 $0, $2, mask;\n}',
                constraints='=r,=l,r,r',
                args=[bits, zero],
                dtype=(tl.uint32, tl.uint64),
                is_pure=False,
                pack=1)
        return forwarded.to(value.dtype, bitcast=True), stamp

    @triton.jit
    def leave(value, zero):
        if value.dtype == tl.int64:
            bits = value.to(tl.uint64, bitcast=True)
            wide_zero = zero.to(tl.uint64) | (zero.to(tl.uint64) << 32)
            stamp = tl.inline_asm_elementwise(
                '{ .reg .pred ready; .reg .b64 mask;\n'
                '// flagprism_opaque_primitive_end64\n'
                'and.b64 mask, $1, $2;\n'
                'setp.eq.u64 ready, mask, 0;\n'
                'mov.u64 $0, 0;\n'
                '@ready mov.u64 $0, %globaltimer;\n}',
                constraints='=l,l,l',
                args=[bits, wide_zero],
                dtype=tl.uint64,
                is_pure=False,
                pack=1)
        else:
            bits = value.to(tl.uint32, bitcast=True)
            stamp = tl.inline_asm_elementwise(
                '{ .reg .pred ready; .reg .b32 mask;\n'
                '// flagprism_opaque_primitive_end32\n'
                'and.b32 mask, $1, $2;\n'
                'setp.eq.u32 ready, mask, 0;\n'
                'mov.u64 $0, 0;\n'
                '@ready mov.u64 $0, %globaltimer;\n}',
                constraints='=l,r,r',
                args=[bits, zero],
                dtype=tl.uint64,
                is_pure=False,
                pack=1)
        return stamp

    @triton.jit(noinline=True)
    def control_clock(shape):
        return tl.inline_asm_elementwise(
            '// flagprism_opaque_control_clock\nmov.u64 $0, %globaltimer;\n// shape $1',
            constraints='=l,r',
            args=[shape],
            dtype=tl.uint64,
            is_pure=False,
            pack=1)

    @triton.jit
    def leave_control(value, zero):
        if value.dtype == tl.int64:
            bits = value.to(tl.uint64, bitcast=True)
            wide_zero = zero.to(tl.uint64) | (zero.to(tl.uint64) << 32)
            mask = bits & wide_zero
        else:
            mask = value.to(tl.uint32, bitcast=True) & zero
        if mask == 0:
            result = control_clock(mask.to(tl.uint32))
        else:
            result = tl.full((), 0, tl.uint64)
        return result

    @triton.jit
    def update(X, Y, K, Zero, T, State, N: tl.constexpr, MAX_K: tl.constexpr,
               OBSERVE: tl.constexpr, B: tl.constexpr, SCALAR: tl.constexpr):
        pid = tl.program_id(0)
        lane = tl.full((), 0, tl.int32) if SCALAR else tl.arange(0, B)
        i = pid if SCALAR else pid * B + lane
        active = i < N
        value = tl.load(X + i, active, 0)
        k = tl.load(K)
        if OBSERVE:
            zero = tl.load(Zero, volatile=True).to(tl.uint32)
        for iteration in range(k):
            if OBSERVE:
                value, begin = entry(value, zero)
            if value.dtype == tl.int64:
                value = value ^ (value << 1)
            else:
                value = value * 0.5 + 0.25
            if OBSERVE:
                end = leave_control(value, zero) if SCALAR else leave(
                    value, zero)
                tl.store(T + i * MAX_K * 2 + iteration * 2, begin, active)
                tl.store(T + i * MAX_K * 2 + iteration * 2 + 1, end, active)
        tl.store(Y + i, value, active)
        state = tl.load(State + pid + lane, lane == 0, 0)
        tl.store(State + pid + lane, state + 1, lane == 0)

    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability(0) == (12, 0), 'Unexpected target')
    tool = find_nvdisasm()
    need(tool is not None, 'Actual nvdisasm is required for this experiment')
    scalar = args.strategy == 'scalar_control_call'
    n, max_k, block = (3, 16, 1) if scalar else (129, 16, 64)
    registration = dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        target='sm_120',
        strategy=args.strategy,
        runtime_k=[3, 7],
        elements=n,
        block=block,
        grid=[3, 1, 1],
        max_k=max_k,
        dtypes=['float32', 'int64'],
        modes=['ordinary', 'opaque'],
        numerical_check='exact CPU output/input/state/tail',
        opaque_zero='explicit private read-only runtime device input',
        completion_barrier_added=False,
        scope=
        'handwritten dependency development primitive; not automatic profiling'
    )
    save(args.output / 'registration.json', registration)
    cases = []
    for dtype in [torch.float32, torch.int64]:
        for observed in [False, True]:
            name = ('fp32' if dtype == torch.float32 else
                    'int64') + ('-opaque' if observed else '-ordinary')
            directory = args.output / name
            directory.mkdir()
            source = torch.arange(n, dtype=dtype) - 64
            x = source.cuda()
            y = torch.full((n + 7, ), -711, dtype=dtype, device='cuda')
            k = torch.tensor([3], dtype=torch.int32, device='cuda')
            zero = torch.zeros(1, dtype=torch.int32, device='cuda')
            stamps = torch.full((n * max_k * 2 + 8, ),
                                -1,
                                dtype=torch.int64,
                                device='cuda')
            state = torch.zeros(3, dtype=torch.int32, device='cuda')
            inputs = (x, y, k, zero, stamps, state)
            config = dict(N=n,
                          MAX_K=max_k,
                          OBSERVE=observed,
                          B=block,
                          num_warps=4,
                          enable_fp_fusion=False,
                          SCALAR=scalar)
            compiled = update.warmup(*inputs, **config, grid=(3, ))
            compiled._init_handles()
            need(state.cpu().tolist() == [0, 0, 0],
                 'Compile-only invoked user math')
            artifacts = {}
            for kind in ['ttir', 'ttgir', 'llir', 'ptx', 'cubin']:
                data = compiled.asm[kind]
                if isinstance(data, str):
                    data = data.encode()
                (directory / ('kernel.' + kind)).write_bytes(data)
                artifacts[kind] = dict(bytes=len(data),
                                       sha256=hashlib.sha256(data).hexdigest())
            save(directory / 'artifacts.json', artifacts)
            commands = []
            deadline = time.monotonic() + 35
            for label, flags in [
                ('version', ['--version']),
                ('lines', [
                    '--print-code', '--print-line-info-ptx',
                    str(directory / 'kernel.cubin')
                ]),
                ('machine', ['--emit-json',
                             str(directory / 'kernel.cubin')])
            ]:
                _run_tool(tool, flags, directory, label, deadline, commands)
            for trial, count in enumerate([3, 7]):
                k.copy_(torch.tensor([count], dtype=torch.int32,
                                     device='cuda'))
                stamps.fill_(-1)
                actual = update[(3, )](*inputs, **config)
                torch.cuda.synchronize()
                expected = source.clone()
                for _ in range(count):
                    expected = expected ^ (
                        expected << 1
                    ) if dtype == torch.int64 else expected * 0.5 + 0.25
                output, ticks = y.cpu(), stamps.cpu()
                need(torch.equal(output[:n], expected),
                     'Exact CPU math failed')
                need(
                    torch.equal(x.cpu(), source)
                    and output[n:].tolist() == [-711] * 7,
                    'Input/output tail changed')
                need(state.cpu().tolist() == [trial + 1] * 3,
                     'Math call was replayed')
                need(zero.cpu().tolist() == [0],
                     'Private runtime zero was modified')
                need(
                    hashlib.sha256(actual.asm['cubin']).hexdigest() ==
                    artifacts['cubin']['sha256'],
                    'Runtime K changed the actual binary')
                positive = 0
                if observed:
                    for i in range(n):
                        pairs = ticks[i * max_k * 2:i * max_k * 2 +
                                      count * 2].reshape(count, 2)
                        need(
                            bool((pairs > 0).all()) and bool(
                                (pairs[:, 1] >= pairs[:, 0]).all()),
                            'Actual timer was zero or reversed')
                        positive += int((pairs[:, 1] > pairs[:, 0]).sum())
                        need(
                            bool((ticks[i * max_k * 2 + count * 2:(i + 1) *
                                        max_k * 2] == -1).all()),
                            'Unexecuted iterations acquired timestamps')
                    need(positive > 0, 'No positive real intervals')
                else:
                    need(bool((ticks == -1).all()),
                         'Ordinary control wrote observer records')
                need(ticks[-8:].tolist() == [-1] * 8,
                     'Timestamp allocation tail changed')
                (directory / ('ticks-' + str(count) + '.bin')).write_bytes(
                    ticks.numpy().tobytes())
                row = dict(case=name,
                           trial=trial,
                           k=count,
                           cubin_sha256=artifacts['cubin']['sha256'],
                           requested_user_launches=1,
                           exact_math_input_tail_state=True,
                           intervals=n * count if observed else 0,
                           positive_intervals=positive)
                cases.append(row)
                save(args.output / 'cases.json', cases)
    save(
        args.output / 'result.json',
        dict(
            status=
            'real_math_dependency_primitive_passed_pending_final_dependency_audit',
            cases=cases,
            limits=[
                'Handwritten primitive, not public automatic collector',
                'No final-object boundary qualification until actual dependency audit',
                'No source-latency, epoch, async, engine-busy or performance certificate'
            ]))


if __name__ == '__main__':
    main()
