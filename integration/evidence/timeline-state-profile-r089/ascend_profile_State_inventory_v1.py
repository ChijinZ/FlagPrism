"""Bind retained actual profiling codegen inputs; never recompile/profile."""
import argparse,base64,hashlib,importlib.util,json,re,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
roots=[('original-six',Path('/tmp/chijin-timeline-r055-qualification-ascend-v2/runs/profile-first-v1'),72),('supplement',Path('/tmp/chijin-timeline-r057-qualification-supplement-ascend-v1/runs/profile-first-v1'),24)];registered=[]
for stage,root,count in roots:
 indices=sorted(root.glob('*/capture/timeline/index.json'));need(len(indices)==count,'Original profiling denominator differs')
 for index in indices:registered.append(dict(stage=stage,case=index.parents[2].name,timeline=str(index.parent),math_file=str(index.parents[2]/'math.json')))
registration=Path('/tmp/chijin-timeline-r062-ascend/runs/prepare-v1/output/registration-v2.json');reg=json.loads(registration.read_bytes());need(len(reg['calls'])==60,'Original affected60 denominator differs')
for index,call in enumerate(reg['calls']):
 root=Path('/tmp/chijin-timeline-r062-ascend/runs')/f'{index:03d}'/'output';registered.append(dict(stage='affected',case=call['id']+'-'+call['phase'],timeline=str(root/'capture/timeline'),math_file=str(root/'math.json')))
rows=[];objects={}
for registration in registered:
 row=dict(registration,status='unverified',state_writer_qualified=False)
 try:
  timeline=Path(row['timeline']);index=json.loads((timeline/'index.json').read_bytes());need(len(index['captures'])==1,'Actual registered capture count differs');capfile=timeline/index['captures'][0]['capture_file'];cap=json.loads(capfile.read_bytes());mathfile=Path(row['math_file']);math=json.loads(mathfile.read_bytes());meta=cap['metadata']['compiler_metadata'];snap=cap['metadata']['compiled_snapshot'];binary=base64.b64decode(snap['binary_base64'],validate=True);binary_sha=digest(binary);need(binary_sha==math['asm_sha256']['npubin']==snap['executable']['binary_sha256'] and cap['owner']['binary_id']==math['compiled_hash'],'Actual loaded binary/math differs');need(math['requested_launches']==1 and math['input_immutable'] is True and math.get('state_unique_logical_index_pass',math.get('state_count_passed')) is True,'Original mathematical once/State check failed')
  handoff=meta['flagprism_ascend_handoff'];association=handoff['producer_association'];need(handoff['phase']=='finished' and handoff['returncode']==0 and association['basis']=='same_enclosing_sdk_process_group_and_exact_final_output_bytes' and association['final_binary_sha256']==binary_sha,'Actual compiler/loaded-output association differs');final=handoff['final_outputs']['binary'];need(final['sha256']==binary_sha and digest(base64.b64decode(final['data'],validate=True))==binary_sha and sha(final['retained_path'])==binary_sha,'Actual retained final output differs')
  need(meta['hash']==math['compiled_hash'] and meta['arch']=='Ascend910B4-1' and meta['enable_auto_blockify'] is False and meta['force_simt_only'] is False and meta['parallel_mode']=='simd','Actual profiling launch ABI differs');artifacts=snap['compiler_artifacts'];need(digest(artifacts['ttir'].encode())==math['asm_sha256']['ttir'] and digest(artifacts['bcmlir'].encode())==math['asm_sha256']['bcmlir'],'Actual profiling frontend/SDK source differs')
  header=next(l for l in artifacts['ttir'].splitlines() if 'tt.func public @' in l);formals=re.findall(r'%([A-Za-z_][\w]*):\s*!tt.ptr<',header);need(formals.count('State')==1,'Actual profiling State ordinal absent');jobs=[]
  for job in handoff['codegen_jobs']:
   if '--cce-aicore-only' not in job['executed_command']:continue
   need(job['state']=='finished' and job['exit_code']==0,'Actual SDK codegen job not finished');inputs=[]
   for src in job['inputs']:
    need(src.get('pass_returncode',0)==0,'Original timeline rewriting failed');path=Path(src.get('adapted_path',src.get('retained_path','')));wanted=src.get('adapted_sha256',src['sha256']);need(path.is_file() and sha(path)==wanted,'Actual retained codegen input changed');need(str(path) in job['executed_command'],'Retained input not used in actual codegen');inputs.append(dict(path=str(path),sha256=wanted,original_source_sha256=src['sha256']))
   need(inputs,'Actual profiled LLVM codegen input missing');jobs.append(dict(actor_kind=job['actor_kind'],target_arch=job['target_arch'],command=job['executed_command'],inputs=inputs,input_files=job.get('executed_input_files',job.get('input_files',[]))))
  need(jobs,'No actual actor codegen jobs');has_cube=any(j['actor_kind']=='AIC' for j in jobs);need((meta['mix_mode'],meta['bs_task_type'])==(('mix',32) if has_cube else ('aiv',10)),'Actual profile actor/task mismatch');grid=cap['owner']['layout']['grid'];need(tuple(grid[:len(math['grid'])])==tuple(math['grid']) and all(x==1 for x in grid[len(math['grid']):]),'Original profiling launch geometry differs')
  key=tuple((j['actor_kind'],tuple(s['sha256'] for s in j['inputs'])) for j in jobs);objects.setdefault(key,len(objects));row.update(status='bound_actual_profile_codegen',capture_file=str(capfile),capture_sha256=sha(capfile),math_sha256=sha(mathfile),binary_sha256=binary_sha,ttir_sha256=digest(artifacts['ttir'].encode()),bcmlir_sha256=digest(artifacts['bcmlir'].encode()),formals=formals,State_index=formals.index('State'),grid=grid,elements=math['math']['count'],has_cube=has_cube,mix_mode=meta['mix_mode'],bs_task_type=meta['bs_task_type'],compiler_identity=meta['ascend_compiler_identity'],jobs=jobs,object_index=objects[key])
 except (ValueError,KeyError,StopIteration) as error:row.update(error=str(error))
 rows.append(row);(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
current={};history=[]
for row in rows:
 if row['case'] in current:need(row['stage']=='affected','Unexpected historical replacement');history.append(current[row['case']])
 current[row['case']]=row
need(len(rows)==156 and len(current)==96 and len(history)==60,'Actual current/profile historical registry differs');(a.output/'current-rows.json').write_text(json.dumps(list(current.values()),indent=2))
(a.output/'result.json').write_text(json.dumps(dict(status='actual_retained_Ascend_profile_codegen_inventory',historical_registered=156,historical_bound=sum(r['status']!='unverified' for r in rows),current_registered=96,current_bound=sum(r['status']!='unverified' for r in current.values()),distinct_codegen_inputs=len(objects),current_failures=[r for r in current.values() if r['status']=='unverified'],state_writer_qualified=False,SDK_ABI_binding_qualified=False,device_executed=False,SDK_recompiled=False,application_replayed=False),indent=2))
