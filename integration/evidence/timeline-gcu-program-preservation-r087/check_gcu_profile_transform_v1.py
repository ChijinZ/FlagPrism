"""Bind preserved actual profiling inputs/outputs without device or SDK replay."""
import argparse, base64, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--tool',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('owned_deadline','/workspace/chijin-r15-python-alignment/venv/lib/python3.12/site-packages/flagtree/profiler/_deadline.py');deadline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=deadline;spec.loader.exec_module(deadline)
roots=[('original-six','/tmp/chijin-timeline-r052-qualification-profile-v1/runs/profile-first-v1',72),('supplement','/tmp/chijin-timeline-r054-supplement-profile-v1/runs/profile-first-v1',24),('affected','/tmp/chijin-timeline-r055-qualification-gcu-affected-v1/runs/affected-v1',13)]
cache={};rows=[];tool_sha=sha(a.tool.read_bytes())
for stage,root,count in roots:
 indices=sorted(Path(root).rglob('timeline/index.json'));need(len(indices)==count,'Original capture registration changed')
 for index in indices:
  ix=json.loads(index.read_bytes());need(len(ix['captures'])==1,'Registered capture count changed');entry=ix['captures'][0];path=index.parent/entry['capture_file'];capture=json.loads(path.read_bytes());mathpath=index.parents[2]/'math.json';math=json.loads(mathpath.read_bytes());row=dict(stage=stage,case=index.parents[2].name,capture_file=str(path),capture_sha256=sha(path.read_bytes()),math_file=str(mathpath),math_sha256=sha(mathpath.read_bytes()),state_writer_qualified=False)
  try:
   snap=capture['metadata']['compiled_snapshot'];meta=capture['metadata']['compiler_metadata'];binary=base64.b64decode(snap['binary_base64'],validate=True)
   need(sha(binary)==math['asm_sha256']['fatbin']==snap['executable']['binary_sha256'],'Actual loaded binary/math differs');need(capture['owner']['binary_id']==math['compiled_hash'],'Loaded owner identity differs')
   need(math['requested_launches']==1 and math['input_immutable'] is True and math.get('state_unique_logical_index_pass',math.get('state_count_passed')) is True and all(math[key] is True for key in ('state_unique_logical_index_pass','state_count_passed') if key in math),'Original numerical/host-once checks failed')
   need(sha(snap['compiler_artifacts']['llir'].encode())==math['asm_sha256']['llir'],'Actual SDK input binding differs')
   before=meta['debug_execution_input_ir'];before_sha=sha(before.encode());receipt=meta['debug_execution_rewrite_receipt'];argv=receipt['argv'];old_input=Path(argv[1]);old_output=Path(argv[2]);after_sha=meta['debug_execution_output_sha256'];hidden=meta['debug_execution_hidden_argument'];capacity=meta['debug_execution_manifest']['capacity'];regions=meta['debug_execution_max_sites']
   need(receipt['state']=='terminal' and receipt['returncode']==0,'Original rewrite was not successful');need(before_sha==meta['debug_execution_input_sha256']==receipt['source_sha256']==sha(old_input.read_bytes()),'Actual before input binding differs');need(after_sha==sha(old_output.read_bytes()),'Actual rewritten output binding differs');need(argv[4:]==list(map(str,(hidden,capacity,regions))),'Actual transform arguments differ')
   key=(before_sha,after_sha,hidden,capacity,regions)
   if key not in cache:
    folder=a.output/('object-'+str(len(cache)));folder.mkdir();certificate=folder/'certificate.json';cmd=[str(a.tool),'--check-preservation',str(old_input),str(old_output),str(certificate),str(hidden),str(capacity),str(regions)]
    with (folder/'stdout.log').open('xb') as so,(folder/'stderr.log').open('xb') as se:
     child=subprocess.Popen(cmd,stdout=so,stderr=se,start_new_session=True)
     try:child.wait(timeout=20)
     except BaseException:deadline._stop_worker(child);raise
    answer=dict(argv=cmd,returncode=child.returncode,certificate_file=str(certificate),before_sha256=before_sha,after_sha256=after_sha)
    if child.returncode:answer.update(status='unverified',error=(folder/'stderr.log').read_text()[-2000:])
    else:
     proof=json.loads(certificate.read_bytes());need(proof['original_program_preserved'] is True and proof['observer_memory_isolated'] is True and proof['actual_output_program_core_identical'] is True and proof['native_timing_boundary_qualified'] is False,'Transform proof scope differs');answer.update(status='original_GCU_program_projection_preserved',certificate=proof,certificate_sha256=sha(certificate.read_bytes()))
    cache[key]=answer;(a.output/'objects.json').write_text(json.dumps(list(cache.values()),indent=2))
   need(sha(old_input.read_bytes())==before_sha and sha(old_output.read_bytes())==after_sha,'Original transform input/output changed during validation');answer=cache[key];row.update(answer);row.update(before_sha256=before_sha,after_sha256=after_sha,original_before_file=str(old_input),original_after_file=str(old_output),binary_sha256=sha(binary),LLVM_sha256=math['asm_sha256']['llir'],actual_transform_arguments=[hidden,capacity,regions])
  except (ValueError,KeyError,FileNotFoundError) as error:row.update(status='unverified',error=str(error))
  rows.append(row);(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
need(sha(a.tool.read_bytes())==tool_sha,'New checker changed during validation')
result=dict(status='registered_GCU_profile_transform_preservation',registered=109,checked=len(rows),preserved=sum(r['status']=='original_GCU_program_projection_preserved' for r in rows),distinct_transforms=len(cache),tool_sha256=tool_sha,state_writer_qualified=False,SDK_lowering_qualified=False,native_timing_boundary_qualified=False,device_executed=False,application_replayed=False,failures=[r for r in rows if r['status']=='unverified'])
(a.output/'result.json').write_text(json.dumps(result,indent=2))
