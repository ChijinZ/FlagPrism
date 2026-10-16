"""Independent postcapture CPU proof of actual scalar terminal ownership and raw visits.
Private source/IR never leave this prefix. No compiler or workload invocation.
"""
import argparse,ast,copy,hashlib,json,re,sys
from pathlib import Path
R=Path('/tmp/chijin-r15-independent-qualification');sys.path[:0]=[str(Path(__file__).resolve().parent),str(R/'final'),str(R/'original_qualification')]
from authorization_r15 import require,sha,load,verify_authorization
from c1_ascend_core_r13 import llvm_body,markers,llvm_expressions
from c1_ascend_actor_join_r13 import compiler_proof
from c1_ascend_frontend_r13 import frontend
from c1_ascend_required_visits_r13 import verify_required_visits
from check_common_report import ContractError
from c1_source_census_r10 import CensusError
from standalone_execution_r15 import prove_standalone,verify_standalone_sum

def cfg(body):
    args=re.findall(r'%[\w.]+',body.splitlines()[0]);entry=str(max(int(v[1:]) for v in args)+1);block=entry;blocks={entry:[]};positions=[];at=0
    for line in body.splitlines(True):
        label=re.match(r'^([\w.]+):',line)
        if label:block=label[1];blocks.setdefault(block,[])
        blocks[block].append(line);positions.append((at,at+len(line),block));at+=len(line)
    succ={b:set(re.findall(r'label %([\w.]+)',''.join(lines))) for b,lines in blocks.items()}
    require(all(t in blocks for s in succ.values() for t in s),'CFG target missing')
    returns={b for b,lines in blocks.items() if any(re.match(r'\s*ret void',l) for l in lines)};require(returns,'CFG no return')
    pred={b:{p for p in blocks if b in succ[p]} for b in blocks}
    dom={b:({b} if b==entry else set(blocks)) for b in blocks}
    while True:
        new={b:({b} if b==entry else {b}|set.intersection(*(dom[p] for p in pred[b]))) for b in blocks}
        if new==dom:break
        dom=new
    post={b:({b} if b in returns else set(blocks)) for b in blocks}
    while True:
        new={b:({b} if b in returns else {b}|set.intersection(*(post[s] for s in succ[b]))) for b in blocks}
        if new==post:break
        post=new
    def atblock(pos):
        matches=[b for start,end,b in positions if start<=pos<end];require(len(matches)==1,'position missing in CFG');return matches[0]
    def reachable(start,target):
        todo=list(succ[start]);seen=set()
        while todo:
            v=todo.pop()
            if v==target:return True
            if v not in seen:seen.add(v);todo+=list(succ[v])
        return False
    return entry,blocks,succ,dom,post,atblock,reachable

