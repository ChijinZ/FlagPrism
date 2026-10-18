"""Real automatic runtime-loop/GEMM observations plus compile-only controls.

Development evidence only: counts/math/counter maps do not certify machine
source boundaries, ordinary pipeline preservation or cross-observer epochs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shared-views', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    import torch
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    from flagtree.profiler.timeline_nvidia_machine import find_nvdisasm, _run_tool
    import ordinary_timeline_workload as workload

    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability(0) == (12, 0), 'Wrong booked target')
    cpu = torch.linspace(-1, 1, 189)
    x = cpu.cuda()
    y = torch.full((197, ), -17.25, device='cuda')
    state = torch.zeros(3, dtype=torch.int32, device='cuda')
    k_device = torch.tensor(3, dtype=torch.int32, device='cuda')
    torch.manual_seed(9217)
    reduction_size = 192 if args.shared_views else 96
    ac = torch.randn(48, reduction_size, dtype=torch.float16)
    bc = torch.randn(reduction_size, 56, dtype=torch.float16)
    av, bv = ac.cuda(), bc.cuda()
    cv = torch.full((48, 56), -17.25, dtype=torch.float32, device='cuda')
    controls = dict(recurrence=workload.recurrence.warmup(x,
                                                          y,
                                                          state,
                                                          k_device,
                                                          189,
                                                          64,
                                                          grid=(3, ),
                                                          num_warps=4),
                    gemm=workload.gemm.warmup(av,
                                              bv,
                                              cv,
                                              48,
                                              56,
                                              reduction_size,
                                              32,
                                              32,
                                              32,
                                              grid=(2, 2),
                                              num_warps=4,
                                              num_stages=3))
    need(
        state.cpu().tolist() == [0, 0, 0]
        and y.cpu().tolist() == [-17.25] * 197
        and torch.equal(cv.cpu(), torch.full(
            (48, 56), -17.25)), 'Compile-only controls executed math')
    for name, compiled in controls.items():
        directory = args.output / ('ordinary-' + name)
        directory.mkdir()
        for suffix in ('ptx', 'llir', 'ttgir', 'cubin'):
            value = compiled.asm[suffix]
            (directory / ('kernel.' + suffix)
             ).write_bytes(value.encode() if isinstance(value, str) else value)
        need('%globaltimer' not in compiled.asm['ptx'],
             'Ordinary control is instrumented')
    rows = []
    session = profiler.start(str(args.output / 'public'), detail='timeline')
    try:
        binaries = []
        for k in (3, 7):
            k_device.fill_(k)
            expected = cpu.clone()
            for _ in range(k):
                expected = expected * 0.75 + 0.125
            compiled = workload.recurrence[(3, )](x,
                                                  y,
                                                  state,
                                                  k_device,
                                                  189,
                                                  64,
                                                  num_warps=4)
            torch.cuda.synchronize()
            need(torch.allclose(y[:189].cpu(), expected, rtol=2e-6, atol=2e-6),
                 'Runtime loop math differs')
            need(
                torch.equal(x.cpu(), cpu)
                and y[189:].cpu().tolist() == [-17.25] * 8,
                'Loop input/tail differs')
            need(state.cpu().tolist() == [len(binaries) + 1] * 3,
                 'Loop was replayed or a program was lost')
            binary = hashlib.sha256(compiled.asm['cubin']).hexdigest()
            binaries.append(binary)
            rows.append(
                dict(name='recurrence',
                     runtime_k=k,
                     object_sha256=binary,
                     state=state.cpu().tolist()))
            (args.output / 'math-results.json').write_text(
                json.dumps(rows, indent=2))
        need(len(set(binaries)) == 1, 'Runtime K unexpectedly recompiled')
        compiled = workload.gemm[(2, 2)](av,
                                         bv,
                                         cv,
                                         48,
                                         56,
                                         reduction_size,
                                         32,
                                         32,
                                         32,
                                         num_warps=4,
                                         num_stages=3)
        torch.cuda.synchronize()
        need(
            torch.allclose(cv.cpu().double(),
                           ac.double() @ bc.double(),
                           rtol=1e-2,
                           atol=1e-2), 'GEMM math differs')
        need(
            torch.equal(av.cpu(), ac) and torch.equal(bv.cpu(), bc),
            'GEMM inputs changed')
        rows.append(
            dict(name='gemm',
                 object_sha256=hashlib.sha256(
                     compiled.asm['cubin']).hexdigest()))
        (args.output / 'math-results.json').write_text(
            json.dumps(rows, indent=2))
    finally:
        profiler.finalize(session)
    prefix = args.output / 'public/timeline'
    index = json.loads((prefix / 'index.json').read_text())
    need(len(index['captures']) == 3, 'Wrong public capture count')
    captures = []
    for entry in index['captures']:
        capture = json.loads((prefix / entry['capture_file']).read_text())
        need(
            capture['machine_counter_mapping']['status'] ==
            'counter_mapping_complete_region_unverified',
            'Machine mapping failed')
        batch = validate_raw_batch(
            json.loads((prefix / capture['events_file']).read_text()))
        need(batch['complete'] and batch['events'],
             'Capture lost actual records')
        captures.append((capture, batch))
    if args.shared_views:
        capture = captures[-1][0]
        decoded = json.loads((prefix / capture['decoded_file']).read_text())
        facts = json.loads((prefix / capture['async_file']).read_text())
        need(
            decoded['record_version'] == 3
            and all(r['raw_byte_length'] == 32 for r in decoded['records']),
            'Actual device records do not carry the shared-view ABI')
        need(facts['shared_view_generations'] and facts['shared_view_loads'],
             'Actual GEMM has no dynamic shared-view history')
        need(
            all(v['status'] == 'same_origin_prior_group_wait_covered'
                for v in facts['shared_view_loads']),
            'A GEMM load lacks a recorded same-origin wait-covered generation')
        need(
            any(v['generation'] >= 2
                for v in facts['shared_view_generations']),
            'No repeated actual shared-view generation was recorded')
        (args.output / 'shared-views.json').write_text(
            json.dumps(dict(
                status=
                'real_runtime_shared_origins_and_logical_wait_associations_not_clock_or_boundary_qualification',
                generations=facts['shared_view_generations'],
                loads=facts['shared_view_loads']),
                       indent=2))
    tool = find_nvdisasm()
    need(tool is not None, 'Actual machine inspector unavailable')
    comparisons = []
    for name, pair in [('recurrence', captures[0]), ('gemm', captures[-1])]:
        directory = args.output / ('ordinary-' + name)
        output = _run_tool(
            tool,
            ['--emit-json', str(directory / 'kernel.cubin')], directory,
            'json',
            time.monotonic() + 20, [])
        capture, batch = pair
        machine_file = prefix / capture['machine_counter_mapping'][
            'counter_map_file']
        instrumented = json.loads(
            machine_file.with_name('json.stdout').read_bytes())
        before, after = json.loads(output)[1], instrumented[1]

        def summary(functions):
            counts = Counter(ins['opcode'] for f in functions
                             for ins in f['sass-instructions'])
            return dict(instructions=dict(sorted(counts.items())),
                        barriers={
                            op: n
                            for op, n in sorted(counts.items())
                            if op.startswith(('BAR.', 'MEMBAR', 'DEPBAR',
                                              'LDGDEPBAR', 'WARPSYNC'))
                        },
                        matrix_instructions=sum(n for op, n in counts.items()
                                                if any(t in op
                                                       for t in ('HMMA', 'MMA',
                                                                 'TCGEN'))))

        comparisons.append(
            dict(name=name,
                 ordinary=summary(before),
                 observed=summary(after),
                 ordinary_pipeline_preservation_verified=False))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'real_native_v3_loop_gemm_math_raw_and_maps_passed_not_boundaries_or_P01',
            requested_math_launches=3,
            math=rows,
            captures=[
                dict(binary=c['owner']['binary_id'],
                     events=len(b['events']),
                     observers=len(b['observers'])) for c, b in captures
            ],
            comparisons=comparisons),
                   indent=2))


if __name__ == '__main__':
    main()
