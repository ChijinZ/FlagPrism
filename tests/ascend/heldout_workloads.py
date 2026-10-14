"""Preselected RMSNorm heldout; no user trace parameter or source patching."""
import triton
import triton.language as tl

@triton.jit
def rmsnorm(X,W,Y,R:tl.constexpr,N:tl.constexpr,BLOCK:tl.constexpr):
    row=tl.program_id(0)
    column=tl.arange(0,BLOCK)
    value=tl.load(X+row*N+column,column<N,0)
    weight=tl.load(W+column,column<N,0)
    normalized=value*tl.rsqrt(tl.sum(value*value,0)/N+1.e-5)*weight
    tl.store(Y+row*N+column,normalized,column<N)
