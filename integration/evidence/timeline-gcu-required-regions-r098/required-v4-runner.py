"""Derive frozen structural obligations before reading checker outcomes."""
import argparse
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True)
payload = Path(__file__).parent
objects = json.loads((payload/'objects.json').read_text())
rows = json.loads((payload/'rows.json').read_text())
source_tables = {}
plans = []
tool = Path('/tmp/chijin-timeline-r097-gcu/runs/normal-install-v1/output/native/flagtree/debugger/_bin/gcu-timeline')
if hashlib.sha256(tool.read_bytes()).hexdigest() != '374ab5f9fd07e2c5c7e8ec32f82365fa5c98e5736fd36648b3ee96b7263bf8d4':
    raise ValueError('Installed original-member producer changed')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def origins(location):
    return {(p, int(n)) for p,n in re.findall(r'"((?:[^"\\\n]|\\.)*)":(\d+):\d+', location)}

def call(node, name):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == name and isinstance(node.func.value, ast.Name) and node.func.value.id == 'tl'

def stages(kernel):
    source = payload/('supplement-kernels.py' if kernel in ('q07','q08') else 'kernels.py')
    prepared = payload/('supplement-prepare-manifest.json' if kernel in ('q07','q08') else 'prepare_manifest.json')
    source_freeze = json.loads(prepared.read_text())
    if sha(source.read_bytes())!=source_freeze['files_sha256']['kernels.py']:raise ValueError('Preregistered mathematics source changed')
    module = ast.parse(source.read_text())
    function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == kernel)
    loops = [n for n in function.body if isinstance(n, ast.For)]
    output = next(n for n in function.body if isinstance(n, ast.Expr) and call(n.value, 'store') and any(isinstance(x, ast.Name) and x.id == 'Out' for x in ast.walk(n.value.args[0])))
    if loops:
        if len(loops) != 1: raise ValueError('Expected one registered mathematical loop')
        loop = loops[0]
        body_lines = list(range(loop.body[0].lineno,loop.end_lineno+1))
        contractions = [n for n in ast.walk(loop) if call(n,'dot')]
        reductions = [n for n in ast.walk(loop) if call(n,'sum')]
        if contractions:
            body_lines = sorted({n.lineno for n in contractions})
        elif reductions:
            body_lines = [max(n.lineno for n in reductions)]
        first = dict(name='runtime_body' if kernel in ('q01','q02') else 'Ktile_body', lines=body_lines, loop_required=True, runtime_input=kernel in ('q01','q02'), contraction=bool(contractions))
    else:
        reductions = [n for n in function.body if any(call(x,'sum') for x in ast.walk(n))]
        if not reductions: raise ValueError('Missing registered reduction')
        first = dict(name='reduction_body',lines=[max(n.lineno for n in reductions)],loop_required=False,runtime_input=False)
    second_lines = list(range(output.lineno,output.end_lineno+1))
    value = output.value.args[1]
    if isinstance(value, ast.Name) and loops:
        assignment = next((n for n in function.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == value.id for t in n.targets) and loops[0].end_lineno < n.lineno < output.lineno),None)
        if assignment is not None: second_lines = list(range(assignment.lineno,assignment.end_lineno+1))
    second = dict(name='dependent_epilogue_or_output_issue',lines=second_lines,loop_required=False,runtime_input=False)
    return dict(source_sha256=sha(source.read_bytes()),function=kernel,source_file=str(source),stages=[first,second])

