"""Compare current installed and new recorder outputs on distinct retained inputs."""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
r=Path('/tmp/chijin-timeline-r087-gcu');objects=json.loads((r/'runs/preservation-build-v5/output/actual-profiles/objects.json').read_text());new=r/'runs/preservation-build-v5/output/build/flagprism-gcu-timeline';reference=Path('/tmp/chijin-timeline-r077-gcu/runs/native-install-v3/output/venv/lib/python3.12/site-packages/flagtree/debugger/_bin/gcu-timeline')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('owned_deadline','/workspace/chijin-r15-python-alignment/venv/lib/python3.12/site-packages/flagtree/profiler/_deadline.py');deadline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=deadline;spec.loader.exec_module(deadline)
rows=[]
for i,obj in enumerate(objects):
 argv=obj['argv'];before=Path(argv[2]);need= obj['before_sha256'];
 if sha(before)!=need:raise ValueError('Retained input differs')
 outputs=[]
 for name,tool in [('installed',reference),('candidate',new)]:
  folder=a.output/(str(i)+'-'+name);folder.mkdir();cmd=[str(tool),str(before),str(folder/'output.mlir'),str(folder/'manifest.json'),*argv[5:]]
  with (folder/'stdout.log').open('xb') as so,(folder/'stderr.log').open('xb') as se:
   child=subprocess.Popen(cmd,stdout=so,stderr=se,start_new_session=True)
   try:child.wait(timeout=20)
   except BaseException:deadline._stop_worker(child);raise
  outputs.append(dict(tool=str(tool),returncode=child.returncode,output=str(folder/'output.mlir'),output_sha256=sha(folder/'output.mlir') if (folder/'output.mlir').exists() else None))
 rows.append(dict(before_sha256=need,outputs=outputs,exact_output_equal=all(x['returncode']==0 for x in outputs) and outputs[0]['output_sha256']==outputs[1]['output_sha256']));(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
(a.output/'result.json').write_text(json.dumps(dict(status='current_installed_GCU_transform_output_comparison',checked=len(rows),identical=sum(x['exact_output_equal'] for x in rows),reference_tool_sha256=sha(reference),candidate_tool_sha256=sha(new),device_executed=False,application_replayed=False,SDK_executed=False,failures=[x for x in rows if not x['exact_output_equal']]),indent=2))
