"""Compile-only ordinary controls for the actual outlined development objects.

No ordinary kernel launch or application replay. Comparison is static; matching
barrier counts alone never certifies dynamic schedule or participant boundaries.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    import torch
    from flagtree.profiler.timeline_nvidia_machine import find_nvdisasm, _run_tool
    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability() == (12, 0), 'Wrong booked target')
    source = Path('/workspace/chijin-timeline-r012/check-input-v1/ordinary_timeline_workload.py')
    spec = importlib.util.spec_from_file_location('ordinary_timeline_workload', source)
    workload = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = workload
    spec.loader.exec_module(workload)
    torch.manual_seed(9217)
    x = torch.zeros(320, dtype=torch.float32).cuda()
    y = torch.full((328,), -17.25, dtype=torch.float32).cuda()
    state = torch.zeros(5, dtype=torch.int32).cuda()
    kd = torch.tensor(3, dtype=torch.int32).cuda()
    rec = workload.recurrence.warmup(x, y, state, kd, 189, 64,
                                     grid=(3,), num_warps=4)
    aa = torch.zeros((48, 96), dtype=torch.float16).cuda()
    bb = torch.zeros((96, 56), dtype=torch.float16).cuda()
    cc = torch.full((48, 56), -17.25, dtype=torch.float32).cuda()
    gemm = workload.gemm.warmup(aa, bb, cc, 48, 56, 96, 32, 32, 32,
                                grid=(2, 2), num_warps=4, num_stages=3)
    need(torch.equal(y.cpu(), torch.full((328,), -17.25)) and
         state.cpu().tolist() == [0]*5 and
         torch.equal(cc.cpu(), torch.full((48, 56), -17.25)),
         'Compile-only controls executed a math/store side effect')
    prefix = Path('/workspace/chijin-timeline-r012/runs/public-outlined-v1/output/api-cold/timeline')
    index = json.loads((prefix/'index.json').read_text())
    captures = [json.loads((prefix/e['capture_file']).read_text())
                for e in (index['captures'][0], index['captures'][-1])]
    tool = find_nvdisasm()
    need(tool is not None, 'Pinned disassembler is required')
    deadline = time.monotonic()+120
    rows = []
    barrier_prefixes = ('BAR.', 'MEMBAR', 'DEPBAR', 'LDGDEPBAR', 'WARPSYNC')
    for name, compiled, capture in zip(['recurrence', 'gemm'], [rec, gemm], captures):
        directory = a.output/name
        directory.mkdir()
        for suffix, value in compiled.asm.items():
            if isinstance(value, (str, bytes)):
                (directory/('ordinary.'+suffix)).write_bytes(value.encode() if isinstance(value, str) else value)
        need('%globaltimer' not in compiled.asm['ptx'] and
             'flagprism_timeline_v1_site_' not in compiled.asm['ptx'],
             'Compile-only control is still instrumented')
        commands = []
        raw = _run_tool(tool, ['--emit-json', str(directory/'ordinary.cubin')],
                        directory, 'json', deadline, commands)
        _run_tool(tool, ['--print-code', '--print-line-info-ptx', str(directory/'ordinary.cubin')],
                  directory, 'lines', deadline, commands)
        _run_tool(tool, ['--output-control-flow-graph', '--print-instr-offsets-cfg',
                         str(directory/'ordinary.cubin')], directory, 'cfg', deadline, commands)
        ordinary = json.loads(raw)[1]
        map_path = prefix/capture['machine_counter_mapping']['counter_map_file']
        instrumented = json.loads(map_path.with_name('json.stdout').read_bytes())[1]

        def barriers(functions):
            return [dict(function=f['function-name'], pc=f['start']+16*i,
                         opcode=ins['opcode'], operands=ins.get('operands'))
                    for f in functions for i, ins in enumerate(f['sass-instructions'])
                    if ins['opcode'].startswith(barrier_prefixes)]

        before, after = barriers(ordinary), barriers(instrumented)
        count_before, count_after = Counter(x['opcode'] for x in before), Counter(x['opcode'] for x in after)
        row = dict(name=name, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   ordinary_cubin_sha256=hashlib.sha256(compiled.asm['cubin']).hexdigest(),
                   instrumented_cubin_sha256=json.loads(map_path.read_text())['artifacts']['cubin_sha256'],
                   ordinary_barriers=before, instrumented_barriers=after,
                   ordinary_counts=dict(count_before), instrumented_counts=dict(count_after),
                   static_barrier_counts_match=count_before == count_after)
        rows.append(row)
    result = dict(status='ordinary_compile_only_barrier_comparison', actual_math_launches=0,
                  canaries_unchanged=True, objects=rows,
                  limitations=['Static barrier counts do not certify dynamic schedule, source regions or clocks.'])
    (a.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    need(all(r['static_barrier_counts_match'] for r in rows),
         'Static synchronization changed; preserve results and inspect before qualification')


if __name__ == '__main__':
    main()
