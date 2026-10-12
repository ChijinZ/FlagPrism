#!/usr/bin/env python3
"""Derive supported CANN PMU gates from installed SDK using its own cc1 pipeline."""
import argparse,hashlib,json,shlex,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True);o=a.output.resolve()
src=o/'gates.cpp';src.write_text('extern "C" [aicore] void study_prof_start(){bisheng::cce::metrics_prof_start();}\nextern "C" [aicore] void study_prof_stop(){bisheng::cce::metrics_prof_stop();}\n')
cmd=['/usr/local/Ascend/cann-9.0.0/bin/bisheng','-v','-x','cce','--cce-aicore-arch=dav-c220-vec','--cce-aicore-only','-O2','-c',str(src),'-o',str(o/'gates.o')]
r=subprocess.run(cmd,capture_output=True,timeout=30);log=r.stdout+r.stderr;(o/'compile.log').write_bytes(log);assert r.returncode==0
line=next(x for x in log.decode().splitlines() if ' -cc1 ' in x);cc=shlex.split(line);cc[cc.index('-emit-obj')]='-emit-llvm-bc';cc[cc.index('-o')+1]=str(o/'gates.bc');r=subprocess.run(cc,capture_output=True,timeout=30);(o/'ir.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
subprocess.run(['/usr/local/Ascend/cann-9.0.0/tools/bisheng_compiler/bin/llvm-link','-S',str(o/'gates.bc'),'-o',str(o/'gates.ll')],check=True,timeout=30)
ll=(o/'gates.ll').read_text();receipt={'commands':[cmd,cc],'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'llvm_sha256':hashlib.sha256(ll.encode()).hexdigest(),'sdk_gate_semantics':'SDK MetricsProfStart/Stop PIPE_ALL; CTRL bit0 set/clear; PIPE_ALL. This gate mutates profiler state through supported SDK, not SYS_CNT.', 'status':'compiled'};(o/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(ll)
