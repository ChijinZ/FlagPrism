"""Real ordinary kernels check compiler anchors across register storage types.

Public API, no kernel annotations. Development regression, not the independent
six-math qualification or a clock/final-machine-boundary certificate.
"""
import argparse
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    import torch
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch

    @triton.jit
    def ordinary_update(X, Y, State, N: tl.constexpr, INTEGER: tl.constexpr,
                        BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        lane = tl.arange(0, BLOCK)
        index = pid * BLOCK + lane
        value = tl.load(X + index, index < N, 0)
        if INTEGER:
            value = value ^ (value << 1)
        else:
            value = value * 0.5 + 0.25
        tl.store(Y + index, value, index < N)
        prior = tl.load(State + pid + lane, lane == 0, 0)
        tl.store(State + pid + lane, prior + 1, lane == 0)

    torch.cuda.set_device(0)
    require(torch.cuda.get_device_capability(0) == (12, 0), 'Wrong booked target')
    types = [torch.float16, torch.bfloat16, torch.float32, torch.float64, torch.int64]
    rows = []
    session = profiler.start(str(a.output/'public'), detail='timeline')
    try:
        for dtype in types:
            integer = dtype == torch.int64
            cpu = (torch.arange(-64, 65, dtype=dtype) if integer else
                   torch.linspace(-2, 2, 129, dtype=dtype))
            x = cpu.cuda()
            y = torch.full((132,), -77, dtype=dtype, device='cuda')
            state = torch.zeros(3, dtype=torch.int32, device='cuda')
            compiled = ordinary_update[(3,)](x, y, state, 129, integer, 64, num_warps=4)
            torch.cuda.synchronize()
            expected = cpu ^ (cpu << 1) if integer else cpu * 0.5 + 0.25
            actual = y.cpu()
            require(torch.equal(actual[:129], expected), 'Math differs: '+str(dtype))
            require(torch.equal(x.cpu(), cpu), 'Input changed: '+str(dtype))
            require(actual[129:].tolist() == [-77, -77, -77], 'Tail changed')
            require(state.cpu().tolist() == [1, 1, 1], 'Math launch was replayed')
            llir = compiled.asm['llir']
            require('timeline_llvm_begin_dependency' in llir and
                    'timeline_llvm_counter_dependency' in llir,
                    'Actual compiled SSA dependencies are absent')
            getter_lines = [line for line in llir.splitlines() if '%globaltimer' in line]
            require(getter_lines and all('~{memory}' in line and 'asm sideeffect' in line
                                         for line in getter_lines),
                    'Actual timeline getter omitted its compiler memory clobber')
            row = dict(dtype=str(dtype), programs=3, requested_math_launches=1,
                       state=state.cpu().tolist(), exact_cpu_math=True,
                       cubin_sha256=hashlib.sha256(compiled.asm['cubin']).hexdigest(),
                       llir_sha256=hashlib.sha256(llir.encode()).hexdigest())
            rows.append(row)
            (a.output/'math-results.json').write_text(json.dumps(rows, indent=2)+'\n')
    finally:
        profiler.finalize(session)
    prefix = a.output/'public/timeline'
    index = json.loads((prefix/'index.json').read_text())
    require(index['status'] == 'partial_clock_unverified', 'Unproven clock was upgraded')
    require(len(index['captures']) == len(types), 'Public path lost or replayed calls')
    events = 0
    for row in index['captures']:
        capture = json.loads((prefix/row['capture_file']).read_text())
        plan = capture['owner']['plan']
        machine = capture['machine_counter_mapping']
        require(machine['status']=='counter_mapping_complete_region_unverified',
                'Actual type machine mapping failed: '+str(machine))
        proof = json.loads((prefix/machine['counter_map_file']).read_text())
        require(not proof['region_boundaries_verified'] and not proof['clock_qualified'] and
                proof['counter_pcs'], 'Machine mapping incorrectly certified time or boundaries')
        require(plan.get('timeline_boundary_version') == 2 and
                plan.get('timeline_boundary_strategy') == 'outlined_device_calls_pending_region_audit',
                'Actual binary plan lost the boundary strategy')
        canonical = validate_raw_batch(json.loads((prefix/capture['events_file']).read_text()))
        require(canonical['complete'] and all(e['kind']=='interval' for e in canonical['events']),
                'Type regression lost complete source-linked records')
        require({o['program_coordinates'][0] for o in canonical['observers']} == {0, 2},
                'Default selected programs lost actual runtime coordinates')
        events += len(canonical['events'])
    (a.output/'result.json').write_text(json.dumps(dict(
        status='public_type_math_and_llvm_dependencies_passed_not_machine_certified',
        actual_math_launches=len(types), captures=len(index['captures']),
        canonical_intervals=events, math=rows), indent=2)+'\n')


if __name__ == '__main__':
    main()
