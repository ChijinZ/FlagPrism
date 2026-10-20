import argparse,json,subprocess,sys
from pathlib import Path
from flagtree.profiler._deadline import _stop_worker
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);s=Path(__file__).parent;steps=[]
for name,args,timeout in [('fixtures',['-I','-m','pytest','-q',str(s/'test_ascend_state_writer_partition.py')],35),('fixtures-O',['-I','-O','-m','pytest','-q',str(s/'test_ascend_state_writer_partition.py')],35),('actual-profile',['-I',str(s/'actual.py'),'--output',str(a.output/'actual-profile')],150)]:
 cmd=[sys.executable,*args]
 with (a.output/(name+'.stdout')).open('xb') as so,(a.output/(name+'.stderr')).open('xb') as se:
  child=subprocess.Popen(cmd,stdout=so,stderr=se,start_new_session=True)
  try:child.wait(timeout=timeout)
  except BaseException:_stop_worker(child);raise
 steps.append(dict(name=name,argv=cmd,returncode=child.returncode));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if child.returncode:raise RuntimeError('Owned Ascend State CPU step failed: '+name)
(a.output/'result.json').write_text(json.dumps(dict(status='Ascend_profile_State_CPU_checks',steps=steps,SDK_recompiled=False,device_executed=False,application_replayed=False),indent=2))
