import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
source=Path('/workspace/chijin-timeline-r061-nvidia/compute-install-input-v1/source');env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0',CUDA_VISIBLE_DEVICES='0',TRITON_CACHE_DIR=str(a.output/'cache'),TMPDIR=str(a.output/'tmp'));(a.output/'tmp').mkdir();env.pop('PYTHONPATH',None);steps=[]
def run(name,cmd):
 with (a.output/(name+'.log')).open('xb') as log:
  c=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();row=dict(name=name,argv=cmd,pid=c.pid,startticks=int(f[19]));steps.append(row);(a.output/'steps.json').write_text(json.dumps(steps));row['returncode']=c.wait(timeout=180);(a.output/'steps.json').write_text(json.dumps(steps))
 if row['returncode']:raise RuntimeError(name+' failed')
run('C2',[sys.executable,'-I',str(source/'tests/timeline/p01_controlled_workloads.py'),'--backend','nvidia','--device','0','--case','C2','--variant','32','--repetitions','2','--ordinary-repetitions','1','--output',str(a.output/'device')])
for rep in [0,1]:run('native-boundaries-'+str(rep),[sys.executable,'-I',str(source/'tests/timeline/p01_nvidia_native_boundaries.py'),'--timeline',str(a.output/'device'/('32-'+str(rep))/'capture/timeline'),'--output',str(a.output/('boundaries-'+str(rep)))])
result=json.loads((a.output/'device/result.json').read_text());profiles=[r for r in result['rows'] if r['repetition']>=0]
if len(profiles)!=2:raise RuntimeError('Wrong C2 profile count')
(a.output/'result.json').write_text(json.dumps(dict(status='affected_C2_real_math_and_native_async_families_passed_not_schedule_certificate',math=result,boundaries=[json.loads((a.output/('boundaries-'+str(rep))/'result.json').read_text()) for rep in [0,1]],performance_measured=False),indent=2))
