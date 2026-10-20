from pathlib import Path
import argparse,subprocess,json,hashlib,base64
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
tool=Path('/tmp/chijin-timeline-r100-ascend/runs/structure-v1/output/build/flagprism-ascend-structure')
if hashlib.sha256(tool.read_bytes()).hexdigest()!='d0e82b1fdc5fc322c322bc80c44a9e5e552afc5918174e2ba0f9504cc7a99d61':raise ValueError('Current read-only index tool changed')
objects=json.loads(Path('/tmp/chijin-timeline-r091-ascend/runs/source-loop-inventory-v1/output/objects.json').read_text());results=[]
for k in ('q01','q03','q05'):
 obj=next(x for x in objects if x['first_case'].startswith(k));cap=json.loads(Path(obj['capture_file']).read_text());artifacts=cap['metadata']['compiler_metadata']['flagprism_ascend_handoff']['artifacts']
 for i,artifact in enumerate(artifacts):
  raw=base64.b64decode(artifact['original_input']['data'],validate=True)
  if hashlib.sha256(raw).hexdigest()!=artifact['original_input']['sha256']:raise ValueError('Retained original actor input identity differs')
  dest=a.output/(k+'-'+str(i)+'.original.ll');dest.write_bytes(raw)
  with (a.output/(k+'-'+str(i)+'.original.json')).open('xb') as stdout,(a.output/(k+'-'+str(i)+'.stderr')).open('xb') as stderr:c=subprocess.run([str(tool),str(dest)],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=20)
  if c.returncode:raise ValueError('Original actor parsing failed')
  graph=json.loads((a.output/(k+'-'+str(i)+'.original.json')).read_text())
  if graph['input_sha256']!=artifact['original_input']['sha256']:raise ValueError('Original graph input identity differs')
  manifest=artifact['metadata'];entries=[x['function'] for x in manifest['actors']];carriers=[]
  for f in graph['functions']:
   if f['name'] not in entries:continue
   for b in f['blocks']:
    for inst in b['instructions']:
     asm=inst.get('assembly','')
     if 'flagprism.source_census_site.v3:' in asm:carriers.append(dict(function=f['name'],block_id=b['id'],instruction_id=inst['id'],assembly=asm))
  results.append(dict(case=obj['first_case'],artifact_index=i,input_sha256=graph['input_sha256'],graph_sha256=hashlib.sha256((a.output/(k+'-'+str(i)+'.original.json')).read_bytes()).hexdigest(),entries=entries,original_carriers=carriers,manifest_source_fragments=sum(s['semantic_code']==1 for s in manifest['dynamic_sites'])))
(a.output/'result.json').write_text(json.dumps(dict(status='original_actor_structure_indexed',tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),objects=results,device_executed=False,SDK_recompiled=False,source_loop_qualified=False),indent=2))
