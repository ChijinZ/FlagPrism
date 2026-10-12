#!/usr/bin/env python3
"""Audit SDK timer adaptation, same-invocation nesting and empirical scale controls."""
import argparse,csv,hashlib,json,random,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--operators',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case-prefix',default='global');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def native(d,kernel):
 e=json.loads((d/'profile/report/timeline.json').read_text())['traceEvents']
 return sorted([x for x in e if x.get('ph')=='X' and x.get('cat')=='kernel' and x.get('name')==kernel],key=lambda x:x['ts'])
def fit(points):
 xs,ys=zip(*points);xm=statistics.mean(xs);ym=statistics.mean(ys);s=sum((x-xm)*(y-ym) for x,y in points)/sum((x-xm)**2 for x in xs);b=ym-s*xm;res=[y-(s*x+b) for x,y in points];total=sum((y-ym)**2 for y in ys)
 return {'tick_period_us':s,'intercept_us':b,'r_squared':1-sum(x*x for x in res)/total,'max_absolute_residual_us':max(abs(x) for x in res)}
summary={'status':'passed','unit':'SDK_global_timer_ticks','official_frequency_hz':None,'time_in_us':None,'prototype':True,'clock_domain':'actor-local per logical program; cross-program/SIP origin unverified','cases':{},'limits':['SDK helper returns a masked 46-bit timer; these source records retain low 32 bits and decode unsigned modular differences.','SDK global_timer and TOPSPTI are different observation paths; distinct physical oscillators are not established.','Counters and fences perturb execution; no unperturbed busy-time or internal precision certificate.']}
rows=[];source_hashes=set()
for prefix,op in [(a.case_prefix+'-fused128','gemm_bias_gelu'),(a.case_prefix+'-softmax','softmax')]:
 for mode in ['nested','body','output']:
  name=prefix+'-'+mode;d=a.operators/name;r=json.loads((d/'result.json').read_text());assert r['status']=='passed' and r['correct'] and r['post_profile_correct'];assert len(r['samples'])==15;source_hashes.add(r['source_sha256'])
  events=native(d,'matmul_regions' if op=='gemm_bias_gelu' else 'softmax_regions');assert len(events)==15
  ad=a.operators/(name+'-adapter');before=(ad/'original.llir.mlir').read_text();after=(ad/'global-timer.llir.mlir').read_text();bc=before.count('callee = @tops_clock_begin');ec=before.count('callee = @tops_clock_end');ac=after.count('callee = @study_sdk_global_timer');assert bc+ec==ac==(4 if mode=='nested' else 2)
  ids0=re.findall(r'(%\d+) = "llvm.call"\(\)[^\n]*callee = @tops_clock_(?:begin|end)',before);ids1=re.findall(r'(%\d+) = "llvm.call"\(\)[^\n]*callee = @study_sdk_global_timer',after);assert ids0==ids1
  adapter_receipt=json.loads((ad/'adapter.json').read_text())
  if a.case_prefix.startswith('leader-'):assert adapter_receipt['leader_record_staging'] and adapter_receipt['leader_guarded_staging_stores']==8
  case={'recording_actor':'work-item0 with leader-guarded staging and GM writes' if a.case_prefix.startswith('leader-') else 'thread0 GM writer; pre-guard staging memory scope unverified','operator':op,'capture':mode,'source_result':str(d/'result.json'),'unit':'SDK_global_timer_ticks','time_in_us':None,'native_kernel_events':15,'native_task_median_us':statistics.median(e['dur'] for e in events),'native_association':'15 chronological same-name TOPSPTI kernel events correspond to 15 serial profiled launches. Initial validation and 5/10 warmups occur before profiling.','adapter_audit':{'before_begin_calls':bc,'before_end_calls':ec,'after_helper_calls':ac,'ssa_order':ids0,'original_sha256':hashlib.sha256(before.encode()).hexdigest(),'adapted_sha256':hashlib.sha256(after.encode()).hexdigest(),'source_math_preserved':'Clock declarations/callees and library target changed. Final leader variant also changes T staging/publication by moving scalar staging into existing thread0 copy branches and retaining compiler fences. Mathematical operations, source timing endpoints, arguments, T addresses, original source SHA and input hashes are preserved; CPU validation passes.'},'per_launch':[],'joint_program_records':0,'joint_violations':0}
  for i,sample in enumerate(r['samples']):
   values=sample['program_records'];assert len(values)==r['programs'];body=[];output=[]
   for j,v in enumerate(values):
    coords=[j//r['grid'][1],j%r['grid'][1]] if len(r['grid'])==2 else [j,0];assert v[4:6]==coords and v[6]==1
    db=(v[1]-v[0])&0xffffffff;do=(v[3]-v[2])&0xffffffff
    if mode=='nested':
     relative=[0,(v[2]-v[0])&0xffffffff,(v[3]-v[0])&0xffffffff,db];assert relative==sorted(relative) and db<2**31,(name,i,j,relative);case['joint_program_records']+=1
    if mode in ['nested','body']:body.append(db)
    if mode in ['nested','output']:output.append(do)
   item={'invocation_id':i,'native_duration_us':events[i]['dur'],'native_correlation_id':events[i]['args']['correlation_id'],'body_median_ticks':statistics.median(body) if body else None,'body_max_ticks':max(body) if body else None,'output_median_ticks':statistics.median(output) if output else None,'output_max_ticks':max(output) if output else None};case['per_launch'].append(item);rows.append({'capture_id':name,**item})
  case['body_median_of_launch_medians_ticks']=statistics.median(x['body_median_ticks'] for x in case['per_launch'] if x['body_median_ticks'] is not None) if mode!='output' else None
  case['output_median_of_launch_medians_ticks']=statistics.median(x['output_median_ticks'] for x in case['per_launch'] if x['output_median_ticks'] is not None) if mode!='body' else None
  summary['cases'][name]=case
assert len(source_hashes)==1;summary['shared_operator_source_sha256']=next(iter(source_hashes))
# Same primitive, different physical invocations: descriptive capture agreement.
summary['same_primitive_comparison']={}
for prefix in [a.case_prefix+'-fused128',a.case_prefix+'-softmax']:
 n=summary['cases'][prefix+'-nested'];b=summary['cases'][prefix+'-body'];o=summary['cases'][prefix+'-output'];summary['same_primitive_comparison'][prefix]={'nested_body_to_single_active_body_ratio':n['body_median_of_launch_medians_ticks']/b['body_median_of_launch_medians_ticks'],'nested_output_to_single_active_output_ratio':n['output_median_of_launch_medians_ticks']/o['output_median_of_launch_medians_ticks'],'limitation':'Separate launches and additional clock reads perturb duration; ratios are consistency observations, not exact equality or accuracy truth.'}
properties=json.loads((a.operators/'device-properties.json').read_text());summary['device_properties']=properties
levels={};all_pairs=[]
for q in [0,16,64,256,1024]:
 d=a.calibration/f'global-calibration-q{q}';r=json.loads((d/'result.json').read_text());assert r['status']=='passed' and r['correct'];events=native(d,'probe');assert len(events)==len(r['samples'])==15
 assert all(e['args']['activity.block_x']==1 and e['args']['activity.block_y']==1 and e['args']['activity.block_z']==1 for e in events)
 pairs=[(s['delta_ticks_mod32'],e['dur']) for s,e in zip(r['samples'],events)];all_pairs+=pairs;levels[q]={'pairs':pairs,'median_ticks':statistics.median(x for x,y in pairs),'median_native_us':statistics.median(y for x,y in pairs),'native_range_us':[min(y for x,y in pairs),max(y for x,y in pairs)],'counter_range_ticks':[min(x for x,y in pairs),max(x for x,y in pairs)],'source_result':str(d/'result.json'),'native_block_xyz':sorted({(e['args']['activity.block_x'],e['args']['activity.block_y'],e['args']['activity.block_z']) for e in events}),'correct':r['correct'],'max_abs_error':r['max_abs_error']}
train=[0,64,1024];held=[16,256];model=fit([(levels[q]['median_ticks'],levels[q]['median_native_us']) for q in train]);assert model['tick_period_us']>0
cal={'model':'native_whole_kernel_us = tick_period_us * local_bracket_ticks + prefix_suffix_intercept_us','train_levels':train,'held_out_from_fit_levels':held,'partition_provenance':'Parent specified this partition before this fit; earlier exploratory all-level summaries existed. This is not a blinded or preregistered holdout.','model_fit':model,'holdout':{},'levels':levels,'raw_75_point_ols_sensitivity':fit(all_pairs),'official_frequency_hz':None,'interpretation':'Stack-specific empirical scale/consistency calibration, not physical frequency verification, independent oscillator evidence, or internal timing precision ground truth.'}
for q in held:
 pred=model['tick_period_us']*levels[q]['median_ticks']+model['intercept_us'];actual=levels[q]['median_native_us'];cal['holdout'][q]={'predicted_native_us':pred,'observed_median_native_us':actual,'residual_us':actual-pred,'relative_residual':(actual-pred)/actual}
# Conditional resampling sensitivity, preserving each level; not independent frequency CI.
rng=random.Random(20261013);slopes=[]
for _ in range(3000):
 points=[]
 for q in train:
  v=levels[q]['pairs'];draw=[rng.choice(v) for _ in v];points.append((statistics.median(x for x,y in draw),statistics.median(y for x,y in draw)))
 slopes.append(fit(points)['tick_period_us'])
slopes.sort();cal['within_level_resampling_sensitivity']={'slope_percentiles_2_5_97_5_us_per_tick':[slopes[75],slopes[2924]],'warning':'Conditional bootstrap of 15 serial paired observations within each fixed level. Launch dependence and environment drift are not modeled. This is not an independent physical-frequency confidence interval.'}
violations=0
for name,c in summary['cases'].items():
 if c['capture']=='output':continue
 v=[{'invocation_id':x['invocation_id'],'estimated_max_body_us':x['body_max_ticks']*model['tick_period_us'],'native_us':x['native_duration_us']} for x in c['per_launch'] if x['body_max_ticks']*model['tick_period_us']>x['native_duration_us']];violations+=len(v);c['empirical_scale_holdout_containment']={'violations':v,'tested_launches':15,'scale_source':'Calibration training q=0/64/1024 only; no operator data fit.','limitation':'Coarse whole-task duration consistency only, not internal accuracy ground truth.'}
cal['real_operator_holdout_containment_violations']=violations
candidate_rate=properties['clockInstructionRate_kHz']/1000;candidate_violations=sum(x['body_max_ticks']/candidate_rate>x['native_duration_us'] for c in summary['cases'].values() for x in c['per_launch'] if x['body_max_ticks'] is not None) if candidate_rate else None
summary['clock_instruction_rate_candidate']={'reported_kHz':properties['clockInstructionRate_kHz'],'global_timer_binding':'not established','candidate_body_containment_violations':candidate_violations,'decision':'Do not use this property to convert SDK global_timer records. Core clockRate is also not a timer binding.'}
summary['empirical_calibration']=cal
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(a.output/'calibration.json').write_text(json.dumps(cal,indent=2)+'\n')
with (a.output/'launch-regions.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
print(json.dumps({'joint_records':sum(c['joint_program_records'] for c in summary['cases'].values()),'joint_violations':0,'model':model,'holdout':cal['holdout'],'operator_containment_violations':violations,'ratios':summary['same_primitive_comparison']}))
