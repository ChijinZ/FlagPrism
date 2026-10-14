"""Execute inherited Proton RUN/FileCheck directives using the fresh compiler."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
root=Path(os.environ['METHOD_COMPILER_SOURCE'])/'test/Proton'
output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=False)
env=dict(os.environ)
env['PATH']='/workspace/method-full-build-nvidia/bin:/workspace/cache/triton/.triton/llvm/llvm-f6ded0be-ubuntu-x64/bin:'+env['PATH']
results=[]
for path in sorted(root.rglob('*.mlir')):
    for number,line in enumerate(path.read_text().splitlines()):
        if 'RUN:' not in line:continue
        command=line.split('RUN:',1)[1].strip().replace('%s',shlex.quote(str(path)))
        process=subprocess.run(['bash','-o','pipefail','-c',command],env=env,capture_output=True,text=True)
        item={'source':str(path),'run_line':number+1,'command':command,'exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr}
        results.append(item)
        print('PASS' if process.returncode==0 else 'FAIL',str(path.relative_to(root)),number+1,flush=True)
(output/'results.json').write_text(json.dumps(results,indent=2))
raise SystemExit(1 if any(item['exit_code'] for item in results) else 0)
