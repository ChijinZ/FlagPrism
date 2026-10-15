"""Ordinary original-compiler Q4 eligibility, only in exclusively booked server Docker."""
import argparse,hashlib,json,os
from pathlib import Path
import signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data): path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--backend',choices=['nvidia','enflame','ascend'],required=True)
    p.add_argument('--device',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--booking',type=Path,required=True)
    a=p.parse_args()
    assert Path('/.dockerenv').exists(),'server Docker only'
    booking=json.loads(a.booking.read_text())
    assert booking['exclusive'] is True and booking['owner']=='usability_qualification' and booking['backend']==a.backend
    assert a.device=={'nvidia':'cuda','enflame':'gcu','ascend':'npu'}[a.backend]+':'+str(booking['device'])
    manifest=json.loads((HERE/'dynamic-reserve-Q4-manifest.json').read_text())
    assert sha(HERE/'reserve_dynamic.py')==manifest['source_sha256']['reserve_dynamic.py']
    assert manifest['baseline_timeout_seconds']==300
    assert not a.output.exists(),'refuse overwrite'
    a.output.mkdir(parents=True)
    write(a.output/'authorization.json',{'booking':booking,'manifest_sha256':sha(HERE/'dynamic-reserve-Q4-manifest.json'),
          'source_sha256':manifest['source_sha256'],'python':sys.executable,'profiler_invoked':False,
          'PYTHONPATH':os.environ.get('PYTHONPATH'),'FLAGTREE_BACKEND':os.environ.get('FLAGTREE_BACKEND')})
    results=[]
    for case in ['coupled_logistic','neighbor_accumulation']:
        for si in [0,1]:
            for ci in [0,1]:
                key=f'{case}-s{si}-c{ci}'
                folder=a.output/key
                folder.mkdir()
                receipt,ledger=folder/'receipt.json',folder/'startup-ledger.jsonl'
                command=[sys.executable,str(HERE/'reserve_dynamic.py'),'--case',case,'--backend',a.backend,
                         '--device',a.device,'--shape-index',str(si),'--config-index',str(ci),
                         '--receipt',str(receipt.resolve()),'--startup-ledger',str(ledger.resolve())]
                env=os.environ.copy()
                env['TRITON_CACHE_DIR']=str((folder/'cache').resolve())
                row={'case':case,'shape_index':si,'config_index':ci,'command':command,'status':'fail','timeout_s':300}
                started=time.monotonic()
                with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
                    proc=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True)
                    write(folder/'process.json',{'pid':proc.pid,'command':command})
                    try: row['returncode']=proc.wait(timeout=300)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGTERM)
                        try: proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid,signal.SIGKILL)
                            proc.wait()
                        row['returncode'],row['timeout']=proc.returncode,True
                row['host_process_wall_s']=time.monotonic()-started
                try:
                    assert row['returncode']==0,'ordinary baseline failed'
                    assert len(ledger.read_text().splitlines())==1,'host replay'
                    r=json.loads(receipt.read_text())
                    assert [c['runtime_steps'] for c in r['calls']]==[2,5]
                    hashes={c['compiled_kernel_hash'] for c in r['calls']}
                    assert len(hashes)==1 and '' not in hashes,'runtime bounds recompiled'
                    assert all(c['input_unchanged'] and c['canaries'] for c in r['calls'])
                    row.update(status='pass',receipt=r,receipt_sha256=sha(receipt))
                except (AssertionError,OSError,ValueError,KeyError) as error:
                    row['error']=f'{type(error).__name__}: {error}'
                write(folder/'qualification.json',row)
                results.append(row)
                write(a.output/'eligibility.json',{'status':'running','results':results})
    seal={'status':'pass' if all(r['status']=='pass' for r in results) else 'fail',
          'expected':8,'resolved':len(results),'source_sha256':manifest['source_sha256'],'profiler_invoked':False,'results':results}
    write(a.output/'eligibility.json',seal)
    raise SystemExit(0 if seal['status']=='pass' else 1)
if __name__=='__main__': main()
