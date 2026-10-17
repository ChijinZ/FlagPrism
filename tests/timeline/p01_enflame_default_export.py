"""Actual standard advanced-request export, with no custom prepare/decoder hook.

This tests GCU storage v2 and the capture/report bridge. detail=timeline,
deferred owner transport, clock qualification and Perfetto remain separate.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def need(value,message):
    if not value:
        raise RuntimeError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();args.output.mkdir(exist_ok=False)
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    torch.gcu.set_device(0)

    @triton.jit(do_not_specialize=['steps'])
    def recurrence(X,Y,State,N,steps,BLOCK:tl.constexpr):
        pid=tl.program_id(0);lane=tl.arange(0,BLOCK)
        offsets=pid*BLOCK+lane
        value=tl.load(X+offsets,offsets<N,0)
        for _ in range(steps):
            value=value*0.75+0.125
        tl.store(Y+offsets,value,offsets<N)
        previous=tl.load(State+pid+lane,lane==0,0)
        tl.store(State+pid+lane,previous+1,lane==0)

    cpu=torch.linspace(-2,2,257)
    x=cpu.to('gcu');y=torch.full((261,),-17.25,device='gcu')
    state=torch.zeros(3,device='gcu',dtype=torch.int32)
    bundle=args.output/'capture'
    session=profiler.start(str(bundle),backend='enflame',hook='instrumentation',
        observation_request=profiler.ObservationRequest(programs=None,program_policy='runtime_first_last',
            automatic=True,max_sites=8,max_events_per_instance=64))
    try:
        recurrence[(3,)](x,y,state,257,7,128,num_warps=4)
        torch.gcu.synchronize()
        reference=cpu.clone()
        for _ in range(7):reference=reference*0.75+0.125
        need(torch.allclose(y[:257].cpu(),reference,rtol=2e-6,atol=2e-6),'Original math')
        need(torch.equal(y[257:].cpu(),torch.full((4,),-17.25)),'Tail canary')
        need(torch.equal(x.cpu(),cpu) and state.cpu().tolist()==[1,1,1],'Input or replay/side effects')
    finally:
        profiler.finalize(session)
    document=json.loads((bundle/'ai/observations.json').read_text())
    events=[row for row in document['observations'] if row.get('semantic')=='observer_region_elapsed']
    need(events and {r['program'] for r in events}=={0,2},'Standard exporter lost selected program data')
    need(all(e['duration_ns'] is None and e['clock']['alignment']=='unverified' for e in events),'Exporter invented clock qualification')
    native=json.loads((bundle/'raw/native/capture.observations.json').read_text())
    captures=[row for row in native['captures'] if row.get('canonical_timeline')]
    need(len(captures)==1,'Canonical timeline not retained in standard capture')
    capture=captures[0];canonical=validate_raw_batch(capture['canonical_timeline'])
    raw=base64.b64decode(capture['raw_base64'])
    need(hashlib.sha256(raw).hexdigest()==canonical['raw_artifact']['sha256'],'Canonical/raw association changed')
    need(len(canonical['events'])==len(events) and canonical['complete'],'Standard event count/completeness mismatch')
    status=json.loads((bundle/'ai/selection_status.json').read_text())
    need(status['status']=='complete','Automatic source-presence guard did not pass honestly')
    need((bundle/'manifest.json').is_file(),'Actual standard bundle not produced')
    (args.output/'result.json').write_text(json.dumps(dict(
        status='actual_gcu_standard_advanced_export_passed_not_default_timeline_or_P01',
        math_calls=1,per_program_side_effects=[1,1,1],events=len(events),
        canonical_records=len(canonical['records']),raw_sha256=canonical['raw_artifact']['sha256'],
        actual_programs=[o['program_coordinates'] for o in canonical['observers']],
        clock_qualified=False,boundary_qualified=False,perfetto_qualified=False),indent=2)+'\n')


if __name__=='__main__':
    main()
