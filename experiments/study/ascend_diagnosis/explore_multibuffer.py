#!/usr/bin/env python3
"""Exploratory causal screening; candidates are not frozen NVIDIA ports."""
import argparse,json,subprocess,time,hashlib,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();w=a.workspace.resolve();code=w/'code';out=w/'captures';out.mkdir(exist_ok=True)
plan={'scope':'exploratory, NVIDIA-tuned N/P not yet frozen','device':4,'hypothesis':'For long-K GEMM, stages=2 enables different L1 buffering/synchronization, reducing load/compute serialization; stages=1 should incur greater cost per K iteration. Fused versus unfused distinguishes Cube-loop cost from AIC/AIV epilogue cost.','prediction_before_measurement':'Stage-2 compiler emits separate alternating L1 buffers/event IDs and lower long-K kernel latency; if buffers unchanged or benefit absent, reject. Increasing BK alone is a competing explanation (fewer iterations).','alternatives':['Increasing BK lowers loop/ND2NZ/event issue overhead independent of overlapping.','Fused AIV epilogue/workspace handoff dominates, so Cube buffering changes little.','Hardware bandwidth or compiler resource pressure removes benefit.'],'comparison_policy':'same source math/shape/input seed; stage changes and BK changes isolated; no instrumentation; exploratory serial measurements','code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code.glob('*.py')}}
(w/'prediction.json').write_text(json.dumps(plan,indent=2)+'\n')
cases=[]
for shape in ['512x512x512','512x512x4096']:
 for operator in ['gemm','gemm_bias_gelu']:
  for bk in ([64] if shape.endswith('x512') else [64,128]):
   for stages in [1,2]:cases.append((operator,shape,bk,stages))
results=[]
for index,(op,shape,bk,stages) in enumerate(cases):
 tag=f'{index:02d}-{op}-{shape}-b64-k{bk}-s{stages}';cmd=['python',str(code/'run_case.py'),'--backend','cann','--operator',op,'--shape',shape,'--device','4','--phase','baseline','--tile','64','--k-tile',str(bk),'--stages',str(stages),'--repeats','9','--batch','50','--output',str(out/tag)]
 receipt={'tag':tag,'command':cmd,'started_unix':time.time(),'timeout_s':180}
 with (w/(tag+'.log')).open('xb') as f:
  try:q=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180);receipt['returncode']=q.returncode
  except subprocess.TimeoutExpired:receipt.update(returncode=124,error='timeout')
 receipt['ended_unix']=time.time();resultpath=out/tag/'result.json'
 if resultpath.exists():
  r=json.load(open(resultpath));receipt.update(status=r.get('status'),statistics=r.get('statistics'),validation=r.get('validation'),config=r.get('requested_compile_config'),asm=r.get('asm'))
 results.append(receipt);(w/'screen-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({'tag':tag,'status':receipt.get('status'),'rc':receipt['returncode'],'statistics':receipt.get('statistics')}),flush=True)
(w/'screen-complete.json').write_text(json.dumps({'completed':True,'cases':len(results),'passed':sum(r.get('status')=='passed' for r in results)},indent=2)+'\n')
