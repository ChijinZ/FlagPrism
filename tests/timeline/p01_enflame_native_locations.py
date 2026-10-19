"""Two new ordinary math kernels through the public GCU timeline API.

Checks automatic native-marker retention, numerical results, untouched inputs,
tail guards and once-only side effects. Final-machine line tables are inspected
from the resulting executable snapshots separately, without application replay.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    torch.gcu.set_device(0)

    @triton.jit(do_not_specialize=['steps'])
    def polynomial(X, Y, State, N, steps, B: tl.constexpr):
        pid = tl.program_id(0)
        lane = tl.arange(0, B)
        offset = pid * B + lane
        x = tl.load(X + offset, offset < N, 0)
        for _ in range(steps):
            x = (x * x) * 0.0625 + x * 0.25 - 0.125
        tl.store(Y + offset, x, offset < N)
        old = tl.load(State + pid + lane, lane == 0, 0)
        tl.store(State + pid + lane, old + 1, lane == 0)

    @triton.jit
    def weighted_moment(X, Y, State, C: tl.constexpr, B: tl.constexpr):
        row = tl.program_id(0)
        lane = tl.arange(0, B)
        x = tl.load(X + row * C + lane, lane < C, 0)
        centered = x - 0.25
        weighted = centered * centered * ((lane + 1).to(tl.float32) / B)
        total = tl.sum(tl.where(lane < C, weighted, 0), axis=0)
        tl.store(Y + row, total)
        old = tl.load(State + row + lane, lane == 0, 0)
        tl.store(State + row + lane, old + 1, lane == 0)

    def inputs():
        vector = torch.linspace(-1.5, 1.25, 251)
        matrix = torch.linspace(-0.75, 1.5, 3 * 129).reshape(3, 129)
        reference = vector.clone()
        for _ in range(3):
            reference = (reference *
                         reference) * 0.0625 + reference * 0.25 - 0.125
        moment = (((matrix - 0.25)**2) *
                  ((torch.arange(129, dtype=torch.float32) + 1) / 256)).sum(
                      dim=1)
        return [
            dict(name='polynomial',
                 cpu=vector,
                 reference=reference,
                 n=251,
                 grid=2,
                 x=vector.to('gcu'),
                 y=torch.full((255, ), -17.25, device='gcu'),
                 state=torch.zeros(2, dtype=torch.int32, device='gcu')),
            dict(name='weighted_moment',
                 cpu=matrix,
                 reference=moment,
                 n=3,
                 grid=3,
                 x=matrix.to('gcu'),
                 y=torch.full((7, ), -17.25, device='gcu'),
                 state=torch.zeros(3, dtype=torch.int32, device='gcu'))
        ]

    def launch(row):
        if row['name'] == 'polynomial':
            return polynomial[(2, )](row['x'],
                                     row['y'],
                                     row['state'],
                                     251,
                                     3,
                                     128,
                                     num_warps=4)
        return weighted_moment[(3, )](row['x'],
                                      row['y'],
                                      row['state'],
                                      129,
                                      256,
                                      num_warps=4)

    def verify(rows):
        for row in rows:
            need(
                torch.allclose(row['y'][:row['n']].cpu(),
                               row['reference'],
                               rtol=2e-5,
                               atol=2e-5), row['name'] + ': math')
            need(torch.equal(row['x'].cpu(), row['cpu']),
                 row['name'] + ': input')
            need(
                torch.equal(row['y'][row['n']:].cpu(), torch.full(
                    (4, ), -17.25)), row['name'] + ': tail')
            need(row['state'].cpu().tolist() == [1] * row['grid'],
                 row['name'] + ': replay or lost side effect')

    ordinary = inputs()
    for row in ordinary:
        launch(row)
    torch.gcu.synchronize()
    verify(ordinary)
    (args.output / 'ordinary.json').write_text(
        json.dumps(dict(math_calls=2,
                        kernels=[r['name'] for r in ordinary],
                        math=True,
                        input_unchanged=True,
                        guards=True,
                        host_once=True),
                   indent=2))
    rows = inputs()
    output = args.output / 'profile'
    session = profiler.start(str(output), detail='timeline')
    try:
        for row in rows:
            launch(row)
    finally:
        profiler.finalize(session)
    verify(rows)
    root = output / 'timeline'
    index = json.loads((root / 'index.json').read_text())
    need(len(index['captures']) == 2, 'Expected two actual capture owners')
    summaries = []
    for entry in index['captures']:
        capture = json.loads((root / entry['capture_file']).read_text())
        batch = validate_raw_batch(
            json.loads((root / capture['events_file']).read_text()))
        need(batch['complete'] and len(batch['events']) >= 2,
             'Incomplete internal intervals')
        need(
            any(((e['end_tick'] - e['start_tick']) & ((1 << 46) - 1)) > 0
                for e in batch['events']),
            'No positive actual internal duration')
        compiler = capture['metadata']['compiler_metadata']
        need(compiler['debug_execution_tool_identity']['version'] == 2,
             'Stale compiler/tool identity')
        need(compiler['debug_execution_native_marker_version'] == 1,
             'Missing native clock markers')
        snapshot = capture['metadata']['compiled_snapshot']
        llir = snapshot['compiler_artifacts']['llir']
        need(
            '__flagprism_gcu_clock_v1__' in llir
            and '#llvm.di_subprogram<' in llir,
            'Final SDK LLVM serialization lost clock locations/scopes')
        retained = compiler['debug_execution_native_locations']
        fatbin = base64.b64decode(snapshot['binary_base64'], validate=True)
        need(
            retained['fatbin_sha256'] == hashlib.sha256(fatbin).hexdigest() ==
            snapshot['executable']['binary_sha256'],
            'Native locations belong to another executable')
        points = retained['report']['locations']
        need(
            retained['report']['status'] == 'compiler_locations_mapped'
            and len({p['site_id']
                     for p in points}) >= 2,
            'Normal compiler did not retain native site/phase locations')
        need(
            retained['report']['source_region_qualified'] is False
            and retained['report']['reader_valueflow_qualified'] is False,
            'Debug locations granted unrelated timing rights')
        manifest = compiler['debug_execution_manifest']
        need(
            all(s['native_clock_marker']['line'] == s['id']
                for s in manifest['sites']),
            'Manifest marker/site identity mismatch')
        summaries.append(
            dict(capture_file=entry['capture_file'],
                 binary_id=capture['owner']['binary_id'],
                 sites=len(manifest['sites']),
                 native_location_points=len(points),
                 native_missing_phase_sites=len(retained['missing_phase_locations']),
                 events=len(batch['events']),
                 observers=len(batch['observers']),
                 native_scope_output_sha256=compiler[
                     'debug_execution_native_scope_output_sha256'],
                 final_sdk_ir_sha256=compiler[
                     'debug_execution_native_ir_sha256']))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='GCU_native_location_two_math_public_capture_passed',
            ordinary_math_calls=2,
            profiled_math_calls=2,
            math=True,
            input_unchanged=True,
            guards=True,
            host_once=True,
            captures=summaries,
            final_machine_boundary_qualified=False),
                   indent=2))


if __name__ == '__main__':
    main()
