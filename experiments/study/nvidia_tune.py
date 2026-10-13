#!/usr/bin/env python3
"""NVIDIA-only source-configuration search; execute in the remote study Docker.

CPU references, device graph intervals and every failed configuration are saved.
Graph timing estimates resident-kernel throughput; native individual-launch
FlagPrism timing is a separate required collection, never inferred from this.
"""
import argparse, hashlib, itertools, json, os, statistics, time, traceback
from pathlib import Path

os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD', '0')
p=argparse.ArgumentParser()
p.add_argument('--operator',required=True,choices=['gemm','gemm_bias_gelu','softmax','layernorm','reduce_sum','transpose'])
p.add_argument('--shape',required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--device',type=int,default=0)
p.add_argument('--input-dir',type=Path)
p.add_argument('--graph-replays',type=int,default=100)
p.add_argument('--search-batches',type=int,default=5)
p.add_argument('--validation-batches',type=int,default=15)
p.add_argument('--quick',action='store_true')
a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
import torch, triton
import kernels
torch.cuda.set_device(a.device); device=f'cuda:{a.device}'
shape=tuple(map(int,a.shape.split('x'))); torch.manual_seed(1729)
inputs=[]
def rand(s,dtype=torch.float32):
    if a.input_dir:
        family='matmul' if a.operator.startswith('gemm') else 'transpose' if a.operator=='transpose' else 'rows'
        path=a.input_dir/f'{family}-{a.shape}-{len(inputs)}.bin'
        x=torch.frombuffer(bytearray(path.read_bytes()),dtype=dtype).reshape(s).clone()
    else:x=torch.randn(s,dtype=dtype,device='cpu')*.1
    raw=x.contiguous().numpy().tobytes(); inputs.append({'shape':list(s),'dtype':str(dtype),'sha256':hashlib.sha256(raw).hexdigest()})
    return x
if a.operator.startswith('gemm'):
    M,N,K=shape; ca,cb,cc=rand((M,K),torch.float16),rand((K,N),torch.float16),rand((N,))
    ref=ca.float()@cb.float()
    if a.operator!='gemm': ref=torch.nn.functional.gelu(ref+cc,approximate='tanh')
    A,B,C=ca.to(device),cb.to(device),cc.to(device); Y=torch.empty((M,N),device=device,dtype=torch.float32)
    tol={'atol':.002,'rtol':.02}
    tiles=[(16,16,16),(32,32,32),(64,64,32),(64,128,32),(128,64,32),(128,128,32),(64,64,64),(128,128,64),(64,64,128),(128,64,128),(64,128,128),(128,128,128)]
    configs=[dict(BM=m,BN=n,BK=k,num_warps=w,num_stages=s) for (m,n,k),w,s in itertools.product(tiles,[4,8],[1,2,3,4])]
    configs += [dict(BM=m,BN=n,BK=256,num_warps=w,num_stages=s) for (m,n),w,s in itertools.product([(64,64),(128,64),(64,128)],[4,8],[1,2])]
    def launch(c):return kernels.matmul[(triton.cdiv(M,c['BM']),triton.cdiv(N,c['BN']))](A,B,C,Y,M,N,K,c['BM'],c['BN'],c['BK'],a.operator!='gemm',num_warps=c['num_warps'],num_stages=c['num_stages'])
elif a.operator=='transpose':
    M,N=shape; cx=rand(shape); ref=cx.T.contiguous(); X=cx.to(device);Y=torch.empty((N,M),device=device);tol={'atol':0.,'rtol':0.}
    configs=[dict(BM=m,BN=n,num_warps=w,num_stages=1) for m,n,w in itertools.product([16,32,64],[16,32,64],[1,2,4,8])]
    def launch(c):return kernels.transpose[(triton.cdiv(M,c['BM']),triton.cdiv(N,c['BN']))](X,Y,M,N,c['BM'],c['BN'],num_warps=c['num_warps'],num_stages=1)
else:
    R,N=shape;cx,cw,cb=rand(shape),rand((N,)),rand((N,)); X,W,B=cx.to(device),cw.to(device),cb.to(device)
    ref=torch.softmax(cx,-1) if a.operator=='softmax' else torch.nn.functional.layer_norm(cx,(N,),cw,cb,1e-5) if a.operator=='layernorm' else cx.sum(-1)
    Y=torch.empty(ref.shape,device=device);tol={'atol':.0005,'rtol':.002}
    configs=[dict(ROWS=r,BLOCK=triton.next_power_of_2(N),num_warps=w,num_stages=1) for r,w in itertools.product([1,2,4,8,16],[1,2,4,8])]
    def launch(c):return kernels.rows[(triton.cdiv(R,c['ROWS']),)](X,W,B,Y,R,N,c['BLOCK'],c['ROWS'],a.operator,num_warps=c['num_warps'],num_stages=1)
if a.quick: configs=configs[:4]
state={'schema_version':1,'operator':a.operator,'shape':shape,'inputs':inputs,'seed':1729,'tolerance':tol,'timing':'CUDA graph replay stream interval divided by resident launches; not native device task duration','graph_replays':a.graph_replays,'torch':torch.__version__,'triton':triton.__version__,'triton_file':triton.__file__,'device':torch.cuda.get_device_name(a.device),'capability':torch.cuda.get_device_capability(a.device),'attempts':[]}
state['source_sha256']={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),Path(kernels.__file__)]}
state['search_budget']={'configurations':len(configs),'batches_per_configuration':a.search_batches,'graph_replays_per_batch':a.graph_replays,'warps':[4,8] if a.operator.startswith('gemm') else [1,2,4,8]}
if a.operator.startswith('gemm'):
    state['search_exclusions']=[{'parameter':'BK=512 at BM=BN=64 or larger','reason':'Conventional full-operand shared staging estimate131072bytes exceeds device cuDeviceGetAttribute97 opt-in limit101376bytes; excluded from finite search budget. Compiler subdivision feasibility was not tested.'}]
