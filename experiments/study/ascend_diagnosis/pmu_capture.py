#!/usr/bin/env python3
"""Capture shipped PMU counters; validate output rather than trusting exit status."""
import argparse,json,subprocess,time,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--tag',default='pmu-v2');p.add_argument('--canonical',type=Path);p.add_argument('--extended',action='store_true');p.add_argument('--configs',type=Path);a=p.parse_args();os.chdir(a.workspace)
cases=json.load(open(a.configs)) if a.configs else [{'name':f'k{bk}-s{stages}'+('-unroll2' if kind=='unroll' else ''),'BM':64,'BN':64,'BK':bk,'num_stages':stages,'kernel':kind} for bk,stages,kind in ([(64,2,'original'),(128,2,'original'),(256,2,'original'),(512,2,'original'),(64,2,'unroll')] if a.extended else [(64,1,'original'),(64,2,'original'),(128,2,'original')])]
for cfg in cases:
 bk,stages,kind=cfg['BK'],cfg['num_stages'],cfg['kernel']
 tag=f'{a.tag}-'+cfg['name'];app=f'python single_kernel.py --bk={bk} --stages={stages} --tile-m={cfg["BM"]} --tile-n={cfg["BN"]} --operator=gemm_bias_gelu --output={tag}-app --kernel-kind={kind}'+(f' --input-dir={a.canonical}' if a.canonical else '');cmd=['msprof','op','--application='+app,'--output='+tag,'--aic-metrics=ArithmeticUtilization,PipeUtilization,MemoryL0,Memory,L2Cache,ResourceConflictRatio','--kernel-name=matmul','--launch-count=1','--warm-up=10'];receipt={'command':cmd,'config':cfg,'started_unix':time.time(),'timeout_s':180}
 with Path(tag+'.log').open('xb') as f:
  try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180);receipt['returncode']=r.returncode
  except subprocess.TimeoutExpired:receipt['returncode']=124
 receipt.update(ended_unix=time.time(),csv_files=[str(p) for p in Path(tag).rglob('*.csv')]);receipt['status']='collected' if receipt['returncode']==0 and receipt['csv_files'] else 'failed_or_no_data';Path(tag+'-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
