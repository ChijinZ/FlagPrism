"""Bind registered original GCU final LLVM inputs to whole fatbin bytes, CPU only."""
import argparse, hashlib, importlib.util, json, os, subprocess, sys, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def need(value,message):
 if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
root=Path('/tmp/chijin-timeline-r078-gcu/runs/state-inventory-v1/output');inventory=json.loads((root/'inventory.json').read_bytes());tool=Path('/opt/triton_gcu/bin/gcu-compiler-compile');library=Path('/opt/triton_gcu/lib/kurama/gcu300_tops_builtins.bc')
need(sha(tool)=='1b7e13a7a2888e126a1022de6a129eec1404da5e0f0f0a0c2e702de784855e40','Original SDK compiler differs');need(sha(library)=='fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a','Original builtin library differs')
spec=importlib.util.spec_from_file_location('owned_probe_deadline','/workspace/chijin-r15-python-alignment/venv/lib/python3.12/site-packages/flagtree/profiler/_deadline.py');deadline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=deadline;spec.loader.exec_module(deadline)
rows=[];objects={};start=time.monotonic()
for index,row in enumerate(inventory['rows']):
 need(sha(Path(row['math_file']))==row['math_sha256'],'Original mathematical report changed');artifacts={e['kind']:e for e in row['artifacts']}
 for entry in artifacts.values():need(sha(root/entry['retained_file'])==entry['sha256'],'Original compiler artifact changed')
 source=root/artifacts['llir']['retained_file'];original=root/artifacts['fatbin']['retained_file'];key=(sha(source),sha(original))
 if key in objects:
  result=dict(objects[key],reused=True)
 else:
  folder=a.output/('object-'+str(index));folder.mkdir();output=folder/'kernel.fatbin';command=[str(tool),'--device-only','--is-triton-backend','--arch=gcu300','--toolkit-path=/opt/triton_gcu','--output='+str(output)]
  with (folder/'sdk.stdout').open('xb') as stdout,(folder/'sdk.stderr').open('xb') as stderr:
   child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,env=dict(os.environ),start_new_session=True)
   try:child.communicate(input=source.read_bytes(),timeout=30)
   except BaseException:deadline._stop_worker(child);raise
  result=dict(exit=child.returncode,argv=command,source_path=str(source),source_sha256=key[0],original_fatbin_sha256=key[1],produced_fatbin_sha256=sha(output) if output.is_file() else None,whole_binary_identical=output.is_file() and output.read_bytes()==original.read_bytes(),reused=False)
  (folder/'result.json').write_text(json.dumps(result,indent=2));objects[key]=result
 rows.append(dict(id=row['id'],variant=row['variant'],math_file=row['math_file'],math_sha256=row['math_sha256'],compiled_hash=row['compiled_hash'],grid=row['grid'],codegen=result));(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
result=dict(status='registered_ordinary_GCU_whole_binary_binding',registered=len(inventory['rows']),checked=len(rows),distinct_objects=len(objects),bound=sum(x['codegen']['exit']==0 and x['codegen']['whole_binary_identical'] for x in rows),elapsed_s=time.monotonic()-start,tool_sha256=sha(tool),builtin_sha256=sha(library),device_executed=False,mathematical_application_replayed=False,state_writer_qualified=False)
(a.output/'result.json').write_text(json.dumps(result,indent=2));need(result['bound']==result['registered'],'Original fatbin whole bytes differ; keep failed rows')
