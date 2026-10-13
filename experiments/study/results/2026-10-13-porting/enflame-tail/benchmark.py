import json,subprocess,os,random
from pathlib import Path
root=Path(__file__).parent
hyp={'case':'NVIDIA native-selected Softmax127x769 ROWS1,w4 → exact GCU P; guided Rw1 with w2 alternative','prediction':'Holding grid127 and rows1fixed, one work-item per row removes cooperative partialexchange and avoids uneven769-column split; native duration and compiledbarriers/partialexchange decrease. Two work-items remain control for attributing speedup, not barrier-onlycause.','controls':['canonicalbytes','FP32 output and full CPUref','three independentprocesspairedbatches90calls/version','all source math identical','closed research instrumentation','no configuration substitution in P'],'limitations':['similar program organization only, vectorlowering differs','N is searched best under fixedbudget, not globaloptimal','source timing projections not enginebusy']}
(root/'hypothesis-before.json').write_text(json.dumps(hyp,indent=2));state=[]
for b in range(3):
 order=[4,1,2];random.Random(20261013+b).shuffle(order)
 for w in order:
  d=root/'native'/f'b{b}-w{w}'
  cmd=['python3',str(root/'run_case.py'),'--backend','enflame','--operator','softmax','--shape','127x769','--rows','1','--num-warps',str(w),'--stages','1','--phase','native','--profile-launches','30','--input-dir','/workspace/chijin-study-canonical-inputs-r007','--output',str(d)]
  with (root/f'b{b}-w{w}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  state.append({'batch':b,'w':w,'returncode':r.returncode,'command':cmd});(root/'execution.json').write_text(json.dumps(state,indent=2));print(b,w,r.returncode,flush=True)
  if r.returncode:raise RuntimeError('Case failed; inspect retained logs before continue')
(root/'native.done').write_text('0')
