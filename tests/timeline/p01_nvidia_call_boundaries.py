"""Real-math device-call boundary primitive, not automatic profiler qualification.

Tests whether actual noinline device calls survive lowering. Final code and
participant/completion semantics still need auditing before a production change.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def need(value, message):
    if not value:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    import torch
    import triton
    import triton.language as tl

    @triton.jit(noinline=True)
    def enter(value):
        if value.dtype == tl.float32:
            forwarded, stamp = tl.inline_asm_elementwise(
                '// flagprism_call_probe_entry\nmov.u64 $1, %globaltimer;\nmov.b32 $0, $2;',
                constraints='=f,=l,f', args=[value], dtype=(tl.float32,tl.uint64),
                is_pure=False, pack=1)
        else:
            forwarded, stamp = tl.inline_asm_elementwise(
                '// flagprism_call_probe_entry\nmov.u64 $1, %globaltimer;\nmov.b64 $0, $2;',
                constraints='=l,=l,l', args=[value], dtype=(tl.int64,tl.uint64),
                is_pure=False, pack=1)
        return forwarded, stamp

    @triton.jit(noinline=True)
    def leave(value):
        if value.dtype == tl.float32:
            forwarded, stamp = tl.inline_asm_elementwise(
                '// flagprism_call_probe_exit\nmov.b32 $0, $2;\nmov.u64 $1, %globaltimer;',
                constraints='=f,=l,f', args=[value], dtype=(tl.float32,tl.uint64),
                is_pure=False, pack=1)
        else:
            forwarded, stamp = tl.inline_asm_elementwise(
                '// flagprism_call_probe_exit\nmov.b64 $0, $2;\nmov.u64 $1, %globaltimer;',
                constraints='=l,=l,l', args=[value], dtype=(tl.int64,tl.uint64),
                is_pure=False, pack=1)
        return forwarded, stamp

    @triton.jit(noinline=True)
    def read_only(value, START:tl.constexpr):
        if START:
            assembly = '// flagprism_call_probe_entry\nmov.u64 $0, %globaltimer;\n// value $1'
        else:
            assembly = '// flagprism_call_probe_exit\nmov.u64 $0, %globaltimer;\n// value $1'
        if value.dtype == tl.float32:
            stamp = tl.inline_asm_elementwise(assembly, constraints='=l,r',
                args=[value.to(tl.uint32,bitcast=True)], dtype=tl.uint64,
                is_pure=False,pack=1)
        else:
            stamp = tl.inline_asm_elementwise(assembly, constraints='=l,l',
                args=[value], dtype=tl.uint64, is_pure=False,pack=1)
        return stamp

    @triton.jit
    def math(X,Y,K,T,State,INTEGER:tl.constexpr,MAX_K:tl.constexpr,FORWARD:tl.constexpr):
        pid=tl.program_id(0)
        value=tl.load(X+pid)
        k=tl.load(K+pid)
        for r in range(k):
            if FORWARD:
                value, begin=enter(value)
            else:
                begin=read_only(value,True)
            if INTEGER:
                value=value*3+1
            else:
                value=value*0.75+0.125
            if FORWARD:
                value, finish=leave(value)
            else:
                finish=read_only(value,False)
            tl.store(T+pid*MAX_K*2+r*2,begin)
            tl.store(T+pid*MAX_K*2+r*2+1,finish)
        tl.store(Y+pid,value)
        prior=tl.load(State+pid)
        tl.store(State+pid,prior+1)

    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability(0)==(12,0),'Wrong registered target')
    registration=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        target='cuda:120',programs=3,max_k=32,runtime_k=[[3,7,11],[11,3,7]],
        dtypes=['float32','int64'],modes=['forwarded','read_only'],math_requests_per_dtype_mode=2,
        float_rtol=2e-6,float_atol=2e-6,explicit_compile_only=True,
        scope='device call primitive only, no automatic profiler or clock certificate')
    save(a.output/'registration.json',registration)
    cases=[]
    for forward,dtype in [(True,torch.float32),(True,torch.int64),
                          (False,torch.float32),(False,torch.int64)]:
        integer=dtype==torch.int64
        name=('forwarded-' if forward else 'read-only-')+('int64' if integer else 'fp32')
        source=torch.tensor([1,2,3],dtype=dtype) if integer else torch.tensor([0.25,0.5,0.75],dtype=dtype)
        x=source.cuda();y=torch.full((5,),-711,dtype=dtype,device='cuda')
        k=torch.tensor([3,7,11],dtype=torch.int32,device='cuda')
        state=torch.zeros(3,dtype=torch.int32,device='cuda')
        stamps=torch.full((3*32*2+4,),-1,dtype=torch.int64,device='cuda')
        inputs=(x,y,k,stamps,state)
        compiled=math.warmup(*inputs,INTEGER=integer,MAX_K=32,FORWARD=forward,grid=(3,),num_warps=4)
        compiled._init_handles()
        need(state.cpu().tolist()==[0,0,0],'Compile-only ran math')
        ptx=compiled.asm['ptx']
        need(re.search(r'\bcall(?:\.uni)?\s*\(',ptx) is not None,
             'No actual PTX device call survived')
        artifacts=[]
        for kind,blob in compiled.asm.items():
            if isinstance(blob,str):blob=blob.encode()
            if not isinstance(blob,bytes):continue
            path=a.output/(name+'.'+kind);path.write_bytes(blob)
            artifacts.append(dict(path=path.name,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()))
        save(a.output/(name+'-artifacts.json'),artifacts)
        for trial,counts in enumerate(registration['runtime_k']):
            k.copy_(torch.tensor(counts,dtype=torch.int32,device='cuda'))
            stamps.fill_(-1)
            actual=math[(3,)](*inputs,INTEGER=integer,MAX_K=32,FORWARD=forward,num_warps=4)
            torch.cuda.synchronize()
            output=y.cpu();expected=source.clone()
            for pid,n in enumerate(counts):
                for _ in range(n):
                    expected[pid]=expected[pid]*3+1 if integer else expected[pid]*0.75+0.125
            raw=stamps.cpu().tolist();states=state.cpu().tolist()
            row=dict(dtype=name,trial=trial,counts=counts,state=states,ticks=raw,
                output=output.tolist(),expected=expected.tolist(),
                binary_sha256=hashlib.sha256(actual.asm['cubin']).hexdigest())
            cases.append(row);save(a.output/'calls.json',cases)
            need(actual is compiled,'Runtime input changed actual binary')
            need(states==[trial+1]*3,'Requested math call was replayed')
            need(torch.equal(x.cpu(),source) and output[3:].tolist()==[-711,-711],
                 'Input or output tail changed')
            need(torch.equal(output[:3],expected) if integer else
                 torch.allclose(output[:3],expected,rtol=2e-6,atol=2e-6),
                 'Real math differs from frozen CPU oracle')
            positives=0
            for pid,n in enumerate(counts):
                observed=raw[pid*64:pid*64+n*2]
                need(all(0<z<2**63 for z in observed),'Missing actual clock value')
                for i in range(0,len(observed),2):
                    need(observed[i]<=observed[i+1],'Counter order reversed')
                    positives+=observed[i]<observed[i+1]
                need(raw[pid*64+n*2:(pid+1)*64]==[-1]*(64-n*2),
                     'Unexecuted iterations received synthesized timestamps')
            need(raw[-4:]==[-1]*4 and positives>0,'Missing intervals or damaged timestamp tail')
            row['math_input_tail_and_once_passed']=True
            row['positive_counter_intervals']=positives
            save(a.output/'calls.json',cases)
    save(a.output/'result.json',dict(status='real_device_call_math_passed_pending_final_machine_audit',
        registration=registration,cases=cases,
        limits=['Dedicated manually observed primitive, not automatic user profiling',
                'No clock scale/epoch/endpoint-error certificate',
                'Actual call and observed-operation ordering must be checked in final objects',
                'No claim of uninstrumented latency, engine busy or async completion']))


if __name__=='__main__':
    main()
