def softmax_reduce_trace(X,Y,T,R:tl.constexpr,N:tl.constexpr,BLOCK:tl.constexpr):
 pid=tl.program_id(0);row=pid+tl.arange(0,1);c=tl.arange(0,BLOCK);valid=(row[:,None]<R)&(c[None,:]<N);x=tl.load(X+row[:,None]*N+c[None,:],valid,float('-inf'))
 s0=tl.full((),0,tl.int32)
 if pid==0:s0=gd.begin_clock().to(tl.int32)
 mx=tl.max(x,1)
 e0=tl.full((),0,tl.int32)
 if pid==0:e0=gd.end_clock().to(tl.int32)
 e=tl.exp(x-mx[:,None])
 s1=tl.full((),0,tl.int32)
 if pid==0:s1=gd.begin_clock().to(tl.int32)
 den=tl.sum(e,1)
 e1=tl.full((),0,tl.int32)
 if pid==0:e1=gd.end_clock().to(tl.int32)
 y=e/den[:,None]
 tl.store(Y+row[:,None]*N+c[None,:],y,valid)
 if pid==0:
  tl.store(T+pid*8,s0);tl.store(T+pid*8+1,e0);tl.store(T+pid*8+2,s1);tl.store(T+pid*8+3,e1)
  tl.store(T+pid*8+4,pid);tl.store(T+pid*8+5,0);tl.store(T+pid*8+6,1);tl.store(T+pid*8+7,0)
