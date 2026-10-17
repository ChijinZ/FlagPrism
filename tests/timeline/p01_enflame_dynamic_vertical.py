"""Real automatic GCU append samples for the common timeline adapter.

Uses the existing published advanced producer, not a completed detail=timeline
path. Raw ticks stay unqualified. No scope annotations or site/operator dispatch.
"""
import argparse
import hashlib
import json
from pathlib import Path


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler

    @triton.jit(do_not_specialize=['steps'])
    def recurrence(X, Y, State, N, steps, BLOCK: tl.constexpr):
        offsets = tl.program_id(0)*BLOCK+tl.arange(0, BLOCK)
        value = tl.load(X+offsets, offsets < N, 0)
        for _ in range(steps):
            value = value*0.75+0.125
        tl.store(Y+offsets, value, offsets < N)
        if tl.program_id(0) == 0:
            prior = tl.load(State)
            tl.store(State, prior+1)

    torch.gcu.set_device(0)
    cpu = torch.linspace(-2, 2, 257)
    x = cpu.to('gcu')
    y = torch.full((261,), -17.25, dtype=torch.float32, device='gcu')
    state = torch.zeros((), dtype=torch.int32, device='gcu')

    def check(k):
        ref = cpu.clone()
        for _ in range(k):
            ref = ref*0.75+0.125
        need(torch.allclose(y[:257].cpu(), ref, rtol=2e-6, atol=2e-6), 'Original math')
        need(torch.equal(y[257:].cpu(), torch.full((4,), -17.25)), 'Tail canary')
        need(torch.equal(x.cpu(), cpu), 'Input changed')
        need(state.cpu().item() == 1, 'Requested math call replayed or missed')

    ordinary = recurrence[(3,)](x, y, state, 257, 3, 128, num_warps=4)
    torch.gcu.synchronize()
    check(3)
    for kind, value in ordinary.asm.items():
        if isinstance(value, (str, bytes)):
            (a.output/('ordinary.'+kind)).write_bytes(value.encode() if isinstance(value, str) else value)
    results = []
    for k in [3, 7, 11]:
        state.zero_()
        y.fill_(-17.25)
        bundle = a.output/('k'+str(k))
        sid = profiler.start(str(bundle), backend='enflame', hook='instrumentation',
            observation_request=profiler.ObservationRequest(
                semantics=('source_control_interval',), programs=(0,),
                automatic=True, max_sites=8, max_events_per_instance=512))
        try:
            compiled = recurrence[(3,)](x, y, state, 257, k, 128, num_warps=4)
            torch.gcu.synchronize()
            check(k)
        finally:
            profiler.finalize(sid)
        metadata = compiled.metadata._asdict()
        metadata.pop('target', None)
        (a.output/('metadata-k'+str(k)+'.json')).write_text(json.dumps(metadata, default=str, indent=2)+'\n')
        for kind, value in compiled.asm.items():
            if isinstance(value, (str, bytes)):
                (a.output/('compiled-k'+str(k)+'.'+kind)).write_bytes(value.encode() if isinstance(value, str) else value)
        doc = json.loads((bundle/'ai/observations.json').read_text())
        events = [e for e in doc['observations'] if e.get('storage') == 'selected_dynamic_append']
        need(events and all(e['start_tick'] > 0 and e['end_tick'] >= e['start_tick'] and
                            e['duration_ns'] is None and e['program'] == 0 and e['actor'] == 0
                            for e in events), 'Real selected raw intervals are required')
        need(metadata['debug_record_layout'] == 'selected_dynamic_timeline_v1', 'Wrong physical producer')
        need(len({e['site'] for e in events}) >= 2, 'Source-region breadth is missing')
        results.append(dict(steps=k, actual_math_launches=1, events=len(events),
                            binary_hash=metadata['hash'],
                            sites=sorted({e['site'] for e in events}),
                            observations_sha256=hashlib.sha256((bundle/'ai/observations.json').read_bytes()).hexdigest(),
                            exact_input=True, state=1, math_tolerance={'rtol':2e-6,'atol':2e-6}))
        (a.output/'calls.json').write_text(json.dumps(results, indent=2)+'\n')
    need(len({r['binary_hash'] for r in results}) == 1, 'Runtime K changed actual binary identity')
    (a.output/'result.json').write_text(json.dumps(dict(
        status='real_gcu_automatic_dynamic_source_samples_not_full_P01',
        ordinary_math_launches=1, profiled_math_launches=3, calls=results,
        limitations=['Existing advanced producer; common timeline adapter not installed.',
                     'No ns/epoch/region/async or Perfetto qualification.']), indent=2)+'\n')


if __name__ == '__main__':
    main()
