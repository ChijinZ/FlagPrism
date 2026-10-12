#!/usr/bin/env python3
"""Draw measured Study results; retain backend units and capture provenance."""
import argparse,csv,json,statistics,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from tcu_invocations import parse
from observations import native,read
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':12,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
colors={'cann':'#2166ac','enflame':'#d6604d','cuda':'#1b9e77'};names={'cann':'Ascend 910B4-1','enflame':'Enflame GCU300','cuda':'NVIDIA V100S'}
def save(fig,name):
 for ext in ['pdf','png','svg']:fig.savefig(a.output/(name+'.'+ext),bbox_inches='tight',dpi=180)
 plt.close(fig)
def export(name,rows):
 with (a.bundle/name).open('w') as f:
  w=csv.DictWriter(f,lineterminator='\n',fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
rows=list(csv.DictReader((a.bundle/'nested_comparison.csv').open()))
fig,axes=plt.subplots(1,3,figsize=(10.8,3.25),layout='constrained')
for ax,b in zip(axes,['cuda','enflame','cann']):
 for region,marker,color in [('outer','o',colors[b]),('inner','s','#555555')]:
  rs=[r for r in rows if r['backend']==b and r['region']==region]
  ax.plot([int(r['q']) for r in rs],[float(r['ratio']) for r in rs],marker=marker,color=color,label=region.capitalize(),lw=1.5)
  for r in rs:
   ref=float(r['reference_median']);x=int(r['q']);ax.vlines(x,float(r['baseline_min'])/ref,float(r['baseline_max'])/ref,color=color,alpha=.5,lw=1)
 ax.axhline(1,color='#999999',ls='--',lw=.8);ax.set_yscale('log');ax.set_ylim(.35,4.5);ax.set_yticks([.5,1,2,4],['0.5','1','2','4']);ax.set_title(names[b]);ax.set_xlabel('Iterations before inner region (q)');ax.set_ylabel('Nested / reference');ax.set_xticks([0,32,64,96,128]);ax.grid(alpha=.2);ax.legend()
fig.suptitle('Same request: Outer = 256 iterations, Inner = 128; final outputs verified\nPoints: medians; lines: min–max relative to the single-region median',fontsize=12)
save(fig,'study-nested-semantics')
clock=list(csv.DictReader((a.bundle/'clock_calibration.csv').open()))
if clock:
 fig,axes=plt.subplots(1,2,figsize=(9.6,3.2),layout='constrained')
 for ax,b in zip(axes,['cann','enflame']):
  for sync,marker in [(0,'o'),(1,'s')]:
   rs=sorted([r for r in clock if r['backend']==b and int(r['sync'])==sync],key=lambda r:int(r['loops']))
   ax.plot([int(r['loops']) for r in rs],[float(r['median_ticks']) for r in rs],marker=marker,label='End barrier' if sync else 'No end barrier')
  ax.set_xscale('symlog',linthresh=16);ax.set_xticks([0,16,64,256,1024],[0,16,64,256,1024]);ax.set_xlabel('Dependent FMA iterations');ax.set_ylabel('SYS_CNT ticks' if b=='cann' else 'SDK counter units');ax.set_title(names[b]);ax.legend();ax.grid(alpha=.2)
  z={int(r['sync']):r['median_ticks'] for r in clock if r['backend']==b and int(r['loops'])==0}
  ax.text(.04,.48,f"Zero work: {z.get(0)} / {z.get(1)}\n(no / with end barrier)",transform=ax.transAxes,fontsize=11)
 fig.suptitle('Endpoint intervention: identical input-readiness barrier; only end barrier changes\nZero-work controls included; instrumented interval, not unperturbed engine busy time',fontsize=12)
 save(fig,'study-endpoint-control')
# Preserve per-invocation device and per-SIP identities. No activity/name join.
tcu=[];free=[];records={}
for op in ['gemm','gemm_bias_gelu']:
 for tile in [16,64]:
  config=f'{op}-t{tile}';path=a.raw/'enflame/tcu'/config/'invocations.csv';rs=parse(path);assert len(rs)==21
  records[config]=rs
  for ordinal,r in enumerate(rs):
   for m in r['metrics']:
    tcu.append({'config':config,'capture':config,'invocation_ordinal':ordinal,'tcu_kernel_id':r['tcu_kernel_id'],'device_identifier':r['device_identifier'],'relative_start_us':r['relative_start_us'],'duration_us':r['duration_us'],'metric':m['name'],'unit':m['unit'],'value':m['value'],'scope':'TCU invocation aggregate; ID capture-local'})
  case=a.raw/'enflame/counter-free'/config;d=read(case/'result.json');assert d['status']=='passed' and d['post_profile_validation']['passed']
  ds=[e['duration_us'] for e in native(case,'enflame') if e['kind']=='kernel'];assert len(ds)==15
  free.append({'operator':op,'tile':tile,'median_us':statistics.median(ds),'min_us':min(ds),'max_us':max(ds),'native_observations':len(ds),'raw_case':str(case)})
export('tcu_invocations.csv',tcu);export('controlled_tile.csv',free)
(a.bundle/'tcu_invocations.json').write_text(json.dumps({'captures':records,'notes':['IDs are capture-local. Do not join to TOPSPTI by name.','21 invocations include warmup; the plot keeps all 21.','Per-SIP instances and instruction-family units retained.','TCU percentage denominators are SDK-defined; families can overlap.','Counter-free timings collected separately.']},indent=2)+'\n')
fig,axes=plt.subplots(1,3,figsize=(11,3.4),layout='constrained')
for op,color,offset,label in [('gemm','#2166ac',-.13,'GEMM'),('gemm_bias_gelu','#d6604d',.13,'Fused')]:
 rs=[r for r in free if r['operator']==op]
 axes[0].plot([0+offset,1+offset],[r['median_us'] for r in rs],marker='o',label=label,color=color)
 for x,r in zip([0+offset,1+offset],rs):axes[0].errorbar(x,r['median_us'],yerr=[[r['median_us']-r['min_us']],[r['max_us']-r['median_us']]],fmt='none',color=color,capsize=3)
axes[0].set_yscale('log');axes[0].set_xticks([0,1],['16 × 16','64 × 64']);axes[0].set_xlabel('Output tile (BK = 32)');axes[0].set_ylabel('Native interval (µs)');axes[0].set_title('(a) Controlled tiling, GCU300');axes[0].legend(fontsize=10);axes[0].grid(axis='y',alpha=.2)
configs=list(records)
for ax,metric,title in [(axes[1],'SIP/1D_EFFICIENCY','(b) Native 1D instruction family'),(axes[2],'SIP/MSF_EFFICIENCY','(c) Native MSF instruction family')]:
 for i,c in enumerate(configs):
  vs=[next(m['value'] for m in r['metrics'] if m['name']==metric) for r in records[c]]
  ax.scatter([i]*len(vs),vs,color='#2166ac' if c.startswith('gemm-t') else '#d6604d',s=13,alpha=.45)
  ax.plot([i-.15,i+.15],[statistics.median(vs)]*2,color='black',lw=1.4)
 ax.set_xticks(range(4),['GEMM\n16','GEMM\n64','Fused\n16','Fused\n64']);ax.set_ylabel('TCU-reported efficiency (%)');ax.set_title(title);ax.grid(axis='y',alpha=.2)
fig.suptitle('Useful detail is backend-specific: performance and instruction-family observations\nSeparate captures; percentages keep SDK denominators; MSF is not labeled as a matrix engine',fontsize=12)
save(fig,'study-native-detail')
# Static source mapping, verified tokens, not dynamic pipeline reconstruction.
ptx=(a.raw/'cuda/full/gemm_bias_gelu-128x128x128-v0-baseline/asm/ptx').read_text();gcu=(a.raw/'enflame/full/gemm_bias_gelu-128x128x128-v0-baseline/asm/gcuir').read_text();asc=(a.bundle/'evidence/fused-128-debug.hivm.mlir').read_text()
assert '.target sm_70' in ptx and 'fma.rn.f32' in ptx and ptx.count('.visible .entry')==1
assert 'gcu.matmul' in gcu and 'math.exp' in gcu and gcu.count('gpu.kernel')==1
assert all(t in asc for t in ['@matmul_mix_aic','@matmul_mix_aiv','sync_block_set','sync_block_wait','hivm.hir.vexp'])
fig,ax=plt.subplots(figsize=(10.8,4.5));ax.set_xlim(0,10.8);ax.set_ylim(0,4.5);ax.axis('off')
def box(x,y,w,h,t,c):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.06',facecolor=c,edgecolor='#555555',lw=.7));ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=11)
def arrow(x,y,xx,yy):ax.annotate('',xy=(xx,yy),xytext=(x,y),arrowprops={'arrowstyle':'->','lw':1})
box(.4,3.75,10,.5,'One source: tiled GEMM → bias + GELU → store (128³)','#eeeeee')
for x in [1.9,5.4,8.9]:arrow(x,3.65,x,3.25)
box(.3,2.1,3.1,1.05,'NVIDIA V100S\nOne PTX entry, sm_70\nfma.rn.f32 → epilogue\n(current compiler lowering)','#dcefe8')
box(3.85,2.1,3.1,1.05,'Enflame GCU300\nOne gpu.kernel entry\ngcu.matmul (8×8 local)\n→ math.exp / epilogue','#f4d5ce')
box(7.4,2.65,3.1,.5,'Ascend AIC\nmmadL1 → workspace (gm)','#d5e6f5');box(7.4,1.65,3.1,.5,'Ascend AIV\nworkspace → vexp / epilogue','#d5e6f5');arrow(7.65,2.57,7.65,2.23);ax.text(8.95,2.4,'sync_block_set / wait',ha='center',fontsize=10)
for x,t in [(.3,'CUPTI: one kernel interval'),(3.85,'TOPSPTI: one kernel interval'),(7.4,'aclprof: one MIX_AIC task')]:box(x,.58,3.1,.55,t,'#eeeeee')
for x in [1.85,5.4,8.95]:arrow(x,1.52,x,1.2)
ax.text(5.4,.17,'Compiler structure and native observation scope; no internal overlap or duration inferred.',ha='center',fontsize=10)
save(fig,'study-fused-decomposition')

# Selected emitted pipeline stages; horizontal position is NOT a time axis.
assert all(t in ptx for t in ['ld.global','st.shared','ld.shared','bar.sync','fma.rn.f32','ex2.approx.f32','st.global'])
assert all(t in gcu for t in ['gcu.border','gpu.barrier','gcu.matmul','math.exp','triton_gcu.store'])
assert all(t in asc for t in ['hivm.hir.nd2nz','hivm.hir.mmadL1','hivm.hir.fixpipe','sync_block_set','sync_block_wait','hivm.hir.load','hivm.hir.vexp','hivm.hir.store'])
fig,ax=plt.subplots(figsize=(11.4,6.3));ax.set_xlim(0,11.4);ax.set_ylim(0,6.3);ax.axis('off')
xs=[1.55,4,6.45,8.9];w=2.1;h=.72
stage_colors={'move':'#e3eef8','compute':'#fbe3cd','sync':'#ededed'}
def stage(x,y,text,kind):
 ax.add_patch(FancyBboxPatch((x,y-h/2),w,h,boxstyle='round,pad=.04',facecolor=stage_colors[kind],edgecolor='#555555',lw=.8))
 ax.text(x+w/2,y,text,ha='center',va='center',fontsize=11.5)
def flow(x1,y1,x2,y2,dashed=False):
 ax.annotate('',xy=(x2,y2),xytext=(x1,y1),arrowprops={'arrowstyle':'->','lw':1.1,'linestyle':'--' if dashed else '-','color':'#444444'})
ax.text(5.7,6.05,'Fused GEMM+bias+GELU: emitted data paths and synchronization',ha='center',fontsize=14)
for y,label,entries in [
 (5.15,'V100S\nPTX', [('Global A/B\nld.global','move'),('Shared staging\nst/ld.shared\nbar.sync','move'),('Dot + GELU\nfma.rn.f32 / ex2','compute'),('Global output\nst.global','move')]),
 (3.85,'GCU300\nGCU IR', [('Input staging\nload / gpu.barrier','move'),('Local matmul\ngcu.matmul (8×8)','compute'),('Bias + GELU\nmath.exp\nvector ops','compute'),('Global output\ntriton_gcu.store','move')]),
 (2.45,'910B4-1\nAIC', [('Global → CBUF\nnd2nz','move'),('Matrix → CC\nmmadL1','compute'),('CC → GM workspace\nfixpipe','move'),('Producer signal\nsync_block_set (0)','sync')]),
 (1.05,'910B4-1\nAIV', [('Consumer wait\nsync_block_wait (0)','sync'),('GM workspace → UB\nload (+ bias)','move'),('Bias + GELU in UB\nvexp / vector ops','compute'),('UB → global output\nstore','move')])]:
 ax.text(.12,y,label,ha='left',va='center',fontsize=12,weight='bold')
 for x,(text,kind) in zip(xs,entries):stage(x,y,text,kind)
 for x,xnext in zip(xs,xs[1:]):flow(x+w+.04,y,xnext-.04,y)
# Compiler-level dependencies, with event families taken from the saved HIVM.
ax.text(3.8,3.02,'MTE2 ↔ MTE1 set/wait',ha='center',fontsize=11)
ax.text(6.5,3.02,'M → FIX set/wait',ha='center',fontsize=11)
# Route the cross-core dependency through the gap, without suggesting duration.
ax.plot([9.95,9.95,2.6],[2.04,1.75,1.75],ls='--',color='#444444',lw=1.1)
flow(2.6,1.75,2.6,1.47,True)
ax.text(6.3,1.82,'Cross-core dependency, flag 0',ha='center',fontsize=11)
ax.text(6.5,.45,'AIV: MTE2 → V and V → MTE3 set/wait',ha='center',fontsize=11)
ax.text(5.7,.08,'Blue: data movement / memory; orange: computation; grey: cross-core synchronization.\nSelected emitted dependencies; box positions/widths carry no timing or overlap information.',ha='center',fontsize=11)
save(fig,'study-pipeline-structure')
print(json.dumps({'tcu_invocations':sum(map(len,records.values())),'counter_free_intervals':60,'figures':'nested, endpoint (if available), native-detail, fused-decomposition, pipeline-structure'}))
