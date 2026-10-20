"""Extract only the actual linked State writeback helper; no device/replay."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
r=Path('/tmp/chijin-timeline-r079-ascend/runs/ordinary-lowering-v1/output')
previous=json.loads((r/'result.json').read_bytes())
if not any(x['whole_binary_identical'] for x in previous['produced']):raise ValueError('Original object not bound')
jobs=[(Path(f),json.loads(Path(f).read_bytes())) for f in previous['codegen_receipts']]
receipt,job=next((p,d) for p,d in jobs if '--cce-aicore-only' in d['argv'])
meta,= [x for x in job['inputs'] if x['path'].endswith('/meta_op.aiv.bc')]
source=receipt.parent/meta['retained_file']
if hashlib.sha256(source.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Original linked helper input changed')
tool=Path('/usr/bin/llvm-extract-15');dest=a.output/'state-writeback.ll'
command=[str(tool),'--recursive','--func=_mlir_ciface_store_ubuf_to_gm_1d_int32_t',str(source),'-S','-o',str(dest)]
x=subprocess.run(command,capture_output=True,timeout=25)
(a.output/'stdout.log').write_bytes(x.stdout);(a.output/'stderr.log').write_bytes(x.stderr)
result=dict(status='original_actual_linked_helper_extraction',command=command,exit=x.returncode,tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),original_binary_sha256=previous['original_npubin_sha256'],original_linked_meta=meta,device_executed=False,application_replayed=False,state_writer_qualified=False)
if dest.exists():
 if dest.stat().st_size>8*1024*1024:raise ValueError('Extracted helper bound')
 result.update(bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
(a.output/'result.json').write_text(json.dumps(result,indent=2))
if x.returncode:raise RuntimeError('Retain LLVM helper extraction failure')
