import sys,json,statistics,re,hashlib
from pathlib import Path
for ancestor in Path(__file__).resolve().parents:
 if (ancestor/'tcu_invocations.py').exists():sys.path.insert(0,str(ancestor));break
 if (ancestor/'FlagPrism/experiments/study/tcu_invocations.py').exists():sys.path.insert(0,str(ancestor/'FlagPrism/experiments/study'));break
from tcu_invocations import parse
root=Path(__file__).parent
data=root/'captures' if (root/'captures').exists() else root
p=json.loads((data/'independent-baseline/result.json').read_text());assert p['status']=='passed' and p['validation']['passed'];summary={'scope':'bounded matrixpath sanityappendix, controlnative1batch30calls not finalindependent3batchoptimizationcase','independent_original_baseline':p['statistics'],'native_controls':[],'tcu':[],'native_original_reference':'../enflame-overview-r010/gemm-512x512x512-v0-b*/profile/ai/events.jsonl'}
for name in ['fixedgrid-w1','fixedgrid-w2','tile64-w4','tile64-w1']:
 d=data/name;r=json.loads((d/'result.json').read_text());assert r['status']=='passed' and r['validation']['passed'];es=[json.loads(x) for x in (d/'profile/ai/events.jsonl').read_text().splitlines()];ks=[e for e in es if e.get('kind')=='kernel' and e['name']=='matmul'];assert len(ks)==30;v=[e['duration_us'] for e in ks];ir=(d/'asm/gcuir').read_text();summary['native_controls'].append({'name':name,'config':r['requested_compile_config'],'grid':r['grid'],'samples_us':v,'median_us':statistics.median(v),'matmul_operand_types':re.findall(r'"gcu.matmul"[^\n]*',ir),'source':str(d.relative_to(root)),'validation':r['validation'],'input_sha256':r['input_hashes']})
for name in ['original','fixedgrid-w1','fixedgrid-w2','tile64-w4','tile64-w1']:
 d=root/'tcu'/name;rs=parse(d/'invocations.csv');assert len(rs)==9
 results=[json.loads(f.read_text()) for f in (d/'runs').glob('*/result.json')];assert results and all(r['status']=='passed' and r['validation']['passed'] for r in results)
 for key in ['SIP/2D_EFFICIENCY','SIP/1D_EFFICIENCY','SIP/BUSY']:
  ms=[m for r in rs for m in r['metrics'] if m['name']==key];assert len(ms)==9 and all(len(m['instances'])==24 for m in ms);v=[m['value'] for m in ms];summary['tcu'].append({'config_name':name,'metric':key,'unit':ms[0]['unit'],'median_value':statistics.median(v),'all_values':v,'samples':9,'instances_per_record':24,'source':str((d/'invocations.csv').relative_to(root)),'scope':'originalbinary applicationreplay, capture-localIDs; nineinclude6initial/warmupcalls +3measurementcalls'})
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('matrixsanityverified')
