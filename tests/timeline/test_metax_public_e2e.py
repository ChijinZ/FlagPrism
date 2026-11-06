"""Real user kernels through the public MetaX timeline API; no manual probes."""
import json
from pathlib import Path
import pytest

torch = pytest.importorskip('torch')
triton = pytest.importorskip('triton')
import triton.language as tl

@triton.jit
def vector(X,Y,N:tl.constexpr):
    i=tl.program_id(0)*128+tl.arange(0,128)
    x=tl.load(X+i,i<N,other=0)
    tl.store(Y+i,x*2+1,i<N)

@triton.jit
def reduction(X,Y):
    x=tl.load(X+tl.arange(0,1024))
    tl.store(Y,tl.sum(x,0))

@triton.jit
def matrix(A,B,C):
    m=tl.arange(0,32);k=tl.arange(0,32);n=tl.arange(0,32)
    a=tl.load(A+m[:,None]*32+k[None,:])
    b=tl.load(B+k[:,None]*32+n[None,:])
    c=tl.dot(a,b)
    tl.store(C+m[:,None]*32+n[None,:],c)

@triton.jit
def loop(X,Y,N:tl.constexpr,ITER:tl.constexpr):
    i=tl.program_id(0)*128+tl.arange(0,128)
    x=tl.load(X+i,i<N,other=0)
    for j in range(ITER):
        x=x*1.0001+0.0001
    tl.store(Y+i,x,i<N)

@pytest.mark.parametrize('kind',['vector','reduction','matrix','loop'])
def test_metax_public_kernel_timeline(tmp_path,kind):
    if triton.runtime.driver.active.get_current_target().backend!='maca':
        pytest.skip('MetaX hardware required')
    from flagtree import profiler
    torch.manual_seed(19)
    x=torch.randn(1024,device='cuda');y=torch.empty_like(x)
    if kind=='vector':
        launch=lambda:vector[(8,)](x,y,1024)
        reference=x*2+1
    elif kind=='reduction':
        y=torch.empty((),device='cuda')
        launch=lambda:reduction[(1,)](x,y)
        reference=x.sum()
    elif kind=='matrix':
        a=torch.randn(32,32,device='cuda',dtype=torch.float16)
        b=torch.randn_like(a);y=torch.empty_like(a)
        launch=lambda:matrix[(1,)](a,b,y)
        reference=(a.float()@b.float()).half()
    else:
        launch=lambda:loop[(8,)](x,y,1024,32)
        reference=x.clone()
        for _ in range(32):reference=reference*1.0001+0.0001
    launch();torch.cuda.synchronize()
    torch.testing.assert_close(y,reference,rtol=.01,atol=.002)
    root=tmp_path/kind
    sid=profiler.start(str(root),detail='timeline',timeline_record_capacity=512)
    try:
        launch();launch();torch.cuda.synchronize()
    finally:
        profiler.finalize(sid)
    torch.testing.assert_close(y,reference,rtol=.01,atol=.002)
    files=list(root.glob('timeline/captures/*.events.json'))
    assert len(files)==2,files
    identities=[]
    for path in files:
        data=json.loads(path.read_text());identities.append(str(data['identity']))
        assert data['complete'] and data['events'] and data['sites']
        assert data['sources']
        for observer in data['observers']:
            assert observer['dropped_records']==0
            assert 'metax' in observer['kind'].lower() or 'maca' in observer['kind'].lower()
        for event in data['events']:
            if event.get('start_tick') is not None and event.get('end_tick') is not None:
                assert event['end_tick']>=event['start_tick']>0
    assert len(set(identities))==2
    assert list(root.rglob('*.perfetto-trace')) or list(root.rglob('*.pftrace')), 'Perfetto export missing'
