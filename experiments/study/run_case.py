#!/usr/bin/env python3
"""One fresh-process study case. Preserve raw observations and missing data explicitly."""
import argparse, hashlib, json, os, platform, statistics, time, traceback
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD', '0')
p = argparse.ArgumentParser()
p.add_argument('--backend', required=True, choices=['cann', 'enflame', 'cuda'])
p.add_argument('--operator', required=True, choices=['gemm','gemm_bias_gelu','softmax','layernorm','reduce_sum','transpose'])
p.add_argument('--shape', required=True, help='MxNxK for GEMM, RxN otherwise')
p.add_argument('--variant', type=int, choices=[0,1], default=0)
p.add_argument('--device', type=int, default=0)
p.add_argument('--phase', choices=['baseline','native','internal','lowering'], default='baseline')
p.add_argument('--output', type=Path, required=True)
p.add_argument('--collector', choices=['flagprism','torch'], default='flagprism')
p.add_argument('--repeats', type=int, default=7)
p.add_argument('--batch', type=int, default=20)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
result = {'schema_version':1, 'backend':a.backend, 'operator':a.operator,
          'shape':[int(x) for x in a.shape.split('x')], 'variant':a.variant,
          'phase':a.phase, 'device':a.device, 'status':'started',
          'host':{'machine':platform.machine(),'python':platform.python_version()},
          'measurement':{'warmup':5,'repeats':a.repeats,'batch':a.batch,
                         'host_clock':'perf_counter_ns',
                         'device_event_semantics':'stream interval enclosing a batch; not busy cycles'},
          'utc_started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
if a.phase!='baseline':
    result['measurement']={'warmup':5,'scope':'compiler diagnostics' if a.phase=='lowering' else 'three prewarmed profiled launches followed by synchronization','launch_count':1 if a.phase=='lowering' else 3}
def save():
    (a.output/'result.json').write_text(json.dumps(result, indent=2, default=str)+'\n')
save()
if a.phase=='lowering':
    os.environ['TRITON_KERNEL_DUMP']='1'
    os.environ['TRITON_DUMP_DIR']=str(a.output.resolve()/'compiler_dump')
try:
    import torch
    if a.backend == 'cann':
        import torch_npu
        iface, device_type = torch.npu, 'npu'
    elif a.backend == 'enflame':
        import torch_gcu
        iface, device_type = torch.gcu, 'gcu'
    else:
        iface, device_type = torch.cuda, 'cuda'
    import triton
    import kernels
    iface.set_device(a.device)
    device = torch.device(f'{device_type}:{a.device}')
    driver=triton.runtime.driver
    if hasattr(driver,'active'):
        target=driver.active.get_current_target()
    elif a.backend=='cuda':
        target={'backend':'cuda','arch':torch.cuda.get_device_capability(a.device),'legacy_triton_driver':True}
    else:raise RuntimeError('Unsupported legacy Triton driver API')
    result['runtime']={'torch':torch.__version__, 'triton':triton.__version__,
                       'torch_file':torch.__file__, 'triton_file':triton.__file__, 'target':str(target)}
    torch.manual_seed(1729)
    def rand(shape, dtype=torch.float32):
        return torch.randn(shape, device='cpu', dtype=dtype) * 0.1
    shape = result['shape']; op = a.operator
    if op.startswith('gemm'):
        M,N,K=shape
        cpu_a, cpu_b, cpu_bias=rand((M,K),torch.float16),rand((K,N),torch.float16),rand((N,))
        ref=cpu_a.float() @ cpu_b.float()
        if op=='gemm_bias_gelu':
            ref=torch.nn.functional.gelu(ref + cpu_bias, approximate='tanh')
        A,B,Bias=cpu_a.to(device),cpu_b.to(device),cpu_bias.to(device)
        Y=torch.empty((M,N),dtype=torch.float32,device=device)
        config={'BM':16,'BN':16,'BK':16,'num_stages':a.variant+1,'num_warps':4}
        grid=(triton.cdiv(M,16),triton.cdiv(N,16))
        def launch():
            return kernels.matmul[grid](A,B,Bias,Y,M,N,K,16,16,16,op=='gemm_bias_gelu',num_stages=a.variant+1,num_warps=4,debug=(a.phase=='lowering'))
        tolerance={'atol':0.002,'rtol':0.02}
    elif op=='transpose':
        M,N=shape; cpu_x=rand((M,N)); ref=cpu_x.T.contiguous()
        X=cpu_x.to(device); Y=torch.empty((N,M),dtype=torch.float32,device=device)
        bm=16 if a.variant==0 else 32
        config={'BM':bm,'BN':16,'num_stages':1,'num_warps':4}
        grid=(triton.cdiv(M,bm),triton.cdiv(N,16))
        def launch():
            return kernels.transpose[grid](X,Y,M,N,bm,16,num_stages=1,num_warps=4,debug=(a.phase=='lowering'))
        tolerance={'atol':0.0,'rtol':0.0}
    else:
        R,N=shape; cpu_x,cpu_w,cpu_b=rand((R,N)),rand((N,)),rand((N,))
        if op=='softmax': ref=torch.softmax(cpu_x,dim=-1)
        elif op=='layernorm': ref=torch.nn.functional.layer_norm(cpu_x,(N,),cpu_w,cpu_b,1e-5)
        else: ref=cpu_x.sum(-1)
        X,W,B=cpu_x.to(device),cpu_w.to(device),cpu_b.to(device)
        Y=torch.empty(ref.shape,dtype=torch.float32,device=device)
        rows=1 if a.variant==0 else 2
        config={'ROWS':rows,'BLOCK':triton.next_power_of_2(N),'num_stages':1,'num_warps':4}
        grid=(triton.cdiv(R,rows),)
        def launch():
            return kernels.rows[grid](X,W,B,Y,R,N,config['BLOCK'],rows,op,num_stages=1,num_warps=4,debug=(a.phase=='lowering'))
        tolerance={'atol':0.0005,'rtol':0.002}
    if ref.device.type!='cpu':raise RuntimeError('Reference unexpectedly resides on accelerator')
    result['reference_device']=str(ref.device)
    result['requested_compile_config']=config; result['grid']=grid
    compiled=launch(); iface.synchronize()
    actual=Y.detach().cpu()
    result['validation']={'reference':'PyTorch CPU float32',**tolerance,
                          'max_abs_error':(actual-ref).abs().max().item(),
                          'finite':bool(torch.isfinite(actual).all()),
                          'passed':bool(torch.allclose(actual,ref,**tolerance))}
    if not result['validation']['passed']: raise RuntimeError('CPU-reference correctness check failed')
    result['compiled_metadata']=repr(getattr(compiled,'metadata',{'num_warps':getattr(compiled,'num_warps',None),'num_stages':getattr(compiled,'num_stages',None),'shared':getattr(compiled,'shared',None)}))
    ir=a.output/'asm'; ir.mkdir()
    result['asm']={}
    for stage,content in compiled.asm.items():
        if not isinstance(content,(str,bytes)): continue
        content=content.encode() if isinstance(content,str) else content
        filename=str(stage).replace('/','_')
        (ir/filename).write_bytes(content)
        result['asm'][stage]={'file':f'asm/{filename}','sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
    for _ in range(5): launch()
    iface.synchronize()
    if a.phase=='baseline':
        samples=[]; event_error=None
        for _ in range(a.repeats):
            iface.synchronize()
            try:
                start=iface.Event(enable_timing=True); end=iface.Event(enable_timing=True)
                start.record()
            except Exception as exc:
                start=end=None; event_error=repr(exc)
            t0=time.perf_counter_ns()
            for _ in range(a.batch): launch()
            t1=time.perf_counter_ns()
            if end is not None: end.record()
            iface.synchronize(); t2=time.perf_counter_ns()
            try: event_ns=start.elapsed_time(end)*1e6/a.batch if start is not None else None
            except Exception as exc: event_ns=None; event_error=repr(exc)
            samples.append({'host_submit_ns_per_call':(t1-t0)/a.batch,
                            'host_submit_and_sync_ns_per_call':(t2-t0)/a.batch,
                            'device_stream_interval_ns_per_call':event_ns})
        result['samples']=samples; result['device_event_error']=event_error
        result['statistics']={k:{'median':statistics.median(v), 'min':min(v),'max':max(v)}
                              for k in samples[0] if (v:=[s[k] for s in samples if s[k] is not None])}
    elif a.phase=='lowering':
        result['lowering_dump']={'scope':'static compiler diagnostics; not dynamic execution or a timing baseline',
                                 'files':[str(f.relative_to(a.output)) for f in (a.output/'compiler_dump').rglob('*') if f.is_file()]}
    elif a.phase=='native' and a.collector=='torch':
        if a.backend!='cuda': raise ValueError('Torch reference collection is currently validated only for CUDA')
        trace_dir=a.output/'reference';trace_dir.mkdir()
        result['profiling']={'collector':'torch.profiler / Kineto / CUPTI', 'launch_count':3,
                             'scope':'three prewarmed launches; independent reference collector, not FlagPrism'}
        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as capture:
            for _ in range(3): launch()
            iface.synchronize()
        capture.export_chrome_trace(str(trace_dir/'trace.json'))
        trace=json.loads((trace_dir/'trace.json').read_text())
        device_events=[e for e in trace.get('traceEvents',[]) if e.get('cat')=='kernel' and e.get('ph')=='X']
        result['profiling']['observed_kernel_events']=len(device_events)
        if not device_events: raise RuntimeError('CUPTI reference capture produced no device kernel intervals')
        actual=Y.detach().cpu()
        result['post_profile_validation']={'passed':bool(torch.allclose(actual,ref,**tolerance)),
                                           'max_abs_error':(actual-ref).abs().max().item()}
        if not result['post_profile_validation']['passed']: raise RuntimeError('Profiled correctness check failed')
    else:
        from flagtree import profiler
        hook='triton' if a.phase=='native' else 'instrumentation'
        if a.backend=='cann' and a.phase=='native':
            os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
        result['profiling']={'hook':hook,'requested_mode':'runtime_base:runtime_host_timing_fallback=false:device_id='+str(a.device),
                             'launch_count':3,'scope':'three kernel launches plus final synchronization; prewarmed'}
        if a.backend=='cuda':
            result['profiling']['requested_mode'] += ':vendor_metrics=launch_stats'
        if a.phase=='internal' and a.backend=='cann':
            result['profiling']['requested_mode'] += ':aclprof_runtime_enabled=false:aclprof_auto_export=false:mstx_enabled=false:aclprof_msproftx_enabled=false'
        result['profiling']['cann_legacy_hook']=os.environ.get('FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY')
        result['profiling']['profiler_module']=profiler.__file__
        session=profiler.start(str(a.output/'profile'),backend=a.backend,hook=hook,
                               mode=result['profiling']['requested_mode'])
        try:
            for _ in range(3): launch()
            iface.synchronize()
        finally:
            profiler.finalize(session)
        result['profiling']['files']=[str(f.relative_to(a.output)) for f in a.output.rglob('*') if f.is_file() and 'asm' not in f.parts]
        actual=Y.detach().cpu()
        result['post_profile_validation']={'passed':bool(torch.allclose(actual,ref,**tolerance)),
                                           'max_abs_error':(actual-ref).abs().max().item()}
        if not result['post_profile_validation']['passed']: raise RuntimeError('Profiled correctness check failed')
    result['status']='passed'
except Exception as exc:
    result['status']='failed'; result['error']=repr(exc); result['traceback']=traceback.format_exc()
    traceback.print_exc()
finally:
    save()
print(json.dumps({'operator':a.operator,'shape':a.shape,'variant':a.variant,'phase':a.phase,'status':result['status'],'error':result.get('error')}))
raise SystemExit(0 if result['status']=='passed' else 1)
