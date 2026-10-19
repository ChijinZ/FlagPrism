import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);source=Path('/workspace/chijin-timeline-r061-nvidia/budget-install-input-v1/source');env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0',CUDA_VISIBLE_DEVICES='0',TRITON_CACHE_DIR=str(a.output/'cache'),TMPDIR=str(a.output/'tmp'));(a.output/'tmp').mkdir();env.pop('PYTHONPATH',None);steps=[]
def run(name,cmd):
 with (a.output/(name+'.log')).open('xb') as log:
  c=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT);f=Path('/proc/'+str(c.pid)+'/stat').read_text().rsplit(')',1)[1].split();row=dict(name=name,argv=cmd,pid=c.pid,startticks=int(f[19]));steps.append(row);(a.output/'steps.json').write_text(json.dumps(steps));row['returncode']=c.wait(timeout=180);(a.output/'steps.json').write_text(json.dumps(steps))
 if row['returncode']:raise RuntimeError(name+' failed')
run('real-async',[sys.executable,'-I',str(source/'tests/timeline/p01_nvidia_late_pipeline.py'),'--kernel-module',str(source/'tests/timeline/p01_nvidia_dynamic_pipeline.py'),'--output',str(a.output/'device')])
run('native-present',[sys.executable,'-I',str(source/'tests/timeline/p01_nvidia_native_boundaries.py'),'--timeline',str(a.output/'device/profile/timeline'),'--output',str(a.output/'boundaries')])
result=json.loads((a.output/'device/result.json').read_text());result['actual_boundary_result']=str(a.output/'boundaries/result.json');result['actual_boundary_result_sha256']=hashlib.sha256((a.output/'boundaries/result.json').read_bytes()).hexdigest();result['schedule_preservation_qualified']=False
# Preserve exact new isolated cache paths for the already recorded math hashes;
# do not rebuild or replay to recover the ordinary object.
math_hashes={r['hash'] for r in result['math']};cache_objects=[]
for path in (a.output/'cache').rglob('*.json'):
 try:metadata=json.loads(path.read_text())
 except (ValueError,UnicodeError):continue
 if not isinstance(metadata,dict) or metadata.get('hash') not in math_hashes:continue
 files={str(p.relative_to(a.output)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in path.parent.iterdir() if p.is_file()}
 cache_objects.append(dict(binary_hash=metadata['hash'],metadata_file=str(path),files=files))
(a.output/'cache-object-index.json').write_text(json.dumps(cache_objects,indent=2));result['cache_object_index']=str(a.output/'cache-object-index.json')
(a.output/'result.json').write_text(json.dumps(result,indent=2))
