"""Extract the same reviewed State closure from the actual new linked library."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from flagtree.profiler._deadline import _stop_worker
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,msg):
 if not ok:raise ValueError(msg)
rows=json.loads(Path('/tmp/chijin-timeline-r089-ascend/runs/supplement-State-v2/output/rows.json').read_bytes());bindings=[];source=None
for row in rows:
 for job in row['jobs']:
  if '--cce-aicore-arch=dav-c220-vec' not in job['argv']:continue
  entries=[s for s in job['inputs'] if s['path'].endswith('/meta_op.aiv.bc')];need(len(entries)==1,'Actual AIV linked library missing');entry=entries[0];p=Path(entry['retained_file']);need(sha(p)==entry['sha256']=='c816c724c8d0455ff1a85cd08b1f6097131f67809dfc0fbe31209d66139d04a6','Actual linked State library changed');source=p;bindings.append(dict(id=row['id'],library_sha256=entry['sha256'],receipt_file=job['receipt_file'],receipt_sha256=job['receipt_sha256']))
need(len(bindings)==8 and source is not None,'Actual supplemental State library scope differs');tool=Path('/usr/bin/llvm-extract-15');dest=a.output/'state-writeback.ll';cmd=[str(tool),'--recursive','--rfunc=^_mlir_ciface_store_ubuf_to_gm_[12]d_int32_t$',str(source),'-S','-o',str(dest)]
with (a.output/'stdout.log').open('xb') as so,(a.output/'stderr.log').open('xb') as se:
 child=subprocess.Popen(cmd,stdout=so,stderr=se,start_new_session=True)
 try:child.wait(timeout=25)
 except BaseException:_stop_worker(child);raise
need(child.returncode==0 and dest.stat().st_size<8*1024*1024,'Actual State library extraction failed');old=Path('/tmp/chijin-timeline-r080-ascend/runs/state-helpers-v2/output/state-writeback.ll');before=old.read_text().splitlines();after=dest.read_text().splitlines();normalize=lambda v:'\n'.join(l for l in v if not l.startswith('; ModuleID = '));same=normalize(before)==normalize(after)
(a.output/'result.json').write_text(json.dumps(dict(status='actual_supplement_State_SDK_closure',actual_library_sha256=sha(source),previous_library_sha256='d5c10fbdcb1a976e888a2ddb2bcccd0b66febc10e959e044d141ad2760b63fa0',actual_closure_sha256=sha(dest),previous_closure_sha256=sha(old),complete_closure_equal_ignoring_ModuleID=same,command=cmd,returncode=child.returncode,tool_sha256=sha(tool),bindings=bindings,device_executed=False,application_replayed=False,state_writer_qualified=False),indent=2))
