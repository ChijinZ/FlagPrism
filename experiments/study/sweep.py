#!/usr/bin/env python3
"""Sequential fresh processes, bounded timeout, durable per-case logs; stop on device faults."""
import argparse,json,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--backend',required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--device',type=int,default=0)
p.add_argument('--pilot',action='store_true')
p.add_argument('--phases',nargs='+',default=['baseline','native'])
p.add_argument('--timeout',type=int,default=240)
a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
operators=['gemm','gemm_bias_gelu','softmax','layernorm','reduce_sum','transpose']
plan=[]
for op in operators:
 if op.startswith('gemm'): shapes=['32x32x32'] if a.pilot else ['128x128x128','512x512x512','257x193x320']
 elif op=='transpose': shapes=['32x64'] if a.pilot else ['256x256','1024x1024','513x257']
 else: shapes=['4x64'] if a.pilot else ['32x256','256x1024','127x769']
 for shape in shapes:
  for variant in ([0] if a.pilot else [0,1]):
   for phase in a.phases: plan.append((op,shape,variant,phase))
(a.output/'plan.json').write_text(json.dumps({'backend':a.backend,'device':a.device,'cases':plan},indent=2))
for op,shape,variant,phase in plan:
 name=f'{op}-{shape}-v{variant}-{phase}'; out=a.output/name
 if out.exists():
  print('EXISTS, no overwrite:',name,flush=True); continue
 cmd=[sys.executable,str(Path(__file__).with_name('run_case.py')),'--backend',a.backend,'--operator',op,'--shape',shape,'--variant',str(variant),'--device',str(a.device),'--phase',phase,'--output',str(out)]
 print(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'RUN',name,flush=True)
 with (a.output/(name+'.log')).open('w') as log:
  try: r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout); code=r.returncode
  except subprocess.TimeoutExpired: code=124
 text=(a.output/(name+'.log')).read_text(errors='replace')
 with (a.output/'execution.jsonl').open('a') as f:
  f.write(json.dumps({'name':name,'returncode':code,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})+'\n')
 print('DONE',name,code,flush=True)
 if code==124 or any(s in text.lower() for s in ['illegal memory','device-side assert','device error','aicore exception','driver error','segmentation fault']):
  print('STOP: timed out or device fault; inspect before rerun',flush=True); sys.exit(2)
print('SWEEP COMPLETE',flush=True)
