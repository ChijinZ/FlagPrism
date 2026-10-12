#!/usr/bin/env python3
"""Publication artifacts from collected measurements; never manufacture intervals."""
import argparse,json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
p=argparse.ArgumentParser();p.add_argument('--ascend',type=Path,required=True);p.add_argument('--enflame',type=Path,required=True);p.add_argument('--cuda',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':9,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
colors={'cann':'#2166ac','enflame':'#d6604d','cuda':'#1b9e77'}
ops=['gemm','gemm_bias_gelu','softmax','layernorm','reduce_sum','transpose']
labels=['GEMM','GEMM + bias + GELU','Softmax','LayerNorm','Reduce-sum','Transpose']
from observations import read, native
def save(fig,name):
 for suffix in ['pdf','png','svg']:fig.savefig(a.output/(name+'.'+suffix),dpi=190,bbox_inches='tight')
 plt.close(fig)
# Real kernel/task distributions, no event-stream substitute.
fig,axes=plt.subplots(2,3,figsize=(10.6,5.3),layout='constrained')
for ax,op,title in zip(axes.flat,ops,labels):
 shapes=['128x128x128','512x512x512','257x193x320'] if op.startswith('gemm') else (['256x256','1024x1024','513x257'] if op=='transpose' else ['32x256','256x1024','127x769'])
 backends=[('cann',a.ascend,'native-full'),('enflame',a.enflame,'full')]+([('cuda',a.cuda,'full')] if a.cuda else [])
 for bi,(backend,root,sub) in enumerate(backends):
  for j,shape in enumerate(shapes):
   for v in [0,1]:
    case=root/sub/f'{op}-{shape}-v{v}-native';f=case/'result.json'
    if not f.exists() or read(f)['status']!='passed':continue
    ds=[e['duration_us'] for e in native(case,backend) if e['kind']=='kernel' and e.get('duration_us') is not None]
    if not ds:continue
    x=j*3+v+(bi-(len(backends)-1)/2)*.22
    med=statistics.median(ds);ax.errorbar(x,med,yerr=[[med-min(ds)],[max(ds)-med]],color=colors[backend],fmt='o' if v==0 else 's',ms=4,capsize=2)
    ax.scatter([x]*len(ds),ds,s=8,color=colors[backend],alpha=.4)
 ax.set_title(title);ax.set_yscale('log');ax.grid(axis='y',alpha=.2)
 ax.set_xticks([.5,3.5,6.5],['small\nv0 / v1','large\nv0 / v1','tail\nv0 / v1']);ax.set_ylabel('Kernel/task duration (µs)')
fig.suptitle('Observed device activity: Ascend (blue), Enflame (red)'+(', V100S (green)' if a.cuda else '')+'\nThree prewarmed launches per configuration; dots = observations, bars = min–max',fontsize=10)
save(fig,'study-device-duration')
# Separate clocks; only Enflame exposes correlated host/device activities here.
fig,axes=plt.subplots(2,1,figsize=(10,4.5),layout='constrained')
for ax,backend,root,sub in [(axes[0],'cann',a.ascend,'native-full'),(axes[1],'enflame',a.enflame,'full')]:
 case=root/sub/'gemm-128x128x128-v0-native';ev=native(case,backend)
 kernels=[e for e in ev if e['kind']=='kernel' and e.get('start_ns') and e.get('end_ns')]
 apis=[e for e in ev if e['kind']=='runtime' and e['name']=='topsModuleLaunchKernel' and e.get('start_ns') and e.get('end_ns')]
 if kernels:
  origin=min(e['start_ns'] for e in kernels+apis)
  for i,e in enumerate(kernels):
   start=(e['start_ns']-origin)/1e3;dur=(e['end_ns']-e['start_ns'])/1e3
   ax.broken_barh([(start,dur)],(.35,.3),facecolors=colors[backend]);ax.text(start+dur/2,.7,f'#{i+1}',ha='center',fontsize=8)
  for e in apis:
   start=(e['start_ns']-origin)/1e3;dur=(e['end_ns']-e['start_ns'])/1e3
   ax.broken_barh([(start,dur)],(-.25,.3),facecolors='#777777')
   linked=[k for k in kernels if k.get('correlation_key')==e.get('correlation_key') and e.get('correlation_key')]
   if len(linked)==1:ax.annotate('',xy=((linked[0]['start_ns']-origin)/1e3,.34),xytext=((e['end_ns']-origin)/1e3,.06),arrowprops={'arrowstyle':'->','lw':.8,'color':'#777777'})
 ax.set_ylim(-.45,1);ax.set_yticks([-.1,.5],['Host launch API' if apis else 'Host API: unavailable','Device activity']);ax.set_xlabel('Time since first recorded launch/kernel (µs; separate capture origin)');ax.grid(axis='x',alpha=.2);ax.set_title(('Ascend 910B4-1: aclprof task intervals' if backend=='cann' else 'Enflame GCU300: TOPSPTI API/kernel intervals')+' — GEMM 128³')
fig.suptitle('Measured whole-kernel timelines; no internal pipeline timing is inferred',fontsize=10)
save(fig,'study-capture-timeline')
# Static pipeline mapping from actual emitted IR; verify all displayed operation names.
cfile=next((a.ascend/'lowering/gemm-128-debug').rglob('kernel.npuir.mlir'))
cir=cfile.read_text();gfile=a.enflame/'full/gemm-128x128x128-v0-baseline/asm/gcuir';gir=gfile.read_text()
assert all(s in cir for s in ['hivm.hir.nd2nz','hivm.hir.mmadL1','hivm.hir.fixpipe','hivm.hir.set_flag','hivm.hir.wait_flag'])
assert all(s in gir for s in ['gcu.matmul','gpu.barrier','memref<8x8xf32>'])
fig,ax=plt.subplots(figsize=(10.5,4.1));ax.set_xlim(0,10.5);ax.set_ylim(0,4.1);ax.axis('off')
def box(x,y,w,h,text,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.07',facecolor=color,edgecolor='#555555',linewidth=.8));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9)
def arrow(x1,y1,x2,y2):ax.annotate('',xy=(x2,y2),xytext=(x1,y1),arrowprops={'arrowstyle':'->','lw':1})
box(.65,3.15,9.1,.63,'Identical tiled GEMM source, 128³, BM=BN=BK=16\nload A/B → dot (16×16) → store; eight K-loop iterations per program','#eeeeee')
arrow(3,3.13,3,2.84);arrow(7.65,3.13,7.65,2.84)
ax.text(2.7,2.8,'Enflame GCU300 / Triton 3.6.0',ha='center',weight='bold');ax.text(7.9,2.8,'Ascend 910B4-1 / Triton 3.5.1',ha='center',weight='bold')
box(.3,1.95,4.75,.57,'gcuir: thread partition + memory views\ngcu.matmul: 8×8 local accumulation; launch block 4','#f4d5ce')
box(5.5,1.95,4.65,.57,'HIVM IR: AIC, gm → cbuf → cc → gm\nexplicit pipeline/event-ID synchronization','#d5e6f5')
arrow(2.7,1.9,2.7,1.7);arrow(7.8,1.9,7.8,1.7)
box(.3,.77,4.75,.82,'Input staging → gpu.barrier → gcu.matmul\n→ output staging/store\nTwo static gpu.barrier sites in this loop body','#fbeae5')
box(5.5,.77,4.65,.82,'nd2nz → set_flag / wait_flag → mmadL1\n→ wait_flag(M→FIX) → fixpipe → barrier\nEmitted op: hivm.hir.mmadL1','#e8f1fa')
ax.text(5.25,.27,'Observed compiler output, not a measured execution schedule or proof of overlap.\nAscend diagnostic and baseline device binaries have identical SHA-256.',ha='center',fontsize=8)
save(fig,'study-lowering-measured')

# Fused case: static split plus native observation granularity, both verified.
fused=a.ascend/'lowering/fused-128-debug'
fc=next(fused.rglob('kernel.npuir.mlir')).read_text()
fg=(a.enflame/'full/gemm_bias_gelu-128x128x128-v0-baseline/asm/gcuir').read_text()
assert all(t in fc for t in ['@matmul_mix_aic','@matmul_mix_aiv','sync_block_set','sync_block_wait','hivm.hir.vexp'])
assert fg.count('gpu.kernel')==1 and 'gcu.matmul' in fg and 'math.exp' in fg
assert read(fused/'result.json')['asm']['npubin']['sha256']==read(a.ascend/'full/gemm_bias_gelu-128x128x128-v0-baseline/result.json')['asm']['npubin']['sha256']
fig,ax=plt.subplots(figsize=(10.5,4.7));ax.set_xlim(0,10.5);ax.set_ylim(0,4.7);ax.axis('off')
box(.65,3.84,9.1,.58,'One fused source kernel: tiled GEMM → bias + GELU → store; shape 128³','#eeeeee')
arrow(2.6,3.78,2.6,3.52);arrow(7.7,3.78,7.7,3.52)
ax.text(2.7,3.48,'Enflame GCU300',ha='center',weight='bold');ax.text(7.8,3.48,'Ascend 910B4-1',ha='center',weight='bold')
box(.3,2.08,4.65,1.02,'One gpu.kernel entry: matmul\ngcu.matmul (8×8 local tile)\n→ math.exp + vector epilogue → store','#f4d5ce')
box(5.45,2.62,4.75,.48,'AIC: matmul_mix_aic\nmmadL1 → fixpipe → workspace (gm)','#d5e6f5')
box(5.45,1.5,4.75,.48,'AIV: matmul_mix_aiv\nload workspace → bias / vexp / vmul → store','#d5e6f5')
arrow(7.8,2.52,7.8,2.08);ax.text(7.98,2.3,'sync_block_set / wait, flag=0',ha='left',fontsize=8)
arrow(2.65,2.02,2.65,1.26);arrow(7.8,1.45,7.8,1.26)
box(.3,.65,4.65,.51,'TOPSPTI: one timed kernel record per launch','#fbeae5')
box(5.45,.65,4.75,.51,'aclprof: one timed MIX_AIC task per launch','#e8f1fa')
ax.text(5.25,.18,'Compile-time decomposition and observed native record scope. No AIC/AIV timing or overlap is inferred.',ha='center',fontsize=8)
save(fig,'study-fused-decomposition')
