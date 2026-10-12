#!/usr/bin/env python3
"""Summarize native-associated actor intervals without cross-actor subtraction."""
import argparse,csv,hashlib,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--interval-output',type=Path);p.add_argument('--extra-root',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
clock={'unit':'SYS_CNT_ticks','ticks_per_us':50,'tick_resolution_ns':20,'documentation':'https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0282.html','sdk':'CANN compiler 9.0.0; AscendNPU IR 1.1.0','implementation':'dav_c220 GetSystemCycleImpl uses asm volatile MOV SYS_CNT on device','cross_actor_origin':'unverified; no cross-actor subtraction','measurement':'PIPE_S counter; async engine completion requires selected synchronization. Containment is a coarse consistency check, not an internal timing accuracy ground truth.'}
(a.output/'clock-provenance.json').write_text(json.dumps(clock,indent=2)+'\n')
summary={'status':'passed','backend':'cann','device':4,'cases':{},'clock':clock,'global_body':None,'hardware_core_id':None,'limits':['Actors are logical block + AIC/AIV + subblock; physical core ID is not collected.','Added counters, stores and synchronization perturb execution.','Native association is by ordered matching task events for this serial launch loop, not hardware counter alignment.','Within-launch actors are not independent statistical replicates. Statistics below use medians per launch.','Generic fused records have no subblock identity; no actual mixed-record rate is inferred.']}
rows=[]
case_names=['fused128-control-run','fused128-instrumented-run','fused128-delay-post-run','fused128-delay-pre-run','fused128-fenced-delay-post-run','fused128-fenced-delay-half-run','fused128-fenced-delay-pre-run','softmax-control-native','softmax-instrumented-native']
if a.extra_root:case_names+=['fused128-completion-run','softmax-completion-v2-run']
for name in case_names:
 d=a.root/name
 if not d.exists() and a.extra_root:d=a.extra_root/name
 r=json.loads((d/'result.json').read_text());assert r['status']=='passed'
 native=json.loads((d/'profile.timeline.json').read_text())['traceEvents'];native=sorted([e for e in native if e.get('ph')=='X' and e.get('cat')=='cann_runtime:aclprof_op_summary' and e.get('name')==('matmul' if r['operator']=='gemm_bias_gelu' else 'rows')],key=lambda x:x['ts']);assert len(native)==18,(name,len(native));samples=r['samples'];assert [s['invocation'] for s in samples]==list(range(3,18))
 cs={'operator':r['operator'],'shape':r['shape'],'completion_fences':r.get('completion_fences',False),'binary_sha256':r['binary_sha256'],'correctness':'18 launches pass CPU reference; first 3 warmups excluded from 15 measured samples','measured_launches':15,'native_task_events':18,'native_task_median_us':statistics.median(e['dur'] for e in native[3:]),'native_task_min_us':min(e['dur'] for e in native[3:]),'native_task_max_us':max(e['dur'] for e in native[3:]),'association':'profile starts before loop of 18 launches. Retained sample invocation i maps to ith chronological native same-name task; invocations 0,1,2 are excluded warmups. Helpers have distinct op names. Filter native aclprof category to exclude mirrored scope events.','source_result':str(d/'result.json'),'max_abs_error':max(s['max_abs_error'] for s in samples),'regions':{}}
 perlaunch={};viol=[];maxbody=[]
 for s in samples:
  event=native[s['invocation']];groups={};actors=s.get('actors',[])
  assert len(actors)==(192 if r['operator']=='gemm_bias_gelu' else 32) if r['instrumented'] else not actors
  seen=set()
  for actor in actors:
   key=(actor['program_id'],actor['actor'],actor['subblock_id']);assert key not in seen;seen.add(key)
   raw=actor['raw_record'];order=[raw[3],raw[5],raw[6],raw[7],raw[8],raw[4]] if r['operator']=='softmax' or actor['actor']=='AIV' else [raw[3],raw[5],raw[6],raw[4]];assert order==sorted(order),(name,s['invocation'],key,order)
   for region in ['body','output','readiness_wait','workspace_transfer','epilogue_with_bias_load','output_store','producer_signal','input_transfer','normalization_compute']:
    if region not in actor:continue
    start,end=actor[region];duration=end-start;assert duration>=0
    groups.setdefault(actor['actor']+':'+region,[]).append(duration)
    if region=='body' and duration/50>event['dur']:viol.append({'invocation_id':s['invocation'],'actor':key,'body_us':duration/50,'task_us':event['dur']})
    rows.append({'operator':r['operator'],'region':region,'program_id':actor['program_id'],'actor':actor['actor'],'subblock_id':actor['subblock_id'],'capture_id':name,'invocation_id':s['invocation'],'start':start,'end':end,'duration_ticks':duration,'duration_us':duration/50,'clock_domain':f"{name}/inv{s['invocation']}/block{actor['program_id']}/{actor['actor']}/sub{actor['subblock_id']}",'unit':'SYS_CNT_ticks','endpoint_policy':'actor entry through original PIPE_ALL post-store barrier' if region=='body' else ('before original readiness wait through original PIPE_ALL post-store barrier' if region=='output' and r['operator']=='gemm_bias_gelu' else 'direct recorded endpoints; see source LLVM and raw record schema'),'included_activities':region,'association_provenance':'unique allocated GM slot; native task association by serial same-name task order excluding 3 warmups','native_task_id':event['args']['metrics']['cann.task_id'],'native_stream_id':event['args']['metrics']['cann.stream_id'],'native_task_duration_us':event['dur'],'containment':duration/50<=event['dur']})
  for k,v in groups.items():perlaunch.setdefault(k,[]).append(statistics.median(v))
  if actors:maxbody.append(max((x['body'][1]-x['body'][0])/50 for x in actors))
 cs['regions']={k:{'median_of_launch_medians_ticks':statistics.median(v),'min_launch_median_ticks':min(v),'max_launch_median_ticks':max(v),'n_launches':len(v)} for k,v in perlaunch.items()};cs['containment']={'actor_body_violations':viol,'all_actor_bodies_within_native_task_duration':not viol,'max_actor_body_us_per_launch':maxbody};assert not viol
 summary['cases'][name]=cs
