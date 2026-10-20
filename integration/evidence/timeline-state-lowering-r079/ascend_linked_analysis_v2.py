"""Target-independent inspection of exact linked inputs, never vendor final IR."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
previous=Path('/tmp/chijin-timeline-r079-ascend/runs/linked-analysis-v1/output');d=json.loads((previous/'result.json').read_bytes());src=previous/'linked.bc'
entry,=[x for x in d['files'] if x['path']==str(src)]
if hashlib.sha256(src.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Bound original linked input changed')
text=a.output/'linked-source.ll';neutral=a.output/'analysis-input.ll';folded=a.output/'analysis.ll';steps=[]
commands=[['/usr/bin/llvm-dis-15',str(src),'-o',str(text)],['/usr/bin/opt-15','-internalize-public-api-list=q03','-passes=internalize,globaldce,always-inline,sroa,mem2reg,early-cse,instcombine,simplifycfg,globaldce',str(neutral),'-S','-o',str(folded)]]
for i,cmd in enumerate(commands):
 if i==1:
  raw=text.read_text();marker='target triple = "hiipu64-hisilicon-cce"\n'
  if raw.count(marker)!=1:raise ValueError('Unexpected actual triple')
  neutral.write_text(raw.replace(marker,''))
 with (a.output/(str(i)+'.stdout')).open('xb') as out,(a.output/(str(i)+'.stderr')).open('xb') as err:
  x=subprocess.run(cmd,stdout=out,stderr=err,timeout=30)
 steps.append(dict(argv=cmd,exit=x.returncode,tool_sha256=hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest()));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if x.returncode:break
files=[]
for f in [text,neutral,folded]:
 if f.exists():
  if f.stat().st_size>32*1024*1024:raise ValueError('Bounded analysis view')
  files.append(dict(path=str(f),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(a.output/'result.json').write_text(json.dumps(dict(status='target_independent_linked_input_inspection',steps=steps,files=files,original_binary_sha256=d['original_binary_sha256'],original_linked_input_sha256=entry['sha256'],removed_only_target_triple=True,data_layout_preserved=True,vendor_final_IR=False,target_codegen_executed=False,device_executed=False,application_replayed=False,state_writer_qualified=False),indent=2))
if any(x['exit'] for x in steps):raise RuntimeError('Retain standard LLVM analysis failure')
