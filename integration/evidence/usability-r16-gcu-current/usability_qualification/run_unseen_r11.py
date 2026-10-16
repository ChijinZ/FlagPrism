"""Independent six-kernel qualification controller; server Docker only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_common_report_c1_r11 as checker
from authorization_r16 import verify_authorization
import check_unseen_metadata_r11 as metadata


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


from owned_process import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['baseline', 'profile'])
    parser.add_argument('--backend', choices=['nvidia', 'enflame', 'ascend'], required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--booking', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checker.require(Path('/.dockerenv').exists(), 'server Docker only')
    freeze, booking = checker.load(args.freeze), checker.load(args.booking)
    token_path=HERE.parent/'GPU_READY.json'
    checker.require(token_path.is_file(),'r16 GPU_READY absent: no launch')
    token=checker.load(token_path)
    expected=dict(owner='qualification_r16_gcu',backend='enflame',device=0,freeze_sha256=sha(args.freeze),runner_sha256=sha(Path(__file__)),authorization_sha256=sha(HERE/'authorization_r16.py'),controller_sha256=sha(HERE.parent/'controller.py'))
    checker.require(all(token.get(k)==v for k,v in expected.items()) and token.get('authorized') is True,'r16 GPU_READY binding mismatch: no launch')
    verifier = verify_authorization(HERE, freeze)
    checker.require(booking.get('exclusive') is True and booking.get('backend')==args.backend
                    and booking.get('owner')=='usability_qualification', 'exclusive backend booking required')
    checker.require(freeze['backend']==args.backend, 'candidate backend mismatch')
    manifest_path = HERE / 'private_r11' / 'manifest.json'
    checker.require(sha(manifest_path)==freeze['unseen_manifest_sha256'], 'frozen independent source manifest changed')
    manifest = checker.load(manifest_path)
    app = HERE / 'private_r11' / 'unseen_r11.py'
    checker.require(sha(app)==manifest['source_sha256'][app.name], 'new mathematical source changed after freeze')
    checker.require(len(manifest['cases'])==6 and all(sum(case['category']==category for case in manifest['cases'])==2
                    for category in ['pointwise', 'reduction', 'matrix']), 'new six-kernel category freeze incomplete')
    root = args.output
    root.mkdir(parents=True, exist_ok=True)
    write(root / ('authorization-'+args.phase+'.json'), dict(freeze=freeze, booking=booking, manifest_sha256=sha(manifest_path), verifier_sha256=verifier))
    env = dict(os.environ)
    for key in list(env):
        if key=='PYTHONPATH' or key.startswith(('FLAGPRISM_', 'PROTON_', 'TRITON_PROTON_')):
            env.pop(key)
    env.pop('FLAGTREE_BACKEND', None)
    if args.backend!='nvidia':
        env['FLAGTREE_BACKEND']=args.backend
    if args.backend=='ascend':
        env['TORCH_DEVICE_BACKEND_AUTOLOAD']='0'
    device = dict(nvidia='cuda', enflame='gcu', ascend='npu')[args.backend]+':'+str(booking['device'])
    eligibility_path = root / 'eligibility.json'
    if args.phase=='baseline':
        checker.require(not eligibility_path.exists(), 'refuse to overwrite new baseline')
        rows=[]
        for spec in manifest['cases']:
            case=spec['case']
            for si in [0, 1]:
                for ci in [0, 1]:
                    key=f'{case}-s{si}-c{ci}'
                    folder=root / 'baseline' / key
                    receipt=folder/'receipt.json';ledger=folder/'startup-ledger.jsonl'
                    env['TRITON_CACHE_DIR']=str(folder/'cache')
                    command=[sys.executable, '-I', str(app), '--backend', args.backend, '--device', device,
                             '--case', case, '--shape-index', str(si), '--config-index', str(ci),
                             '--receipt', str(receipt), '--startup-ledger', str(ledger)]
                    terminal=run(command, folder, env, 300)
                    result=dict(case=case, shape_index=si, config_index=ci, category=spec['category'], status='fail', terminal=terminal)
                    try:
                        checker.require(terminal['returncode']==0 and not terminal['timed_out'], 'ordinary baseline failed')
                        checker.require(len(ledger.read_text().splitlines())==1, 'ordinary application replay')
                        actual=checker.load(receipt)
                        checker.require(Path(actual['triton_path']).resolve().is_relative_to(Path(freeze['venv']).resolve()), 'ordinary Triton import escaped installed candidate')
                        checker.require(actual['revision']=='R11-unseen' and actual['case']==case, 'wrong new numerical receipt')
                        checker.require(len(actual['calls'])==(2 if spec['runtime_proof_required'] else 1), 'ordinary requested-call count changed')
                        for call in actual['calls']:
                            checker.require(call['input_unchanged'] and call['canaries'], 'ordinary input/canary failed')
                            checker.require(call['atol']==spec['atol'] and call['rtol']==spec['rtol'], 'original frozen tolerance changed')
                            checker.require(call['non_idempotence_witness_max_abs']>100*spec['atol'], 'weak original non-idempotence witness')
                        actual['cold_timeout_s']=min(300, max(120, 3*actual['calls'][0]['compile_launch_sync_wall_s']))
                        result.update(status='pass', receipt=actual, receipt_sha256=sha(receipt))
                    except (checker.ContractError, KeyError, ValueError, OSError) as error:
                        result['error']=str(error)
                    rows.append(result);write(root/'baseline-progress.json', dict(status='running', results=rows))
        eligibility=dict(status='pass' if all(r['status']=='pass' for r in rows) else 'fail', results=rows, source_sha256=manifest['source_sha256'], profiler_invoked=False, expected=24, resolved=len(rows))
        write(eligibility_path, eligibility);write(root/'eligibility-seal.json', dict(sha256=sha(eligibility_path), manifest_sha256=sha(manifest_path)))
        raise SystemExit(0 if eligibility['status']=='pass' else 1)
    eligibility=checker.load(eligibility_path);seal=checker.load(root/'eligibility-seal.json')
    checker.require(sha(eligibility_path)==seal['sha256'] and sha(manifest_path)==seal['manifest_sha256'], 'ordinary baseline seal changed')
    checker.require(eligibility['expected']==24 and eligibility['resolved']==24 and len(eligibility['results'])==24, 'incomplete original ordinary baseline')
    cohort=dict(source_sha256=manifest['source_sha256'], cases=[dict(case=s['case'], source=app.name) for s in manifest['cases']], backend_evidence={args.backend:dict(common_combinations=[r['receipt'] for r in eligibility['results'] if r['status']=='pass'], runtime_probe=[])})
    cohort_path=root/'cohort.json';checker.require(not cohort_path.exists(), 'refuse overwrite profile cohort');write(cohort_path,cohort)
    rows=[]
    for baseline in eligibility['results']:
        if baseline['status']!='pass':
            rows.append(dict(case=baseline['case'], shape_index=baseline['shape_index'], config_index=baseline['config_index'], status='baseline_ineligible', baseline=baseline))
            continue
        case,si,ci=baseline['case'],baseline['shape_index'],baseline['config_index'];spec=next(s for s in manifest['cases'] if s['case']==case)
        key=f'{case}-s{si}-c{ci}';env['TRITON_CACHE_DIR']=str(root/'profile-cache'/key)
        for repetition in ['cold', 'warm']:
            folder=root/'profile'/key/repetition;receipt=folder/'receipt.json';ledger=folder/'startup-ledger.jsonl';bundle=folder/'bundle'
            command=[sys.executable, '-I', '-m', 'flagtree.profiler.cli', '--detail', 'auto', '--device', str(booking['device']), '-n', str(bundle), str(app),
                     '--backend', args.backend, '--device', device, '--case', case, '--shape-index', str(si), '--config-index', str(ci),
                     '--receipt', str(receipt), '--startup-ledger', str(ledger)]
            result=dict(case=case, shape_index=si, config_index=ci, repetition=repetition, status='fail')
            result['terminal']=run(command,folder,env,120+baseline['receipt']['cold_timeout_s']+60+60)
            try:
                checker.require(result['terminal']['returncode']==0 and not result['terminal']['timed_out'], 'default public CLI failed')
                actual=checker.load(receipt);ordinary=baseline['receipt']
                checker.require(actual['output_initial_sha256']==ordinary['output_initial_sha256'], 'non-idempotent seed changed')
                checker.require(len(actual['calls'])==len(ordinary['calls']), 'requested application count changed')
                for call,original in zip(actual['calls'],ordinary['calls']):
                    checker.require(call['runtime_input_sha256']==original['runtime_input_sha256'] and call['non_idempotence_witness_max_abs']==original['non_idempotence_witness_max_abs'], 'runtime input/replay witness changed')
                    checker.require(call['program_state_counts']==[call['call_index']+1]*actual['grid'][0], 'hidden device replay/missed programs')
                if args.backend=='ascend':
                    from retain_ascend_compiler_r11 import retain
                    result['independent_compiler_retention']=retain(bundle,folder)
                result['verification']=metadata.verify(bundle,receipt,eligibility_path,manifest_path,args.freeze,folder/'terminal.json',ledger,folder/'full-gate')
                checker.require(result['verification']['status']=='pass','complete original v2 raw gate failed')
                result['status']='pass'
            except (checker.ContractError, KeyError, TypeError, ValueError, OSError, StopIteration) as error:
                result['error']=f'{type(error).__name__}: {error}'
            write(folder/'qualification.json',result);rows.append(result);write(root/'profile-progress.json',dict(status='running',results=rows))
    status='pass' if len(rows)==48 and all(r['status']=='pass' for r in rows) else 'fail'
    write(root/'summary.json',dict(status=status, expected_profiles=48, resolved=len(rows), baseline_eligible_cases_removed=0, results=rows))
    raise SystemExit(0 if status=='pass' else 1)


if __name__=='__main__':
    main()
