"""Offline evidence table exporter for the exact NVIDIA-origin tail case."""
import json,csv,re,statistics,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'FlagPrism/experiments/study'))
from tcu_invocations import parse
root=Path(__file__).parent
rows=[];summary={'scope':'actual native-selected NVIDIA N, exactGCU P, config-guided R, alternatives retained','native':[],'probes':[],'tcu':[]}
for b in range(3):
 for w in [4,1,2]:
  d=root/'native'/f'b{b}-w{w}';r=json.loads((d/'result.json').read_text());assert r['status']=='passed' and r['validation']['passed'] and r['reference_device']=='cpu';es=[json.loads(x) for x in (d/'profile/ai/events.jsonl').read_text().splitlines()];ks=[e for e in es if e.get('kind')=='kernel' and e['name']=='rows'];assert len(ks)==30;assert all(e['metrics']['activity.block_x']==w and e['metrics']['activity.grid_x']==127 for e in ks)
  ir=(d/'asm/gcuir').read_text();ll=(d/'asm/llir').read_text();vals=[e['duration_us'] for e in ks]
  summary['native'].append({'batch':b,'work_items':w,'samples':30,'median_us':statistics.median(vals),'minimum_us':min(vals),'maximum_us':max(vals),'barriers':ir.count('"gpu.barrier"'),'local_bytes_per_item':int(re.search(r'gcu.local_memory_size = (\d+)',ll).group(1)),'shared_bytes':int(re.search(r'gcu.shared_memory_size = (\d+)',ll).group(1)),'source':str(d.relative_to(root)),'input_sha256':r['input_hashes'],'result_sha256':hashlib.sha256((d/'result.json').read_bytes()).hexdigest()})
  for i,e in enumerate(ks):rows.append({'batch':b,'work_items':w,'invocation':i,'duration_us':e['duration_us'],'source':str((d/'profile/ai/events.jsonl').relative_to(root)),'native_event_id':e['id'],'binary_id':e['binary_id']})
with (root/'uninstrumented-native.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
for w in [4,1,2]:
 d=root/f'brackets-w{w}';r=json.loads((d/'result.json').read_text());assert r['status']=='passed' and r['correct'] and r['post_correct'];ev=[json.loads(x) for x in (d/'profile/ai/events.jsonl').read_text().splitlines()];ks=[x for x in ev if x.get('kind')=='kernel' and 'softmax_reduce_trace' in x.get('name','')];assert len(ks)==15
 values=[[(s['records'][0][1]-s['records'][0][0])%2**32,(s['records'][0][3]-s['records'][0][2])%2**32] for s in r['samples']]
 summary['probes'].append({'work_items':w,'max_median_ticks':statistics.median(v[0] for v in values),'sum_median_ticks':statistics.median(v[1] for v in values),'task_median_us':statistics.median(e['duration_us'] for e in ks),'samples':15,'scope':'same-invocation program0/workitem0 source reductioncontrol-pathbrackets, rawSDKticks; not enginebusy or originalphasefraction','source':str(d.relative_to(root)),'barriers':(d/'asm/gcuir').read_text().count('"gpu.barrier"'),'local_memory_fences':(d/'asm/gcuir').read_text().count('"gcu.mfence"')})
 records=parse(root/'tcu'/f'w{w}'/'invocations.csv');assert len(records)==21
 for key in ['SIP/BUSY','SIP/1D_EFFICIENCY','SIP/MSF_EFFICIENCY']:
  ms=[m for t in records for m in t['metrics'] if m['name']==key];assert len(ms)==21 and all(len(m['instances'])==24 for m in ms)
  summary['tcu'].append({'work_items':w,'metric':key,'unit':ms[0]['unit'],'median_value':statistics.median(m['value'] for m in ms),'samples':21,'instances_per_record':24,'source':f'tcu/w{w}/invocations.csv','scope':'originalbinary applicationreplay, capture-localIDs;21include6initial/warmupcalls, not joinedtoTOPSPTI'})
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('verified all tail evidence')
