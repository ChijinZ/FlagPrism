#!/usr/bin/env python3
import os,sys,subprocess,json
from pathlib import Path
args=sys.argv[1:];o=Path(os.environ['STUDY_ASCEND_OUTPUT']);patch=Path(os.environ['SPARSE_PATCH_DIR'])
for a in args:
 p=Path(a)
 if p.is_file() and p.suffix=='.ll' and ('mix_aic' in p.name or 'mix_aiv' in p.name):
  actor='aic' if 'mix_aic' in p.name else 'aiv';(o/(p.name+'.original')).write_bytes(p.read_bytes());p.write_bytes((patch/f'instrumented-{actor}.ll').read_bytes());(o/(p.name+'.instrumented')).write_bytes(p.read_bytes())
(o/'actual-argv.jsonl').open('a').write(json.dumps(args)+'\n');raise SystemExit(subprocess.run(['/usr/local/Ascend/cann-9.0.0/bin/bisheng',*args]).returncode)
