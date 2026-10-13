#!/usr/bin/env python3
"""Real operator profiling consequences, native captures and source mappings."""
import argparse,csv,json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':12,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
 for ext in ['pdf','png','svg']:fig.savefig(a.output/(name+'.'+ext),dpi=180,bbox_inches='tight')
 plt.close(fig)
rows=list(csv.DictReader((a.bundle/'protocol_comparison.csv').open()))
gtimer=json.loads((a.bundle/'gcu-global-timer/summary.json').read_text()) if (a.bundle/'gcu-global-timer/summary.json').exists() else None
fig,axes=plt.subplots(1,2,figsize=(10.8,3.8),layout='constrained')
for ax,op,label,config,key in [(axes[0],'gemm_bias_gelu','Fused GEMM+bias+GELU','t16','leader-global-fused128'),(axes[1],'softmax','Softmax','r1','leader-global-softmax')]:
 for i,(provider,offset,color) in enumerate([('V100 timer',-.22,'#1b9e77'),('GCU window counter',0,'#d6604d'),('GCU SDK timer adapter',.22,'#2166ac')]):
  if i==2 and gtimer is None:continue
  values=[]
  for region in ['body','output']:
   if i<2:values.append(float(next(r['ratio_of_medians'] for r in rows if r['backend']==('cuda' if i==0 else 'enflame') and r['operator']==op and r['config']==config and r['region']==region)))
   else:values.append(gtimer['same_primitive_comparison'][key][f'nested_{region}_to_single_active_{region}_ratio'])
  ax.bar([j+offset for j in range(2)],values,width=.20,color=color,label=provider,edgecolor='#444444',lw=.6)
  for j,v in enumerate(values):ax.text(j+offset,v*1.08,f'{v:.3f}',ha='center',va='bottom',fontsize=10)
 ax.axhline(1,color='#555555',lw=1,ls='--');ax.set_yscale('log');ax.set_ylim(.012,2);ax.set_yticks([.02,.1,1],['0.02','0.1','1']);ax.set_title(label);ax.set_xticks([0,1],['Body','Output']);ax.set_ylabel('Nested / single-active median');ax.grid(axis='y',alpha=.2)
fig.legend(*axes[0].get_legend_handles_labels(),ncol=3,loc='lower center',bbox_to_anchor=(.5,-.13),fontsize=11)
fig.suptitle('Same request: two real operators, clock-protocol reuse and adaptation\nEach provider has its own single-active reference; ratios are not timing-accuracy errors',fontsize=12)
save(fig,'study-operator-protocol')
# Actual CUDA instruction/scheduling brackets for selected recorded programs.
fig,axes=plt.subplots(2,1,figsize=(10.8,6.3),layout='constrained')
for ax,op,cfg,title in [(axes[0],'gemm_bias_gelu','t16','Fused GEMM+bias+GELU, tile16²'),(axes[1],'softmax','r1','Softmax, 1 row/program')]:
 d=json.loads((a.raw/'cuda/operators'/f'{op}-{cfg}-nested/result.json').read_text());records=d['samples'][7]['program_records'][:8]
 def signed(x):return ((x+2**31)%2**32)-2**31
 origin=records[0][0]&0xffffffff;earliest=min(signed((r[0]&0xffffffff)-origin) for r in records)
 for i,v in enumerate(records):
  start=signed((v[0]&0xffffffff)-origin)-earliest;dur=(v[1]-v[0])&0xffffffff;outstart=signed((v[2]&0xffffffff)-origin)-earliest;outdur=(v[3]-v[2])&0xffffffff
  ax.broken_barh([(start/1000,dur/1000)],(i-.28,.52),facecolors='#b9ded1',edgecolors='#777777',lw=.4)
  ax.broken_barh([(outstart/1000,outdur/1000)],(i-.28,.52),facecolors='#1b9e77')
 ax.set_yticks(range(len(records)),[f'({v[4]},{v[5]})' for v in records]);ax.invert_yaxis();ax.set_ylabel('Program ID');ax.set_title(title);ax.set_xlabel('Time (µs), origin = earliest shown body start');ax.grid(axis='x',alpha=.2)
