"""Finite actual native-loop diagnostic; no device or application execution."""
import argparse, importlib.util, json, sys
from collections import deque
from pathlib import Path
from flagtree.profiler import timeline_unit_nvidia_late as units
from flagtree.profiler.timeline_nvidia_control import _bound_functions
from flagtree.profiler.timeline_nvidia_late_values import _predecessors
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
name='flagtree.profiler._r071_boundaries';spec=importlib.util.spec_from_file_location(name,Path('/workspace/chijin-timeline-r071-nvidia/matrix-rule-input-v1/boundaries.py'));boundaries=importlib.util.module_from_spec(spec);sys.modules[name]=boundaries;spec.loader.exec_module(boundaries)
results=[]
for label,case in [('default','budget-pipeline-v1'),('sparse','sparse-pipeline-v1')]:
 root=Path('/workspace/chijin-timeline-r061-nvidia/runs')/case/'output/device/profile/timeline';entry=json.loads((root/'index.json').read_text())['captures'][0];capture=json.loads((root/entry['capture_file']).read_text());machine=units.load_late_machine_map(root,capture);base=root/'machine'/capture['owner']['binary_id'];text=(base/'lines.stdout').read_bytes();native=(base/'json.stdout').read_bytes();ptx=next(x for x in capture['metadata']['timeline_artifacts'] if x['retained_file'].endswith('.ptx'));report=boundaries.derive_native_boundaries(machine_map=machine,sass_lines=text,sass_json=native,ptx=(root/ptx['retained_file']).read_bytes(),plan=capture['owner']['plan']);functions=_bound_functions(machine,text,native)
 for site in report['matrix_issue_sites']:
  body=functions[site['function']];pred=_predecessors(body);succ={pc:set() for pc in pred}
  for pc,parents in pred.items():
   for parent in parents:succ[parent].add(pc)
  start=min(body);reachable=set();work=[start]
  while work:
   pc=work.pop()
   if pc in reachable:continue
   reachable.add(pc);work.extend(succ[pc])
  if len(reachable)>4096:raise RuntimeError('Native diagnostic size budget')
  pcs=sorted(reachable);index={pc:i for i,pc in enumerate(pcs)};full=(1<<len(pcs))-1;dom={pc:full for pc in pcs};dom[start]=1<<index[start];work=deque(pc for pc in pcs if pc!=start);queued=set(work);updates=0
  while work:
   pc=work.popleft();queued.remove(pc);common=full
   for parent in pred[pc]&reachable:common &= dom[parent]
   value=common|(1<<index[pc]);updates+=1
   if updates>1000000:raise RuntimeError('Native diagnostic convergence budget')
   if value!=dom[pc]:
    dom[pc]=value
    for nxt in succ[pc]:
     if nxt!=start and nxt in reachable and nxt not in queued:work.append(nxt);queued.add(nxt)
  loops={}
  for tail in pcs:
   for header in succ[tail]&reachable:
    if not dom[tail]&(1<<index[header]):continue
    loop=loops.setdefault(header,dict(nodes={header},latches=set()));loop['latches'].add(tail);stack=[tail]
    while stack:
     node=stack.pop()
     if node in loop['nodes']:continue
     loop['nodes'].add(node);stack.extend(pred[node]&reachable)
  begin,end=site['begin_reader_pc'],site['end_reader_pc'];candidates=[]
  for header,loop in loops.items():
   nodes=loop['nodes']
   if begin not in nodes or end not in nodes:continue
   exits=[(x,y) for x in nodes for y in succ[x] if y not in nodes]
   candidates.append(dict(header=header,latches=sorted(loop['latches']),nodes=len(nodes),exits=sorted(exits),begin_dominates_latches=all(dom[x]&(1<<index[begin]) for x in loop['latches']),end_dominates_latches=all(dom[x]&(1<<index[end]) for x in loop['latches']),end_dominates_exit_sources=all(dom[x]&(1<<index[end]) for x,_ in exits)))
  results.append(dict(case=label,binary_id=capture['owner']['binary_id'],site_id=site['site_id'],begin=begin,end=end,reachable_instructions=len(pcs),dom_updates=updates,enclosing_loops=candidates))
(a.output/'result.json').write_text(json.dumps(dict(results=results,device_executed=False,application_replayed=False,loop_qualification_granted=False),indent=2))
