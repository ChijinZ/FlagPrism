#!/usr/bin/env python3
"""Measured issue gates, independent PMU activities and held-out fused-port recovery."""
import argparse,csv,hashlib,json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import numpy as np
from observations import native
p=argparse.ArgumentParser();p.add_argument('--ascend',type=Path,required=True);p.add_argument('--cuda',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
s=json.loads((a.ascend/'summary.json').read_text());selected=['P32_K32','R_K32_K256','R_KMN64_K256'];native_stats=s['native']['frozenN-staged-holdout']
issues=list(csv.DictReader((a.ascend/'selected_actual_issue_traces.csv').open()))
plt.rcParams.update({'font.size':8,'axes.titlesize':8,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
blue='#28689d';green='#16836b';gray='#747474'
fig=plt.figure(figsize=(3.3,6.0),layout='constrained');gs=fig.add_gridspec(4,1,height_ratios=[1.1,1.65,1.15,1.05]);fig.get_layout_engine().set(h_pad=.06,w_pad=.025)
ax=fig.add_subplot(gs[0]);ax.set(xlim=(0,10),ylim=(0,4));ax.axis('off');ax.set_title('(a) Compiled producer–consumer mapping',loc='left',pad=2)
def box(x,y,w,h,label,face='#eef3f7'):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',fc=face,ec='#555555',lw=.6));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8)
def arrow(x,y,u,v):ax.annotate('',xy=(u,v),xytext=(x,y),arrowprops={'arrowstyle':'->','lw':.7,'color':'#555555'})
box(.5,2.65,9,.85,'AIC: load A/B → Cube → write X')
arrow(5,2.60,2.7,1.65);arrow(5,2.60,7.3,1.65)
ax.text(5,1.95,'event 0',ha='center',fontsize=8)
box(.4,.45,4.2,1.1,'AIV0\nwait, GELU, store',face='#f7f0df');box(5.4,.45,4.2,1.1,'AIV1\nwait, GELU, store',face='#f7f0df')
ax=fig.add_subplot(gs[1]);ax.set_title('(b) Program-0 control (one call/config)',loc='left',pad=29)
joint_path=a.ascend/'joint-sys/summary.json';joint=json.loads(joint_path.read_text())
assert joint['association_status']=='verified_shared_reported_SYS_epoch' and joint['tick_ns']==20
joint_issues=list(csv.DictReader((a.ascend/'joint-sys/selected_issue_points.csv').open()))
trace_provenance=[];labels=[];body_color='#b8c7d0';wait_color='#d9a441'
for cfg_index,key in enumerate(selected[:2]):
 info=joint['configurations'][key];actors=info['selected_actor_values']
 assert len(actors)==3 and len({(r['stream_id'],r['task_id'],r['start_SYS']) for r in actors})==1
 for actor_index,r in enumerate(actors):
  y=6-actor_index if cfg_index==0 else 2-actor_index;start=r['body_enter_us'];end=r['body_exit_us']
  ax.barh(y,end-start,left=start,height=.45,color=body_color,zorder=1)
  if r['actor']=='AIC':
   loops=[v for v in joint_issues if v['configuration']==key];assert len(loops)==info['loop_count']
   ax.plot([float(v['MMA_helper_issue_enter_us']) for v in loops],[y]*len(loops),'|',color=blue,ms=4,mew=.55,zorder=3)
   signal=r['signal_enter_us'];ax.plot(signal,y,'D',ms=3,color=blue,zorder=4)
   ax.text(start,y+.33,f"{info['loop_count']} K iterations",fontsize=8,va='bottom')
  else:
   w0=r['wait0_enter_us'];w1=r['wait0_return_us'];assert start<=w0<=w1<=end
   ax.barh(y,w1-w0,left=w0,height=.45,color=wait_color,zorder=2)
   ax.plot([w1,w1],[y-.25,y+.25],color='#795715',lw=.7,zorder=3)
  labels.append(('P' if cfg_index==0 else '+K')+' '+r['actor'])
 trace_provenance.append({'config':key,'source_pid':info['selected_source_pid'],'packet':info['selected_packet'],'source':str(joint_path),'loops':info['loop_count']})
ax.axhline(3,color='#cccccc',lw=.5)
ax.set(xlim=(0,67),ylim=(-.65,6.8),xlabel='µs since common SYS start of each call')
ax.set_yticks([6,5,4,2,1,0],labels);ax.grid(axis='x',alpha=.15,lw=.4)
handles=[Line2D([],[],lw=4,color=body_color,label='Source body'),Line2D([],[],lw=4,color=wait_color,label='wait0'),Line2D([],[],marker='D',ls='',ms=3,color=blue,label='Signal issue')]
handles.append(Line2D([],[],marker='|',ls='',ms=4,color=blue,label='MMA issue'))
ax.legend(handles=handles,loc='lower left',bbox_to_anchor=(0,1),frameon=False,ncol=2,handletextpad=.3,columnspacing=.55,borderaxespad=0)
ax.set_ylim(-.65,7.2)

ax=fig.add_subplot(gs[2]);ax.set_title('(c) Program-0 activity (independent PMU)',loc='left')
pmu_values={}
for i,key in enumerate(selected[:2]):
 pmu=s['pmu']['pmu-staged-'+key]['PipeUtilization.csv']['program0_rows'];aic=next(r for r in pmu if r['sub_block_id']=='cube0');aiv=next(r for r in pmu if r['sub_block_id']=='vector0')
 ys=[float(aic['aic_mte2_time(us)']),float(aiv['aiv_scalar_wait_id0_time(us)']),float(aiv['aiv_vec_time(us)'])];pmu_values[key]=ys
 ax.bar(np.arange(3)+(i-.5)*.30,ys,.27,color=blue,alpha=1 if i==0 else .45,label='P' if i==0 else '+K')
 for j,v in enumerate(ys):
  if j!=2:ax.text(j+(i-.5)*.30,v*1.15,f'{v:.2f}',ha='center',fontsize=8)
assert pmu_values[selected[0]][2]==pmu_values[selected[1]][2]
ax.text(2,.40,f'{pmu_values[selected[0]][2]:.3f} (both)',ha='center',fontsize=8)
ax.set(yscale='log',ylim=(.16,200),ylabel='Reported activity (µs)');ax.set_xticks(range(3),['AIC\nMTE2','AIV0\nwait0','AIV0\nvector']);ax.grid(axis='y',alpha=.15,lw=.4);ax.legend(frameon=False,ncol=1,loc='upper right',handlelength=1.0)
ax=fig.add_subplot(gs[3]);ax.set_title('(d) Held-out whole launch (no probes)',loc='left')
nvidia=[];raw_nvidia=[]
for batch in range(3):
 path=a.cuda/f'long-k-frozen-n-b{batch}';r=json.loads((path/'result.json').read_text());assert r['status']=='passed' and r['validation']['passed']
 e=[e for e in native(path,'cuda') if e.get('kind')=='kernel' and e.get('duration_us',0)>0];assert len(e)==30;nvidia.append(statistics.median(e['duration_us'] for e in e));raw_nvidia.append(str(path/'result.json'))
ys=[statistics.median(nvidia)]+[native_stats[k]['median_us'] for k in selected]
ax.bar(range(4),ys,color=[green,blue,blue,blue],alpha=.82,width=.65)
for i,(v,ms) in enumerate(zip(ys,[nvidia]+[native_stats[k]['batch_medians_us'] for k in selected])):
 ax.scatter(i+np.array([-.055,0,.055]),ms,s=7,color='#222222',zorder=3)
 ax.text(i,v+10,f'{v:.1f}',ha='center',fontsize=8)
ax.set(ylim=(0,420),ylabel='Latency (µs)');ax.set_xticks(range(4),['NVIDIA','P\nBK32','+K\nBK256','+K,MN\n64² tile']);ax.grid(axis='y',alpha=.15,lw=.4)
ax.set_xlabel('Larger MN tile: programs 256 → 64\nSource A/B: 128 → 64 MiB (logical)', fontsize=8)
speedup=ys[1]/ys[3];ax.text(.5,.94,f'{speedup:.2f}× (P / +K,MN)',transform=ax.transAxes,ha='center',fontsize=8)
a.output.mkdir(parents=True,exist_ok=True)
for ext in ['pdf','svg','png']:fig.savefig(a.output/f'study-actor-case.{ext}',dpi=300)
plt.close(fig)
(a.output/'study-actor-case-data.json').write_text(json.dumps({'summary_sha256':hashlib.sha256((a.ascend/'summary.json').read_bytes()).hexdigest(),'trace':trace_provenance,'pmu_program0_us':pmu_values,'whole_launch_us':dict(zip(['NVIDIA N',*selected],ys)),'nvidia_source':raw_nvidia,'target_speedup':speedup,'latency_statistics':{'NVIDIA':'median of three batch medians; all90 raw calls retained','targets':'pooled median of90 calls; three batch medians also displayed'},'derived_source_work':s['derived_source_work'],'scope':'(a) static dependencies; (b) same-invocation AIC/AIV source-control timeline in an empirically matched common reported SYS epoch, warm-up0 SDK application replay. Body bars are source entry/exit; wait0 bars are scalar wait brackets; ticks are MMA-helper dispatch points; diamonds signal issue. Not hardware occupancy or standalone GELU durations. (c) independent native-PMU replay activities, may overlap and are not added; separate cache/invocation from trace. (d) heldout native latencies, instrumentation disabled, 3x30 each.'},indent=2)+'\n')
print('Targetspeedup',speedup,'latencies',ys)