fig.suptitle('V100 internal source-region brackets: light = body, dark = output\nEight program instances from recorded invocation 7; these are instrumented brackets',fontsize=12)
save(fig,'study-cuda-operator-timeline')
# Softmax mapping: every label is checked against emitted artifacts.
ptx=(a.raw/'cuda/operators/softmax-r1-nested/asm/ptx').read_text();gcu=(a.raw/'enflame/operators/softmax-r1-nested/asm/gcuir').read_text()
assert all(x in ptx for x in ['shfl.sync','ex2','st.global'])
assert all(x in gcu for x in ['gpu.barrier','math.exp'])
fig,ax=plt.subplots(figsize=(10.8,3.9));ax.set_xlim(0,10.8);ax.set_ylim(0,3.9);ax.axis('off')
def box(x,y,w,h,text,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.04',facecolor=color,edgecolor='#555555',lw=.8));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=12)
def arrow(x,y,xx,yy):ax.annotate('',xy=(xx,yy),xytext=(x,y),arrowprops={'arrowstyle':'->','lw':1})
box(.25,3.05,10.3,.55,'Softmax source: load → max / exp / sum → divide → store; output region = divide / store','#eeeeee')
for x in [1.8,5.4,9]:arrow(x,2.96,x,2.6)
box(.25,.95,3.1,1.6,'V100: one CTA/program\nld.global\nshfl.sync reductions / ex2\ndivide → st.global\nGlobal timer brackets','#dcefe8')
box(3.85,.95,3.1,1.6,'GCU300: one kernel entry\nload / gpu.barrier\nlocal reduction / math.exp\ndivide → output staging\nbegin/end counter protocol','#f4d5ce')
box(7.45,.95,3.1,1.6,'Ascend: one AIV actor\nGM → UB / MTE2→V wait\nvector reduction / exp\ndivide → V→MTE3 wait\nUB → GM / PIPE_ALL','#d5e6f5')
ax.text(5.4,.42,'The shared request succeeds only where actor mapping, endpoints and clock protocol are preserved.\nCompiler paths and source-region brackets; no inferred engine overlap.',ha='center',fontsize=11)
save(fig,'study-softmax-mapping')
print('Saved actual-operator protocol comparisons, V100 internal brackets and softmax mapping')
# Actor-local measured pipeline segments, without an assumed cross-actor origin.
asc=a.bundle/'ascend/summary.json'
if asc.exists():
 ad=json.loads(asc.read_text());fig,axes=plt.subplots(2,1,figsize=(10.8,5.1),layout='constrained')
 palette={'readiness_wait':'#b2182b','workspace_transfer':'#2166ac','epilogue_with_bias_load':'#ef8a62','output_store':'#67a9cf','input_transfer':'#2166ac','normalization_compute':'#ef8a62'}
 for ax,case,title in [(axes[0],'fused128-completion-run','Fused GEMM+bias+GELU: one AIC + two AIV actors for program 0'),(axes[1],'softmax-completion-v2-run','Softmax: first four AIV program instances')]:
  data=json.loads(Path(ad['cases'][case]['source_result']).read_text());sm=data['samples'][7];actors=[x for x in sm['actors'] if x['program_id']==0] if case.startswith('fused') else sm['actors'][:4]
  ticks=ad['clock']['ticks_per_us']
  for i,actor in enumerate(actors):
   b0,b1=actor['body'];ax.broken_barh([(0,(b1-b0)/ticks)],(i-.28,.56),facecolors='#dddddd',edgecolors='#777777',lw=.5)
   for key,color in palette.items():
    if key not in actor:continue
    start,end=actor[key];x=(start-b0)/ticks;duration=(end-start)/ticks
    if duration:ax.broken_barh([(x,duration)],(i-.28,.56),facecolors=color)
    else:ax.plot([x],[i],marker='|',ms=12,color=color)
   if 'output' in actor:
    out0,out1=actor['output'];ax.plot([(out0-b0)/ticks,(out1-b0)/ticks],[i-.38,i-.38],color='#762a83',lw=1.8,marker='|',ms=7)
  ax.set_yticks(range(len(actors)),[f"{x['actor']} p{x['program_id']} s{x['subblock_id']}"+(' (body only)' if x['actor']=='AIC' else '') for x in actors]);ax.invert_yaxis();ax.set_title(title);ax.set_xlabel('µs since each actor body start (separate origins)');ax.grid(axis='x',alpha=.2)
 import matplotlib.patches as mp
 handles=[mp.Patch(color='#dddddd',label='Body'),mp.Patch(color='#b2182b',label='Wait'),mp.Patch(color='#2166ac',label='Completion-fenced input/workspace'),mp.Patch(color='#ef8a62',label='Completion-fenced output compute'),mp.Patch(color='#67a9cf',label='Compute-ready → store barrier')]
 from matplotlib.lines import Line2D
 handles.append(Line2D([0],[0],color='#762a83',marker='|',label='Requested output bracket'))
 fig.legend(handles=handles,ncol=3,loc='lower center',bbox_to_anchor=(.5,-.13),fontsize=11)
 fig.suptitle('Ascend internal intervals from recorded launch 10 (sample index 7)\nActor-local, completion-fenced SYS_CNT brackets; no cross-actor overlap inferred',fontsize=12)
 save(fig,'study-ascend-operator-pipeline')
 # Plot distributions of per-launch actor medians, not independent actor replicates.
 launch=list(csv.DictReader((a.bundle/'ascend/launch-regions.csv').open()));fig,axes=plt.subplots(1,2,figsize=(10.8,3.65),layout='constrained')
 configurations=[('fused128-fenced-delay-post-run',0),('fused128-fenced-delay-half-run',8192),('fused128-fenced-delay-pre-run',16384)]
 for ax,actor,region,title in [(axes[0],'AIC','producer_signal','Producer interval before signal'),(axes[1],'AIV','readiness_wait','Consumer readiness wait')]:
  for case,before in configurations:
   vals=[float(r['median_ticks'])/50 for r in launch if r['capture_id']==case and r['actor']==actor and r['region']==region];assert len(vals)==15
   ax.scatter([before]*len(vals),vals,s=20,alpha=.5,color='#2166ac' if actor=='AIC' else '#b2182b');med=statistics.median(vals);ax.plot([before-650,before+650],[med]*2,color='black',lw=1.5)
  ax.set_xticks([0,8192,16384],['0','8192','16384']);ax.set_xlabel('NOPs before signal (total = 16384)');ax.set_ylabel('Per-launch actor median (µs)');ax.set_title(title);ax.grid(axis='y',alpha=.2)
 fig.suptitle('Fixed mathematical work + fixed total auxiliary work; identical producer completion fence\nMove auxiliary work across the original signal; AIV code and wait endpoints stay identical',fontsize=12)
 save(fig,'study-readiness-control')
# Same scalar gate observations vs explicit completion fences.
if asc.exists():
 cases=ad['cases'];fig,axes=plt.subplots(1,2,figsize=(10.8,3.5),layout='constrained')
 for ax,op,old,new,regions,labels in [(axes[0],'Fused GEMM','fused128-instrumented-run','fused128-completion-run',['AIV:workspace_transfer','AIV:epilogue_with_bias_load','AIV:output_store'],['Workspace','Bias/GELU','Suffix to store']),(axes[1],'Softmax','softmax-instrumented-native','softmax-completion-v2-run',['AIV:input_transfer','AIV:normalization_compute','AIV:output_store'],['Input','Normalize','Suffix to store'])]:
  for name,offset,color,label in [(old,-.18,'#999999','Original issue/gate endpoints'),(new,.18,'#2166ac','Explicit completion-fenced endpoints')]:
   vals=[cases[name]['regions'][r]['median_of_launch_medians_ticks'] for r in regions];ax.bar([i+offset for i in range(3)],vals,width=.34,color=color,label=label)
  ax.set_xticks(range(3),labels);ax.set_title(op);ax.set_ylabel('Median of launch medians (ticks)');ax.grid(axis='y',alpha=.2)
 fig.legend(*axes[0].get_legend_handles_labels(),ncol=2,loc='lower center',bbox_to_anchor=(.5,-.13),fontsize=11)
 fig.suptitle('Timing endpoints must synchronize the observer pipeline with the observed work\nSame inputs/math; explicit PIPE_ALL fences perturb scheduling; zero ticks are unresolved',fontsize=12)
 save(fig,'study-completion-endpoints')
# Independent native whole-kernel reference checks the timer scale, not region truth.
cal=json.loads((a.bundle/'native_scale_calibration.json').read_text());fig,axes=plt.subplots(1,3,figsize=(10.8,3.5),layout='constrained')
gcal=gtimer['empirical_calibration'] if gtimer else None
for ax,b,title in zip(axes,['cuda','cann','enflame'],['V100 global timer','Ascend SYS_CNT','GCU SDK timer (empirical scale)']):
 if b=='enflame':
  if gcal is None:continue
  levels=gcal['levels'];period=gcal['model_fit']['tick_period_us'];intercept=gcal['model_fit']['intercept_us'];slope=1
 else:
  levels=cal[b]['levels'];period=cal[b]['documented_tick_period_us'];intercept=cal[b]['outside_bracket_intercept_us'];slope=cal[b]['tick_period_us_fit']/period
 for n in [0,16,64,256,1024]:
  row=levels[str(n)];x=row['median_ticks']*period;y=row.get('median_native_us',row.get('median_native_us'))
  if b=='enflame':y=row['median_native_us']
  ax.scatter([x],[y],marker='o' if n in [0,64,1024] else 's',s=35,color='#2166ac' if n in [0,64,1024] else '#d6604d')
 xmin=min(v['median_ticks']*period for v in levels.values());xmax=max(v['median_ticks']*period for v in levels.values());ax.plot([xmin,xmax],[slope*xmin+intercept,slope*xmax+intercept],color='#777777',ls='--',lw=1)
 ax.set_title(title,fontsize=11);ax.set_xlabel('Recorded bracket (µs)');ax.set_ylabel('Native whole-kernel/task (µs)');ax.grid(alpha=.2)
fig.suptitle('Single-program scale check: circles = fitting levels, squares = held-out levels\nIndependent endpoint/collection path; same physical oscillator is not ruled out',fontsize=12)
save(fig,'study-native-scale-check')

# Pair the source/actor mapping with measured elapsed intervals in the main pipeline figure.
import subprocess,sys
subprocess.run([sys.executable,str(Path(__file__).with_name("plot_timed_pipeline.py")),"--bundle",str(a.bundle),"--output",str(a.output)],check=True)
