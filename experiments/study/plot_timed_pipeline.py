#!/usr/bin/env python3
"""Compiled paths beside actual same-invocation, actor-local recorded intervals.

No unmeasured operation is assigned a duration. Cross-actor origins remain
unverified. GCU raw ticks are retained; its empirical scale is identified.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.lines import Line2D

p = argparse.ArgumentParser()
p.add_argument('--bundle', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
sample = 7
colors = {'body': '#e0e4e8', 'matrix': '#b9d9f3', 'output': '#ffe2a4',
          'wait': '#c54b56', 'transfer': '#4796c5', 'compute': '#efb65a',
          'store': '#8dbfc5', 'bracket': '#762a83'}
fig = plt.figure(figsize=(13.8, 11.5))
grid = fig.add_gridspec(3, 2, height_ratios=[1, 1, 3], width_ratios=[1, 1.25],
                       left=.03, right=.98, bottom=.16, top=.86, hspace=.75, wspace=.22)
fig.suptitle('Fused GEMM + bias + GELU: compiled paths and measured time\n'
             'One selected program p = (0,0), tile16², 128³; sample index7 in separate backend captures',
             fontsize=15)
receipts = []


def load(relative):
    f = a.bundle / relative
    receipts.append({'path': str(relative), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
    return json.loads(f.read_text())


def box(ax, x, y, w, text, color):
    ax.add_patch(FancyBboxPatch((x, y-.22), w, .44,
                 boxstyle='round,pad=.025,rounding_size=.04',
                 facecolor=color, edgecolor='#444444', lw=.8))
    ax.text(x+w/2, y, text, ha='center', va='center', fontsize=10)


def arrow(ax, x, y, xx, yy, dashed=False):
    ax.annotate('', xy=(xx, yy), xytext=(x, y),
                arrowprops={'arrowstyle': '-|>', 'lw': 1,
                            'linestyle': '--' if dashed else '-',
                            'color': '#b14b4b' if dashed else '#444444'})


def mapped_gpu(ax, title, lane):
    ax.set(xlim=(0, 12), ylim=(0, 1.5))
    ax.axis('off')
    ax.set_title(title+' — compiled path', loc='left', fontsize=13, weight='bold')
    ax.text(.1, .84, lane, fontsize=10, va='center')
    ops = [(2, 1.35, 'Load /\nstage', colors['body']),
           (3.8, 1.6, 'GEMM', colors['matrix']),
               (6.4, 2.3, 'Bias +\nGELU', colors['output']),
           (9.3, 1.7, 'Store', colors['body'])]
    for x, w, text, color in ops:
        box(ax, x, .84, w, text, color)
    for left, right in zip(ops, ops[1:]):
        arrow(ax, left[0]+left[1]+.04, .84, right[0]-.04, .84)
    ax.text(6, .21, 'Load/GEMM/store subdivision is not separately timed.',
            ha='center', fontsize=10, color='#555555')


def gpu_time(ax, record, factor, xlabel, title, detail):
    assert record[4:6] == [0, 0] and record[6] == 1
    body = ((record[1]-record[0]) & 0xffffffff)*factor
    start = ((record[2]-record[0]) & 0xffffffff)*factor
    output = ((record[3]-record[2]) & 0xffffffff)*factor
    assert 0 <= start <= start+output <= body
    ax.broken_barh([(0, body)], (-.22, .44), facecolors=colors['body'], edgecolors='#555555')
    ax.broken_barh([(start, output)], (-.22, .44), facecolors=colors['output'], edgecolors='#b78c3d')
    ax.plot([start, start+output], [.30, .30], color=colors['bracket'], marker='|', ms=9)
    ax.set(xlim=(0, body*1.08), ylim=(-.6, .6), xlabel=xlabel)
    ax.set_yticks([0], ['p=(0,0)'])
    ax.set_title(title+'\n'+detail, loc='left', fontsize=11)
    ax.grid(axis='x', alpha=.2)
    return {'body': body, 'output': output, 'output_start': start}


cuda = load('captures/cuda/gemm_bias_gelu-t16-nested/result.json')
assert cuda['status'] == 'passed' and cuda['correct'] and cuda['post_profile_correct']
v = cuda['samples'][sample]['program_records'][0]
nv = load('captures/cuda/gemm_bias_gelu-t16-nested/native.json')
mapped_gpu(fig.add_subplot(grid[0, 0]), '(a) NVIDIA V100S', 'CTA p')
ct = gpu_time(fig.add_subplot(grid[0, 1]), v, .001,
              'Elapsed µs since this CTA body entry',
              f'Body {(v[1]-v[0])&0xffffffff:d}ns; output {(v[3]-v[2])&0xffffffff:d}ns',
              f'Whole launch {nv[sample]["duration_us"]:.3f}µs (all 64 programs)')

gd = load('gcu-global-timer/captures/leader-global-fused128-nested/result.json')
gs = load('gcu-global-timer/summary.json')
assert gd['status'] == 'passed' and gd['correct'] and gd['post_profile_correct']
v = gd['samples'][sample]['program_records'][0]
body_ticks = (v[1]-v[0]) & 0xffffffff
out_ticks = (v[3]-v[2]) & 0xffffffff
period = gs['empirical_calibration']['model_fit']['tick_period_us']
mapped_gpu(fig.add_subplot(grid[1, 0]), '(b) Enflame GCU300', 'Group p')
gt = gpu_time(fig.add_subplot(grid[1, 1]), v, .001,
              'Elapsed SDK ticks ×10³; official tick rate unknown',
              f'Body {body_ticks} ticks (~{body_ticks*period:.1f}µs); output {out_ticks} ticks (~{out_ticks*period:.2f}µs)',
              f'Whole launch {gs["cases"]["leader-global-fused128-nested"]["per_launch"][sample]["native_duration_us"]:.3f}µs; µs estimates use empirical scale')

left = fig.add_subplot(grid[2, 0])
left.set(xlim=(0, 12), ylim=(0, 3.6))
left.axis('off')
left.set_title('(c) Ascend 910B4-1 — compiled actor paths', loc='left', fontsize=13, weight='bold')
ops = [(2, 1.25, 'Load', colors['body']),
       (3.7, 1.6, 'GEMM', colors['matrix']),
       (5.8, 1.35, 'Write\nX', colors['body']),
       (7.7, 1.15, 'Signal', '#f3c8c8')]
for x, w, text, color in ops:
    box(left, x, 2.95, w, text, color)
for first, second in zip(ops, ops[1:]):
    arrow(left, first[0]+first[1]+.04, 2.95, second[0]-.04, 2.95)
left.text(.1, 2.95, 'AIC p', va='center', fontsize=11, weight='bold')
for y, sid in [(1.85, 0), (.75, 1)]:
    left.text(.1, y, f'AIV p,s{sid}', va='center', fontsize=11, weight='bold')
    ops = [(4.8, 1.15, 'Wait', '#f3c8c8'),
           (6.3, 1.35, 'Read\nX', colors['body']),
           (8, 1.7, 'Bias /\nGELU', colors['output']),
           (10.1, 1.45, 'Store', colors['body'])]
    for x, w, text, color in ops:
        box(left, x, y, w, text, color)
    for first, second in zip(ops, ops[1:]):
        arrow(left, first[0]+first[1]+.04, y, second[0]-.04, y)
    arrow(left, 4.45, y, 4.74, y, True)
left.plot([8.27, 4.45, 4.45], [2.68, 2.68, .75], ls='--', color='#b14b4b', lw=1)
left.text(2.9, 1.5, 'X: GM\nworkspace', fontsize=11, ha='center')
left.text(6, .15, 'Dependencies only; lane positions are not execution times.',
          ha='center', fontsize=10, color='#555555')

ad = load('ascend/captures/fused128-completion-run/result.json')
assert ad['status'] == 'passed'
sm = ad['samples'][sample]
actors = [x for x in sm['actors'] if x['program_id'] == 0]
assert {(x['actor'], x['subblock_id']) for x in actors} == {('AIC', 0), ('AIV', 0), ('AIV', 1)}
timeline = load('ascend/captures/fused128-completion-run/native.timeline.json')
events = sorted((x for x in timeline['traceEvents'] if x.get('ph') == 'X' and x.get('name') == 'matmul'
                 and x.get('cat') == 'cann_runtime:aclprof_op_summary'), key=lambda x: x['ts'])
assert len(events) == 18
small = grid[2, 1].subgridspec(3, 1, hspace=1.15)
asc_receipt = []
for i, actor in enumerate(actors):
    ax = fig.add_subplot(small[i, 0])
    b0, b1 = actor['body']
    body = (b1-b0)/50
    ax.broken_barh([(0, body)], (-.20, .40), facecolors=colors['body'], edgecolors='#555555')
    durations = {}
    for key, color in [('readiness_wait', 'wait'), ('workspace_transfer', 'transfer'),
                       ('epilogue_with_bias_load', 'compute'), ('output_store', 'store')]:
        if key not in actor:
            continue
        start, end = actor[key]
        assert b0 <= start <= end <= b1
        durations[key] = (end-start)/50
        ax.broken_barh([((start-b0)/50, (end-start)/50)], (-.20, .40), facecolors=colors[color])
    if 'output' in actor:
        start, end = actor['output']
        ax.plot([(start-b0)/50, (end-b0)/50], [.27, .27], color=colors['bracket'], marker='|', ms=8)
        out = (end-start)/50
        detail = f'body {body:.2f}µs; output {out:.2f}µs; wait {durations["readiness_wait"]:.2f}µs'
        other = f'X transfer {durations["workspace_transfer"]:.2f}; bias/GELU {durations["epilogue_with_bias_load"]:.2f}; store bracket {durations["output_store"]:.2f}µs'
    else:
        detail = f'AIC body {body:.2f}µs; internal subdivision not collected'
        other = f'Whole MIX task {events[sm["invocation"]]["dur"]:.2f}µs; each actor has its own zero'
    ax.set_title(detail+'\n'+other, loc='left', fontsize=10)
    ax.set(xlim=(0, 8.3), ylim=(-.48, .52))
    ax.set_yticks([0], [actor['actor']+(f' s{actor["subblock_id"]}' if actor['actor']=='AIV' else '')+'\n(own 0)'])
    ax.grid(axis='x', alpha=.2)
    if i == 2:
        ax.set_xlabel('Actor-local elapsed µs; origins are NOT aligned across actors')
    asc_receipt.append({'actor': actor['actor'], 'subblock_id': actor['subblock_id'],
                        'body_us': body, 'components_us': durations})

handles = [Patch(facecolor=colors['body'], label='Body / unpartitioned'),
           Patch(facecolor=colors['output'], label='GPU output region'),
           Patch(facecolor=colors['wait'], label='AIV wait'),
           Patch(facecolor=colors['transfer'], label='Workspace transfer'),
           Patch(facecolor=colors['compute'], label='Bias/GELU bracket'),
           Patch(facecolor=colors['store'], label='Store bracket'),
           Line2D([], [], color=colors['bracket'], marker='|', label='Requested output interval')]
fig.legend(handles=handles, ncol=4, loc='lower center', bbox_to_anchor=(.5, .028), fontsize=10)
fig.text(.5, .01, 'Actual instrumented intervals, including added fences/probes. No cross-actor overlap inferred; GCU µs is an empirical estimate.',
         ha='center', fontsize=10)
for ext in ['pdf', 'png', 'svg']:
    fig.savefig(a.output/('study-pipeline-timed.'+ext), dpi=190, bbox_inches='tight')
plt.close(fig)
info = {'operator': 'gemm_bias_gelu', 'shape': [128,128,128], 'tile':16,
        'sample_index':sample, 'program_coordinates':[0,0], 'sources':receipts,
        'cuda_us':ct, 'gcu_thousand_ticks':gt, 'gcu_empirical_tick_period_us':period,
        'ascend_actor_us':asc_receipt, 'limits':['separate backend captures',
        'no common crossactor origin proved','not unperturbed busy time',
        'no load/GEMM subdivision for GPUs/AIC','GCU official frequency unverified']}
(a.output/'study-pipeline-timed-data.json').write_text(json.dumps(info,indent=2)+'\n')
