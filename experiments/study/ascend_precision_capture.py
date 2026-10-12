#!/usr/bin/env python3
"""Serial device4 hardware PMU captures with every selected invocation retained."""
import argparse,os,subprocess,json,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace/flagprism-study-closure-20261013'));p.add_argument('--variant',choices=['v2','narrow','shared','dependent','branch','branch-v2'],required=True);a=p.parse_args();os.chdir(a.workspace)
for scope in (['body','output'] if a.variant in ['dependent','branch','branch-v2'] else ['empty','body','output']):
 tag=f'precision-{scope}-{a.variant}-pmu'
 app=f'python ascend_precision_replay.py --operator softmax --binary precision-{scope}-{a.variant}/kernel.o --input-dir inputs --output {tag}-run --samples 1 --instrumented --completion'
 cmd=['msprof','op','--application='+app,'--output='+tag,'--aic-metrics=KernelScale,ArithmeticUtilization','--replay-mode=application','--kernel-name=rows','--launch-count=1','--launch-skip-before-match=0','--warm-up=0']
 with open(tag+'.log','xb') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=160)
 Path(tag+'-command.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'time':time.time(),'selection':'first rows invocation0 in each replay; all0..3 retained. Match rawDeviceProf timestamps to actual replay, then block IDs; do not assume replayordinal.'},indent=2)+'\n')
 print(json.dumps({'scope':scope,'rc':r.returncode,'tag':tag}),flush=True)
