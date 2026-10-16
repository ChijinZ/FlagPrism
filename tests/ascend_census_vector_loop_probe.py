"""Public independent vector-loop smoke for Ascend census v3."""
import argparse,json,os
from pathlib import Path
os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD']='0'
import torch
import torch_npu
import triton
import triton.language as tl
from flagtree import profiler

@triton.jit
def vector_loop(x,out,state,N:tl.constexpr):
    idx=tl.program_id(0)*256+tl.arange(0,256)
    mask=idx<N
    value=tl.full((256,),0,tl.int32)
    for iteration in range(4):
        value+=tl.load(x+idx,mask,0,volatile=True)
        tl.store(out+idx,value,mask)
    prior=tl.load(state+idx,mask,0)
    tl.store(state+idx,prior+1,mask)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    torch.npu.set_device(4)
    cpu=torch.arange(1024,dtype=torch.int32)%17
    x=cpu.npu();out=torch.empty_like(x);state=torch.zeros_like(x)
    session=profiler.start(str(a.output/'capture'),backend='cann',detail='auto')
    try:
        compiled=vector_loop[(4,)](x,out,state,1024,enable_auto_blockify=False)
        torch.npu.synchronize()
    finally:
        profiler.finalize(session)
    torch.testing.assert_close(out.cpu(),cpu*4,rtol=0,atol=0)
    assert bool((state.cpu()==1).all())
    result=dict(status='pass',binary=compiled.hash,state_elements=1024,state_values=[1],pid=os.getpid())
    (a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':main()
