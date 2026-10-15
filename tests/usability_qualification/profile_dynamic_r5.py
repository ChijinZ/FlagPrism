"""Q4 default-public-CLI runner; no execution before explicit new freeze/booking."""
import argparse,json,os
from pathlib import Path
import signal,subprocess,sys,time
import check_common_report_c1 as common
import check_dynamic_report_c1 as checker
from run_common_r5 import workload_device
HERE=Path(__file__).resolve().parent


def write(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--backend',choices=['nvidia','enflame','ascend'],required=True)
    p.add_argument('--device',type=int,required=True)
    p.add_argument('--eligibility',type=Path,required=True)
    p.add_argument('--freeze',type=Path,required=True)
    p.add_argument('--booking',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pass-kind',choices=['first','repair'],required=True)
    a=p.parse_args()
    common.require(Path('/.dockerenv').exists(),'server Docker only')
    common.require(common.digest(HERE/'dynamic-reserve-Q4-manifest.json')=='da2a96fe766270a1b70062a96fea88a8452d99d074b0b2328e3fa47924dd065d','frozen Q4 manifest changed')
    manifest=common.load(HERE/'dynamic-reserve-Q4-manifest.json')
    common.require(common.digest(HERE/'reserve_dynamic.py')==manifest['source_sha256']['reserve_dynamic.py'],'frozen Q4 math changed')
    eligibility,freeze,booking=[common.load(path) for path in [a.eligibility,a.freeze,a.booking]]
    common.require(eligibility['source_sha256']==manifest['source_sha256'] and eligibility['profiler_invoked'] is False,'invalid ordinary source eligibility')
    signatures={(r['case'],r['shape_index'],r['config_index']) for r in eligibility['results']}
    expected={(case,si,ci) for case in ['coupled_logistic','neighbor_accumulation'] for si in [0,1] for ci in [0,1]}
    common.require(eligibility.get('resolved')==8 and len(eligibility['results'])==8 and signatures==expected
                   and eligibility.get('status') in ['pass','fail'],'ordinary baseline eligibility is incomplete')
    common.require(freeze.get('candidate_frozen') is True and all(freeze.get(k) for k in ['product_revision','public_docs_sha256','installed_native_sha256']),'missing final candidate freeze')
    from c1_verifier_authorization_r5 import verify_authorization
    verifier_hashes=verify_authorization(HERE,freeze)
    common.require(booking.get('exclusive') is True and booking.get('owner')=='usability_qualification'
                   and booking.get('backend')==a.backend and booking.get('device')==a.device,'missing exclusive booking')
    common.require(not a.output.exists(),'refuse overwrite')
    a.output.mkdir(parents=True)
    write(a.output/'authorization.json',{'freeze':freeze,'booking':booking,'pass_kind':a.pass_kind,
          'eligibility_sha256':common.digest(a.eligibility),'manifest_sha256':common.digest(HERE/'dynamic-reserve-Q4-manifest.json'),
          'runner_sha256':common.digest(Path(__file__)),'checker_sha256':common.digest(HERE/'check_dynamic_report_c1.py'),
          'unchanged_shared_checker_sha256':common.digest(HERE/'check_common_report.py'),
          'qualification_verifier_version':'C1-r5-v1','qualification_verifier_sha256':verifier_hashes})
    env=os.environ.copy()
    for name in list(env):
        if name=='PYTHONPATH' or name.startswith(('FLAGPRISM_','PROTON_','TRITON_PROTON_')): env.pop(name)
    env.pop('FLAGTREE_BACKEND',None)
    if a.backend!='nvidia': env['FLAGTREE_BACKEND']=a.backend
    if a.backend=='ascend': env['TORCH_DEVICE_BACKEND_AUTOLOAD']='0'
    results=[]
    ineligible=[]
    eligible=[r for r in eligibility['results'] if r['status']=='pass']
    for baseline in eligibility['results']:
        if baseline['status']!='pass': ineligible.append(baseline)
    for baseline in eligible:
        common.require(baseline['receipt']['backend']==a.backend,'wrong baseline backend')
        case,si,ci=baseline['case'],baseline['shape_index'],baseline['config_index']
        key=f'{case}-s{si}-c{ci}'
        cache=a.output/'caches'/key
        cache.mkdir(parents=True)
        env['TRITON_CACHE_DIR']=str(cache.resolve())
        for repetition in ['cold','warm']:
            folder=a.output/key/repetition
            folder.mkdir(parents=True)
            receipt,ledger,bundle=[folder/n for n in ['receipt.json','startup-ledger.jsonl','bundle']]
            command=[sys.executable,'-m','flagtree.profiler.cli','--detail','auto','--device',str(a.device),'-n',str(bundle.resolve()),
                     str(HERE/'reserve_dynamic.py'),'--case',case,'--backend',a.backend,'--device',workload_device(a.backend,a.device),
                     '--shape-index',str(si),'--config-index',str(ci),'--receipt',str(receipt.resolve()),'--startup-ledger',str(ledger.resolve())]
            row={'case':case,'shape_index':si,'config_index':ci,'repetition':repetition,'baseline_eligible':True,'status':'fail','command':command}
            started=time.monotonic()
            with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
                proc=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True)
                write(folder/'process.json',{'pid':proc.pid,'command':command,'outer_guard_seconds':360})
                try: row['returncode']=proc.wait(timeout=360)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL)
                        proc.wait()
                    row['returncode'],row['outer_timeout']=proc.returncode,True
            row['host_process_wall_s']=time.monotonic()-started
            try:
                common.require(row['returncode']==0,'default public CLI failed or timed out')
                common.require(len(ledger.read_text().splitlines())==1,'whole application hidden replay')
                row['verification']=checker.verify(bundle,receipt,a.eligibility,a.backend)
                row['status']='pass'
            except (common.ContractError,KeyError,TypeError,ValueError,OSError,StopIteration) as error:
                row['error']=f'{type(error).__name__}: {error}'
            write(folder/'qualification.json',row)
            results.append(row)
            write(a.output/'summary.json',{'status':'running','results':results,'ordinary_baseline_ineligible':ineligible})
    status='pass' if results and all(r['status']=='pass' for r in results) else 'fail'
    write(a.output/'summary.json',{'status':status,'pass_kind':a.pass_kind,'expected_runs':len(eligible)*2,
          'resolved_runs':len(results),'baseline_eligible_cases_removed':0,'ordinary_baseline_ineligible':ineligible,'results':results})
    raise SystemExit(0 if status=='pass' else 1)


if __name__=='__main__': main()
