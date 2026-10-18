"""Real SM120 bit/selector semantics used by native payload value rules.

Mechanism validation only; these kernels do not count as independent math
qualification and no performance/overhead result is measured.
"""
import argparse
import hashlib
import itertools
import json
import random
import time
from pathlib import Path

import torch
import triton
import triton.language as tl


@triton.jit
def _lut(A, B, C, O, N: tl.constexpr, ASM: tl.constexpr):
    i = tl.program_id(0) * 128 + tl.arange(0, 128)
    a = tl.load(A + i, i < N, 0).to(tl.uint32)
    b = tl.load(B + i, i < N, 0).to(tl.uint32)
    c = tl.load(C + i, i < N, 0).to(tl.uint32)
    value = tl.inline_asm_elementwise(ASM,
                                      constraints='=r,r,r,r',
                                      args=[a, b, c],
                                      dtype=tl.uint32,
                                      is_pure=False,
                                      pack=1)
    tl.store(O + i, value, i < N)


@triton.jit
def _select(A, B, P, O, N: tl.constexpr):
    i = tl.program_id(0) * 128 + tl.arange(0, 128)
    a = tl.load(A + i, i < N, 0).to(tl.uint64)
    b = tl.load(B + i, i < N, 0).to(tl.uint64)
    p = tl.load(P + i, i < N, 0).to(tl.uint32)
    value = tl.inline_asm_elementwise(
        '{ .reg .pred pick; setp.ne.u32 pick, $1, 0; selp.b64 $0, $2, $3, pick; }',
        constraints='=l,r,l,l',
        args=[p, a, b],
        dtype=tl.uint64,
        is_pure=False,
        pack=1)
    tl.store(O + i, value, i < N)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    torch.cuda.set_device(0)
    if torch.cuda.get_device_capability() != (12, 0):
        raise RuntimeError('Native word rules require actual SM120')
    from flagtree.profiler.timeline_nvidia_machine import find_nvdisasm, _run_tool
    tool = find_nvdisasm()
    if tool is None:
        raise RuntimeError('Actual native disassembler unavailable')
    rng = random.Random(144031)
    inputs = list(itertools.product((0, 0xffffffff), repeat=3))
    inputs += [
        tuple(rng.getrandbits(32) for _ in range(3)) for _ in range(249)
    ]
    signed = lambda value: value if value < (1 << 31) else value - (1 << 32)
    arrays = [
        torch.tensor([signed(row[j]) for row in inputs],
                     dtype=torch.int32,
                     device='cuda') for j in range(3)
    ]
    n = len(inputs)
    reports = []

    def retain(name, kernel):
        folder = args.output / name
        folder.mkdir()
        (folder / 'actual.ptx').write_text(kernel.asm['ptx'])
        (folder / 'actual.cubin').write_bytes(kernel.asm['cubin'])
        commands = []
        lines = _run_tool(
            tool,
            ['--print-code', str(folder / 'actual.cubin')], folder, 'lines',
            time.monotonic() + 20, commands)
        native = _run_tool(
            tool, ['--emit-json', str(folder / 'actual.cubin')], folder,
            'json',
            time.monotonic() + 20, commands)
        doc = json.loads(native)
        if doc[0]['SM']['version']['major'] != 12 or doc[0]['SM']['version'][
                'minor'] != 0:
            raise RuntimeError('Actual machine target differs')
        opcodes = [
            row['opcode'] for fn in doc[1] for row in fn['sass-instructions']
        ]
        return dict(
            ptx_sha256=hashlib.sha256(
                (folder / 'actual.ptx').read_bytes()).hexdigest(),
            cubin_sha256=hashlib.sha256(kernel.asm['cubin']).hexdigest(),
            sass_sha256=hashlib.sha256(lines).hexdigest(),
            opcodes=sorted(set(opcodes)),
            disassembler_sha256=hashlib.sha256(tool.read_bytes()).hexdigest())

    for lut in (0xfc, 0xc0, 0x3c, 0xf8, 0x78):
        output = torch.empty(n, dtype=torch.int32, device='cuda')
        kernel = _lut[(triton.cdiv(n, 128), )](
            *arrays,
            output,
            n,
            ASM='lop3.b32 $0, $1, $2, $3, ' + str(lut) + ';')
        torch.cuda.synchronize()
        expected = []
        for a, b, c in inputs:
            value = 0
            for bit in range(32):
                selector = (((a >> bit) & 1) << 2) | ((
                    (b >> bit) & 1) << 1) | ((c >> bit) & 1)
                value |= ((lut >> selector) & 1) << bit
            expected.append(signed(value))
        if output.cpu().tolist() != expected:
            raise RuntimeError('Actual native LUT semantics differ')
        evidence = retain('lut-' + str(lut), kernel)
        if 'LOP3.LUT' not in evidence['opcodes']:
            raise RuntimeError(
                'No actual native LUT operation in the retained object')
        reports.append(
            dict(kind='lut', lut=lut, samples=n, math=True, **evidence))
    a = [rng.getrandbits(63) for _ in range(n)]
    b = [rng.getrandbits(63) for _ in range(n)]
    pred = [i % 2 for i in range(n)]
    tensors = [
        torch.tensor(a, dtype=torch.int64, device='cuda'),
        torch.tensor(b, dtype=torch.int64, device='cuda'),
        torch.tensor(pred, dtype=torch.int32, device='cuda')
    ]
    output = torch.empty(n, dtype=torch.int64, device='cuda')
    kernel = _select[(triton.cdiv(n, 128), )](*tensors, output, n)
    torch.cuda.synchronize()
    if output.cpu().tolist() != [
            left if pick else right for left, right, pick in zip(a, b, pred)
    ]:
        raise RuntimeError('Actual native wide selector differs')
    evidence = retain('select64', kernel)
    if 'SEL.64' not in evidence['opcodes']:
        raise RuntimeError(
            'Actual test did not exercise a native wide selector')
    reports.append(dict(kind='select64', samples=n, math=True, **evidence))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_SM120_payload_ALU_semantics_passed_not_timeline_or_independent_math_qualification',
            reports=reports),
                   indent=2) + '\n')


if __name__ == '__main__':
    main()