# No checker module, status or event occurrence count is used in this phase.
for obj in objects:
    n = obj['object_index']
    cap_path = Path(obj['capture_file'])
    cap_bytes = cap_path.read_bytes()
    cap = json.loads(cap_bytes)
    row = next(r for r in rows if r['capture_file'] == str(cap_path))
    if sha(cap_bytes) != row['capture_sha256']: raise ValueError('Frozen capture changed')
    meta = cap['metadata']['compiler_metadata']
    before = Path(row['original_before_file'])
    if sha(before.read_bytes()) != row['before_sha256'] or row['before_sha256'] != meta['debug_execution_input_sha256']: raise ValueError('Original source IR changed')
    if sha(Path(row['original_after_file']).read_bytes())!=row['after_sha256'] or meta['debug_execution_output_sha256']!=row['after_sha256']:raise ValueError('Original instrumented IR changed')
    binary = base64.b64decode(cap['metadata']['compiled_snapshot']['binary_base64'],validate=True)
    ir = cap['metadata']['compiled_snapshot']['compiler_artifacts']['llir'].encode()
    if sha(binary) != obj['binary_sha256'] or sha(ir) != obj['artifacts']['llir']['sha256']: raise ValueError('Actual execution object changed')
    manifest = meta['debug_execution_manifest']
    dest = args.output/(str(n)+'.origins.json')
    child = subprocess.run([str(tool),'--execution-origins',str(before),str(dest),str(manifest['selected_source_regions'])],capture_output=True,timeout=20)
    (args.output/(str(n)+'.origin.stderr')).write_bytes(child.stderr)
    if child.returncode: raise ValueError('Original producer indexing failed '+str(n))
    original = json.loads(dest.read_text())
    fields = ('id','kind','operation','location')
    if [tuple(x[k] for k in fields) for x in original['sites']] != [tuple(x[k] for k in fields) for x in manifest['sites']]: raise ValueError('Original selection/site identity changed')
    census = meta['debug_execution_source_tracked_table']
    census_by_id = {x['opId']:x for x in census}
    kernel = obj['first_case'].split('-')[0]
    spec = stages(kernel)
    required = []
    chosen = set()
    for stage in spec['stages']:
        ids = {x['opId'] for x in census if any(line in stage['lines'] for _,line in origins(x.get('sourceLoc',''))) and not x.get('isSyntheticStatementCapture')}
        target_locations = set().union(*(origins(census_by_id[x].get('sourceLoc','')) for x in ids)) if ids else set()
        repeated_controls = sorted({(c['controlId'],c['parentOpId']) for x in ids for c in census_by_id[x].get('controlFlowAncestors',[]) if c.get('repeated') and c.get('operation') == 'scf.for'})
        candidates = []
        for site in original['sites']:
            if stage.get('contraction') and site['operation']!='gcu.matmul':continue
            membership = site['source_membership']
            if membership['status'] != 'original_execution_members_indexed': continue
            members = membership['members']
            shared_ids = sorted({x['source_op_id'] for x in members} & ids)
            coordinates = {(x['file'],x['line']) for x in members if type(x.get('file')) is str and type(x.get('line')) is int}
            if not shared_ids and not coordinates.intersection(target_locations): continue
            # Source scf membership is required for a mathematical loop body;
            # a hoisted expression with the same source line cannot stand in.
            controls = membership['enclosing_controls']
            if stage['loop_required'] and not any(x['operation']=='scf.for' for x in controls): continue
            if stage['name'] == 'reduction_body' and site['kind'] not in (3,5): continue
            if stage['loop_required'] and site['kind'] not in (3,5): continue
            rank = 0 if site['kind']==5 else 1 if site['kind']==3 else 2
            candidates.append(dict(site_id=site['id'],kind=site['kind'],operation=site['operation'],rank=rank,source_member_ids=shared_ids,controls=controls,locations=sorted([list(x) for x in coordinates.intersection(target_locations)])))
        candidates.sort(key=lambda x:(x['rank'],x['site_id']))
        selected = next((x for x in candidates if x['site_id'] not in chosen),None)
        family=[x for x in candidates if selected and x['kind']==selected['kind'] and x['operation']==selected['operation'] and x['site_id'] not in chosen]
        chosen.update(x['site_id'] for x in family)
        required.append(dict(**stage,census_source_op_ids=sorted(ids),census_controls=[dict(control_id=x,parent_op_id=y) for x,y in repeated_controls],candidates=candidates,selected=selected,selected_producer_family=family))
    plans.append(dict(object_index=n,case=obj['first_case'],capture_sha256=sha(cap_bytes),before_sha256=row['before_sha256'],binary_sha256=sha(binary),llvm_sha256=sha(ir),source_spec=spec,original_manifest_sha256=sha(json.dumps(manifest,sort_keys=True).encode()),origin_index_sha256=sha(dest.read_bytes()),census_sha256=sha(json.dumps(census,sort_keys=True).encode()),required_obligations=required))
    source_tables[n]=(cap,original)
