import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
source=Path('/tmp/chijin-timeline-r060-ascend/participation-install-input-v2/source');script=source/'tests/timeline/p01_ascend_participation.py';env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0',FLAGTREE_BACKEND='ascend',TRITON_ASCEND_COMPILER='/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile');env['PATH']='/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin:/usr/lib/llvm-15/bin:'+env['PATH'];env.pop('PYTHONPATH',None);env.pop('FLAGPRISM_ASCEND_LATE_PLUGIN',None)
for name in ['TRITON_CACHE_DIR','FLAGTREE_CACHE_DIR','TORCHINDUCTOR_CACHE_DIR','TMPDIR']:
 directory=a.output/('controlled-'+name.lower());directory.mkdir();env[name]=str(directory)
cmd=[sys.executable,'-I',str(script),'--output',str(a.output/'device')]
with (a.output/'device.log').open('xb') as log:
 child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env);f=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split();owner=dict(pid=child.pid,startticks=int(f[19]),argv=cmd,script_sha256=hashlib.sha256(script.read_bytes()).hexdigest());(a.output/'step.json').write_text(json.dumps(owner));owner['returncode']=child.wait(timeout=260);(a.output/'step.json').write_text(json.dumps(owner))
if owner['returncode']:raise RuntimeError('Device participant validation failed; retained device.log/progress/raw')
(a.output/'result.json').write_bytes((a.output/'device/result.json').read_bytes())
