"""CPU-only getter lowering probe on an existing retained actor module."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
b=Path('/tmp/chijin-timeline-r055-qualification-ascend-v2/runs/profile-first-v1/q01-s0-c0-cold/capture/timeline');idx=json.loads((b/'index.json').read_text());capture_file=b/idx['captures'][0]['capture_file'];cap=json.loads(capture_file.read_text());handoff=cap['metadata']['compiler_metadata']['flagprism_ascend_handoff'];art=next(x for x in handoff['artifacts'] if x['metadata']['runtime_actor_binding']['actor_kind']=='AIV');job=next(j for j in handoff['codegen_jobs'] if j.get('actor_kind')=='AIV');original=art['adapted']['llir'];count=original.count('llvm.hivm.GET.SUBBLOCKID')
if count<2:raise RuntimeError('Actual actor getter call/declaration not identifiable')
source=a.output/'probe.ll';source.write_text(original.replace('llvm.hivm.GET.SUBBLOCKID','llvm.hivm.GET.SUBBLOCKDIM'));assembly=a.output/'probe.o';cmd=list(job['executed_command']);cmd[1]=str(source);cmd[cmd.index('-o')+1]=str(assembly)
receipt=dict(scope='CPU codegen only; modified actor is not executed',source_capture=str(capture_file),capture_sha256=hashlib.sha256(capture_file.read_bytes()).hexdigest(),original_adapted_sha256=hashlib.sha256(original.encode()).hexdigest(),probe_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),replacements=count,argv=cmd,original_object=job['object'])
with (a.output/'stdout.log').open('wb') as out,(a.output/'stderr.log').open('wb') as err:r=subprocess.run(cmd,stdout=out,stderr=err,timeout=90)
receipt['returncode']=r.returncode
if assembly.exists():
 receipt.update(object_sha256=hashlib.sha256(assembly.read_bytes()).hexdigest(),object_bytes=assembly.stat().st_size)
(a.output/'result.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if r.returncode:raise SystemExit(r.returncode)