plan = dict(schema_version=1,derivation_rule='frozen_math_AST_role_then_original_producer_split_family_v2',selection_uses_checker_results=False,selection_uses_dynamic_occurrences=False,registry_sha256=sha((payload/'registry.json').read_bytes()),supplement_registry_sha256=sha((payload/'supplement-registry.json').read_bytes()),objects=plans)
plan_path = args.output/'required-plan.json'
plan_path.write_text(json.dumps(plan,indent=2))
plan_sha = sha(plan_path.read_bytes())

from flagtree.debugger import gcu_llvm_regions
ledger_bytes=(payload/'typed-index-ledger.json').read_bytes()
if sha(ledger_bytes)!='c18ab8855121a87e054d9fe21c4a5f76f77d7957bd0f96e0a034896c8002042e':raise ValueError('Original typed-index receipt changed')
index_ledger={x['object_index']:x for x in json.loads(ledger_bytes)['objects']}
results = {}
for obj in objects:
    n = obj['object_index']
    cap,original=source_tables[n]
    enriched=copy.deepcopy(cap['metadata']['compiler_metadata']['debug_execution_manifest'])
    for site,source in zip(enriched['sites'],original['sites']): site['source_membership']=source['source_membership']
    path=Path('/tmp/chijin-timeline-r096-gcu/runs/regions-v1/output')/(str(n)+'.structure.json')
    actual_ir=cap['metadata']['compiled_snapshot']['compiler_artifacts']['llir'].encode()
    if path.with_name(str(n)+'.mlir').read_bytes()!=actual_ir: raise ValueError('Typed graph input changed')
    indexed=index_ledger[n]
    if indexed['llvm_sha256']!=sha(actual_ir) or indexed['binary_sha256']!=obj['binary_sha256'] or sha(path.read_bytes())!=indexed['typed_index_sha256']:raise ValueError('Actual typed-index bytes differ from original sealed receipt')
    result=gcu_llvm_regions.analyze_regions(json.loads(path.read_text()),enriched)
    (args.output/(str(n)+'.regions.json')).write_text(json.dumps(result,indent=2))
    results[n]={x['site_id']:x for x in result['regions']}

