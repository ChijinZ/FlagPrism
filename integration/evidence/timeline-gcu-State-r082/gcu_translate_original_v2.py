"""Translate unchanged LLVM operations from the registered device module for inspection."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
root=Path('/tmp/chijin-timeline-r078-gcu/runs/state-inventory-v1/output');inv=json.loads((root/'inventory.json').read_bytes());row=next(x for x in inv['rows'] if x['id']=='q03-s0-c0' and x['variant']=='primary');entry=next(x for x in row['artifacts'] if x['kind']=='llir');source=root/entry['retained_file']
if sha(source)!=entry['sha256']:raise ValueError('Original SDK input changed')
lines=source.read_text().strip().splitlines()
if not lines[0].startswith('"builtin.module"() ({') or not lines[1].lstrip().startswith('"gpu.module"() ') or not lines[-2].strip().startswith('})') or not lines[-1].strip().startswith('})'):raise ValueError('Unknown module wrapper')
# Preserve every LLVM function/operation line; remove only the GPU module container.
body=lines[2:-2];text='"builtin.module"() ({\n'+'\n'.join(body)+'\n}) : () -> ()\n';input_file=a.output/'input-LLVM-functions.mlir';input_file.write_text(text);output=a.output/'functions.ll';tool=Path('/opt/triton_gcu/bin/gcu-compiler-translate');command=[str(tool),'--mlir-to-llvmir',str(input_file),'-o',str(output)]
x=subprocess.run(command,capture_output=True,timeout=25);(a.output/'stdout.log').write_bytes(x.stdout);(a.output/'stderr.log').write_bytes(x.stderr)
result=dict(status='LLVM_dialect_input_translation_inspection',argv=command,exit=x.returncode,tool_sha256=sha(tool),source_sha256=sha(source),analysis_input_sha256=sha(input_file),function_operation_lines_unchanged=True,gpu_container_removed=True,vendor_final_IR=False,vendor_final_native=False,device_executed=False,application_replayed=False,state_writer_qualified=False)
if output.exists():result.update(output_sha256=sha(output),output_bytes=output.stat().st_size)
(a.output/'result.json').write_text(json.dumps(result,indent=2))
if x.returncode:raise RuntimeError('Preserve translation failure')
