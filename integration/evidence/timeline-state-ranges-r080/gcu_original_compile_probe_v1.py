"""CPU-only reproduction of one ordinary GCU final compiler input."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
r=Path('/tmp/chijin-timeline-r078-gcu/runs/state-inventory-v1/output');d=json.loads((r/'inventory.json').read_bytes());row=next(x for x in d['rows'] if x['id']=='q03-s0-c0' and x['variant']=='primary');objects={x['kind']:x for x in row['artifacts']}
math=Path(row['math_file'])
if sha(math)!=row['math_sha256']:raise ValueError('Original ordinary report changed')
for entry in objects.values():
 if sha(r/entry['retained_file'])!=entry['sha256']:raise ValueError('Original compiler artifact changed')
source=r/objects['llir']['retained_file'];original=(r/objects['fatbin']['retained_file']).read_bytes();tool=Path('/opt/triton_gcu/bin/gcu-compiler-compile');builtins=Path('/opt/triton_gcu/lib/kurama/gcu300_tops_builtins.bc')
if sha(tool)!='1b7e13a7a2888e126a1022de6a129eec1404da5e0f0f0a0c2e702de784855e40':raise ValueError('SDK compiler changed')
if sha(builtins)!='fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a':raise ValueError('SDK builtin library changed')
output=a.output/'kernel.fatbin';command=[str(tool),'--device-only','--is-triton-backend','--arch=gcu300','--toolkit-path=/opt/triton_gcu','--output='+str(output)]
(a.output/'command.json').write_text(json.dumps(dict(argv=command,stdin_file=str(source),stdin_sha256=sha(source),tool_sha256=sha(tool),toolkit_builtin_file=str(builtins),toolkit_builtin_sha256=sha(builtins),original=row,device_executed=False),indent=2))
spec=importlib.util.spec_from_file_location('owned_probe_deadline','/workspace/chijin-r15-python-alignment/venv/lib/python3.12/site-packages/flagtree/profiler/_deadline.py');deadline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=deadline;spec.loader.exec_module(deadline)
start=time.monotonic()
with (a.output/'sdk.stdout').open('xb') as out,(a.output/'sdk.stderr').open('xb') as err:
 child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=out,stderr=err,env=dict(os.environ),start_new_session=True)
 try:child.communicate(input=source.read_bytes(),timeout=60)
 except BaseException:
  deadline._stop_worker(child);raise
result=dict(status='ordinary_GCU_final_input_reproduction',exit=child.returncode,elapsed_s=time.monotonic()-start,source_sha256=sha(source),original_fatbin_sha256=hashlib.sha256(original).hexdigest(),device_executed=False,mathematical_application_replayed=False,product_runtime_changed=False,state_writer_qualified=False)
if output.exists():
 raw=output.read_bytes();result.update(produced_fatbin_sha256=hashlib.sha256(raw).hexdigest(),produced_bytes=len(raw),whole_binary_identical=raw==original)
(a.output/'result.json').write_text(json.dumps(result,indent=2))
if child.returncode:raise RuntimeError('Keep original SDK reproduction failure')
