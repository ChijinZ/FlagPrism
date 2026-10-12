#!/usr/bin/env python3
"""Run the shared operator request through the research-only SDK timer adapter."""
import argparse,hashlib,json,os,runpy,sys
from pathlib import Path
p=argparse.ArgumentParser(add_help=False);p.add_argument('--leader-records',action='store_true');p.add_argument('--adapter-output',type=Path,required=True);p.add_argument('--shim',type=Path,required=True);p.add_argument('--source',type=Path,default=Path(__file__).with_name('operator_regions.py'));a,rest=p.parse_known_args()
os.environ['TRITON_CACHE_DIR']=str(a.adapter_output/'cache');from gcu_global_timer_adapter import install
install(a.adapter_output,a.shim,a.leader_records);sys.argv=[str(a.source),*rest]
try:runpy.run_path(str(a.source),run_name='__main__')
finally:
 if '--output' in rest:
  f=Path(rest[rest.index('--output')+1])/'result.json'
  if f.exists():
   r=json.loads(f.read_text());r.update(counter_implementation='SDK read-only tops::global_timer equivalent inline helper',prototype=True,recording_actor='work-item 0' if a.leader_records else 'thread0 GM writer; pre-guard local staging scope not fully established',leader_record_staging=a.leader_records,unit='SDK_global_timer_ticks',clock_domain='actor-local SDK global timer; cross-actor origin unverified',frequency_status='unverified',sdk_shim_sha256=hashlib.sha256(a.shim.read_bytes()).hexdigest(),adapter_artifacts=str(a.adapter_output));f.write_text(json.dumps(r,indent=2)+'\n')