def save(): (a.output/'result.json').write_text(json.dumps(state,indent=2,default=str)+'\n')
save()
def measure(c,batches):
    compiled=launch(c);torch.cuda.synchronize()
    actual=Y.cpu(); valid=bool(torch.allclose(actual,ref,**tol))
    if not valid: raise RuntimeError('CPU reference failed; max abs '+str((actual-ref).abs().max().item()))
    for _ in range(10):launch(c)
    torch.cuda.synchronize()
    graph=torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):
        for _ in range(a.graph_replays):launch(c)
    for _ in range(3):graph.replay()
    torch.cuda.synchronize();samples=[]
    for _ in range(batches):
        start,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        start.record();graph.replay();end.record();end.synchronize()
        samples.append(start.elapsed_time(end)*1000/a.graph_replays)
    if not torch.allclose(Y.cpu(),ref,**tol):raise RuntimeError('Post-graph correctness failed')
    hashes={k:hashlib.sha256(v.encode() if isinstance(v,str) else v).hexdigest() for k,v in compiled.asm.items() if isinstance(v,(str,bytes))}
    return {'passed':True,'max_abs_error':(actual-ref).abs().max().item(),'samples_us':samples,'median_us':statistics.median(samples),'compiled_metadata':repr(compiled.metadata),'asm_sha256':hashes},compiled
for i,c in enumerate(configs):
    row={'index':i,'config':c,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    try:row.update(measure(c,a.search_batches)[0])
    except Exception:row.update(passed=False,error=traceback.format_exc())
    state['attempts'].append(row);save();print(json.dumps({'index':i,'config':c,'passed':row['passed'],'median_us':row.get('median_us')}),flush=True)
good=[r for r in state['attempts'] if r['passed']]
if not good:raise RuntimeError('No valid configurations')
winner=min(good,key=lambda r:r['median_us']);state['selection']={'criterion':'lowest median across fixed search batches','search_index':winner['index'],'config':winner['config']}
state['independent_remeasurement'],compiled=measure(winner['config'],a.validation_batches)
ir=a.output/'selected-asm';ir.mkdir()
for k,v in compiled.asm.items():
    if isinstance(v,(str,bytes)):(ir/k.replace('/','_')).write_bytes(v.encode() if isinstance(v,str) else v)
state['status']='passed';save()
print(json.dumps({'selected':winner['config'],'validation_median_us':state['independent_remeasurement']['median_us']}),flush=True)
