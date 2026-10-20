"""Read-only matching LLVM and raw inspection after one public q05 call."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
root = Path('/tmp/chijin-timeline-r101-ascend')
public = root/'runs/public-q05-v1'
if json.loads((public/'terminal.json').read_text())['returncode'] != 0:
    raise ValueError('Public job did not pass')
capture = json.loads((public/'output/expanded-capture.json').read_text())
batch = json.loads((public/'output/fresh-batch.json').read_text())
compiler = capture['metadata']['compiler_metadata']
plan = compiler['debug_automatic_plan']
selected = {i['opId'] for i in plan['inventory'] if i['selected']}
dots = {i['opId'] for i in plan['inventory'] if i['mlirOpName']=='tt.dot' and i['selected']}
mode = json.loads(compiler['instrumentation_mode'].split('|config=', 1)[1])
if mode.get('debug_timeline_selection_policy_version') != 1 or not dots:
    raise ValueError('Installed public policy/selection differs')
tool = Path('/tmp/chijin-timeline-r100-ascend/runs/structure-v1/output/build/flagprism-ascend-structure')
sha = lambda b: hashlib.sha256(b).hexdigest()
if sha(tool.read_bytes()) != 'd0e82b1fdc5fc322c322bc80c44a9e5e552afc5918174e2ba0f9504cc7a99d61':
    raise ValueError('Read-only tool changed')
from flagtree.profiler.timeline_ascend_regions import bind_record_endpoints
rows=[]
for number, artifact in enumerate(compiler['flagprism_ascend_handoff']['artifacts']):
    graphs={}
    for kind in ('original','adapted'):
        spec=artifact['original_input' if kind=='original' else 'adapted']
        raw=base64.b64decode(spec['data'],validate=True) if kind=='original' else spec['llir'].encode()
        if sha(raw)!=spec['sha256']:
            raise ValueError('Actor input identity differs')
        path=a.output/(str(number)+'.'+kind+'.ll');path.write_bytes(raw)
        dest=path.with_suffix('.json')
        with dest.open('xb') as out,(path.with_suffix('.stderr')).open('xb') as err:
            subprocess.run([str(tool),str(path)],stdout=out,stderr=err,check=True,timeout=20)
        graph=json.loads(dest.read_text())
        if graph['input_sha256']!=spec['sha256']:raise ValueError('Indexed actor identity differs')
        graphs[kind]=graph
    manifest=artifact['metadata']
    for actor in manifest['actors']:
        name=actor['function']
        trace=[r['final_formal_index'] for r in actor['argument_roles'] if r.get('role')=='dynamic_trace']
        if len(trace)!=1:raise ValueError('Trace role ambiguous')
        binding=bind_record_endpoints(graphs['adapted'],manifest=manifest,function=name,trace_argument_index=trace[0])
        original=next(f for f in graphs['original']['functions'] if f['name']==name)
        adapted=next(f for f in graphs['adapted']['functions'] if f['name']==name)
        for site in manifest['dynamic_sites']:
            if site['semantic_code']!=1 or site.get('source_op_id') not in dots:continue
            fragments=[]
            for block in original['blocks']:
                insts=block['instructions']
                for pos,inst in enumerate(insts):
                    asm=inst.get('assembly','')
                    match=re.fullmatch(r'/\* flagprism.source_census_site.v3:(\d+):\d+:\d+ \*/',asm)
                    if not match or int(match[1])!=site['source_op_id']:continue
                    body=[]
                    for value in insts[pos+1:]:
                        if 'flagprism.source_census_site.v3:' in value.get('assembly','') or value['opcode'] in ('br','ret','switch','unreachable'):break
                        body.append(value)
                    fragments.append(dict(block=block['id'],carrier_id=inst['id'],body_ids=[x['id'] for x in body],calls=[dict(id=x['id'],callee=x['callee']) for x in body if x.get('callee')]))
            record=next(r for r in binding['regions'] if r['site_id']==site['site_id'])
            canonical=[s for s in batch['sites'] if s['attributes'].get('ascend.source_op_id')==site['source_op_id'] and s['attributes'].get('ascend.source_op_id')==site['source_op_id']]
            site_ids={s['id'] for s in canonical}
            events=[e for e in batch['events'] if e['kind']=='interval' and e['site_id'] in site_ids and next(o for o in batch['observers'] if o['id']==e['observer_id'])['attributes'].get('ascend.function')==name]
            if not events:raise ValueError('Selected source fragment has no actual interval')
            mma_ids=[i['id'] for b in adapted['blocks'] for i in b['instructions'] if i.get('callee')=='mma_tile_half_to_float']
            edges={}
            loopbacks={(latch,loop['header']) for loop in adapted['loops'] for latch in loop['latches']}
            blocks={b['id']:b for b in adapted['blocks']}
            for block in adapted['blocks']:
                values=block['instructions']
                for left,right in zip(values,values[1:]):edges[left['id']]=[right['id']]
                edges[values[-1]['id']]=[blocks[succ]['instructions'][0]['id'] for succ in block['successors'] if (block['id'],succ) not in loopbacks]
            def reaches(begin,end):
                pending=[begin];seen=set()
                while pending:
                    current=pending.pop()
                    if current==end:return True
                    if current in seen:continue
                    seen.add(current);pending.extend(edges.get(current,[]))
                return False
            mma_paths=[dict(call_id=i,begin_to_call=reaches(record['begin_id'],i),call_to_end=reaches(i,record['end_id'])) for i in mma_ids] if record['status']=='llvm_tuple_endpoints_bound' else []
            rows.append(dict(mma_paths_without_loop_backedge=mma_paths,actor=name,actor_kind=actor['actor_kind'],site_id=site['site_id'],source_op_id=site['source_op_id'],fragments=fragments,manifest_body_sha256=site['original_instructions_sha256'],manifest_body_bytes=len(site['original_instructions'].encode()),tuple=record,actual_events=len(events),positive_events=sum(e['end_tick']>e['start_tick'] for e in events),observer_count=len({e['observer_id'] for e in events}),adapted_calls=[dict(block=b['id'],id=i['id'],callee=i['callee']) for b in adapted['blocks'] for i in b['instructions'] if i.get('callee') and 'mma' in i['callee'].lower()]))
(a.output/'result.json').write_text(json.dumps(dict(status='selected_dot_actual_actor_inspected',selected_ids=sorted(selected),selected_dot_ids=sorted(dots),policy_version=mode['debug_timeline_selection_policy_version'],rows=rows,source_boundary_qualified=False,native_schedule_qualified=False,device_executed=False,SDK_recompiled=False),indent=2))
