#!/usr/bin/env python3
"""Audit same-launch/block independent PMU region-cycle versus SYS_CNT brackets."""
import argparse,csv,hashlib,json,statistics,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[];cases=[]
for scope in ['empty','body','output']:
 for variant in ['broad','narrow','shared','dependent','branch-v2']:
  tag=f'precision-{scope}-'+('pmu' if variant=='broad' else variant+'-pmu')
  reports=sorted(a.raw.glob(tag+'/OPPROF*'))
  if not reports:continue
  report=reports[-1];cf=report/'ArithmeticUtilization.csv'
  if not cf.exists():continue
  cr=list(csv.DictReader(cf.open()));csvby={int(x['block_id']):x for x in cr};assert len(csvby)==32 and set(csvby)==set(range(32))
  basic=next(csv.DictReader((report/'OpBasicInfo.csv').open()));assert basic['Op Type']=='vector' and int(basic['Block Dim'])==32 and basic['Mix Block Dim']=='NA'
  runs=[]
  for d in sorted(a.raw.glob(tag+'-run-*')):
   f=d/'result.json'
   if not f.exists():continue
   r=json.loads(f.read_text())
   if not r.get('precision_replay',{}).get('retained_warmups'):continue
   assert r['status']=='passed'
   runs.append((d,r))
  if not runs:continue
  case={'scope':scope,'variant':variant,'report':str(report.relative_to(a.raw)),'report_sha256':sha(cf),'frequency_mhz_reported':float(basic['Current Freq']),'raw_associations':[]}
  selected=None
  for native in sorted((report/'dump').glob('DeviceProf*.bin')):
   b=native.read_bytes();assert len(b)==4096
   rows=[]
   for off in range(0,len(b),128):
    x=b[off:off+128];sub,bid=struct.unpack_from('<HH',x,28);cycles=struct.unpack_from('<Q',x,32)[0];begin,end=struct.unpack_from('<QQ',x,112);corebits=struct.unpack_from('<H',x,20)[0];stream,task=struct.unpack_from('<HH',x,4)
    rows.append({'block_id':bid,'subblock_id':sub,'core_id':(corebits>>1)&127,'core_type_bit':corebits&1,'cycles':cycles,'task_start_SYS':begin,'task_end_SYS':end,'stream_id':stream,'task_id':task})
   assert {x['block_id'] for x in rows}==set(range(32)) and all(x['subblock_id']==0 for x in rows)
   matches=[]
   for d,r in runs:
    for sample in r['samples']:
     actors={x['program_id']:x for x in sample['actors']};assert set(actors)==set(range(32))
     if all(row['task_start_SYS']<=actors[row['block_id']]['body'][0]<=actors[row['block_id']]['body'][1]<=row['task_end_SYS'] for row in rows):matches.append((d,r,sample,actors))
   assert len(matches)==1,(native,len(matches))
   d,r,sample,actors=matches[0];assert sample['invocation']==0
   exact=all(int(float(csvby[x['block_id']]['aiv_total_cycles']))==x['cycles'] for x in rows)
   case['raw_associations'].append({'native':str(native.relative_to(a.raw)),'native_sha256':sha(native),'source_result':str((d/'result.json').relative_to(a.raw)),'source_result_sha256':sha(d/'result.json'),'invocation':sample['invocation'],'all32_actor_bodies_contained_by_matching_native_SYS_stamps':True,'csv_cycles_exact_match_all32':exact})
   if exact:
    if selected is not None:assert scope=='empty', 'nonempty CSV unexpectedly aliases two replays'
    selected=(rows,actors,d)
  assert selected is not None
  rows,actors,d=selected;case['source_result']=str((d/'result.json').relative_to(a.raw));local=[]
  for row in rows:
   bid=row['block_id'];v=actors[bid]['raw_record'];nativeus=float(csvby[bid]['aiv_time(us)']);calculated=row['cycles']/case['frequency_mhz_reported'];assert abs(nativeus-calculated)<=.000002
   lower=(v[11]-v[10])/50;upper=(v[12]-v[9])/50;inner=(v[4]-v[3 if scope=='body' else 7])/50 if scope!='empty' else None
   assert v[9]<=v[10]<=v[11]<=v[12]
   rec={'scope':scope,'variant':variant,**row,'reference_pmu_us':nativeus,'gate_lower_us':lower,'gate_upper_us':upper,'gate_uncertainty_us':upper-lower,'source_interval_us':inner,'start_gate_to_source_us':None if scope=='empty' else (v[3 if scope=='body' else 7]-v[10])/50,'source_end_to_stop_gate_us':None if scope=='empty' else (v[11]-v[4])/50,'source_minus_reference_us':None if inner is None else inner-nativeus,'within_halo_plus_20ns_quantization':lower-.020002<=nativeus<=upper+.020002,'source_result':case['source_result']}
   if inner is not None:
    rec['scope_conditioned_abs_error_bound_us']=max(upper-inner,inner-lower)+.02+1/case['frequency_mhz_reported']+.000002
   else:rec['scope_conditioned_abs_error_bound_us']=None
   records.append(rec);local.append(rec)
  case.update(records=len(local),halo_quantization_violations=sum(not x['within_halo_plus_20ns_quantization'] for x in local),gate_uncertainty_median_us=statistics.median(x['gate_uncertainty_us'] for x in local),gate_uncertainty_max_us=max(x['gate_uncertainty_us'] for x in local),reference_median_us=statistics.median(x['reference_pmu_us'] for x in local))
  if scope!='empty':case.update(source_minus_reference_median_us=statistics.median(x['source_minus_reference_us'] for x in local),source_minus_reference_max_abs_us=max(abs(x['source_minus_reference_us']) for x in local),source_start_gate_gap_max_us=max(x['start_gate_to_source_us'] for x in local),source_stop_gate_gap_max_us=max(x['source_end_to_stop_gate_us'] for x in local),scope_conditioned_abs_error_bound_max_us=max(x['scope_conditioned_abs_error_bound_us'] for x in local),scope_conditioned_abs_error_rounded_bound_ns=__import__('math').ceil(1000*max(x['scope_conditioned_abs_error_bound_us'] for x in local)),source_point_within_20ns=sum(abs(x['source_minus_reference_us'])<=.020002 for x in local))
  cases.append(case)
