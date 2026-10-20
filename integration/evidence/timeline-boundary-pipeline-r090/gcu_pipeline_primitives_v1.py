"""Read only the actual linked SDK primitive definitions needed by C2."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=Path('/opt/triton_gcu/lib/kurama/gcu300_tops_builtins.bc');tool=Path('/opt/tops/llvm11/bin/opt')
if sha(source)!='fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a':raise ValueError('Actual SDK builtin differs')
roots=['tops_private_dte_ctr','tops_wait_dte','tops_syncthreads','tops_addmm_fp16_fp32','tops_slice_async_2_fp16','tops_slice_pad_async_2_fp16','tops_deslice_async_2_fp16','tops_slice_deslice_async_2_fp16','tops_memset_async_fp16','tops_memcpy_async'];dest=a.output/'pipeline-primitives.ll';command=[str(tool),'-internalize-public-api-list='+','.join(roots),'-internalize','-globaldce',str(source),'-S','-o',str(dest)]
with (a.output/'stdout.log').open('xb') as out,(a.output/'stderr.log').open('xb') as err:
 child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
 try:child.wait(timeout=25)
 except BaseException:child.kill();child.wait(timeout=10);raise
if child.returncode!=0 or not dest.is_file() or dest.stat().st_size>8*1024*1024:raise ValueError('Actual bounded SDK definition extraction failed')
(a.output/'result.json').write_text(json.dumps(dict(status='actual_C2_linked_SDK_primitive_definitions',source=str(source),source_sha256=sha(source),tool_sha256=sha(tool),roots=roots,output_sha256=sha(dest),output_bytes=dest.stat().st_size,command=command,returncode=child.returncode,device_executed=False,application_replayed=False,SDK_recompiled=False,pipeline_qualified=False),indent=2))
