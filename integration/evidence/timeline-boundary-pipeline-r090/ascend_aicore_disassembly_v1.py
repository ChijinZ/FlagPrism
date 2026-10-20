"""Read-only installed SDK disassembler options on retained actual ELF."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
tool=Path('/usr/local/Ascend/cann-9.0.0/tools/bisheng_compiler/bin/llvm-objdump');binary=Path('/tmp/chijin-timeline-r060-ascend/runs/participation-device-v1/output/device/vector/capture/timeline/machine/59c6e82cbc4eb4c265ed899ba6ec23e93c28a65d455351b1dae512d3630a6fad/loaded.elf')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if sha(binary)!='73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d':raise ValueError('Original ELF changed')
steps=[]
for name,flags in [('aicore',['--disassemble-aicore']),('aicore-d',['-d','--disassemble-aicore'])]:
 cmd=[str(tool),*flags,'--line-numbers',str(binary)];row=dict(name=name,argv=cmd);steps.append(row)
 with (a.output/(name+'.stdout')).open('wb') as out,(a.output/(name+'.stderr')).open('wb') as err:
  child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err);fields=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split();row.update(pid=child.pid,startticks=int(fields[19]))
  try:row['returncode']=child.wait(timeout=20)
  except subprocess.TimeoutExpired:
   child.kill();child.wait(timeout=10);row.update(timed_out=True,returncode=child.returncode)
 row.update(stdout_sha256=sha(a.output/(name+'.stdout')),stderr_sha256=sha(a.output/(name+'.stderr')));text=(a.output/(name+'.stdout')).read_text();row['unavailable_lines']=text.count('<not available>');row['stdout_bytes']=len(text.encode());(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
(a.output/'result.json').write_text(json.dumps(dict(status='retained_ELF_disassembly_options',tool_sha256=sha(tool),binary_sha256=sha(binary),steps=steps,device_executed=False,SDK_recompiled=False,application_replayed=False),indent=2))