object_by_key={(o['binary_sha256'],o['artifacts']['llir']['sha256']):o['object_index'] for o in objects}
case_results=[]
for row in rows:
    cap_path=Path(row['capture_file']);cap_bytes=cap_path.read_bytes();cap=json.loads(cap_bytes)
    if sha(cap_bytes)!=row['capture_sha256']: raise ValueError('Capture identity changed during join')
    raw_path=cap_path.parent.parent/cap['raw_file'];raw=raw_path.read_bytes()
    from flagtree.profiler.timeline_events import stable_id
    from flagtree.profiler.timeline_events_enflame_native import decode_execution_capture
    association=cap['launch'];owner=cap['owner']
    identity=dict(capture_id=owner['capture_id'],invocation_id=stable_id((owner['capture_id'],),'enflame-invocation',association['invocation_id'],association['scope_id'],sorted(association['session_ids'])),binary_id=owner['binary_id'])
    if cap['metadata']['compiler_metadata']['hash']!=owner['binary_id']:raise ValueError('Capture binary association differs')
    batch=decode_execution_capture(raw,compiler_metadata=cap['metadata']['compiler_metadata'],identity=identity,association=association,grid=owner['layout']['grid'])['canonical']
    if not batch['complete'] or any(not observer['complete'] or observer['retained_records']<=0 for observer in batch['observers']):raise ValueError('Missing complete default-selected observer records')
    if sha(raw)!=cap['raw_sha256'] or sha(raw)!=batch['raw_artifact']['sha256']: raise ValueError('Raw identity changed')
    ir=cap['metadata']['compiled_snapshot']['compiler_artifacts']['llir'].encode();binary=base64.b64decode(cap['metadata']['compiled_snapshot']['binary_base64'],validate=True)
    n=object_by_key[(sha(binary),sha(ir))];p=plans[n]
    meta=cap['metadata']['compiler_metadata']
    if meta['debug_execution_input_sha256']!=p['before_sha256'] or sha(json.dumps(meta['debug_execution_manifest'],sort_keys=True).encode())!=p['original_manifest_sha256']: raise ValueError('Capture producer differs from object plan')
    sites={x['id']:x for x in batch['sites']};records={x['id']:x for x in batch['records']};bindings=[]
    for obligation in p['required_obligations']:
        family=obligation['selected_producer_family'];failures=[];site_bindings=[];all_witnesses=[]
        if not family:failures.append('no_original_producer_candidate_for_required_stage')
        for member in family:
            region=results[n][member['site_id']]
            matching=[x for x in batch['events'] if sites[x['site_id']]['backend_site_id']==str(member['site_id'])]
            # A split source region can lower to different per-owner branches.
            # Keep the whole preselected same-operation family, recording which
            # branches actually appear in the complete selected raw scope.
            if not matching:
                site_bindings.append(dict(site_id=member['site_id'],observation='not_observed_in_complete_selected_scope',rule=region,raw_witnesses=[]))
                continue
            if region['status']!='llvm_observer_boundary_checked':failures.append('site'+str(member['site_id'])+':region:'+str(region.get('reason')))
            loop=region.get('loop') or {}
            expected_loop='llvm_runtime_iteration_checked' if obligation['runtime_input'] else 'llvm_constant_iteration_checked'
            if obligation['loop_required'] and loop.get('status')!=expected_loop:failures.append('site'+str(member['site_id'])+':loop:'+str(loop))
            witnesses=[]
            for observer in batch['observers']:
                events=[x for x in matching if x['observer_id']==observer['id']]
                if events and obligation['runtime_input'] and len(events)!=3:failures.append('device_K3_body_occurrence_mismatch')
                if events and obligation['loop_required'] and not obligation['runtime_input'] and loop.get('status')=='llvm_constant_iteration_checked' and len(events)!=loop['constant_trip_count']:failures.append('constant_Ktile_body_occurrence_mismatch')
                for event in events:
                    refs=[records[k] for k in event['record_ids']]
                    if len(refs)!=2 or [x['phase'] for x in refs]!=['entry','exit']:raise ValueError('Wrong raw pair')
                    for record in refs:
                        if struct.unpack_from('<Q',raw,record['offset'])[0]!=record['tick']:raise ValueError('Actual raw tick mismatch')
                    if event['end_tick']<event['start_tick'] or event['start_tick']!=refs[0]['tick'] or event['end_tick']!=refs[1]['tick'] or any(r['observer_id']!=event['observer_id'] or r['site_id']!=event['site_id'] for r in refs):raise ValueError('Actual raw endpoint association differs')
                    witnesses.append(dict(event_id=event['id'],observer_id=observer['id'],record_ids=event['record_ids'],offsets=[x['offset'] for x in refs],ticks=[x['tick'] for x in refs],positive=event['end_tick']>event['start_tick']))
            all_witnesses.extend(witnesses)
            site_bindings.append(dict(site_id=member['site_id'],observation='actual_raw_intervals',rule=region,raw_witnesses=witnesses))
        if not all_witnesses:failures.append('missing_required_source_stage_interval')
        if obligation['loop_required'] and any(not any(w['observer_id']==o['id'] for w in all_witnesses) for o in batch['observers']):failures.append('missing_mathematical_body_for_selected_observer')
        bindings.append(dict(name=obligation['name'],site_id=family[0]['site_id'] if family else None,preselected_family=[x['site_id'] for x in family],site_bindings=site_bindings,uncovered=failures))
    if sum(x['end_tick']>x['start_tick'] for x in batch['events'])<2:raise ValueError('No multiple positive raw intervals')
    case_results.append(dict(canonical_redecoded_from_original_raw=True,case=row['case'],capture_sha256=row['capture_sha256'],raw_sha256=sha(raw),object_index=n,source_spec_sha256=p['source_spec']['source_sha256'],bindings=bindings,structural_join_covered=all(not b['uncovered'] for b in bindings),native_schedule_qualified=False))
if sha(plan_path.read_bytes())!=plan_sha:raise ValueError('Required plan changed after checker results')
(args.output/'result.json').write_text(json.dumps(dict(status='frozen_structural_obligations_joined_to_actual_raw',required_plan_sha256=plan_sha,producer_tool_sha256=sha(tool.read_bytes()),region_implementation_sha256=sha(Path(gcu_llvm_regions.__file__).read_bytes()),object_count=len(objects),case_count=len(rows),covered_cases=sum(r['structural_join_covered'] for r in case_results),cases=case_results,device_executed=False,application_replayed=False,native_schedule_qualified=False),indent=2))
