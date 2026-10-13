#!/usr/bin/env python3
"""Original noninstrumented lowering capture with explicit auto-multibuffer setting."""
import argparse,os,subprocess,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--stages',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--interceptor',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);o=a.output.resolve();b=o/'bin';b.mkdir();wrapper=b/'bisheng';wrapper.write_text('#!/bin/sh\nexec python '+str(a.interceptor.resolve())+' "$@"\n');wrapper.chmod(0o755)
env=os.environ.copy();env.update(PATH=str(b)+':'+env['PATH'],STUDY_ASCEND_OUTPUT=str(o),STUDY_ASCEND_INSTRUMENT='0')
cmd=['/usr/local/Ascend/cann-9.0.0/bin/bishengir-compile',str(a.source.resolve()),'--target=Ascend910B4-1','--enable-hfusion-compile=true','--enable-hivm-compile=true','--enable-triton-kernel-compile=true','--enable-auto-bind-sub-block=true',f'--enable-auto-multi-buffer={str(a.stages>1).lower()}','-o',str(o/'kernel')]
r=subprocess.run(cmd,env=env,capture_output=True,timeout=120);(o/'compile.log').write_bytes(r.stdout+r.stderr);receipt={'command':cmd,'returncode':r.returncode,'status':'passed' if r.returncode==0 and (o/'kernel.o').exists() else 'failed','requested_num_stages':a.stages,'effective_auto_multibuffer':a.stages>1,'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest()};(o/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(receipt['status']!='passed')