def bind_and_prove(a,case,state_index,terminal_sites,site_operations,standalone=None):
    ll=a['llir'];funcs=re.findall(r'^define dso_local void @([\w.$-]+)\(',ll,re.M);require(len(funcs)==1,'actual actor kernel missing/ambiguous');body=llvm_body(ll,funcs[0]);kind=a['driver_job']['actor_kind']
    roles=a['argument_roles'];require(len(roles)==1,'actual ABI role array ambiguity');state=[r for r in roles[0] if r.get('source_argument_index')==state_index];require(len(state)==1,'actual State source-to-LLVM formal missing');state=state[0]
    require(state['source_formal_index']==state_index+2 and state['final_formal_index']==state_index+3,'actual bare-pointer prefix source ABI mismatch')
    args=re.findall(r'%[\w.]+',body.splitlines()[0]);formal=args[state['final_formal_index']]
    entry,blocks,succ,dom,post,atblock,reachable=cfg(body)
    actual_marks=[m for m in markers(body) if m[0] in terminal_sites]
    require(actual_marks,'actual terminal source marker absent in module')
    obligations=[]
    for mark in actual_marks:
        mb=atblock(mark[3]);require(mb in post[entry] and not reachable(mb,mb),'terminal marker lacks unconditional exactly-once terminated-path proof')
        obligations.append(mark[0])
    if kind=='AIC':
        require(re.search(re.escape(formal)+r'\b','\n'.join(body.splitlines()[1:])) is None,'AIC unexpectedly references State GM pointer')
        return dict(actor=kind,original_llir_sha256=hashlib.sha256(ll.encode()).hexdigest(),function=funcs[0],state_formal=state['final_formal_index'],terminal_sites=obligations,State_external_writes=0),obligations
    require(kind=='AIV','unknown actual actor')
    calls=[line for line in body.splitlines() if re.search(r'call void @store_ubuf_to_gm_1d_int32_t\(',line) and re.search(r'ptr addrspace\(1\) '+re.escape(formal)+r'(?=,|\))',line)]
    require(len(calls)==1,'exactly one external scalar State store helper call required')
    call=calls[0];arguments=call.split('(',1)[1].split('), !dbg',1)[0].split(', ')
    require(len(arguments)==11 and arguments[2:5]==['i64 0','i64 1','i64 1'] and arguments[5:7]==['ptr addrspace(1) '+formal]*2 and arguments[8:]==['i64 1','i64 1','i32 0'],'actual State GM length/stride/non-atomic descriptor changed')
    offset=arguments[7].removeprefix('i64 ');geps=re.findall(r'(%[\w.]+) = getelementptr i32, ptr addrspace\(1\) '+re.escape(formal)+r', i64 ([%\w.-]+)',body);require(len(geps)==1 and geps[0][1]==offset,'scalar State load/store GM offset mismatch')
    loads=re.findall(r'(%[\w.]+) = call i64 @llvm.hivm.LD.DEV.u32.GM\(ptr addrspace\(1\) '+re.escape(geps[0][0])+r', i64 0\)',body);require(len(loads)==1,'actual State scalar load missing/ambiguous')
    truncs=re.findall(r'(%[\w.]+) = trunc i64 '+re.escape(loads[0])+r' to i32',body);require(len(truncs)==1,'actual State int32 load cast missing')
    adds=re.findall(r'(%[\w.]+) = add i32 '+re.escape(truncs[0])+r', 1\b',body);require(len(adds)==1,'actual State +1 RMW def-use changed')
    stores=re.findall(r'store i32 '+re.escape(adds[0])+r', (ptr addrspace\(6\) [^\n]+?), align 4',body);require(len(stores)==1 and arguments[0]==arguments[1]==stores[0],'actual State +1 UB value not supplied to external store')
    for mark in actual_marks:
        operation=site_operations[mark[0]]
        if operation=='arith.addi':
            following=body[mark[4]:].splitlines()[1].strip().split(', !dbg')[0]
            require(following==adds[0]+' = add i32 '+truncs[0]+', 1','selected terminal addi marker is not actual State RMW SSA')
        else:
            require(operation=='tt.store','terminal source operation lacks State SSA semantics')
            ubpos=body.index('store i32 '+adds[0]+', '+stores[0])
            require(mark[3]<ubpos and atblock(mark[3])==atblock(ubpos),'selected terminal store marker does not bind actual State UB store')
    defs,defblocks,expr=llvm_expressions(body,dict(GX=args[-3],GY=args[-2],GZ=args[-1]))
    require(expr(offset)==expr(actual_marks[0][2][0]) and 'SUB' not in repr(expr(offset)),'State GM cell not exact logical program')
    sb=atblock(body.index(call));require(not reachable(sb,sb),'State writer could execute in a loop')
    candidates=[]
    def depends_on_sub(value,seen=()):
        if value in seen or value not in defs:return False
        definition=defs[value]
        return '@llvm.hivm.GET.SUBBLOCKID()' in definition or any(depends_on_sub(v,seen+(value,)) for v in re.findall(r'%[\w.]+',definition))
    for block,lines in blocks.items():
        for line in lines:
            match=re.search(r'br i1 (%[\w.]+), label %([\w.]+), label %([\w.]+)',line)
            if match and depends_on_sub(match[1]):
                condition=expr(match[1])
                if condition==('icmp','eq','SUB',0) and match[2] in dom[sb] and block in dom[sb] and not (match[3]==sb or reachable(match[3],sb)):
                    candidates.append(dict(predicate=condition,branch_block=block,writer_block=sb,true_successor=match[2],false_successor=match[3]))
    if standalone is None:
        require(len(candidates)==1,'actual State write is not dominated by unique SUB==0 election')
    else:
        require(standalone['kind']=='standalone_aiv_one_instance' and standalone['actual_sdk_AIV_not_part_of_mix'] is True,'standalone actual compiled/launch proof absent')
        require(not candidates and '@llvm.hivm.GET.SUBBLOCKID()' not in body,'standalone proof cannot hide a SUB-dependent writer')
        require(sb in post[entry],'standalone State writer does not execute exactly once per actual vector instance')
    helper=llvm_body(ll,'store_ubuf_to_gm_1d_int32_t');require(len(re.findall(r'call void @_mlir_ciface_store_ubuf_to_gm_1d_int32_t\(',helper))==1 and not re.search(r'\bbr\b',helper),'scalar State helper has unexpected control/replay')
    return dict(actor=kind,original_llir_sha256=hashlib.sha256(ll.encode()).hexdigest(),function=funcs[0],state_formal=state['final_formal_index'],terminal_sites=obligations,State_external_writes=1,guard=candidates[0] if candidates else None,length=1,stride=1,offset_expr=expr(offset),rmw_plus_one_proved=True,writer_proof_kind='mixed_explicit_SUB0_guard' if standalone is None else 'standalone_aiv_one_instance'),obligations

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['finite2','main24','new8'],required=True);args=parser.parse_args()
    m=verify_authorization(R/'final/FINAL_EXECUTION_MANIFEST.json');root=R/f'run-{args.scope}';summary=load(root/'summary.json');proofroot=root/'independent-ownership-v3';proofroot.mkdir(exist_ok=False);proofs=[];safe_rows=[]
    for ordinal,q in enumerate(summary['profiles'],1):
        folder=root/'profile'/f"{q['case']}-s{q['shape_index']}-c{q['config_index']}"/q['repetition'];bundle=folder/'bundle';qpath=folder/'qualification.json';qsha=sha(qpath)
        require(q['status']=='pending_independent_ownership_proof','capture semantic gate did not pass')
        binaries=load(bundle/'ai/binaries.json');require(len(binaries)==1,'one actual specialization required per frozen process')
        b=binaries[0];sourcepath=bundle/b['source']['file_snapshot_file'];require(sha(sourcepath)==b['source']['file_sha256'],'source snapshot changed')
        tree=ast.parse(sourcepath.read_bytes());functions=[f for f in ast.walk(tree) if isinstance(f,ast.FunctionDef) and f.name==q['case']];require(len(functions)==1,'actual mathematical function missing/ambiguous');fn=functions[0]
        state_index=[a.arg for a in fn.args.args].index('State');stores=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='store' and n.args and any(isinstance(x,ast.Name) and x.id=='State' for x in ast.walk(n.args[0]))];require(len(stores)==1,'original scalar State source store missing/ambiguous');store=stores[0]
        require(not any(isinstance(n,(ast.For,ast.While,ast.If)) and n.lineno<=store.lineno<=n.end_lineno for n in ast.walk(fn)),'terminal State source store not unconditional outside loops')
        signature=(bundle/b['compiler_artifact_files']['ttir']['file']).read_text();ttfunc=next(x for x in signature.splitlines() if 'tt.func public @'+q['case']+'(' in x);require('%State: !tt.ptr<i32>' in ttfunc,'actual frontend State pointer binding missing')
        compiler=compiler_proof(bundle,b,frontend_proof=frontend);sites={s['site'] for s in compiler['sites'] if (s['operation']=='tt.store' or s['operation']=='arith.addi' and s['element_dtype']=='i32' and s['value_kind']=='scalar') and any(loc['file']==b['source']['path'] and store.lineno<=loc['line']<=store.end_lineno for loc in s['origin']['source_locations'])};require(sites,'selected terminal State source site missing')
        site_operations={s['site']:s['operation'] for s in compiler['sites'] if s['site'] in sites}
        actual=load(folder/'receipt.json');standalone=None
        if b['compiler_metadata'].get('mix_mode')=='aiv':
            standalone=prove_standalone(bundle,b,actual,root/'profile-cache'/folder.parent.name,Path(m['venv'])/'lib/python3.11/site-packages')
        traces=[];actor_sites={};negative=0
        for a in b['compiler_metadata']['flagprism_ascend_handoff']['artifacts']:
            trace,marks=bind_and_prove(a,q['case'],state_index,sites,site_operations,standalone);traces.append(trace);kind=a['driver_job']['actor_kind'];actor_sites[kind]=set(marks)
            if kind=='AIV' and standalone is None:
                changed=copy.deepcopy(a);old='icmp eq i64';require(old in changed['llir'],'actual guard mutation anchor absent');changed['llir']=changed['llir'].replace(old,'icmp ne i64',1)
                try:bind_and_prove(changed,q['case'],state_index,sites,site_operations)
                except (ContractError,CensusError,ValueError):negative+=1
                else:raise ValueError('actual writer guard removal negative accepted')
        require(sum(t['State_external_writes'] for t in traces)==1,'multiple actor State writers')
        if q['verification']['math'].get('original_requested_calls') and args.scope in ['finite2','new8']:require(set(actor_sites)=={'AIC','AIV'},'mixed matrix actor module missing')
        cells_path=folder/'derived-gate/actual-verified-raw-cells.json';cells=load(cells_path);requirements={};proved=[]
        for cid in sorted({c['capture_id'] for c in cells}):
            selected=[c for c in cells if c['capture_id']==cid and c['site'] in sites]
            require(selected,'actual terminal raw cells absent')
            if standalone is None:
                expected=[dict(program=c['program'],actor_slot=c['actor']['id'],site=c['site'],count=1) for c in selected]
                proved.extend(verify_required_visits([c for c in cells if c['capture_id']==cid],expected))
            else:
                expected=[dict(program=program,site=site,actor_slots=[1,2],count_sum=1) for program in range(actual['grid'][0]) for site in sorted(sites)]
                proved.extend(verify_standalone_sum([c for c in cells if c['capture_id']==cid],expected))
            requirements[cid]=expected
            corrupt=copy.deepcopy([c for c in cells if c['capture_id']==cid]);next(c for c in corrupt if c['site'] in sites)['count']=0
            if standalone is not None:
                first=expected[0]
                for c in corrupt:
                    if c['program']==first['program'] and c['site']==first['site']:c['count']=0
            try:
                if standalone is None:verify_required_visits(corrupt,expected)
                else:verify_standalone_sum(corrupt,expected)
            except (CensusError,ValueError):negative+=1
            else:raise ValueError('missing actual terminal raw visit negative accepted')
        audit=dict(schema='independent-r15-actual-terminal-audit-v3',status='pass',synthetic=False,qualification_sha256=qsha,original_state_formal_bound=True,actual_compiled_single_writer_guard=standalone is None,writer_proof_kind='mixed_explicit_SUB0_guard' if standalone is None else 'standalone_aiv_one_instance',standalone_execution_proof=standalone,actual_generated_object_final_closure=bool(q['verification']['generated_inputs']) and q['verification']['common_gate']['status']=='pass',required_terminal_raw_visits_exact=True,actual_aic_aiv_modules_verified=True,actual_verified_raw_cells_sha256=sha(cells_path),required_visits_by_capture=requirements,terminal_sites=sorted(sites),program_count=actual['grid'][0],proved_obligations=len(proved),private_compiler_proofs=traces,negative_actual_mutations_rejected=negative,derivation_script_sha256=sha(Path(__file__)),source_sha256=b['source']['file_sha256'])
        path=proofroot/f'{ordinal:04d}-audit-private.json';path.write_text(json.dumps(audit,indent=2)+'\n');proofs.append(dict(qualification_sha256=qsha,independent_audit_path=str(path),independent_audit_sha256=sha(path)))
        safe_rows.append(dict(anonymous_profile_ordinal=ordinal,repetition=q['repetition'],status='pass',State_scalar_single_writer=True,writer_proof_kind=audit['writer_proof_kind'],explicit_SUB0_guard=audit['actual_compiled_single_writer_guard'],source_formal_bound=True,actual_actor_modules=len(traces),required_terminal_raw_obligations=len(proved),negative_actual_mutations_rejected=negative,original_bundle_unchanged=True))
    proof=dict(schema='independent-r15-actual-terminal-ownership-v3',scope=args.scope,manifest_sha256=sha(R/'final/FINAL_EXECUTION_MANIFEST.json'),profiles=proofs);proofpath=proofroot/'PROOF_PRIVATE.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
    safe=dict(schema='independent-r15-actual-ownership-safe-v1',scope=args.scope,status='pass',profiles=safe_rows,private_proof_sha256=sha(proofpath),derivation_script_sha256=sha(Path(__file__)),mathematical_sources_unchanged=True,original_history_unchanged=True,device_execution=False,compiler_invocations=0)
    (proofroot/'SAFE_OWNERSHIP_AGGREGATE.json').write_text(json.dumps(safe,indent=2)+'\n');print(json.dumps(safe))
if __name__=='__main__':main()
