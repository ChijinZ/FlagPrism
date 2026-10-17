"""Real ordinary GCU kernels through detail=timeline; raw stage, not full P01."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import struct


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    profile = importlib.import_module('flagtree.profiler.profile')
    torch.gcu.set_device(0)

    @triton.jit(do_not_specialize=['steps'])
    def recurrence(X, Y, State, N, steps, BLOCK: tl.constexpr):
        pid = tl.program_id(0)+tl.program_id(1)*tl.num_programs(0)
        lanes = tl.arange(0, BLOCK)
        offsets = pid*BLOCK+lanes
        value = tl.load(X+offsets, offsets<N, 0)
        for _ in range(steps):
            value = value*0.75+0.125
        tl.store(Y+offsets, value, offsets<N)
        prior = tl.load(State+pid+lanes, lanes==0, 0)
        tl.store(State+pid+lanes, prior+1, lanes==0)

    cases = [((3, 2), 3), ((2, 2), 7), ((1, 1), 11)]
    def inputs():
        result = []
        for grid, steps in cases:
            total = grid[0]*grid[1]
            n = 128*total-5
            cpu = torch.linspace(-2, 2, n)
            result.append(dict(grid=grid, steps=steps, n=n, cpu=cpu,
                x=cpu.to('gcu'), y=torch.full((n+4,), -17.25, device='gcu'),
                state=torch.zeros(total, device='gcu', dtype=torch.int32)))
        return result

    phases = []
    for name in ['api-cold', 'api-warm']:
        data = inputs()
        session = profiler.start(str(args.output/name), detail='timeline')
        collector = profile._active_sessions[session]['timeline_hook']
        actions = []
        transport = collector.timeline_pool.transport
        for method in ['completion_ready', 'read_raw', 'record_completion']:
            original = getattr(transport, method)
            def wrapped(owner, original=original, method=method):
                actions.append((method, owner['invocation_id']))
                return original(owner)
            setattr(transport, method, wrapped)
        synchronize = torch.gcu.synchronize
        def forbidden_global_wait(*args, **kwargs):
            raise RuntimeError('Default timeline performed a per-launch global wait')
        torch.gcu.synchronize = forbidden_global_wait
        try:
            for row in data:
                recurrence[row['grid']](row['x'], row['y'], row['state'], row['n'],
                    row['steps'], 128, num_warps=4)
            need(len(collector.timeline_pool.invocation_ids)==3, 'Invocation owners were not deferred')
            need([a[0] for a in actions]==['record_completion']*3,
                 'Submission path queried/read/waited for a previous invocation')
        finally:
            torch.gcu.synchronize = synchronize
            profiler.finalize(session)
        need(not collector.timeline_pool.invocation_ids, 'Successful finalization retained owners')
        for row in data:
            reference = row['cpu'].clone()
            for _ in range(row['steps']):
                reference = reference*0.75+0.125
            need(torch.allclose(row['y'][:row['n']].cpu(), reference, rtol=2e-6, atol=2e-6), 'Math changed')
            need(torch.equal(row['x'].cpu(), row['cpu']), 'Input changed')
            need(torch.equal(row['y'][row['n']:].cpu(), torch.full((4,), -17.25)), 'Tail changed')
            need(row['state'].cpu().tolist()==[1]*(row['grid'][0]*row['grid'][1]), 'Replay or lost side effects')
        output = args.output/name
        root = output/'timeline'
        index = json.loads((root/'index.json').read_text())
        need(len(index['captures'])==3 and not index['retained_owners'] and not index['pending_decode'],
             'Default bundle lost a capture or reports pending owners')
        counts, binaries = [], []
        total_records = 0
        for item, row in zip(index['captures'], data):
            capture = json.loads((root/item['capture_file']).read_text())
            need(capture['capture_status']=='raw_complete', 'Incomplete default capture')
            canonical = validate_raw_batch(json.loads((root/capture['events_file']).read_text()))
            raw = (root/capture['raw_file']).read_bytes()
            need(hashlib.sha256(raw).hexdigest()==canonical['raw_artifact']['sha256'], 'Raw identity mismatch')
            for endpoint in canonical['records']:
                need(endpoint['length']==8 and struct.unpack_from('<Q', raw, endpoint['offset'])[0]==endpoint['tick'],
                     'Endpoint does not reference its real physical counter field')
            total = row['grid'][0]*row['grid'][1]
            expected = [[0, 0, 0]] if total==1 else [[0, 0, 0], [row['grid'][0]-1, row['grid'][1]-1, 0]]
            need([o['program_coordinates'] for o in canonical['observers']]==expected, 'Actual first/last coordinates wrong')
            per_observer = [sum(e['observer_id']==o['id'] for e in canonical['events']) for o in canonical['observers']]
            need(all(n>=2 for n in per_observer) and canonical['complete'], 'Headers without actual complete events')
            need(canonical['clock_status']=='unverified' and canonical['boundary_status']=='unverified', 'Unproved qualification')
            counts.append(per_observer)
            binaries.append(capture['owner']['binary_id'])
            total_records += len(canonical['records'])
        need(len(set(binaries))==1, 'Runtime K/grid unexpectedly specialized the binary')
        need(counts[0][0]<counts[1][0]<counts[2][0], 'Runtime K did not change actual occurrence count')
        native = json.loads((output/'raw/native/capture.observations.json').read_text())
        need(len([c for c in native['captures'] if c.get('canonical_timeline')])==3,
             'Final standard bundle lost canonical captures')
        need((output/'manifest.json').is_file(), 'Not a standard public bundle')
        phases.append(dict(name=name, math_calls=3, binaries=binaries,
            events_per_observer=counts, raw_endpoint_references=total_records,
            deferred_submission_actions=actions[:3]))
    need(phases[0]['binaries']==phases[1]['binaries'], 'Warm session changed compiled identity')
    (args.output/'result.json').write_text(json.dumps(dict(
        status='gcu_public_default_raw_stage_passed_not_full_P01', phases=phases,
        clock_qualified=False, boundary_qualified=False, allocation_guard_qualified=False,
        async_mechanism_qualified=False, perfetto_qualified=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