summary={'cases':cases,'records':len(records),'reference':'independent hardware PMU cycle window gated via supported installed SDK CTRLbit0 API, vendor per-AIV aiv_time converted from reported core frequency; not whole-kernel timing or simulator','sys_counter_period_us':.02,'comparison':'physical gate occurs between before/after SET.CTRL SYS halos; elapsed floor-counter uncertainty <20ns; additional PIPE_ALL and scalar preparation perturb same instrumented execution','association':'raw native128B records validated against all32 CSV cycles and unique replay/invocation timestamps; block ID matched directly to recorded GET.BLOCK.IDX, plain-AIV subblock0; physical core ID is separately decoded','bound_assumptions':'Physical gate within raw before/afterSET.CTRL halos; 20ns SYS floor-duration uncertainty + one PMUcorecycle at vendorreportedCurrentFreq +2ps verified vendorCSV conversion tolerance; conditionalonreportedfrequencyconversion. Scopepadding=max(upper−source,source−lower), never subtracted to manufacture pointtruth. Finalbranch-v2 rounded conservativebound41ns, empiricalmax20.606ns.', 'limits':['This validates bounded window agreement, not unperturbed compute busy time.','Public-source native128B format is crosschecked against installed output; native timestamps used only for association.','Frequency conversion follows vendor reported Current Freq; no independent frequency lock/mutation or oscillator independence asserted.','Broad halos may substantially exceed source body/output; point disagreement must not be called accurate.','One selected invocation per scope here; precision sample count is32 blocks, correlated within a launch.']}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if records:
 with (a.output/'comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)
print(json.dumps({'records':len(records),'cases':[{k:v for k,v in c.items() if k not in ['raw_associations']} for c in cases]},indent=2))
