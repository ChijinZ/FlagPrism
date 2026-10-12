#!/usr/bin/env python3
"""Keep every private PMU application replay and every invocation, including warmups."""
import hashlib,json,os,sys,time
from pathlib import Path
source=Path(__file__).with_name('ascend_llvm_regions.py');original=source.read_text()
needle="if i>=3:r['samples'].append(rec)";assert original.count(needle)==1
adapted=original.replace(needle,"if i>=0:r['samples'].append(rec)")
idx=sys.argv.index('--output')+1;sys.argv[idx]+='-'+str(os.getpid())+'-'+str(time.time_ns());out=Path(sys.argv[idx])
try:exec(compile(adapted,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
except SystemExit as e:
 if (out/'result.json').exists():
  p=out/'result.json';r=json.loads(p.read_text());r['precision_replay']={'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'source_adaptation':'retain all invocations0..3 including source warmups; math, clock and binary unchanged','native_selection':'msprof kernel-name rows, launch-count1, skip0 selects first rows invocation0 in each application replay','retained_warmups':True};p.write_text(json.dumps(r,indent=2)+'\n')
 raise
