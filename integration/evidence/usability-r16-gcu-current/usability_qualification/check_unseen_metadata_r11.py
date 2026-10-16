"""Deterministic CPU receipt-layout adapter; original mathematical bytes unchanged.

The independent ordinary/profile script executed the frozen elementwise numerical
assertions with the original tolerances before writing these receipts. This file
preserves that authority; it does not replace it with output-hash equality or a
scalar error bound. Derived results never overwrite original qualification files.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import check_common_report_c1_r11_v2 as common
from authorization_r16 import verify_authorization

VERSION='C1-r11-unseen-per-call-receipt-layout-v2'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_index(directory):
    return {str(p.relative_to(directory)):sha(p) for p in sorted(Path(directory).rglob('*')) if p.is_file()}


def hex_digest(value):
    return isinstance(value,str) and len(value)==64 and set(value)<={'0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f'} and value!='0'*64


def validate_receipts(manifest,ordinary,actual,ledger,terminal):
    common.require(actual.get('schema')=='flagprism-usability-workload-v1' and actual.get('revision')=='R11-unseen','unknown independent receipt schema')
    specs=[spec for spec in manifest['cases'] if spec['case']==actual.get('case')]
    common.require(len(specs)==1,'unknown/ambiguous frozen mathematical case')
    spec=specs[0]
    for name in ['case','shape_index','config_index','shape','config','grid','input_sha256','output_initial_sha256','category']:
        common.require(name in actual and name in ordinary and actual[name]==ordinary[name],'original numerical/seed configuration changed: '+name)
    for name in ['shape_index','config_index']:
        common.require(type(actual[name]) is int and actual[name] in [0,1],'invalid independent receipt index')
    common.require(actual['category']==spec['category'] and hex_digest(actual['output_initial_sha256']),'invalid original output seed identity')
    common.require(isinstance(actual['grid'],list) and len(actual['grid'])==1 and type(actual['grid'][0]) is int and actual['grid'][0]>0,'invalid actual ordinary program grid')
    common.require(isinstance(actual['input_sha256'],list) and actual['input_sha256'] and all(hex_digest(v) for v in actual['input_sha256']),'invalid original input identities')
    common.require(terminal.get('returncode')==0 and terminal.get('timed_out') is False,'independent numerical source did not finish successfully')
    common.require(len(ledger)==1 and isinstance(ledger[0],dict) and ledger[0].get('pid')==actual.get('pid') and ledger[0].get('case')==actual['case'],'actual independent host ledger/pid/case mismatch')
    expected_steps=[2,5] if spec['runtime_proof_required'] else [None]
    calls=actual.get('calls');baseline=ordinary.get('calls')
    common.require(isinstance(calls,list) and isinstance(baseline,list) and len(calls)==len(baseline)==len(expected_steps),'missing/extra independent numerical calls')
    common.require([call.get('call_index') for call in calls]==list(range(len(expected_steps))) and [call.get('call_index') for call in baseline]==list(range(len(expected_steps))),'duplicate/reordered original call set')
    bit_differences=[]
    for index,(call,original,steps) in enumerate(zip(calls,baseline,expected_steps)):
        common.require(type(call['call_index']) is int and type(original['call_index']) is int,'invalid original call-index type')
        common.require(call.get('runtime_steps')==original.get('runtime_steps')==steps and (steps is None or type(call['runtime_steps']) is int),'original runtime invocation input changed')
        common.require(call.get('atol')==original.get('atol')==spec['atol'] and call.get('rtol')==original.get('rtol')==spec['rtol'],'original elementwise numerical tolerance changed')
        for receipt in [call,original]:
            common.require(receipt.get('input_unchanged') is True and receipt.get('canaries') is True,'original numerical input/canary check failed')
            common.require(hex_digest(receipt.get('output_sha256')) and hex_digest(receipt.get('compiled_kernel_hash')) and hex_digest(receipt.get('runtime_input_sha256')),'actual output/binary/runtime input identity missing')
            value=receipt.get('max_abs_error');common.require(type(value) in [int,float] and math.isfinite(value) and value>=0,'invalid numerical result diagnostic')
            witness=receipt.get('non_idempotence_witness_max_abs');common.require(type(witness) in [int,float] and math.isfinite(witness) and witness>100*spec['atol'],'missing/zero/nonfinite original replay witness')
            state=receipt.get('program_state_counts');common.require(isinstance(state,list) and len(state)==actual['grid'][0] and all(type(x) is int and x==index+1 for x in state),'original per-program side effect/replay state changed')
        for key in ['runtime_input_sha256','non_idempotence_witness_max_abs','program_state_counts']:
            common.require(call[key]==original[key],'original per-call mathematical/replay evidence changed: '+key)
        if call['output_sha256']!=original['output_sha256']:
            bit_differences.append(index)
    if spec['runtime_proof_required']:
        common.require(len({call['compiled_kernel_hash'] for call in calls})==1,'runtime input changed compiled binary')
    # Only the incompatible top-level seed-layout branch is omitted from the
    # metadata projection after seed and every per-call witness are checked.
    projected={key:copy.deepcopy(value) for key,value in ordinary.items() if key!='output_initial_sha256'}
    return projected,dict(original_tolerances_preserved=True,independent_elementwise_assertions_completed=True,original_requested_calls=len(calls),per_call_seed_runtime_state_witness_checked=True,output_hash_differences_within_original_numerical_assertion=bit_differences,projection_omits_only_top_level_seed_layout=True)


def verify(bundle,receipt_path,eligibility_path,manifest_path,freeze_path,terminal_path,ledger_path,output_directory):
    bundle=Path(bundle);output_directory=Path(output_directory)
    common.require(not output_directory.exists() and not output_directory.resolve().is_relative_to(bundle.resolve()),'derived check must use a new directory outside original bundle')
    output_directory.mkdir(parents=True)
    before=file_index(bundle)
    paths=[Path(p) for p in [receipt_path,eligibility_path,manifest_path,freeze_path,terminal_path,ledger_path]]
    evidence={str(p):sha(p) for p in paths}
    freeze=common.load(Path(freeze_path));verify_authorization(HERE,freeze)
    common.require(sha(manifest_path)==freeze['unseen_manifest_sha256'],'original independent mathematical manifest pin changed')
    manifest=common.load(Path(manifest_path));common.require(sha(HERE/'private_r11'/'unseen_r11.py')==manifest['source_sha256']['unseen_r11.py'],'frozen elementwise mathematical source actual bytes changed');evidence[str(HERE/'private_r11'/'unseen_r11.py')]=sha(HERE/'private_r11'/'unseen_r11.py');eligibility=common.load(Path(eligibility_path));actual=common.load(Path(receipt_path))
    seal=common.load(Path(eligibility_path).parent/'eligibility-seal.json')
    common.require(sha(eligibility_path)==seal['sha256'] and sha(manifest_path)==seal['manifest_sha256'],'original ordinary baseline/manifest seal changed')
    common.require(eligibility['source_sha256']==manifest['source_sha256'] and eligibility['profiler_invoked'] is False and eligibility['expected']==eligibility['resolved']==len(eligibility['results'])==24,'ordinary eligibility source/count not frozen')
    rows=[row for row in eligibility['results'] if all(row[key]==actual[key] for key in ['case','shape_index','config_index'])]
    common.require(len(rows)==1 and rows[0]['status']=='pass','original actual-call baseline missing/ineligible/ambiguous')
    ordinary=rows[0]['receipt'];baseline_directory=Path(eligibility_path).parent/'baseline'/f"{actual['case']}-s{actual['shape_index']}-c{actual['config_index']}"
    common.require(sha(baseline_directory/'receipt.json')==rows[0]['receipt_sha256'],'ordinary numerical receipt actual bytes changed')
    baseline_terminal=common.load(baseline_directory/'terminal.json');common.require(baseline_terminal.get('returncode')==0 and baseline_terminal.get('timed_out') is False,'original ordinary numerical process did not finish successfully')
    for name in ['receipt.json','terminal.json','process.json','startup-ledger.jsonl']:
        evidence[str(baseline_directory/name)]=sha(baseline_directory/name)
    ledger=[json.loads(line) for line in Path(ledger_path).read_text().splitlines()]
    projected,math_evidence=validate_receipts(manifest,ordinary,actual,ledger,common.load(Path(terminal_path)))
    cohort=dict(source_sha256=manifest['source_sha256'],cases=[dict(case=actual['case'],source='unseen_r11.py')],backend_evidence={freeze['backend']:dict(common_combinations=[projected],runtime_probe=[])})
    cohort_path=output_directory/'projected-cohort.json';cohort_path.write_text(json.dumps(cohort,indent=2,sort_keys=True)+'\n')
    spec=next(spec for spec in manifest['cases'] if spec['case']==actual['case'])
    try:
        metrics=common.verify(bundle,Path(receipt_path),cohort_path,freeze['backend'],actual['case'],actual['shape_index'],actual['config_index'],Path(ledger_path),spec['runtime_proof_required'])
        result=dict(status='pass',complete_gate=metrics)
    except Exception as error:
        result=dict(status='fail',error_type=type(error).__name__,error=str(error))
    after=file_index(bundle);common.require(before==after and evidence=={p:sha(p) for p in evidence},'immutable original bundle/receipt/input evidence changed during derived CPU check')
    result.update(adapter_version=VERSION,math=math_evidence,original_bundle_file_sha256=before,original_bundle_unchanged=True,original_evidence_sha256=evidence,adapter_sha256=sha(Path(__file__)),derived_only_original_qualification_unchanged=True)
    (output_directory/'verification.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser()
    for name in ['bundle','receipt','eligibility','manifest','freeze','terminal','ledger','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    common.require(Path('/.dockerenv').exists(),'server Docker only')
    result=verify(args.bundle,args.receipt,args.eligibility,args.manifest,args.freeze,args.terminal,args.ledger,args.output)
    print(json.dumps(dict(status=result['status'],adapter_version=VERSION,error=result.get('error'),original_bundle_unchanged=result['original_bundle_unchanged'])))
    raise SystemExit(0 if result['status']=='pass' else 1)


if __name__=='__main__':
    main()
