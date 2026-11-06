"""Run a normal user kernel with automatic MetaX local-counter profiling."""
import argparse
from pathlib import Path
import torch
import triton
import triton.language as tl
from flagtree import profiler

@triton.jit
def scale_add(X,Y,N:tl.constexpr):
    i=tl.program_id(0)*128+tl.arange(0,128)
    value=tl.load(X+i,i<N,other=0)
    tl.store(Y+i,value*2+1,i<N)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='metax-profile')
    p.add_argument('--device',type=int,default=0)
    args=p.parse_args()
    torch.cuda.set_device(args.device)
    x=torch.arange(1024,device='cuda',dtype=torch.float32);y=torch.empty_like(x)
    scale_add[(8,)](x,y,1024)
    session=profiler.start(args.output,detail='timeline',timeline_record_capacity=512)
    try:
        scale_add[(8,)](x,y,1024)
        scale_add[(8,)](x,y,1024)
        torch.cuda.synchronize()
    finally:
        profiler.finalize(session)
    torch.testing.assert_close(y,x*2+1)
    print('Correct output; open a counter-ticks.pftrace under '+str(Path(args.output).resolve()/'timeline/captures'))
    print('The view shows local counter ticks; its synthetic coordinate is not physical nanoseconds.')
