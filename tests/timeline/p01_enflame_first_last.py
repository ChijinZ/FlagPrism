"""Actual GCU producer/explicit native lifecycle; NOT default timeline or P01.

The documented advanced request and a development prepare hook exercise the
new physical ABI. Legacy launch_context synchronization remains here. Default
collection/owner transport is a separate pending integration requirement.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import uuid


def need(value, message):
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
    import flagtree.debugger as debugger
    from flagtree.debugger import api
    from flagtree.debugger.native import runtime_binding,compiler_binding
    from flagtree.profiler.hooks.timeline import _persist
    from flagtree.profiler.timeline_events_enflame import canonicalize_enflame_capture
    need(runtime_binding().GCU_TIMELINE_STORAGE_VERSION==2 and
         compiler_binding().GCU_TIMELINE_STORAGE_VERSION==2, 'Wrong native storage ABI')
    torch.gcu.set_device(0)

    @triton.jit(do_not_specialize=['steps'])
    def recurrence(X,Y,State,N,steps,BLOCK:tl.constexpr):
        pid=tl.program_id(0)+tl.program_id(1)*tl.num_programs(0)
        lane=tl.arange(0,BLOCK)
        offsets=pid*BLOCK+lane
        value=tl.load(X+offsets,offsets<N,0)
        for _ in range(steps):
            value=value*0.75+0.125
        tl.store(Y+offsets,value,offsets<N)
        prior=tl.load(State+pid+lane,lane==0,0)
        tl.store(State+pid+lane,prior+1,lane==0)

    records=[];owners=[]
    def prepare(metadata,stream,launch_metadata,kernel_args):
        actual=api._build_launch_metadata_dict(metadata)
        materialized=api._materialize_launch_metadata(launch_metadata)
        grid=api._normalize_launch_grid(materialized)
        need(grid is not None, 'Actual grid is required')
        runtime=api._infer_runtime_metadata(metadata,kernel_args)
        runtime.update(grid=grid,record_layout=actual['debug_record_layout'],
            records_per_instance=actual['debug_records_per_instance'],record_plan=actual['debug_record_plan'])
        need(actual['debug_record_layout']=='gcu_first_last_timeline_v2', 'Wrong actual compiled layout')
        identity_object=(launch_metadata.get('_flagprism_launch_identity_object')
                         if isinstance(launch_metadata,dict) else launch_metadata)
        handle=runtime_binding().allocate_timeline_launch(actual,int(stream),runtime)
        owners.append(handle) # Preserve potentially initialized storage on error.
        handle.initialize()
        scope=len(records)
        def finish(error):
            need(error is None, 'Original math launch failed')
            event=torch.gcu.Event(enable_timing=False)
            external=torch.gcu.ExternalStream(int(stream),device=0)
            event.record(external);event.synchronize()
            run=handle.read_raw() # Must not release here.
            raw=bytes(run['raw_buffer'])
            association=getattr(identity_object,'_flagprism_invocation_identity',None)
            need(association and association.get('evidence')=='same_launch_metadata_object',
                 'Real launch association was not propagated')
            runtime_actual=dict(run['runtime_metadata'])
            runtime_actual.update(profiler_invocation_id=association['invocation_id'],
                                 profiler_association_evidence=dict(association))
            # Serialize native tuples exactly as the persisted public raw path.
            runtime_actual=json.loads(json.dumps(runtime_actual))
            capture=dict(capture_status='raw_complete',record_layout=actual['debug_record_layout'],
                runtime_metadata=runtime_actual,raw_sha256=hashlib.sha256(raw).hexdigest(),
                raw_base64=base64.b64encode(raw).decode())
            prefix=args.output/f'capture-{scope}'
            _persist(prefix.with_suffix('.raw'),raw)
            _persist(prefix.with_suffix('.input.json'),
                     (json.dumps(dict(capture=capture,compiler_metadata=actual),indent=2,default=str)+'\n').encode())
            handle.release();owners.remove(handle)
            canonical=canonicalize_enflame_capture(capture,compiler_metadata=actual,
                capture_id='producer-probe-'+uuid.uuid4().hex)
            _persist(prefix.with_suffix('.events.json'),(json.dumps(canonical,indent=2)+'\n').encode())
            records.append(dict(capture_file=str(prefix.with_suffix('.input.json')),
                canonical_file=str(prefix.with_suffix('.events.json')),raw_file=str(prefix.with_suffix('.raw')),
                binary_id=actual['hash'],grid=list(grid),actual_programs=[
                    o['program_coordinates'] for o in canonical['observers']],
                events=len(canonical['events']),complete=canonical['complete'],
                dropped_endpoint_references=sum(o['dropped_records'] for o in canonical['observers'])))
        return debugger.PreparedKernelLaunch(kernel_args=(int(handle.hidden_arg_value),),finalize=finish)

    def math_case(grid,steps,name):
        total=grid[0]*grid[1]
        n=128*total-5
        cpu=torch.linspace(-2,2,n)
        x=cpu.to('gcu');y=torch.full((n+4,),-17.25,device='gcu')
        state=torch.zeros(total,device='gcu',dtype=torch.int32)
        compiled=recurrence[grid](x,y,state,n,steps,128,num_warps=4)
        torch.gcu.synchronize()
        reference=cpu.clone()
        for _ in range(steps):reference=reference*0.75+0.125
        need(torch.allclose(y[:n].cpu(),reference,rtol=2e-6,atol=2e-6),'Original recurrence math')
        need(torch.equal(y[n:].cpu(),torch.full((4,),-17.25)),'Tail canary changed')
        need(torch.equal(x.cpu(),cpu),'Input changed')
        need(state.cpu().tolist()==[1]*total,'Original per-program side effects replayed/missed')
        (args.output/(name+'-math.json')).write_text(json.dumps(dict(
            grid=list(grid),steps=steps,program_side_effects=state.cpu().tolist(),
            rtol=2e-6,atol=2e-6,exact_input=True,tail_canary=True))+'\n')
        return compiled

    cases=[((3,2),3),((2,2),7),((1,1),11)]
    ordinary=math_case(*cases[0],'ordinary')
    for kind,value in ordinary.asm.items():
        if isinstance(value,(str,bytes)):
            (args.output/('ordinary.'+kind)).write_bytes(value.encode() if isinstance(value,str) else value)
    for index,(grid,steps) in enumerate(cases):
        sid=profiler.start(str(args.output/f'advanced-{index}'),backend='enflame',hook='instrumentation',
            observation_request=profiler.ObservationRequest(programs=None,program_policy='runtime_first_last',
                automatic=True,max_sites=8,max_events_per_instance=64))
        debugger.register_launch_prepare_hook(prepare)
        try:compiled=math_case(grid,steps,f'profile-{index}')
        finally:profiler.finalize(sid)
        need(len(records)==index+1 and not owners,'Missing capture or unreleased owner')
        for kind,value in compiled.asm.items():
            if isinstance(value,(str,bytes)):
                (args.output/(f'compiled-{index}.'+kind)).write_bytes(value.encode() if isinstance(value,str) else value)
    need(len({r['binary_id'] for r in records})==1,'Runtime grid/steps changed compiled identity')
    expected=[[[0,0,0],[2,1,0]],[[0,0,0],[1,1,0]],[[0,0,0]]]
    need([r['actual_programs'] for r in records]==expected,'Actual first/last program selection is wrong')
    need(all(r['complete'] and r['events']>=2 for r in records),'Missing real intervals')
    sid=profiler.start(str(args.output/'advanced-overflow'),backend='enflame',hook='instrumentation',
        observation_request=profiler.ObservationRequest(programs=None,program_policy='runtime_first_last',
            automatic=True,max_sites=8,max_events_per_instance=4))
    debugger.register_launch_prepare_hook(prepare)
    try:math_case((3,2),11,'overflow')
    finally:profiler.finalize(sid)
    need(not records[-1]['complete'] and records[-1]['dropped_endpoint_references']>0 and not owners,
         'Overflow was hidden or resource retained')
    (args.output/'result.json').write_text(json.dumps(dict(
        status='actual_gcu_compact_producer_explicit_lifecycle_not_default_or_P01',
        ordinary_calls=1,explicit_profile_calls=4,captures=records,
        uses_development_prepare_hook=True,legacy_per_launch_sync_still_present=True,
        clock_qualified=False,boundary_qualified=False,perfetto_qualified=False),indent=2)+'\n')


if __name__=='__main__':
    main()
