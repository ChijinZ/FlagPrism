#!/usr/bin/env python3
"""Bounded original-pipeline recompile with a private pre-link LLVM interceptor."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--completion',action='store_true');p.add_argument('--producer-fence',action='store_true');p.add_argument('--instrumented',action='store_true');p.add_argument('--n',type=int,default=32);p.add_argument('--budget',type=int,default=0);p.add_argument('--before',type=int,default=0);a=p.parse_args();assert 0<=a.before<=a.budget
a.output.mkdir(parents=True,exist_ok=False);o=a.output.resolve();src=o/'original.mlir';src.write_bytes(a.source.read_bytes());b=o/'bin';b.mkdir();wrapper=b/'bisheng';wrapper.write_text('#!/bin/sh\nexec python '+str(Path(__file__).resolve().with_name('ascend_llvm_intercept.py'))+' "$@"\n');wrapper.chmod(0o755)
env=os.environ.copy();env.update(PATH=str(b)+':'+env['PATH'],STUDY_ASCEND_OUTPUT=str(o),STUDY_ASCEND_INSTRUMENT=str(int(a.instrumented)),STUDY_ASCEND_COMPLETION=str(int(a.completion)),STUDY_ASCEND_PRODUCER_FENCE=str(int(a.producer_fence)),STUDY_ASCEND_N=str(a.n),STUDY_ASCEND_BEFORE=str(a.before),STUDY_ASCEND_BUDGET=str(a.budget))
cmd=['/usr/local/Ascend/cann-9.0.0/bin/bishengir-compile',str(src),'--target=Ascend910B4-1','--enable-hfusion-compile=true','--enable-hivm-compile=true','--enable-triton-kernel-compile=true','--enable-auto-bind-sub-block=true','--enable-auto-multi-buffer=false','-o',str(o/'kernel')]
r={'command':cmd,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'instrumented':a.instrumented,'n':a.n,'completion_fences':a.completion,'producer_fence':a.producer_fence,'budget':a.budget,'before':a.before,'timeout_s':120,'status':'started','time_started_unix':time.time()}
try:
 q=subprocess.run(cmd,env=env,capture_output=True,timeout=120);(o/'compile.log').write_bytes(q.stdout+q.stderr);r['returncode']=q.returncode;binary=o/'kernel.o';r['status']='passed' if q.returncode==0 and binary.exists() and binary.stat().st_size else 'failed'
 if binary.exists():r['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest();r['binary_bytes']=binary.stat().st_size
except subprocess.TimeoutExpired as e:r.update(status='timeout',error=str(e))
r['time_ended_unix']=time.time();(o/'compile-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(r['status']!='passed')
