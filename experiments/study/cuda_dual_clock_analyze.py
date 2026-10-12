#!/usr/bin/env python3
"""Compare relative region fractions using distinct counters, without clock calibration."""
import argparse,csv,hashlib,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
rows=[];summary={}
for case in ['fused-v2','softmax']:
 d=a.raw/case;r=json.loads((d/'result.json').read_text());assert r['status']=='passed' and r['correct'] and r['post_profile_correct']
 assert r['clock_record_width_bits']==64
 ptx=(d/'asm/ptx').read_text();assert ptx.count('%clock64')==8 and ptx.count('%globaltimer')==4
 for sample in r['samples']:
  for rec in sample['program_records']:
   gbody=rec[1]-rec[0];gout=rec[3]-rec[2];blo=rec[10]-rec[9];bhi=rec[11]-rec[8];olo=rec[14]-rec[13];ohi=rec[15]-rec[12]
   assert 0<gout<=gbody and 0<blo<=bhi and 0<=olo<=ohi
   cl=olo/bhi;cu=ohi/blo;fraction=gout/gbody
   # Observed granularity is not a guaranteed hardware error bound.
   gl=max(0,gout-32)/(gbody+32);gu=(gout+32)/max(1,gbody-32)
   rows.append({'case':case,'invocation':sample['invocation_id'],'program0':rec[4],'program1':rec[5],'body_ns':gbody,'output_ns':gout,'body_cycles_lower':blo,'body_cycles_upper':bhi,'output_cycles_lower':olo,'output_cycles_upper':ohi,'global_fraction':fraction,'cycle_fraction_lower':cl,'cycle_fraction_upper':cu,'fraction_in_cycle_bracket':cl<=fraction<=cu,'fraction_intervals_overlap_with_empirical_32ns_margin':max(gl,cl)<=min(gu,cu),'body_midpoint_cycles_per_ns':(blo+bhi)/2/gbody,'endpoint_cycle_bracket_max':max(rec[9]-rec[8],rec[11]-rec[10],rec[13]-rec[12],rec[15]-rec[14])})
 rr=[x for x in rows if x['case']==case]
 summary[case]={'records':len(rr),'raw_fraction_outside_cycle_brackets':sum(not x['fraction_in_cycle_bracket'] for x in rr),'nonoverlap_with_empirical_32ns_margin':sum(not x['fraction_intervals_overlap_with_empirical_32ns_margin'] for x in rr),'median_global_fraction':statistics.median(x['global_fraction'] for x in rr),'median_cycle_fraction_lower':statistics.median(x['cycle_fraction_lower'] for x in rr),'median_cycle_fraction_upper':statistics.median(x['cycle_fraction_upper'] for x in rr),'median_body_midpoint_cycles_per_ns':statistics.median(x['body_midpoint_cycles_per_ns'] for x in rr),'body_midpoint_cycles_per_ns_range':[min(x['body_midpoint_cycles_per_ns'] for x in rr),max(x['body_midpoint_cycles_per_ns'] for x in rr)],'max_endpoint_bracket_cycles':max(x['endpoint_cycle_bracket_max'] for x in rr),'source_sha256':r['source_sha256'],'input_hashes':r['input_hashes'],'ptx_sha256':hashlib.sha256(ptx.encode()).hexdigest()}
with (a.output/'relative_phase_checks.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
out={'schema_version':1,'quantity':'output/body relative control-path interval fraction, paired same execution endpoints','independent_registers':['PTX globaltimer nanosecond timer','PTX clock64 cycle counter'],'frequency_conversion_performed':False,'conditional_assumptions':['SM cycle frequency constant across each paired body/output interval','same recording thread for all fields (verify emitted PTX/SASS)'],'limits':['Absolute ns precision is not established: SM frequency/DVFS lacks authoritative per-interval provenance.','Clock64/globaltimer are different register counters; independent physical oscillators are not proved.','32ns margin is observed globaltimer granularity, not vendor-guaranteed error bound.','Probes perturb both operators.','No common calibration is used to transform clock64 into ns.'],'cases':summary}
(a.output/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
