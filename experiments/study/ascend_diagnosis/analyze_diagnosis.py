#!/usr/bin/env python3
"""Offline evidence index; preserve literal SDK metrics and actual invocation identities."""
import argparse,json,csv,hashlib,statistics,gzip,shutil,re,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--nvidia-selection',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def stats(vals):return {'median_us':statistics.median(vals),'min_us':min(vals),'max_us':max(vals),'n_invocations':len(vals)}
def write_csv(path,rows):
 with path.open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def native_events(path):
 x=json.load(open(path));xs=x['traceEvents'] if isinstance(x,dict) else x
 return sorted([e for e in xs if e.get('ph')=='X' and e.get('name','').startswith('matmul') and 'aclprof_op_summary' in e.get('cat','')],key=lambda e:e['ts'])
summary={'status':'verified_offline','raw_root':str(a.raw.resolve()),'source_kernel_sha256':hashlib.sha256((a.raw/'code/kernels.py').read_bytes()).hexdigest(),'native':{},'pmu':{},'sparse_traces':{},'native_latency_scope':'Uninstrumented/instrumented whole MIX task duration from aclprof_op_summary. CPU transfer and Python submit excluded. Batch/replay metadata kept separately.','limits':['PMU categories overlap and are not additive critical paths. Different metric groups can be collected in separate SDK replays.','Program0 PMU measurements and clocks do not stand for the whole launch. CSV rows are actor instances, not independent repetitions.','Scalar issue brackets and non-scalar WAIT instruction timestamps are not engine occupancy/completion. AIV clocks have separate origins; no precise cross-actor overlap inferred.','Logical A/B requested-byte volume is derived from program tiling; it is not physical DDR traffic or a cache-miss measurement.','SDK aic_cube_fops is preserved literally; it changes with command count although source mathematical work is invariant. Do not use it as validated FLOP work.','Only NVIDIA-selected initial config is P; earlier tile64/stage2 data are exploratory. Fused port identity requires matching frozen NVIDIA selection.']}
raw_sha={};native_rows=[];chosen_rows=[]
for name in ['native-gemm','native-fused','native-canonical-unroll','native-canonical-large-bk','frozenN-native-gemm','frozenN-native-gemm_bias_gelu','frozenN-staged-holdout','sparse-native-trace','sparse-frozenN-staged']:
 d=a.raw/name
 if not (d/'result.json').exists():continue
 r=json.load(open(d/'result.json'));assert r['status']=='passed',name;events=native_events(d/'profile.timeline.json');assert len(events)==len(r['raw_invocations']),(name,len(events),len(r['raw_invocations']))
 out=a.output/'captures'/name;out.mkdir(parents=True,exist_ok=True)
 for f in ['result.json','profile.timeline.json','profile.meta.json','profile.vendor.json']:
  path=d/f
  if not path.exists():continue
  raw_sha[str(path.relative_to(a.raw))]=hashlib.sha256(path.read_bytes()).hexdigest()
  with gzip.open(out/(f+'.gz'),'wb') as z:z.write(path.read_bytes())
 by={};cfgs={cfg['name']:cfg for cfg in r.get('configs',[])}
 for i,v in enumerate(r['raw_invocations']):
  assert v['invocation']==i;key=v['config'];duration=events[i]['dur'];by.setdefault(key,[]).append((v['batch'],duration));native_rows.append({'dataset':name,'invocation':i,'batch':v['batch'],'config':key,'native_task_us':duration,'host_sync_ns':v['host_sync_ns'],'max_abs_error':v['max_abs_error']})
 summary['native'][name]={key:{**stats([t for b,t in values]),'batch_medians_us':[statistics.median([t for bb,t in values if bb==b]) for b in sorted(set(b for b,t in values))]} for key,values in by.items()}
 if name.startswith('sparse-'):
  selected={}
  for key,vals in by.items():
   if not key.endswith('-instrumented'):continue
   med=statistics.median(t for b,t in vals);candidates=[(abs(events[i]['dur']-med),i) for i,v in enumerate(r['raw_invocations']) if v['config']==key];index=min(candidates)[1];inv=r['raw_invocations'][index];base=inv['actor_headers'][0][3]
   selection={'invocation':index,'config':key,'native_task_us':events[index]['dur'],'actor_headers':inv['actor_headers'],'loop_records':inv['loop_records'],'tick_ns':20,'counter_scope':'actual one invocation; program0; scalar issue clocks; independent actor origins'}
   (out/(key+'-selected.json')).write_text(json.dumps(selection,indent=2)+'\n');selected[key]={'invocation':index,'native_task_us':events[index]['dur'],'loop_count':len(inv['loop_records']),'aic_body_us':(inv['actor_headers'][0][4]-base)*.02,'aiv_source_wait_brackets_us':[(h[6]-h[5])*.02 for h in inv['actor_headers'][1:]],'observed_L1_A_addresses':sorted(set(v[14] for v in inv['loop_records'])),'observed_L1_B_addresses':sorted(set(v[15] for v in inv['loop_records']))}
   for fields in inv['loop_records']:
    chosen_rows.append({'dataset':name,'config':key,'invocation':index,'program_id':0,'iteration':fields[0],'buffer_parity':fields[1],'L1_A_address':fields[14],'L1_B_address':fields[15],**{label:(fields[field]-base)*.02 for label,field in [('iteration_entry_us',2),('A_reuse_wait_issue_enter_us',3),('A_reuse_wait_issue_return_us',4),('load_A_issue_enter_us',5),('load_A_issue_return_us',6),('B_reuse_wait_issue_enter_us',7),('B_reuse_wait_issue_return_us',8),('load_B_issue_enter_us',9),('load_B_issue_return_us',10),('MMA_helper_issue_enter_us',11),('MMA_helper_issue_return_us',12),('iteration_exit_us',13)]}})
  perturb={}
  for key in selected:
   orig=key.replace('-instrumented','-original');perturb[key]=summary['native'][name][key]['median_us']/summary['native'][name][orig]['median_us']
  summary['sparse_traces'][name]={'selected':selected,'task_perturbation_ratios':perturb,'barrier_policy':'Mutually exclusive original/instrumented clones preserve original fence sequence; no added runtime barriers. Only program0 clocks/stores.'}
