"""Finite parent waits/reaps children inside Docker; no device imports."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent
def write(name,value):(R/name).write_text(json.dumps(value,indent=2)+'\n')
sys.path.insert(0,str(R/'usability_qualification'))
from owned_process import run
with (R/'controller-once').open('x') as marker:marker.write(str(os.getpid()))
write('controller-started.json',dict(pid=os.getpid(),pgid=os.getpgrp(),argv=sys.argv,started=time.time()))
rows=[]
for phase in ['baseline','profile']:
 command=[sys.executable,'-I',str(R/'usability_qualification/run_unseen_r11.py'),phase,'--backend','enflame','--freeze',str(R/'freeze.json'),'--booking',str(R/'booking.json'),'--output',str(R/'results')]
 result=run(command,R/('controller-'+phase),dict(os.environ),14400)
 rows.append(dict(phase=phase,**result));write('controller-progress.json',rows)
 if result.get('interrupted_signal') or (phase=='baseline' and not (R/'results/eligibility.json').is_file()):break
write('controller-terminal.json',dict(results=rows,returncode=0 if len(rows)==2 and all(r['returncode']==0 for r in rows) else 1,finished=time.time(),GPU_lease_released=True))
