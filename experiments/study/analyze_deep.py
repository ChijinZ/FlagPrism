#!/usr/bin/env python3
"""Audit measured cases and export non-tautological comparisons and scope limits."""
import argparse,csv,json,statistics,hashlib,collections,importlib.util,shutil
from pathlib import Path
from observations import native,read
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
rows=[];clock=[];hashgroups=collections.defaultdict(list)
for backend,folder in [('cann','ascend'),('enflame','enflame'),('cuda','cuda')]:
 root=a.root/folder
 for f in sorted((root/'full').glob('*/result.json')):
  d=read(f);assert d['status']=='passed' and d['validation']['passed'];key=(d['operator'],tuple(d['shape']),d['variant'],d['phase']);hashgroups[key].append(d['input_hashes'])
 nested=root/('clock' if backend=='cuda' else 'nested');ref=root/('clock' if backend=='cuda' else 'reference')
 for q in [0,32,64,96,128]:
  base=nested/(f'q{q}-both' if backend=='cuda' else f'q{q}');bf=base/'result.json'
  if not bf.exists():continue
  bd=read(bf);assert bd['status']=='passed' and bd['correct']
  for region in ['outer','inner']:
   rf=ref/f'q{q}-{region}'/'result.json'
   if not rf.exists():continue
   rd=read(rf);assert rd['status']=='passed' and rd['correct'];field='delta_ticks_mod32' if region=='outer' else 'inner_delta_ticks_mod32'
   bvals=[x[field] for x in bd['samples']];rvals=[x[field] for x in rd['samples']];bmed=statistics.median(bvals);rmed=statistics.median(rvals)
   rows.append({'backend':backend,'q':q,'region':region,'total_fma_iterations':256,'inner_fma_iterations':128,'baseline_median':bmed,'reference_median':rmed,'ratio':bmed/rmed,'relative_difference':(bmed-rmed)/rmed,'baseline_min':min(bvals),'baseline_max':max(bvals),'reference_min':min(rvals),'reference_max':max(rvals),'unit':'SYS_CNT_ticks' if backend=='cann' else ('globaltimer_ns' if backend=='cuda' else 'SDK_counter_units_unverified'),'baseline_file':str(bf),'reference_file':str(rf),'scope':'barrier-delimited bracket; not engine busy time','reference_independence':'separate capture with one active region, same vendor clock primitive; not an independent physical clock'})
 for f in sorted((root/'endpoint-v2').glob('*/result.json')):
  d=read(f)
  if d['status']!='passed':continue
  vals=[x['delta_ticks_mod32'] for x in d['samples']];dur=[e['duration_us'] for e in native(f.parent,backend) if e.get('kind')=='kernel' and e.get('duration_us') is not None]
  clock.append({'backend':backend,'loops':d['loops'],'sync':d['sync'],'median_ticks':statistics.median(vals),'min_ticks':min(vals),'max_ticks':max(vals),'native_kernel_or_task_median_us':statistics.median(dur) if dur else None,'result_file':str(f)})
assert len(hashgroups)==72 and all(len(v)==3 and len({tuple(x) for x in v})==1 for v in hashgroups.values()),'Input identity audit failed'
def write(name,data):
 with (a.output/name).open('w') as f:
  w=csv.DictWriter(f,lineterminator='\n',fieldnames=list(dict.fromkeys(k for r in data for k in r)));w.writeheader();w.writerows(data)
write('nested_comparison.csv',rows);write('clock_calibration.csv',clock)
info={'matched_input_groups':len(hashgroups),'byte_identical_across_three_backends':True,'nested_comparison_rows':len(rows),'baseline_description':'generic timestamp-style subtraction of two nested vendor begin/end pairs; not a reproduction of Proton, KPerfIR or TCU','reference_description':'same mathematical work and final-output checks; a separate capture enables exactly one requested interval; same hardware primitive, independently selected endpoints','limits':['Different probes alter execution; these are instrumented barrier-delimited intervals, not unperturbed busy times.','No cross-core clock alignment assumed.','GCU counter conversion to ns has not been verified.','Cross-run invocation identity is not inferred from kernel names.','Three backends do not by themselves establish a same-SIMT-model multi-vendor result.']}
(a.output/'deep-audit.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info))
# Retain individual probe observations so compact bundles can be audited offline.
probe_captures=0
for folder in ['ascend','enflame','cuda']:
 for sub in (['clock'] if folder=='cuda' else ['nested','reference','endpoint-v2']):
  for f in sorted((a.root/folder/sub).glob('*/result.json')):
   d=read(f);assert d['status']=='passed' and d['correct'] and len(d['samples'])==15
   b={'ascend':'cann','enflame':'enflame','cuda':'cuda'}[folder]
   ev=[e for e in native(f.parent,b) if e['kind']=='kernel' and e.get('duration_us') is not None]
   assert len(ev)==15 and all(e['duration_us']>0 for e in ev)
   probe_captures+=1
   dest=a.output/'region_probes'/folder/sub/f.parent.name/'result.json'
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
info['region_probe_captures_audited']=probe_captures
info['region_probe_positive_native_intervals']=probe_captures*15
(a.output/'deep-audit.json').write_text(json.dumps(info,indent=2)+'\n')
if all((a.root/b/'endpoint-v2/n64-s0/result.json').exists() for b in ['ascend','enflame']):
 evidence=a.output/'evidence';evidence.mkdir(exist_ok=True);audit=[]
 for sync in [0,1]:
  c=next((a.root/f'ascend/endpoint-v2/n64-s{sync}').rglob('kernel.npuir.mlir')).read_text()
  g=(a.root/f'enflame/endpoint-v2/n64-s{sync}/asm/llir').read_text()
  assert c.count('SYS_CNT')==2 and c.count('PIPE_ALL')==2+sync
  assert g.count('callee = @tops_clock_begin')==1 and g.count('callee = @tops_clock_end')==1
  assert g.count('callee = @tops_syncthreads')==1+sync
  audit.append({'sync':sync,'ascend_SYS_CNT':2,'ascend_PIPE_ALL':c.count('PIPE_ALL'),'gcu_begin_calls':1,'gcu_end_calls':1,'gcu_syncthreads':g.count('callee = @tops_syncthreads')})
  for b,t,suffix in [('ascend',c,'hivm.mlir'),('enflame',g,'llvm.mlir')]:
   (evidence/f'{b}-endpoint-n64-s{sync}.{suffix}').write_text(t.rstrip("\n")+"\n")
 (a.output/'endpoint_ir_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 g=(a.root/'enflame/nested/q64/asm/llir').read_text()
 assert g.count('callee = @tops_clock_begin')==2 and g.count('callee = @tops_clock_end')==2
 (evidence/'gcu-nested-q64.llvm.mlir').write_text(g.rstrip("\n")+"\n")
