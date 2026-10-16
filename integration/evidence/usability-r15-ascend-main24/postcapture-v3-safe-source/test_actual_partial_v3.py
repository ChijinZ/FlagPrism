"""Finite CPU checks of actual standalone/mixed proof; existing profile bytes only."""
import ast,copy,json,sys
from pathlib import Path
R=Path('/tmp/chijin-r15-independent-qualification');sys.path[:0]=[str(R/'postcapture-v3'),str(R/'final'),str(R/'original_qualification')]
from authorization_r15 import require,sha,load
from c1_ascend_actor_join_r13 import compiler_proof
from c1_ascend_frontend_r13 import frontend
from derive_ownership_v3 import bind_and_prove
from standalone_execution_r15 import prove_standalone,verify_standalone_sum
rows=[]
for scope in ['main24','finite2']:
    q=sorted((R/f'run-{scope}').glob('profile/*/*/qualification.json'))[0];v=load(q);b=load(q.parent/'bundle/ai/binaries.json')[0];bundle=q.parent/'bundle';actual=load(q.parent/'receipt.json');source=bundle/b['source']['file_snapshot_file'];require(sha(source)==b['source']['file_sha256'],'source hash');fn=next(f for f in ast.walk(ast.parse(source.read_bytes())) if isinstance(f,ast.FunctionDef) and f.name==v['case']);state_index=[a.arg for a in fn.args.args].index('State');store=next(n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='store' and n.args and any(isinstance(x,ast.Name) and x.id=='State' for x in ast.walk(n.args[0])));cp=compiler_proof(bundle,b,frontend_proof=frontend);sites={s['site'] for s in cp['sites'] if s['operation'] in ['tt.store','arith.addi'] and any(l['file']==b['source']['path'] and store.lineno<=l['line']<=store.end_lineno for l in s['origin']['source_locations'])};operations={s['site']:s['operation'] for s in cp['sites'] if s['site'] in sites};standalone=None
    if scope=='main24':standalone=prove_standalone(bundle,b,actual,R/f'run-{scope}/profile-cache'/q.parent.parent.name,Path('/tmp/chijin-r15-compiler-identity-install-v2/venv/lib/python3.11/site-packages'))
    traces=[bind_and_prove(a,v['case'],state_index,sites,operations,standalone)[0] for a in b['compiler_metadata']['flagprism_ascend_handoff']['artifacts']]
    rows.append(dict(actual_profile_scope=scope,status='pass',kind='standalone_aiv_one_instance' if standalone else 'mixed_explicit_SUB0_guard',explicit_guard=standalone is None,actual_actor_modules=len(traces),writer_calls=sum(t['State_external_writes'] for t in traces),terminal_source_SSA_bound=True,native_blockDim_actual_ELF_proved=bool(standalone)))
    if standalone:
        cells=load(q.parent/'derived-gate/actual-verified-raw-cells.json');cid=sorted({c['capture_id'] for c in cells})[0];cells=[c for c in cells if c['capture_id']==cid];req=[dict(program=p,site=s,actor_slots=[1,2],count_sum=1) for p in range(actual['grid'][0]) for s in sorted(sites)];verify_standalone_sum(cells,req);first=req[0]
        failures=[]
        for name in ['all_zero','duplicate_visit','missing_bank_cell','missing_program_site']:
            bad=copy.deepcopy(cells)
            group=[c for c in bad if c['program']==first['program'] and c['site']==first['site']]
            if name=='all_zero':
                for c in group:c['count']=0
            elif name=='duplicate_visit':
                for c in group:c['count']=1
            elif name=='missing_bank_cell':bad.remove(group[0])
            else:
                bad=[c for c in bad if not (c['program']==first['program'] and c['site']==first['site'])]
            try:verify_standalone_sum(bad,req)
            except ValueError as e:failures.append(dict(case=name,exception_class=type(e).__name__,reason=str(e)))
            else:raise ValueError('actual standalone negative accepted: '+name)
        rows[-1].update(negative_rejections=failures,required_sum_obligations=len(req),dynamic_sdk_query_packets_observed=standalone['dynamic_sdk_query_receipts'],blockDim_basis=standalone['blockDim_basis'],raw_zero_per_bank_reclassified=False)
require(not any(n in sys.modules for n in ['torch','torch_npu','triton']),'unexpected product/workload import')
safe=dict(schema='r15-postcapture-v3-partial-CPU-safe-v1',status='pass',actual_profile_structure_positives=rows,device_execution=False,compiler_invocations=0,product_imported=False,original_frozen_files_changed=False,script_sha256={p.name:sha(p) for p in sorted((R/'postcapture-v3').glob('*.py'))})
path=R/'postcapture-v3/SAFE_ACTUAL_PARTIAL_CPU.json'
with path.open('x') as f:json.dump(safe,f,indent=2);f.write('\n')
print(json.dumps(safe))
