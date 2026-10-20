"""Inspect vendor bitcode definitions of the State transfer primitives."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
source=Path('/opt/triton_gcu/lib/kurama/gcu300_tops_builtins.bc');tool=Path('/opt/tops/llvm11/bin/opt')
if not source.is_file() or source.stat().st_size>128*1024*1024:raise ValueError('Bounded actual SDK builtin input')
base=dict(input=str(source),input_bytes=source.stat().st_size,input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),device_executed=False,application_replayed=False,state_writer_qualified=False)
if not tool.is_file():
 base.update(status='llvm_extract_unavailable',tools=[p.name for p in tool.parent.iterdir()][:150]);(a.output/'result.json').write_text(json.dumps(base,indent=2));raise SystemExit(1)
output=a.output/'state-primitives.ll'
command=[str(tool),'-internalize-public-api-list=tops_get_thread_id,tops_get_block_id,tops_memcpy_async,tops_slice_pad_async_1_si32,tops_slice_pad_async_2_si32,tops_slice_async_1_si32,tops_deslice_async_1_si32,tops_slice_deslice_async_1_si32,tops_slice_async_2_si32,tops_deslice_async_2_si32,tops_slice_deslice_async_2_si32','-internalize','-globaldce',str(source),'-S','-o',str(output)]
x=subprocess.run(command,capture_output=True,timeout=25)
(a.output/'stdout.log').write_bytes(x.stdout);(a.output/'stderr.log').write_bytes(x.stderr)
base.update(status='SDK_builtin_selected_root_semantic_inspection',argv=command,exit=x.returncode,tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest())
if output.exists():
 if output.stat().st_size>8*1024*1024:raise ValueError('Primitive extraction bound')
 base.update(output_bytes=output.stat().st_size,output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
(a.output/'result.json').write_text(json.dumps(base,indent=2))
if x.returncode:raise RuntimeError('Retain actual LLVM11 extraction failure')