write_csv(a.output/'native_task_samples.csv',native_rows);write_csv(a.output/'selected_actual_issue_traces.csv',chosen_rows)
# Preserve SDK CSVs and report exact selected actor rows plus virtual-instance counts.
for d in sorted(a.raw.glob('pmu-*')):
 if not d.is_dir():continue
 csvpaths=list(d.rglob('*.csv'))
 if not csvpaths:continue
 out=a.output/'pmu'/d.name;out.mkdir(parents=True,exist_ok=True);fields={}
 for path in csvpaths:
  if path.name not in ['PipeUtilization.csv','ArithmeticUtilization.csv','MemoryL0.csv','Memory.csv','L2Cache.csv','OpBasicInfo.csv','ResourceConflictRatio.csv']:continue
  shutil.copy2(path,out/path.name);raw_sha[str(path.relative_to(a.raw))]=hashlib.sha256(path.read_bytes()).hexdigest();rows=list(csv.DictReader(open(path)));fields[path.name]={'row_count':len(rows),'program0_rows':[row for row in rows if row.get('block_id')=='0'] if rows and 'block_id' in rows[0] else rows}
 receipt=a.raw/(d.name+'-receipt.json')
 if receipt.exists():shutil.copy2(receipt,out/'receipt.json')
 summary['pmu'][d.name]=fields
# Compiler artifacts: originals only, public user-source lowering, no SDK bitcode distribution.
for d in sorted(a.raw.glob('lowering-*')):
 if not d.is_dir():continue
 out=a.output/'lowering'/d.name;out.mkdir(parents=True,exist_ok=True)
 for path in d.glob('*.ll.original'):shutil.copy2(path,out/path.name);raw_sha[str(path.relative_to(a.raw))]=hashlib.sha256(path.read_bytes()).hexdigest()
 for name in ['receipt.json','compile.log']:
  if (d/name).exists():shutil.copy2(d/name,out/name)
for key in ['P32_K32','R_K32_K256','k64-s2','k128-s2','k256-s2','k512-s2']:
 path=a.raw/f'lowering-{key}/kernel.mix_aiv.ll.original'
 if path.exists():summary.setdefault('AIV_llvm_sha256',{})[key]=hashlib.sha256(path.read_bytes()).hexdigest()
for name in ['P32_K32','R_K32_K256','R_KMN64_K256']:
 cfg=next(x for x in json.load(open(a.raw/'frozen_n_staged_holdout_configs.json')) if x['name']==name);bm,bn,bk=cfg['BM'],cfg['BN'],cfg['BK'];programs=math.ceil(512/bm)*math.ceil(512/bn);kpart=(16384//math.ceil(max(bm,bn)/16)//16//16)*16 # equivalent floor(16384/roundup(maxMN,16)/16)*16
 kpart=(16384//(math.ceil(max(bm,bn)/16)*16)//16)*16
 summary.setdefault('derived_source_work',{})[name]={'config':cfg,'logical_programs':programs,'AIC_instances':programs,'AIV_instances':2*programs,'outer_K_iterations':math.ceil(4096/bk),'nd2nz_API_calls_per_program':2*math.ceil(4096/bk),'logical_AB_load_bytes_whole_launch':programs*(bm+bn)*4096*2,'source_GEMM_flops':2*512*512*4096,'source_GELU_output_elements':512*512,'SDK_inner_Kpart_from_linked_formula':kpart,'predicted_cube_commands_per_program':math.ceil(4096/bk)*math.ceil(bk/kpart)}
if a.nvidia_selection:
 nv=json.load(open(a.nvidia_selection));entry=next(x for x in nv if x['operator']=='gemm_bias_gelu' and x['shape']=='512x512x4096');expected={'BM':32,'BN':32,'BK':32,'num_warps':4,'num_stages':4};assert entry['config']==expected;summary['frozen_N_provenance']={'config':entry['config'],'nvidia_native_median_us':entry['median_us'],'source_selection_file':str(a.nvidia_selection),'selection_file_sha256':hashlib.sha256(a.nvidia_selection.read_bytes()).hexdigest(),'source_code_sha256':summary['source_kernel_sha256']};(a.output/'frozen_N_selection.json').write_text(json.dumps(entry,indent=2)+'\n')
summary['raw_sha256']=raw_sha;summary['hardware_metric_sources']=['https://github.com/Ascend/msopprof/blob/master/docs/en/user_guide/msopprof_performance_data.md','https://github.com/Ascend/msinsight/blob/master/docs/zh/best_practices/Operator_Fusion_Analysis.md'];(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'native_datasets':len(summary['native']),'native_rows':len(native_rows),'selected_issue_rows':len(chosen_rows),'pmu_datasets':len(summary['pmu'])}))
