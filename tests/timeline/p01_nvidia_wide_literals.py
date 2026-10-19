"""Actual SM120 wide-literal mechanism validation, not independent math."""
import argparse, hashlib, json, time
from pathlib import Path
import torch, triton
import triton.language as tl


@triton.jit
def literal_kernel(I, O, N: tl.constexpr, ASM: tl.constexpr):
    i = tl.program_id(0) * 128 + tl.arange(0, 128)
    value = tl.load(I + i, i < N, 0)
    result = tl.inline_asm_elementwise(ASM,
                                       constraints='=l,r',
                                       args=[value],
                                       dtype=tl.uint64,
                                       is_pure=False,
                                       pack=1)
    tl.store(O + i, result, i < N)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True)
    torch.cuda.set_device(0)
    if torch.cuda.get_device_capability() != (12, 0):
        raise RuntimeError('Actual SM120 required')
    from flagtree.profiler.timeline_nvidia_machine import find_nvdisasm, _run_tool
    tool = find_nvdisasm()
    if tool is None: raise RuntimeError('Missing actual disassembler')
    inp = torch.arange(257, dtype=torch.int32, device='cuda')
    reports = []
    literals = [
        0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff, 0x100000000,
        0xffffffff80000000, 0xfffffffffffffffe, 0xffffffffffffffff,
        0x8000000000000000, 0x7fffffffffffffff
    ]
    for number in literals:
        folder = a.output / hex(number)
        folder.mkdir()
        out = torch.full((264, ), 0x1234, dtype=torch.int64, device='cuda')
        compiled = literal_kernel[(3, )](inp,
                                         out,
                                         257,
                                         ASM='mov.b64 $0, ' + hex(number) +
                                         ';',
                                         num_warps=4)
        torch.cuda.synchronize()
        result = out.cpu().tolist()
        expected = number if number < (1 << 63) else number - (1 << 64)
        if result[:257] != [expected] * 257 or result[257:] != [0x1234] * 7:
            raise RuntimeError('Actual literal bit pattern/tail differs')
        (folder / 'actual.ptx').write_text(compiled.asm['ptx'])
        (folder / 'actual.cubin').write_bytes(compiled.asm['cubin'])
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
        if doc[0]['SM']['version'] != {'major': 12, 'minor': 0}:
            raise RuntimeError('Actual native target differs')
        moves = [
            row for fn in doc[1] for row in fn['sass-instructions']
            if row['opcode'] in ('MOV.64', 'UMOV.64')
        ]
        (folder / 'commands.json').write_text(json.dumps(commands, indent=2))
        report = dict(
            literal_hex=hex(number),
            samples=257,
            actual_low_word=number & 0xffffffff,
            actual_high_word=number >> 32,
            math=True,
            tail=True,
            moves=moves,
            ptx_sha256=hashlib.sha256(
                compiled.asm['ptx'].encode()).hexdigest(),
            cubin_sha256=hashlib.sha256(compiled.asm['cubin']).hexdigest(),
            sass_sha256=hashlib.sha256(lines).hexdigest(),
            nvdisasm_sha256=hashlib.sha256(tool.read_bytes()).hexdigest())
        reports.append(report)
        print(json.dumps(report))
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_wide_literal_bit_patterns_passed_not_timeline_or_independent_math',
            reports=reports),
                   indent=2))


if __name__ == '__main__': main()
