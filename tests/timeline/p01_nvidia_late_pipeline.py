"""Default API runtime-K GEMM math and collective byte-dependency gate."""
import argparse
import importlib.util
import json
from pathlib import Path
import torch
from flagtree import profiler


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--kernel-module', type=Path, required=True)
    p.add_argument('--num-warps', type=int, choices=(1, 2, 4, 8), default=4)
    p.add_argument('--site-budget', type=int)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('late_pipeline_math',
                                                  a.kernel_module)
    kernels = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernels)
    torch.cuda.set_device(0)
    torch.manual_seed(32046)
    m, n, maximum = 64, 64, 224
    acpu, bcpu = torch.randn(m, maximum, dtype=torch.float16), torch.randn(
        maximum, n, dtype=torch.float16)
    av, bv = acpu.cuda(), bcpu.cuda()
    results = []
    for phase in ('ordinary', 'profile'):
        options = {} if a.site_budget is None else dict(
            timeline_max_sites=a.site_budget)
        session = profiler.start(str(a.output / 'profile'),
                                 detail='timeline',
                                 **options) if phase == 'profile' else None
        try:
            for tiles in (3, 7):
                k = tiles * 32
                ki = torch.tensor([k], dtype=torch.int32, device='cuda')
                out = torch.full((m * n + 7, ), 1234., device='cuda')
                calls = torch.zeros(4, dtype=torch.int32, device='cuda')
                compiled = kernels.runtime_gemm[(2, 2)](av,
                                                        bv,
                                                        out,
                                                        ki,
                                                        calls,
                                                        m,
                                                        n,
                                                        maximum,
                                                        32,
                                                        32,
                                                        32,
                                                        num_warps=a.num_warps,
                                                        num_stages=3)
                need(
                    torch.allclose(out[:m * n].cpu().reshape(m, n).double(),
                                   acpu[:, :k].double() @ bcpu[:k].double(),
                                   rtol=1e-2,
                                   atol=1e-2), 'Original runtime-K GEMM math')
                need(torch.equal(out[m * n:].cpu(), torch.full((7, ), 1234.)),
                     'Original GEMM tail')
                need(calls.cpu().tolist() == [1] * 4,
                     'Original GEMM call count')
                need(
                    torch.equal(av.cpu(), acpu)
                    and torch.equal(bv.cpu(), bcpu), 'Original GEMM inputs')
                results.append(
                    dict(phase=phase,
                         tiles=tiles,
                         hash=compiled.hash,
                         math=True,
                         input=True,
                         tail=True,
                         calls=True))
                (a.output / 'math.json').write_text(
                    json.dumps(results, indent=2))
        finally:
            if session is not None:
                profiler.finalize(session)
    timeline = a.output / 'profile/timeline'
    index = json.loads((timeline / 'index.json').read_text())
    need(
        len(index['captures']) == 2 and not index['failures']
        and not index['retained_owners'], 'Incomplete default GEMM capture')
    captures = []
    for row in index['captures']:
        capture = json.loads((timeline / row['capture_file']).read_text())
        need(capture['capture_status'] == 'raw_complete', 'GEMM raw loss')
        need(
            capture.get('counter_ns_status',
                        {}).get('status') == 'counter_unit_only'
            and len(capture.get('counter_ns_exports', [])) == 8,
            'Default GEMM lacks actual machine-validated counter-ns traces')
        need(
            capture['owner']['plan']['actors'] == 32 * a.num_warps
            and capture['owner']['plan']['dependency_footprint_complete'],
            'Missing actual CTA footprint')
        facts = json.loads((timeline / capture['async_file']).read_text())
        need(facts['status'] == 'dynamic_byte_model_consistent',
             'Native byte dependency model did not close: ' + str(facts))
        need(
            all(program['commit_groups'] >= 2 and program['consumer_edges']
                and program['reuse'] for program in facts['programs']),
            'Missing real wait/consumer/reused-buffer generations')
        need(
            not facts['time_flows_qualified']
            and not facts['hardware_busy_qualified'],
            'Unproven timing qualification')
        need(
            capture.get('observed_dependency_status',
                        {}).get('time_arrows_verified') is True
            and len(capture.get('observed_dependency_exports', [])) == 2,
            'Default API lacks qualified observed dependency traces: ' +
            str(capture.get('observed_dependency_status')))
        captures.append(
            dict(invocation=row['invocation_id'],
                 raw_bytes=capture['owner']['layout']['raw_bytes'],
                 groups=[p['commit_groups'] for p in facts['programs']],
                 consumers=sum(
                     len(p['consumer_edges']) for p in facts['programs']),
                 reuse=sum(len(p['reuse']) for p in facts['programs'])))
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'default_api_runtime_gemm_math_raw_and_observed_dependency_exports_passed',
            requested_site_budget=a.site_budget,
            math=results,
            captures=captures),
                   indent=2))


if __name__ == '__main__':
    main()