fields=list(rows[0]);interval_path=a.interval_output or a.output/'actor-intervals.csv';interval_path.parent.mkdir(parents=True,exist_ok=True);summary['normalized_interval_csv']=str(interval_path);f=interval_path.open('w');writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows);f.close();summary['normalized_interval_rows']=len(rows)
# Audit equal source/pre-link LLVM and unchanged AIV endpoints across intervention variants.
interventions=[]
for name in ['fused128-delay-post','fused128-delay-pre','fused128-fenced-delay-post','fused128-fenced-delay-half','fused128-fenced-delay-pre']:
 d=a.root/name
 if not d.exists() and a.extra_root:d=a.extra_root/name
 r=json.loads((d/'compile-result.json').read_text());aic=(d/'kernel.mix_aic.ll.instrumented').read_text();aiv=d/'kernel.mix_aiv.ll.instrumented';r.update(aic_aux_nop_count=aic.count('NOP'),aiv_instrumented_sha256=hashlib.sha256(aiv.read_bytes()).hexdigest(),original_aic_llvm_sha256=hashlib.sha256((d/'kernel.mix_aic.ll.original').read_bytes()).hexdigest(),original_aiv_llvm_sha256=hashlib.sha256((d/'kernel.mix_aiv.ll.original').read_bytes()).hexdigest(),signal_site='original SET.CROSS.CORE(10,33); aux before versus after; producer-fence cases add same BARRIER(6) before pre-aux endpoint',wait_endpoints='unchanged AIV clock before/after original WAIT.FLAG.DEV.REG(0)',aux_scope='fixed NOP instruction count; scalar control probe, not useful mathematical workload; identical counts do not imply identical elapsed issue time');assert r['aic_aux_nop_count']==r['budget'];interventions.append(r)
assert len({x['aiv_instrumented_sha256'] for x in interventions})==1
assert len({x['original_aic_llvm_sha256'] for x in interventions})==1
(a.output/'intervention-metadata.json').write_text(json.dumps(interventions,indent=2)+'\n')
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'cases':len(case_names),'interval_rows':len(rows),'containment_violations':0}))
