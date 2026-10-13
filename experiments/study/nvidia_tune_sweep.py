#!/usr/bin/env python3
"""Serial, resumable NVIDIA source search; remote Docker execution only."""
import argparse,json,subprocess,sys,time,statistics,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--timeout',type=int,default=1800);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
selected=[]
def native_select(op,shape,out,state):
    ranked=[]; seen=set()
    for row in sorted([r for r in state['attempts'] if r['passed']],key=lambda r:r['median_us']):
        identity=row['asm_sha256'].get('cubin') or row['asm_sha256'].get('ptx') or json.dumps(row['config'],sort_keys=True)
        if identity in seen:continue
        seen.add(identity);ranked.append(row)
        if len(ranked)==3:break
    native=[]
    for rank,row in enumerate(ranked):
        cfg=row['config']; batches=[]
        for batch in range(3):
            dest=out/f'native-candidate-{rank}-batch-{batch}'
            cmd=[sys.executable,str(Path(__file__).with_name('run_case.py')),'--backend','cuda','--operator',op,'--shape',shape,'--phase','native','--profile-launches','30','--input-dir',str(a.input_dir),'--output',str(dest),'--stages',str(cfg['num_stages']),'--num-warps',str(cfg['num_warps'])]
            if 'BM' in cfg:cmd+=['--tile-m',str(cfg['BM']),'--tile-n',str(cfg['BN'])]
            if 'BK' in cfg:cmd+=['--k-tile',str(cfg['BK'])]
            if 'ROWS' in cfg:cmd+=['--rows',str(cfg['ROWS'])]
            if not dest.exists():
                with (out/f'native-candidate-{rank}-batch-{batch}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout,check=True)
            result=json.loads((dest/'result.json').read_text())
            if result.get('status')!='passed':raise RuntimeError(f'Native candidate incomplete {dest}')
            events=[e for e in json.loads((dest/'profile.timeline.json').read_text())['traceEvents'] if e.get('ph')=='X' and 'cupti_activity' in e.get('cat','') and e.get('dur',0)>0]
            if len(events)!=30:raise RuntimeError(f'Expected30native intervals at{dest}, observed{len(events)}')
            batches.append({'samples_us':[e['dur'] for e in events],'median_us':statistics.median(e['dur'] for e in events),'source':str(dest)})
        native.append({'config':cfg,'graph_search_index':row['index'],'graph_median_us':row['median_us'],'native_batches':batches,'native_median_of_batch_medians_us':statistics.median(b['median_us'] for b in batches)})
    win=min(native,key=lambda r:r['native_median_of_batch_medians_us'])
    state['native_candidates']=native;state['native_selection']={'criterion':'minimum native median of three independent30-launch batch medians among top3distinct-binary graph candidates','config':win['config'],'search_index':win['graph_search_index'],'median_us':win['native_median_of_batch_medians_us']}
    (out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    shutil.copytree(Path(win['native_batches'][0]['source'])/'asm',out/'selected-asm-native',dirs_exist_ok=True)
    return state
for op in ['gemm','gemm_bias_gelu','softmax','layernorm','reduce_sum','transpose']:
    shapes=['128x128x128','512x512x512','257x193x320','512x512x4096'] if op.startswith('gemm') else ['256x256','1024x1024','513x257'] if op=='transpose' else ['32x256','256x1024','127x769']
    for shape in shapes:
        out=a.output/f'{op}-{shape}';result=out/'result.json'
        if result.exists() and json.loads(result.read_text()).get('status')=='passed':
            state=json.loads(result.read_text())
            if 'native_selection' not in state:state=native_select(op,shape,out,state)
            selected.append({'operator':op,'shape':shape,**state['native_selection'],'graph_winner_remeasurement':state['independent_remeasurement'],'native_candidates':state['native_candidates'],'inputs':state['inputs'],'source_result':str(result)});continue
        if out.exists():raise RuntimeError(f'Incomplete prior run {out}: inspect, do not silently overwrite/restart')
        cmd=[sys.executable,str(Path(__file__).with_name('nvidia_tune.py')),'--operator',op,'--shape',shape,'--input-dir',str(a.input_dir),'--output',str(out)]
        print('START',op,shape,flush=True)
        with (a.output/f'{op}-{shape}.log').open('w') as f:
            try: code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
            except subprocess.TimeoutExpired:code=124
        with (a.output/'execution.jsonl').open('a') as f:f.write(json.dumps({'operator':op,'shape':shape,'exit':code,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'command':cmd})+'\n')
        if code:raise RuntimeError(f'{op} {shape} failed {code}; inspect retained logs')
        state=native_select(op,shape,out,json.loads(result.read_text()));selected.append({'operator':op,'shape':shape,**state['native_selection'],'graph_winner_remeasurement':state['independent_remeasurement'],'native_candidates':state['native_candidates'],'inputs':state['inputs'],'source_result':str(result)})
        (a.output/'selection.json').write_text(json.dumps(selected,indent=2)+'\n');print('DONE_NATIVE',op,shape,state['native_selection']['config'],flush=True)
(a.output/'selection.json').write_text(json.dumps(selected,indent=2)+'\n')
print('SWEEP_DONE',flush=True)
