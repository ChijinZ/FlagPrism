"""Resumable CANN math/T5 runner through public profiler requests.

Every worker runs in the Ascend Docker. Inputs are fixed Study bytes; kernels
compile afresh. A completed receipt is reused only for the exact plan hash.
Native task intervals require exact invocation and binary identity; off-mode device tasks
remain unavailable rather than comparing them to a stream envelope.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import signal
import statistics
import subprocess
import sys
import time
import traceback

OPERATORS = ('gemm', 'gemm_bias_gelu', 'softmax', 'layernorm', 'reduce_sum',
             'transpose')
SHAPES = {'gemm': [(128,128,128),(512,512,512),(257,193,320)],
          'transpose': [(256,256),(1024,1024),(513,257)],
          'rows': [(32,256),(256,1024),(127,769)]}
MODES = ('off','native','detailed')


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, default=str)+'\n')


def matched_native_tasks(events, samples, binary_id):
    """Select exact measured calls, retaining legal scope zero and rejecting duplicates."""
    requested = {}
    for sample in samples:
        identity = sample.get('invocation_identity')
        if not isinstance(identity, dict):
            return []
        invocation = identity.get('invocation_id')
        if not isinstance(invocation,
                          str) or identity.get('binary_id') != binary_id:
            return []
        if invocation in requested:
            return []
        requested[invocation] = identity
    matches = []
    for event in events:
        identity = event.get('invocation_identity')
        if (event.get('kind') != 'kernel'
                or event.get('source') != 'cann_sdk_task'
                or not isinstance(identity, dict)
                or identity.get('status') != 'verified_task_identity'
                or identity.get('evidence_kind')
                != 'retained_worker_token_and_sdk_connection_tables'):
            continue
        wanted = requested.get(identity.get('invocation_id'))
        if (wanted is not None and identity.get('binary_id') == binary_id
                and identity.get('scope_id') == wanted.get('scope_id')
                and event.get('scope_id') == wanted.get('scope_id')):
            matches.append(event)
    counts = {}
    for event in matches:
        invocation = event['invocation_identity']['invocation_id']
        counts[invocation] = counts.get(invocation, 0) + 1
    return matches if set(counts) == set(requested) and all(
        value == 1 for value in counts.values()) else []


def worker(plan, output):
    os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD']='0'
    # Installed core is never changed: caller selects a freshly built core path.
    compiler_source=Path(os.environ['METHOD_COMPILER_SOURCE'])
    sys.path.insert(0,str(compiler_source/'python'))
    import torch
    import torch_npu
    import triton
    import triton.language as tl
    import triton._C.libtriton as libtriton
    import flagtree
    source=Path(os.environ['METHOD_SOURCE'])
    for component,directory in [('debugger','Debugger/python/flagtree_debugger'),('profiler','Profiler/python/flagtree_profiler')]:
        name='flagtree.'+component;package=source/directory
        built=Path(os.environ['METHOD_COMPONENT_PYTHON'])/'flagtree'/component
        spec=importlib.util.spec_from_file_location(name,package/'__init__.py',submodule_search_locations=[str(built),str(package)])
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
        setattr(flagtree,component,module)
    from flagtree import profiler
    from flagtree.profiler.observations import ObservationRequest
    from flagtree.profiler.hooks.hook import Hook,HookManager
    from flagtree.debugger.native import compiler_binding, runtime_binding as debugger_runtime
    from flagtree.profiler.native import runtime_binding as profiler_runtime
    binding=compiler_binding()
    if binding is None or not hasattr(binding,'prepare_late_observation_abi'):
        raise RuntimeError('new hidden-only Debugger compiler binding was not built/loaded')
    workload_path=source/'tests/nvidia/reference_workloads.py'
    spec=importlib.util.spec_from_file_location('ascend_acceptance_math',workload_path)
    workloads=importlib.util.module_from_spec(spec);sys.modules[spec.name]=workloads;spec.loader.exec_module(workloads)
    heldout_path=Path(__file__).with_name('heldout_workloads.py')
    spec=importlib.util.spec_from_file_location('ascend_acceptance_heldout',heldout_path)
    heldout=importlib.util.module_from_spec(spec);sys.modules[spec.name]=heldout;spec.loader.exec_module(heldout)
    rmsnorm=heldout.rmsnorm
    class IdentityObserver(Hook):
        priority=-100
        last=None
        def activate(self):pass
        def deactivate(self):pass
        def init_handle(self,*args):pass
        def enter(self,metadata):
            self.last=dict(getattr(metadata,'_flagprism_invocation_identity',{}))
        def exit(self,metadata):pass
    torch.set_num_threads(8);torch.npu.set_device(plan['device'])
    device=f"npu:{plan['device']}"
    cpu_inputs=[];device_inputs=[];input_hashes=[]
    family='matmul' if plan['operator'].startswith('gemm') else 'transpose' if plan['operator']=='transpose' else 'rows'
    def read(index,dimensions,dtype=torch.float32):
        path=Path(os.environ['METHOD_CANONICAL_INPUTS'])/f'{family}-{"x".join(map(str,plan["shape"]))}-{index}.bin'
        raw=path.read_bytes();value=torch.frombuffer(bytearray(raw),dtype=dtype).reshape(dimensions).clone()
        cpu_inputs.append(value);input_hashes.append({'file':path.name,'sha256':hashlib.sha256(raw).hexdigest()})
        actual=value.to(device);device_inputs.append(actual);return value,actual
    operator=plan['operator'];shape=plan['shape'];variant=plan['variant']
    if operator.startswith('gemm'):
        m,n,k=shape;a,da=read(0,(m,k),torch.float16);b,db=read(1,(k,n),torch.float16);bias,dbias=read(2,(n,))
        expected=a.float()@b.float()
        if operator=='gemm_bias_gelu':expected=torch.nn.functional.gelu(expected+bias,approximate='tanh')
        config = resolve_matmul_config(plan)
        bm, bn, bk = (config[key] for key in ('BM', 'BN', 'BK'))
        stages, warps = (config[key] for key in ('num_stages', 'num_warps'))
        grid=(triton.cdiv(m,bm),triton.cdiv(n,bn))
        def invoke():return workloads.matmul[grid](da,db,dbias,result,m,n,k,bm,bn,bk,operator=='gemm_bias_gelu',num_stages=stages,num_warps=warps)
        atol,rtol=.002,.02
    elif operator=='transpose':
        m,n=shape;x,dx=read(0,(m,n));expected=x.T.contiguous();bm=16 if variant==0 else 32;bn=16
        config={'BM':bm,'BN':bn,'num_stages':1,'num_warps':4};grid=(triton.cdiv(m,bm),triton.cdiv(n,bn))
        def invoke():return workloads.transpose[grid](dx,result,m,n,bm,bn,num_stages=1,num_warps=4)
        atol,rtol=0.,0.
    else:
        r,n=shape;x,dx=read(0,(r,n));w,dw=read(1,(n,));bias,dbias=read(2,(n,))
        if operator=='softmax':expected=torch.softmax(x,-1)
        elif operator=='layernorm':expected=torch.nn.functional.layer_norm(x,(n,),w,bias,1.e-5)
        elif operator=='rmsnorm':expected=x*torch.rsqrt((x*x).mean(-1,keepdim=True)+1.e-5)*w
        else:expected=x.sum(-1)
        block=triton.next_power_of_2(n);rows=variant+1;warps=(1 if variant==0 else 4) if operator=='rmsnorm' else 4
        config={'ROWS':1 if operator=='rmsnorm' else rows,'BLOCK':block,'num_stages':1,'num_warps':warps}
        grid=(r,) if operator=='rmsnorm' else (triton.cdiv(r,rows),)
        if operator=='rmsnorm':
            def invoke():return rmsnorm[grid](dx,dw,result,r,n,block,num_stages=1,num_warps=warps)
        else:
            def invoke():return workloads.rows[grid](dx,dw,dbias,result,r,n,block,rows,operator,num_stages=1,num_warps=warps)
        atol,rtol=.0005,.002
    storage=torch.full((expected.numel()+32,),-12345.,dtype=torch.float32,device=device)
    result=storage[16:-16].reshape(expected.shape)
    record={'schema_version':1,'status':'running','plan':plan,'input_hashes':input_hashes,'config':config,'grid':grid,
            'oracle':{'device':'CPU in same Docker','atol':atol,'rtol':rtol},
            'source_hashes':{'runner':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'math':hashlib.sha256(workload_path.read_bytes()).hexdigest(),'heldout':hashlib.sha256(heldout_path.read_bytes()).hexdigest()},
            'compiler':{'path':libtriton.__file__,'sha256':hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest()},
            'native_bindings':{name:{'path':library.__file__,'sha256':hashlib.sha256(Path(library.__file__).read_bytes()).hexdigest()}
                               for name,library in [('debugger',debugger_runtime()),('profiler',profiler_runtime())]},
            'samples':[],'device_task_samples':[], 'device_task_identity_status':'unavailable',
            'added_synchronization':'One stream-envelope end synchronization per measured phase; detailed mode also native TransferEngine syncExport, reported separately by capture.',
            'validation_boundary':'Math/input/canary checks after profiler finalization; no CPU reference work inside measured launches.'}
    dump(output/'result.json',record)
    session=None;observer=None
    try:
        mode=plan['mode']
        if mode=='native':
            # Public native-only option: default IR-triton path would add snapshot logging.
            os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY']='1'
        else:os.environ.pop('FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY',None)
        if mode!='off':
            request = ObservationRequest(
                semantics=tuple(
                    plan.get('semantics',
                             ('issue', 'wait_bracket', 'control_checkpoint'))),
                programs=(0, ),
                max_events_per_instance=plan['capacity']
            ) if mode == 'detailed' else None
            session=profiler.start(str(output/'capture'),backend='cann',hook='instrumentation' if request else 'triton',
                observation_request=request,mode=f"runtime_base:device_id={plan['device']}:mstx_enabled=true:aclprof_msproftx_enabled=true:runtime_host_timing_fallback=false",
                metadata={'operator':operator,'parameters':{'shape':shape,'config':config},'validation':record['oracle'],'test_plan':plan})
            observer=IdentityObserver();HookManager.register(observer,session)
        start=time.perf_counter_ns()
        for warmup in range(plan['warmup']):
            compile_start=time.perf_counter_ns();compiled=invoke()
            if warmup==0:record['first_compile_and_launch_ns']=time.perf_counter_ns()-compile_start
        torch.npu.synchronize();record['prepare_compile_warmup_ns']=time.perf_counter_ns()-start
        record['compiled_binary_id']=compiled.hash
        record['compiler_metadata']=dict(compiled.metadata._asdict()) if hasattr(compiled.metadata,'_asdict') else vars(compiled.metadata)
        begin,end=torch.npu.Event(enable_timing=True),torch.npu.Event(enable_timing=True)
        begin.record()
        for index in range(plan['samples']):
            start=time.perf_counter_ns();current=invoke();elapsed=time.perf_counter_ns()-start
            if current.hash!=compiled.hash:raise RuntimeError('binary identity changed within measured phase')
            record['samples'].append({'sample':index,'host_launch_ns':elapsed,'invocation_identity':observer.last if observer else None})
        end.record();end.synchronize();record['npu_stream_envelope_ms']=begin.elapsed_time(end)
        record['npu_stream_envelope_semantics']='Encloses host submission/callback gaps; not engine busy or per-task duration.'
        start=time.perf_counter_ns()
        if session is not None:profiler.finalize(session);session=None
        record['finalization_export_ns']=time.perf_counter_ns()-start
        torch.testing.assert_close(result.cpu(),expected,atol=atol,rtol=rtol)
        guards=storage.cpu();assert torch.all(guards[:16]==-12345.) and torch.all(guards[-16:]==-12345.),'output canary corrupted'
        for cpu,actual in zip(cpu_inputs,device_inputs):torch.testing.assert_close(actual.cpu(),cpu,atol=0,rtol=0)
        record['max_abs_error']=(result.cpu()-expected).abs().max().item()
        if mode!='off':
            events=[json.loads(line) for line in (output/'capture/ai/events.jsonl').read_text().splitlines()]
            kernels=[event for event in events if event.get('kind')=='kernel']
            if not kernels:raise RuntimeError('native CANN capture produced no actual kernel activities')
            matched = matched_native_tasks(kernels, record['samples'],
                                           record['compiled_binary_id'])
            record['all_native_kernel_count']=len(kernels);record['device_task_samples']=matched
            record['device_task_identity_status']='verified' if len(matched)==plan['samples'] else 'partial'
            record['native_kernel_lifecycles']=kernels
            if mode=='detailed':
                document=json.loads((output/'capture/ai/observations.json').read_text())
                detailed=[event for event in document.get('observations',[]) if event.get('source')=='ascend_llvm_dynamic64']
                record['dynamic_observation_count']=len(detailed)
                record['dynamic_evidence_status']='observed' if detailed else 'no_selected_events'
        record['trace_files']=[{'path':str(path.relative_to(output)),'bytes':path.stat().st_size} for path in output.rglob('*') if path.is_file() and path.name!='result.json']
        record['status']='passed_math_and_native' if mode!='off' else 'passed_math'
    except BaseException as error:
        record.update(status='failed',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        try:
            if session is not None:profiler.finalize(session)
        except BaseException as cleanup_error:
            record['cleanup_error']=repr(cleanup_error)
            record['status']='failed'
            raise
        finally:
            dump(output/'result.json',record)


def resolve_matmul_config(plan):
    """Explicit case overrides retain the ordinary mathematical kernel."""
    variant = plan['variant']
    config = {
        'BM': 16 if variant == 0 else 32,
        'BN': 16,
        'BK': 16,
        'num_stages': variant + 1,
        'num_warps': 4
    }
    if 'config' not in plan:
        return config
    override = plan['config']
    if not isinstance(override, dict) or set(override) - set(config):
        raise ValueError(
            'matmul config must be a dictionary of supported tile/stage/warp keys'
        )
    config.update(override)
    for key, value in config.items():
        if type(value) is not int or value <= 0:
            raise ValueError('matmul config values must be positive integers')
        if key != 'num_stages' and value & (value - 1):
            raise ValueError(
                'matmul tile and warp values must be powers of two')
    return config


def build_plans(suite, device):
    """Keep generalization and fixed-shape perturbation as separate contracts."""
    if suite not in ('operators', 't5', 'heldout'):
        raise ValueError('unsupported acceptance suite')
    plans = []
    rng = random.Random(1729)
    for operator in OPERATORS if suite == 'operators' else ('rmsnorm', ):
        if suite == 'operators':
            family = 'gemm' if operator.startswith(
                'gemm') else 'transpose' if operator == 'transpose' else 'rows'
            shapes = SHAPES[family]
        else:
            shapes = [(127, 769)] if suite == 't5' else SHAPES['rows']
        for shape in shapes:
            for variant in (0, ) if suite == 't5' else (0, 1):
                for batch in range(3 if suite == 't5' else 1):
                    modes = list(MODES)
                    rng.shuffle(modes)
                    for mode in modes:
                        plans.append({
                            'operator': operator,
                            'shape': list(shape),
                            'variant': variant,
                            'batch': batch,
                            'mode': mode,
                            'device': device,
                            'capacity': 256,
                            'warmup': 3,
                            'samples': 30 if suite == 't5' else 3
                        })
    return plans


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--worker',type=Path)
    parser.add_argument('--suite',
                        choices=('operators', 't5', 'heldout'),
                        default='operators')
    parser.add_argument('--device', type=int, default=4)
    parser.add_argument('--timeout',type=int,default=300);args=parser.parse_args()
    if args.worker:
        plan=json.loads(args.worker.read_text());args.output.mkdir(parents=True,exist_ok=False);worker(plan,args.output);return
    args.output.mkdir(parents=True,exist_ok=True)
    plans = build_plans(args.suite, args.device)
    source=Path(os.environ['METHOD_SOURCE'])
    provenance={'source_hashes':{str(path.relative_to(source)):hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in [Path(__file__).resolve(),Path(__file__).with_name('heldout_workloads.py').resolve(),source/'tests/nvidia/reference_workloads.py']},
                'compiler_sha256':hashlib.sha256((Path(os.environ['METHOD_COMPILER_SOURCE'])/'python/triton/_C/libtriton.so').read_bytes()).hexdigest(),
                'plugin_sha256':hashlib.sha256(Path(os.environ['FLAGPRISM_ASCEND_LATE_PLUGIN']).read_bytes()).hexdigest()}
    provenance['native_sha256']={}
    for component in ('debugger','profiler'):
        libraries=list((Path(os.environ['METHOD_COMPONENT_PYTHON'])/'flagtree'/component).glob('_native*.so'))
        if len(libraries)!=1:raise RuntimeError(f'new {component} runtime library identity is missing or ambiguous')
        provenance['native_sha256'][component]=hashlib.sha256(libraries[0].read_bytes()).hexdigest()
    plan_text=json.dumps({'plans':plans,'provenance':provenance},sort_keys=True);plan_hash=hashlib.sha256(plan_text.encode()).hexdigest()
    contract={'suite':args.suite,'plan_sha256':plan_hash,'provenance':provenance,'plans':plans,'preselected_heldout':'RMSNorm; CPU float32 x*rsqrt(mean(x*x)+1e-5)*weight; atol .0005/rtol .002','order_seed':1729,'device_task_limit':'SDK-off device task timing unavailable; off NPU event is a stream envelope. No ≤5%/≤10% task claim without a separate reference.'}
    existing=args.output/'plan.json'
    if existing.exists() and json.loads(existing.read_text())!=contract:raise RuntimeError('refusing to resume another acceptance plan')
    dump(existing,contract);receipts=[]
    for index,plan in enumerate(plans):
        directory=args.output/f'job-{index:03d}';plan_file=args.output/f'job-{index:03d}.json';dump(plan_file,plan)
        receipt_path=args.output/f'job-{index:03d}.receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            if receipt.get('status')=='completed' and receipt.get('plan_sha256')==plan_hash:receipts.append(receipt);continue
        if directory.exists():raise RuntimeError(f'failed/incomplete {directory}; preserve it and choose a new output directory after fixing the mechanism')
        command=[sys.executable,str(Path(__file__).resolve()),'--worker',str(plan_file.resolve()),'--output',str(directory.resolve())]
        receipt={'command':command,'plan_sha256':plan_hash,'job':index,'plan':plan,'status':'started','started_unix':time.time()};dump(receipt_path,receipt)
        try:
            with (args.output/f'job-{index:03d}.log').open('wb') as log:
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    process.wait(timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL);process.wait()
                    raise
            receipt['returncode']=process.returncode;receipt['status']='completed' if process.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:receipt['status']='timeout';receipt['returncode']=None
        receipt['ended_unix']=time.time();dump(receipt_path,receipt);receipts.append(receipt)
        dump(args.output/'summary.json',{'status':'running' if receipt['status']=='completed' else 'failed','contract':contract,'receipts':receipts})
        if receipt['status']!='completed':raise RuntimeError(f'acceptance job {index} {receipt["status"]}; see its retained log')
    results=[json.loads((args.output/f'job-{receipt["job"]:03d}/result.json').read_text()) for receipt in receipts]
    measurements=[]
    for result in results:
        tasks=result['device_task_samples']
        durations=[event['duration_us'] for event in tasks if event.get('duration_us') is not None]
        measurements.append({'plan':result['plan'],
                             'host_launch_median_ns':statistics.median(sample['host_launch_ns'] for sample in result['samples']),
                             'device_task_median_us':statistics.median(durations) if durations and result['device_task_identity_status']=='verified' else None,
                             'device_task_identity_status':result['device_task_identity_status'],
                             'stream_envelope_ms':result['npu_stream_envelope_ms'],
                             'first_compile_and_launch_ns':result['first_compile_and_launch_ns'],
                             'finalization_export_ns':result['finalization_export_ns'],
                             'trace_bytes':sum(item['bytes'] for item in result['trace_files']),
                             'dynamic_observation_count':result.get('dynamic_observation_count')})
    dump(args.output/'summary.json',{'status':'completed_math_native_matrix','contract':contract,'receipts':receipts,'measurements':measurements,'capability_acceptance':'Requires separate review of dynamic, identity and clock evidence; this status alone is not method completion.'})

if __name__=='__main__':main()
