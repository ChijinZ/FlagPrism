#!/usr/bin/env python3
"""Independent fixed-grid NVIDIA controls after the frozen search. Remote Docker."""
import argparse,hashlib,json,random,statistics,subprocess,sys,time
from pathlib import Path
from observations import native
from porting_sweep import options

p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['softmax-long-k','gemm-warps'],default='softmax-long-k');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
selection=json.loads(a.selection.read_text())
row=next(r for r in selection if r['operator']=='softmax' and r['shape']=='127x769')
assert row['config']['ROWS']==1
long=next(r for r in selection if r['operator']=='gemm_bias_gelu' and r['shape']=='512x512x4096')
choices=[{'operator':'softmax','shape':'127x769','name':f'softmax-w{w}','config':dict(row['config'],num_warps=w)} for w in [1,2,4]]
choices+=[{'operator':long['operator'],'shape':long['shape'],'name':'long-k-frozen-n','config':long['config']}]
if a.mode=='gemm-warps':
    gemm=next(r for r in selection if r['operator']=='gemm' and r['shape']=='512x512x512')
    choices=[{'operator':'gemm','shape':'512x512x512','name':f'gemm-w{w}','config':dict(gemm['config'],num_warps=w)} for w in [1,2,4]]
plan={'backend':'cuda','choices':choices,'batches':3,'launches':30,'ordering':'deterministic randomized case order within each measurement batch; launches within each case are consecutive','selection_sha256':hashlib.sha256(a.selection.read_bytes()).hexdigest(),'source_sha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['run_case.py','observations.py','nvidia_case_controls.py']},'semantics':'Frozen N unchanged; fixed-grid Softmax warp counterfactuals plus independent long-K N; not post-hoc retuning'}
(a.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
plan['mode']=a.mode
if a.mode=='gemm-warps':plan['semantics']='Frozen GEMM512 native-selected source tile/grid/K/stages; warp1/2/4 bounded counterfactuals absent from original4/8warp GEMMsearch. Preserve failures; not evidence of exhaustive optimality.'
(a.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
rows=[]
for batch in range(3):
    order=list(choices);random.Random(2026101308+batch).shuffle(order)
    for case in order:
        out=a.output/f"{case['name']}-b{batch}"
        cmd=[sys.executable,str(Path(__file__).with_name('run_case.py')),'--backend','cuda','--operator',case['operator'],'--shape',case['shape'],'--phase','native','--profile-launches','30','--input-dir',str(a.input_dir),'--output',str(out),*options(case['config'])]
        print('RUN',case['name'],batch,flush=True)
        with (a.output/f"{case['name']}-b{batch}.log").open('w') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300).returncode
        record={'name':case['name'],'batch':batch,'command':cmd,'returncode':code,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        with (a.output/'execution.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        if code:raise RuntimeError(f"{case['name']} failed {code}; retained evidence")
        result=json.loads((out/'result.json').read_text());assert result['status']=='passed' and result['validation']['passed'] and result['post_profile_validation']['passed']
        events=[e for e in native(out,'cuda') if e.get('kind')=='kernel' and e.get('duration_us',0)>0]
        assert len(events)==30
        rows.append({'name':case['name'],'batch':batch,'config':case['config'],'samples_us':[e['duration_us'] for e in events],'median_us':statistics.median(e['duration_us'] for e in events),'source':str(out)})
        (a.output/'summary.json').write_text(json.dumps({'batches':rows},indent=2)+'\n')
summary={'batches':rows,'median_of_batch_medians_us':{c['name']:statistics.median(r['median_us'] for r in rows if r['name']==c['name']) for c in choices},'status':'passed'}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary['median_of_batch_medians_us']),flush=True)
