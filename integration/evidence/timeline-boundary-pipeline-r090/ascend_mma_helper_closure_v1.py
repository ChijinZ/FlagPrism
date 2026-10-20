"""Read one actual linked SDK helper closure, with no compilation or model run."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from flagtree.profiler._deadline import _stop_worker
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,msg):
 if not ok:raise ValueError(msg)
job=Path('/tmp/chijin-timeline-r0120-ascend/runs/ordinary-BK32-codegen-v1');need(json.loads((job/'terminal.json').read_bytes())['returncode']==0,'Ordinary source capture incomplete');result=json.loads((job/'output/result.json').read_bytes());need(any(q['whole_binary_identical'] and q['sha256']=='77d49b1a3f9f67358f72743a68c39e8adef48a4799af591e4b1ad4f484e8d0cd' for q in result['produced']),'Actual ordinary binary not reproduced');bindings=[];source=None
for filename in result['codegen_receipts']:
 path=Path(filename);receipt=json.loads(path.read_bytes())
 if '--cce-aicore-arch=dav-c220-cube' not in receipt['argv']:continue
 entries=[q for q in receipt['inputs'] if q['path'].endswith('/meta_op.aic.bc')];need(len(entries)==1,'Actual AIC library missing');entry=entries[0];source=Path(entry['retained_file']);need(sha(source)==entry['sha256']=='94c9885a52c9e4cfdfbc239ad104f0a4d14cd330cff9c51d141eb08e88f9ef4f','Actual linked AIC library differs');bindings.append(dict(mode='ordinary',receipt=filename,receipt_sha256=sha(path),library_sha256=entry['sha256']))
need(source is not None and len(bindings)==1,'Actual ordinary actor scope differs')
for density in [1,8]:
 t=Path('/tmp/chijin-timeline-r057-ascend/runs/controlled-density-v1/output')/('BK32-density-'+str(density))/'32-0/capture/timeline';index=json.loads((t/'index.json').read_bytes());path=t/index['captures'][0]['capture_file'];cap=json.loads(path.read_bytes());jobs=cap['metadata']['compiler_metadata']['flagprism_ascend_handoff']['codegen_jobs'];actors=[q for q in jobs if q['actor_kind']=='AIC' and '--cce-aicore-only' in q['executed_command']];need(len(actors)==1,'Actual profile AIC scope differs');files=actors[0].get('executed_input_files',actors[0].get('input_files',[]));entry,=[q for q in files if q['path'].endswith('/meta_op.aic.bc')];need(entry['sha256']==sha(source) and sha(Path(entry['path']))==entry['sha256'],'Actual profile/ordinary helper resource differs');bindings.append(dict(mode='density-'+str(density),capture=str(path),capture_sha256=sha(path),library_sha256=entry['sha256']))
tool=Path('/usr/bin/llvm-extract-15');dest=a.output/'mma-helper.ll';command=[str(tool),'--recursive','--rfunc=^_mlir_ciface_mma_tile_half_to_float$',str(source),'-S','-o',str(dest)]
with (a.output/'stdout.log').open('xb') as out,(a.output/'stderr.log').open('xb') as err:
 child=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True)
 try:child.wait(timeout=25)
 except BaseException:_stop_worker(child);raise
need(child.returncode==0 and 0<dest.stat().st_size<8*1024*1024,'Actual helper extraction failed')
(a.output/'result.json').write_text(json.dumps(dict(status='actual_BK32_MMA_SDK_helper_closure',library_sha256=sha(source),helper_sha256=sha(dest),tool_sha256=sha(tool),command=command,returncode=child.returncode,bindings=bindings,device_executed=False,SDK_recompiled=False,model_executed=False,application_replayed=False,pipeline_qualified=False),indent=2))
