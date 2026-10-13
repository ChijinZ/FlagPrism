#!/usr/bin/env python3
"""Real tail-Softmax mapping, independent intervention, and native replay counters."""
import argparse,json,statistics,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from observations import native
p=argparse.ArgumentParser();p.add_argument('--gcu',type=Path,required=True);p.add_argument('--cuda',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
g=json.loads((a.gcu/'summary.json').read_text());mapping=json.loads((a.gcu/'static-column-mapping.json').read_text())
plt.rcParams.update({'font.size':8,'axes.titlesize':8,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
colors={'cuda':'#16836b','gcu':'#c55a42'};counts=[4,2,1];values={'cuda':{},'gcu':{}}
provenance={'gcu_summary_sha256':hashlib.sha256((a.gcu/'summary.json').read_bytes()).hexdigest(),'mapping':mapping,'native_records':[]}
expected_hashes=None
for w in counts:
    values['cuda'][w]=[];values['gcu'][w]=[]
    for b in range(3):
        for backend,case in [('cuda',a.cuda/f'softmax-w{w}-b{b}'),('gcu',a.gcu/f'native/b{b}-w{w}')]:
            r=json.loads((case/'result.json').read_text());assert r['status']=='passed' and r['validation']['passed'] and r['post_profile_validation']['passed']
            assert r['requested_compile_config']['ROWS']==1 and r['requested_compile_config']['num_warps']==w
            hashes=r['input_hashes'];assert expected_hashes is None or hashes==expected_hashes;expected_hashes=hashes
            e=[e for e in native(case,'cuda' if backend=='cuda' else 'enflame') if e.get('kind')=='kernel' and e.get('duration_us',0)>0];assert len(e)==30
            ds=[e['duration_us'] for e in e];values[backend][w].append(statistics.median(ds))
            provenance['native_records'].append({'backend':backend,'groups':w,'batch':b,'median_us':statistics.median(ds),'samples':ds,'result':str(case/'result.json'),'result_sha256':hashlib.sha256((case/'result.json').read_bytes()).hexdigest()})
fig,axs=plt.subplots(3,1,figsize=(3.3,5.5),layout='constrained');fig.get_layout_engine().set(h_pad=.06,w_pad=.03);fig.suptitle('Tail softmax: 127 × 769',fontsize=8)
ax=axs[0];x=np.arange(4)
for key,label,off in [('nvidia','NVIDIA: striped',-.17),('gcu','GCU: contiguous',.17)]:
    c=colors['cuda' if key=='nvidia' else 'gcu'];ys=mapping[key]['counts'];assert sum(ys)==769
    ax.bar(x+off,ys,.30,color=c,alpha=.8,label=label)
    for i,y in enumerate(ys):ax.text(i+off,max(y,7)+5,str(y),ha='center',fontsize=8)
ax.set(title='(a) Four-group useful columns (compiled)',ylabel='Useful columns',ylim=(0,520))
ax.set_xticks(x,['0','1','2','3']);ax.set_xlabel('Execution-group index');ax.set_yticks([0,128,256]);ax.legend(loc='upper right',frameon=False,fontsize=8,handlelength=.8,ncol=1,columnspacing=.8)
ax=axs[1]
ratios={}
for backend,label in [('cuda','NVIDIA'),('gcu','GCU')]:
    ys=[statistics.median(values[backend][w])/statistics.median(values[backend][4]) for w in counts];ratios[backend]=ys
    ax.plot(range(3),ys,'o-',ms=3,lw=1,color=colors[backend],label=label)
    for i,w in enumerate(counts):
        individual=np.array(values[backend][w])/np.array(values[backend][4]);ax.scatter(i+np.array([-.025,0,.025]),individual,s=6,color=colors[backend],alpha=.7)
ax.axhline(1,color='#888888',ls=':',lw=.7);ax.set(title='(b) Same request, opposite latency response',ylabel='Latency / own 4-group port',ylim=(.5,1.30));ax.set_xticks(range(3),['4\nexchange\n2 barriers','2\nexchange\n2 barriers','1\nno exchange\n0 barriers']);ax.set_xlabel('Source worker request (num_warps)');ax.legend(loc='upper left',frameon=False,ncol=2,handlelength=1.1)
speedup=statistics.median(values['gcu'][4])/statistics.median(values['gcu'][1]);ax.text(1.22,.72,f'GCU: {speedup:.2f}× faster',fontsize=8,color=colors['gcu'])
ax=axs[2]
for metric,label,marker,ls in [('SIP/1D_EFFICIENCY','1D instructions','o','-'),('SIP/MSF_EFFICIENCY','Special math','s','--')]:
    ys=[next(r['median_value'] for r in g['tcu'] if r['work_items']==w and r['metric']==metric) for w in counts]
    ax.plot(range(3),ys,marker=marker,ls=ls,lw=1,ms=3,color=colors['gcu'],label=label)
ax.set(title='(c) SDK cycles (independent replay)',ylabel='Reported cycle share (%)',ylim=(0,3.55));ax.set_xticks(range(3),['4','2','1']);ax.set_xlabel('Vector work-items per row');ax.legend(frameon=False,ncol=2,loc='upper left',handlelength=1.2)
for ax in axs:ax.grid(axis='y',alpha=.15,lw=.5)
a.output.mkdir(parents=True,exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(a.output/f'study-cooperative-case.{ext}',dpi=300)
plt.close(fig)
provenance.update(native_batch_medians_us=values,relative_latency=ratios,gcu_speedup=speedup,input_sha256=expected_hashes,width_inches=3.3,scope='Static counts do not measure utilization; warp and vector-item capacities differ. Native latencies uninstrumented, three batches x30 per choice. TCU replay counters are independent captures,21 calls incl6initial/warmups,24SIPs; not GPU occupancy or exclusive wall-time fractions.')
(a.output/'study-cooperative-case-data.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('GCU speedup:',speedup,'native medians:',values)
