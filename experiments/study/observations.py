"""Read native records, retaining source scope and reported units."""
import json
def read(path):return json.loads(path.read_text())
def native(case,backend):
 if backend=='cann':
  f=case/'profile.vendor.json'
  if not f.exists():return []
  return [{'name':e['runtime_event']['op_name'],'start_ns':e['runtime_event'].get('start_time_ns'), 'end_ns':e['runtime_event'].get('end_time_ns'),'duration_us':e['metrics'].get('task_duration_us'),'task_id':e['runtime_event'].get('task_id'),'kind':'kernel','source':e['source']} for e in read(f).get('associations',[]) if e.get('source')=='aclprof_op_summary' and e.get('state')=='collected']
 if backend=='cuda':
  f=case/'reference/trace.json'
  return [{'kind':'kernel','name':e['name'],'duration_us':e['dur'],'source':'torch.profiler / Kineto / CUPTI'} for e in read(f).get('traceEvents',[]) if e.get('cat')=='kernel' and e.get('ph')=='X'] if f.exists() else []
 f=case/'profile/ai/events.jsonl'
 return [json.loads(s) for s in f.read_text().splitlines()] if f.exists() else []
