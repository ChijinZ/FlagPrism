#!/usr/bin/env python3
"""Bounded real-operator capture sweep. Failed cases remain failed, never overwritten."""
import argparse,json,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--backend',required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',type=int,default=0);p.add_argument('--timeout',type=int,default=240);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
for op,shape,configurations in [('gemm_bias_gelu','128x128x128',[('t16',['--tile','16']),('t64',['--tile','64'])]),('softmax','32x256',[('r1',['--rows','1']),('r2',['--rows','2'])])]:
 for config,options in configurations:
  for mode in ['none','nested','body','output']:
   name=f'{op}-{config}-{mode}';cmd=[sys.executable,str(Path(__file__).with_name('operator_regions.py')),'--backend',a.backend,'--operator',op,'--shape',shape,'--capture',mode,'--device',str(a.device),'--input-dir',str(a.input_dir),'--output',str(a.output/name),*options]
   print('RUN',name,flush=True)
   with (a.output/(name+'.log')).open('w') as log:
    try:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout);rc=r.returncode
    except subprocess.TimeoutExpired:rc=124
   with (a.output/'execution.jsonl').open('a') as f:f.write(json.dumps({'case':name,'returncode':rc,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})+'\n')
   print('DONE',name,rc,flush=True)
   if rc:raise SystemExit(rc)
(a.output/'complete.json').write_text(json.dumps({'backend':a.backend,'completed_cases':16})+'\n')
