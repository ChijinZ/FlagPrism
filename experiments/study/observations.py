"""Read native records, retaining source scope and reported units."""
import json
def read(path):return json.loads(path.read_text())
def native(case,backend):
 if backend=='cann':
  f=case/'profile.vendor.json'
  if not f.exists():return []
  return [{'name':e['runtime_event']['op_name'],'start_ns':e['runtime_event'].get('start_time_ns'), 'end_ns':e['runtime_event'].get('end_time_ns'),'duration_us':e['metrics'].get('task_duration_us'),'task_id':e['runtime_event'].get('task_id'),'kind':'kernel','source':e['source']} for e in read(f).get('associations',[]) if e.get('source')=='aclprof_op_summary' and e.get('state')=='collected']
 if backend=='cuda':
  vendor=case/'profile.vendor.json'
  if vendor.exists():
   events=[]
   for e in read(vendor).get('associations',[]):
    rt=e.get('runtime_event',{})
    if e.get('source')=='cupti_activity' and e.get('state')=='collected' and rt.get('start_time_ns') and rt.get('end_time_ns'):
     events.append({'kind':'kernel','name':rt.get('op_name'),'duration_us':(rt['end_time_ns']-rt['start_time_ns'])/1000,'source':'FlagPrism / CUPTI','start_ns':rt['start_time_ns'],'end_ns':rt['end_time_ns']})
   return events
  f=case/'reference/trace.json'
  return [{'kind':'kernel','name':e['name'],'duration_us':e['dur'],'source':'torch.profiler / Kineto / CUPTI'} for e in read(f).get('traceEvents',[]) if e.get('cat')=='kernel' and e.get('ph')=='X'] if f.exists() else []
 f=case/'profile/ai/events.jsonl'
 return [json.loads(s) for s in f.read_text().splitlines()] if f.exists() else []
