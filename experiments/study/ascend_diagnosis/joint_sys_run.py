#!/usr/bin/env python3
"""Bounded SDK single-metric application replay with per-actor native SYS packets."""
import argparse,subprocess,json,time,os,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--tag',default='joint-sys');a=p.parse_args();os.chdir(a.workspace)
for config in ['P32_K32','R_K32_K256']:
 tag=f'{a.tag}-{config}';app=f'python joint_sys_capture.py --workspace={a.workspace} --inputs={a.inputs} --config={config} --output={tag}-source';cmd=['msprof','op','--application='+app,'--output='+tag,'--aic-metrics=ArithmeticUtilization','--replay-mode=application','--kernel-name=matmul','--launch-count=1','--launch-skip-before-match=0','--warm-up=0'];receipt={'command':cmd,'started_unix':time.time(),'timeout_s':180,'configuration':config,'collection_policy':'single requested SDK metric to limit multipass; retain every actual app replay and packet, never assume one native replay'}
 with Path(tag+'.log').open('xb') as f:
  try:q=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180);receipt['returncode']=q.returncode
  except subprocess.TimeoutExpired:receipt['returncode']=124
 packets=list(Path(tag).glob('**/DeviceProf*.bin'));sources=list(Path(tag+'-source').glob('run-*/result.json'));receipt.update(ended_unix=time.time(),raw_packets=[str(p) for p in packets],source_results=[str(p) for p in sources],status='collected' if packets and sources and receipt['returncode']==0 else 'failed_or_no_data');Path(tag+'-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
