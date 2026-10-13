#!/usr/bin/env python3
"""Expose descriptive within-backend configuration ratios without claiming reversals."""
import argparse
import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('--intervals', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--data-output', type=Path, required=True)
a = p.parse_args()
data = list(csv.DictReader(a.intervals.open()))
ops = ['gemm', 'gemm_bias_gelu', 'softmax', 'layernorm', 'reduce_sum', 'transpose']
labels = ['GEMM', 'GEMM + bias + GELU', 'Softmax', 'LayerNorm', 'Reduce-sum', 'Transpose']
colors = {'cuda': '#1b9e77', 'enflame': '#d6604d', 'cann': '#2166ac'}
names = {'cuda': 'V100S', 'enflame': 'GCU300', 'cann': 'Ascend 910B4-1'}
rows = []
fig, axes = plt.subplots(2, 3, figsize=(11, 6.4), layout='constrained')
fig.get_layout_engine().set(rect=(0, .16, 1, .84))
for ax, op, title in zip(axes.flat, ops, labels):
    shapes = (['128x128x128', '512x512x512', '257x193x320'] if op.startswith('gemm')
              else ['256x256', '1024x1024', '513x257'] if op == 'transpose'
              else ['32x256', '256x1024', '127x769'])
    for b, marker in zip(['cuda', 'enflame', 'cann'], ['o', 's', 'D']):
        ratios = []
        for shape in shapes:
            samples = [[float(r['reported_duration_us']) for r in data
                        if r['backend'] == b and r['operator'] == op and
                        r['shape'] == shape and r['variant'] == str(v)] for v in [0, 1]]
            assert all(len(v) == 15 for v in samples)
            med = [statistics.median(v) for v in samples]
            ratios.append(med[1]/med[0])
            rows.append({'backend': b, 'operator': op, 'shape': shape,
                         'median_v0_us': med[0], 'median_v1_us': med[1],
                         'v1_over_v0': med[1]/med[0], 'samples_per_config': 15})
        ax.plot(range(3), ratios, marker=marker, color=colors[b], label=names[b], lw=1)
    ax.axhline(1, color='#555555', ls='--', lw=.9)
    ax.set(title=title, ylim=(.4, 1.25), ylabel='v1 / v0 duration')
    ax.set_xticks(range(3), ['small', 'large', 'tail'])
    ax.grid(axis='y', alpha=.2)
fig.suptitle('Configuration response within each backend\n'
             'Below 1: v1 has a shorter median duration; 1: unchanged', fontsize=13)
fig.legend(*axes[0, 0].get_legend_handles_labels(), loc='lower center', ncol=3,
           bbox_to_anchor=(.5, .035))
fig.text(.5, .005, '15 prewarmed intervals per configuration; descriptive medians, no confidence intervals.',
         ha='center', fontsize=10)
a.output.mkdir(parents=True, exist_ok=True)
for ext in ['pdf', 'png', 'svg']:
    fig.savefig(a.output / ('study-config-response.'+ext), dpi=190, bbox_inches='tight')
plt.close(fig)
a.data_output.parent.mkdir(parents=True, exist_ok=True)
with a.data_output.open('w') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
