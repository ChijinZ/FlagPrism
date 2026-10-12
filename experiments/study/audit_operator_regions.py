#!/usr/bin/env python3
"""Audit real operator captures, physical identity and independent outer bounds."""
import argparse,csv,hashlib,json,statistics,shutil
from pathlib import Path
from observations import native,read
from region_plan import plan
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
intervals=[];summary=[];comparison=[];bounds=[];checks=[];allcases={}
for backend in ['cuda','enflame']:
 root=a.raw/backend/'operators';assert read(root/'complete.json')['completed_cases']==16
 for f in sorted(root.glob('*/result.json')):
  d=read(f);assert d['status']=='passed' and d['correct'] and d['post_profile_correct'];assert len(d['samples'])==15;case=f.parent.name;allcases[backend,case]=d
  for key,item in d['asm'].items():
   raw=(f.parent/'asm'/key).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
  es=[e for e in native(f.parent,backend) if e['kind']=='kernel' and e.get('duration_us') is not None]
  assert len(es)==15 and all(e['duration_us']>0 for e in es)
  dest=a.output/'captures'/backend/case;dest.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest/'result.json');(dest/'native.json').write_text(json.dumps(es,indent=2)+'\n')
  mode=d['capture'];grid=d['grid'];programs=d['programs'];ids=set()
  for sm,event in zip(d['samples'],es):
   records=sm['program_records'];assert len(records)==programs
   if mode=='none':continue
   for slot,v in enumerate(records):
    expected=[slot//grid[1],slot%grid[1]] if len(grid)==2 else [slot,0];assert v[4:6]==expected and v[6]==1
    identity=(sm['invocation_id'],*expected);assert identity not in ids;ids.add(identity)
    for region,i in [('body',0),('output',2)]:
     if mode not in ['nested',region]:continue
     delta=(v[i+1]-v[i])&0xffffffff
     intervals.append({'backend':backend,'operator':d['operator'],'config':f"t{d['tile']}" if d['operator'].startswith('gemm') else f"r{d['rows']}",'case':case,'capture':mode,'physical_invocation_id':sm['invocation_id'],'program0':v[4],'program1':v[5],'region':region,'start_low32':v[i]&0xffffffff,'end_low32':v[i+1]&0xffffffff,'duration':delta,'unit':d['unit'],'native_interval_us':event['duration_us'],'association':'serial capture has exactly one native kernel per explicit launch; program coordinates stored in distinct slots'})
     if backend=='cuda':
      ok=delta<=event['duration_us']*1000
      bounds.append({'case':case,'invocation_id':sm['invocation_id'],'program0':v[4],'program1':v[5],'region':region,'bracket_ns':delta,'cupti_whole_kernel_ns':event['duration_us']*1000,'contained':ok})
  for region in ['body','output']:
   vals=[r['duration'] for r in intervals if r['backend']==backend and r['case']==case and r['region']==region]
   if vals:summary.append({'backend':backend,'operator':d['operator'],'config':f"t{d['tile']}" if d['operator'].startswith('gemm') else f"r{d['rows']}",'capture':mode,'region':region,'samples':len(vals),'median':statistics.median(vals),'min':min(vals),'max':max(vals),'unit':d['unit'],'native_median_us':statistics.median(e['duration_us'] for e in es)})
  checks.append({'backend':backend,'case':case,'programs_per_launch':programs,'records_verified':len(ids),'native_invocations':len(es),'source_sha256':d['source_sha256'],'input_hashes':d['input_hashes'],'status':'passed'})
 for op,configs in [('gemm_bias_gelu',['t16','t64']),('softmax',['r1','r2'])]:
  for config in configs:
   base=allcases[backend,f'{op}-{config}-nested']
   for region,i in [('body',0),('output',2)]:
    ref=allcases[backend,f'{op}-{config}-{region}'];assert base['input_hashes']==ref['input_hashes']
    # Compare the same logical coordinates and launch ordinal, explicitly different captures.
    ratios=[];sv=[];bv=[]
    for bs,rs in zip(base['samples'],ref['samples']):
     for v,w in zip(bs['program_records'],rs['program_records']):
      assert v[4:6]==w[4:6];b=(v[i+1]-v[i])&0xffffffff;s=(w[i+1]-w[i])&0xffffffff
      bv.append(b);sv.append(s)
      if s:ratios.append(b/s)
    comparison.append({'backend':backend,'operator':op,'config':config,'region':region,'nested_median':statistics.median(bv),'single_region_median':statistics.median(sv),'ratio_of_medians':statistics.median(bv)/statistics.median(sv),'median_coordinate_ratio':statistics.median(ratios),'unit':base['unit'],'reference_scope':'same vendor primitive, separate single-active capture; protocol control, not independent physical-time ground truth'})
def csvfile(name,rows):
 with (a.output/name).open('w') as f:w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
for name,rs in [('operator_intervals.csv',intervals),('operator_summary.csv',summary),('protocol_comparison.csv',comparison),('cuda_independent_outer_bounds.csv',bounds)]:csvfile(name,rs)
info={'cases_verified':len(checks),'cases':checks,'explicit_identity_check':'per launch, each expected logical program slot exists exactly once with matching coordinates','independent_bound_source':'CUPTI activity duration in the same serial capture; bounds do not prove exact internal-region accuracy','cuda_outer_bound_checks':len(bounds),'cuda_outer_bound_violations':sum(not r['contained'] for r in bounds),'plans':{b:vars(plan(b)) for b in ['cuda','enflame','cann']},'joint_gcu_request':vars(plan('enflame',joint_invocation=True)),'limits':['Single-region replay uses the same primitive, so it validates nesting protocol but is not independent physical time.','No statistical confidence interval claimed; program samples share launches/devices.','Body vs output frames from GCU replays are not overlaid as one execution.','Scalar record scope and barrier endpoint semantics require emitted-IR inspection.']}
(a.output/'operator_audit.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps({k:v for k,v in info.items() if k in ['cases_verified','cuda_outer_bound_checks','cuda_outer_bound_violations']}))
