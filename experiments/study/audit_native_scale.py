#!/usr/bin/env python3
"""Native whole-kernel/task scale consistency; not an internal accuracy oracle."""
import argparse,json,statistics,shutil
from pathlib import Path
import numpy as np
from observations import native,read
p=argparse.ArgumentParser();p.add_argument('--cuda',type=Path,required=True);p.add_argument('--cann',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);data={}
for b,root in [('cuda',a.cuda),('cann',a.cann)]:
 levels={}
 for n in [0,16,64,256,1024]:
  case=root/(f'n{n}' if b=='cuda' else f'n{n}-s1');d=read(case/'result.json');assert d['status']=='passed' and d['correct'] and d['sync']==1 and not d['nested'];es=[e for e in native(case,b) if e['kind']=='kernel'];assert len(es)==15
  pairs=[(sm['delta_ticks_mod32'],event['duration_us']) for sm,event in zip(d['samples'],es)];levels[n]={'median_ticks':statistics.median(x for x,y in pairs),'median_native_us':statistics.median(y for x,y in pairs),'pairs':pairs,'source_result':str(case/'result.json')}
  dest=a.output/'calibration-captures'/b/f'n{n}';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(case/'result.json',dest/'result.json');(dest/'native.json').write_text(json.dumps(es,indent=2)+'\n')
 train=[0,64,1024];x=np.array([levels[n]['median_ticks'] for n in train]);y=np.array([levels[n]['median_native_us'] for n in train]);slope,intercept=np.polyfit(x,y,1);hold={str(n):{'predicted_native_us':float(slope*levels[n]['median_ticks']+intercept),'observed_native_us':levels[n]['median_native_us'],'residual_us':float(levels[n]['median_native_us']-(slope*levels[n]['median_ticks']+intercept))} for n in [16,256]}
 expected=.001 if b=='cuda' else .02;data[b]={'train_levels':train,'holdout_levels':[16,256],'partition':'specified after exploratory prior data existed, before this fit; not preregistered/blinded','levels':levels,'tick_period_us_fit':float(slope),'documented_tick_period_us':expected,'scale_ratio_to_documented':float(slope/expected),'outside_bracket_intercept_us':float(intercept),'holdout':hold,'limits':'Independent whole-kernel timing scale/consistency check; does not certify internal endpoint accuracy or unperturbed busy time.'}
(a.output/'native_scale_calibration.json').write_text(json.dumps(data,indent=2)+'\n');print({k:v['tick_period_us_fit'] for k,v in data.items()})
