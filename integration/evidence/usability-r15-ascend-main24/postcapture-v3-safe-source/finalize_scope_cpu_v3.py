"""CPU closeout only after actual independently derived compiled ownership proofs."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,'/tmp/chijin-r15-independent-qualification/final')
from authorization_r15 import ROOT,require,sha,load,verify_authorization
from standalone_execution_r15 import prove_standalone,verify_standalone_sum

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--scope',choices=['finite2','main24','new8'],required=True);p.add_argument('--proof',type=Path,required=True);a=p.parse_args()
    m=verify_authorization(a.manifest);root=ROOT/f'run-{a.scope}';summary=load(root/'summary.json');proof=load(a.proof)
    sys.path.insert(0,str(ROOT/'original_qualification'))
    from c1_ascend_required_visits_r13 import verify_required_visits
    require(proof.get('schema')=='independent-r15-actual-terminal-ownership-v3' and proof.get('scope')==a.scope and proof.get('manifest_sha256')==sha(a.manifest),'proof scope/manifest mismatch')
    require(summary['registered']==dict(finite2=2,main24=24,new8=8)[a.scope] and len(summary['ordinary'])==summary['registered'],'registered ordinary cardinality changed')
    require(summary['removed_registered_cases']==0,'registered case removed')
    if a.scope=='main24':
        history=load(ROOT/'REPLAY_EXECUTION_PLAN_PRIVATE.json')['full_registered_command_plan']
        for old in history:
            if old['phase']=='ordinary' and old['old_ordinary_status']=='pass':require(any(r['key']==old['key'] and r['status']=='pass' for r in summary['ordinary']),'original eligible ordinary regressed')
    else:require(all(r['status']=='pass' for r in summary['ordinary']),'finite/new ordinary failure')
    profiles=summary['profiles'];require(len(profiles)==summary['expected_profiles'] and all(q['status']=='pending_independent_ownership_proof' for q in profiles),'complete capture gate failure/incomplete')
    require(type(proof.get('profiles')) is list and len(proof['profiles'])==len(profiles),'ownership proof cardinality incomplete')
    # This closeout checks the exact independently CPU-audited per-profile proof
    # receipts. Derivation/audit must happen on the actual new private compiler
    # outputs before this script is used; no synthetic proof is created here.
    for q,row in zip(profiles,proof['profiles']):
        folder=root/'profile'/f"{q['case']}-s{q['shape_index']}-c{q['config_index']}"/q['repetition']
        require(row.get('qualification_sha256')==sha(folder/'qualification.json'),'proof bound to different qualification')
        receipt=load(row['independent_audit_path']);require(sha(row['independent_audit_path'])==row['independent_audit_sha256'],'independent actual ownership audit bytes changed')
        require(receipt.get('status')=='pass' and receipt.get('synthetic') is False and receipt.get('qualification_sha256')==row['qualification_sha256'],'actual proof audit did not pass')
        require(receipt.get('schema')=='independent-r15-actual-terminal-audit-v3' and receipt.get('derivation_script_sha256')==sha(Path(__file__).parent/'derive_ownership_v3.py'),'unapproved/changed independent structure proof')
        for k in ['original_state_formal_bound','actual_generated_object_final_closure','required_terminal_raw_visits_exact','actual_aic_aiv_modules_verified']:
            # Matrix/mixed samples require both modules. Pointwise/reduction may
            # have one actor; the independent audit must verify actual modules
            # rather than invent a second module.
            require(receipt.get(k) is True,'independent actual proof missing: '+k)
        require(type(receipt.get('proved_obligations')) is int and receipt['proved_obligations']>0,'missing nonzero actual terminal obligations')
        cells_path=folder/'derived-gate/actual-verified-raw-cells.json';cells=load(cells_path)
        require(receipt.get('actual_verified_raw_cells_sha256')==sha(cells_path),'raw obligation proof bound to different actual cells')
        obligations=receipt.get('required_visits_by_capture');require(type(obligations) is dict and obligations,'actual required visit map absent')
        require(set(obligations)=={c['capture_id'] for c in cells},'required visit proof omitted actual capture')
        actual=load(folder/'receipt.json');require(receipt['program_count']==actual['grid'][0] and receipt['terminal_sites'],'source program/site obligation geometry changed')
        kind=receipt.get('writer_proof_kind')
        if kind=='mixed_explicit_SUB0_guard':
            require(receipt.get('actual_compiled_single_writer_guard') is True and receipt.get('standalone_execution_proof') is None,'mixed explicit SUB0 guard missing/standalone substitution')
        elif kind=='standalone_aiv_one_instance':
            require(receipt.get('actual_compiled_single_writer_guard') is False,'standalone may not claim an absent explicit SUB0 guard')
            binary=load(folder/'bundle/ai/binaries.json');require(len(binary)==1,'standalone actual specialization ambiguity')
            native=prove_standalone(folder/'bundle',binary[0],actual,root/'profile-cache'/folder.parent.name,Path(m['venv'])/'lib/python3.11/site-packages')
            require(native==receipt.get('standalone_execution_proof'),'actual standalone SDK/native/grid evidence changed')
        else:raise ValueError('unknown actual single-writer proof kind')
        count=0
        for cid,requirements in obligations.items():
            capture_cells=[c for c in cells if c['capture_id']==cid]
            if kind=='mixed_explicit_SUB0_guard':
                expected={(c['program'],c['actor']['id'],c['site']) for c in capture_cells if c['site'] in receipt['terminal_sites']}
                require({(r['program'],r['actor_slot'],r['site']) for r in requirements}==expected,'mixed terminal actor/program/site obligation omitted')
                verified=verify_required_visits(capture_cells,requirements)
            else:
                expected={(p,s) for p in range(actual['grid'][0]) for s in receipt['terminal_sites']}
                require(len(requirements)==len(expected) and {(r['program'],r['site']) for r in requirements}==expected,'standalone complete independent obligation geometry omitted')
                verified=verify_standalone_sum(capture_cells,requirements)
            count+=len(verified)
        require(count==receipt['proved_obligations'],'actual proved obligation count mismatch')
    result=dict(status='pass',scope=a.scope,manifest_sha256=sha(a.manifest),registered=summary['registered'],eligible=sum(r['status']=='pass' for r in summary['ordinary']),profiles=len(profiles),independent_proof_sha256=sha(a.proof),old_history_unchanged=True,postcapture_version='independent-r15-actual-terminal-ownership-v3',finalize_adapter_sha256=sha(Path(__file__)))
    with (root/'FINAL_VERDICT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
if __name__=='__main__':main()
