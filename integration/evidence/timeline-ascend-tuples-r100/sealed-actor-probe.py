from pathlib import Path
import argparse,subprocess,json,hashlib,importlib.util
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
f=Path(__file__).parent/'regions.py';spec=importlib.util.spec_from_file_location('rules',f);rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
spec2=importlib.util.spec_from_file_location('cases',Path(__file__).parent/'cases.py');cases=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(cases);negative=[]
sealed=Path('/tmp/chijin-timeline-r099-ascend/runs/structure-v2/output/result.json').read_bytes()
if hashlib.sha256(sealed).hexdigest()!='db9199e99367b8c36b8b70ad15d618b1163d5d31ffbc85928e345db5618c5092':raise ValueError('Original native-index receipt changed')
ledger={(r['case'],r['actor']):r for r in json.loads(sealed)['actual']}
objects=json.loads(Path('/tmp/chijin-timeline-r091-ascend/runs/source-loop-inventory-v1/output/objects.json').read_text());out=[]
for k in ('q01','q03','q05'):
 obj=next(o for o in objects if o['first_case'].startswith(k));cap=json.loads(Path(obj['capture_file']).read_text());artifacts=cap['metadata']['compiler_metadata']['flagprism_ascend_handoff']['artifacts']
 for actor in obj['actor_inputs']:
  name=k+'-'+actor['actor_kind'];graph_bytes=Path('/tmp/chijin-timeline-r099-ascend/runs/structure-v2/output',name+'.log').read_bytes();graph=json.loads(graph_bytes);indexed=ledger[obj['first_case'],actor['actor_kind']]
  if hashlib.sha256(graph_bytes).hexdigest()!=indexed['index_sha256'] or hashlib.sha256(Path(actor['path']).read_bytes()).hexdigest()!=actor['sha256'] or actor['sha256']!=indexed['input_sha256'] or graph['input_sha256']!=actor['sha256']:raise ValueError('Actual graph/input differs from sealed native receipt')
  artifact=next(x for x in artifacts if any(t.get('actor_kind')==actor['actor_kind'] for t in x['metadata']['actors']));manifest=artifact['metadata']
  if artifact['adapted']['sha256']!=graph['input_sha256'] or hashlib.sha256(artifact['adapted']['llir'].encode()).hexdigest()!=graph['input_sha256']:raise ValueError('Compiler actor input differs from actual graph')
  entry=next(x for x in manifest['actors'] if x['actor_kind']==actor['actor_kind']);role=next(r for r in entry['argument_roles'] if r.get('role')=='dynamic_trace');result=rules.bind_record_endpoints(graph,manifest=manifest,function=entry['function'],trace_argument_index=role['final_formal_index']);(a.output/(name+'.json')).write_text(json.dumps(result,indent=2));out.append(dict(name=name,sites=len(result['regions']),bound=sum(x['status']=='llvm_tuple_endpoints_bound' for x in result['regions']),failures=[dict(site_id=x['site_id'],reason=x.get('reason')) for x in result['regions'] if x['status']!='llvm_tuple_endpoints_bound']))
  if not negative:negative=cases.check_negative_records(rules,graph,manifest=manifest,function=entry['function'],trace_argument_index=role['final_formal_index'])
(a.output/'result.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),actual=out,negative=negative,device_executed=False,source_loop_qualified=False),indent=2))
