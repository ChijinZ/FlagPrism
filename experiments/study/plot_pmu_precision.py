#!/usr/bin/env python3
"""Plot actual matched PMU records and explicitly different timing scopes."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

p = argparse.ArgumentParser()
p.add_argument('--comparison', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--variant', action='append', help='Select measured variants; repeat to include several')
p.add_argument('--name', default='study-pmu-reference')
a = p.parse_args()
rows = list(csv.DictReader(a.comparison.open()))
if a.variant:
    rows = [r for r in rows if r['variant'] in a.variant]
variants = list(dict.fromkeys(r['variant'] for r in rows))
assert variants, 'No measured comparisons'
fig, axes = plt.subplots(len(variants), 2, squeeze=False,
                         figsize=(10.8, 2.7 * len(variants) + 1), layout='constrained')
fig.get_layout_engine().set(rect=(0, .16, 1, .84))
for i, variant in enumerate(variants):
    for j, scope in enumerate(['body', 'output']):
        ax = axes[i, j]
        selected = sorted((r for r in rows if r['variant'] == variant and
                           r['scope'] == scope), key=lambda r: int(r['block_id']))
        if not selected:
            ax.text(.5, .5, 'Capture unavailable', ha='center', va='center',
                    transform=ax.transAxes)
            ax.set_title(f'{variant}: {scope}')
            continue
        for r in selected:
            x = int(r['block_id'])
            lo, hi = float(r['gate_lower_us']), float(r['gate_upper_us'])
            ax.plot([x, x], [lo - .02, hi + .02], color='#66a61e', lw=2, alpha=.75)
            ax.scatter(x, float(r['reference_pmu_us']), color='#d95f02', s=17, zorder=3)
            ax.scatter(x, float(r['source_interval_us']), color='#1b6ca8',
                       marker='x', s=22, zorder=4)
        prefix = f'{variant}: ' if len(variants) > 1 else ''
        ax.set_title(f'{prefix}{scope.capitalize()}: one launch, 32 AIV blocks')
        ax.set_xlabel('Logical program / PMU block ID')
        ax.set_ylabel('Instrumented duration (µs)')
        ax.set_xticks([0, 8, 16, 24, 31])
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.2)
handles = [Line2D([], [], marker='o', ls='', color='#d95f02', label='Hardware PMU window'),
           Line2D([], [], marker='x', ls='', color='#1b6ca8', label='Source body/output bracket'),
           Line2D([], [], color='#66a61e', lw=2, label='SET.CTRL halo + 20ns quantization')]
fig.legend(handles=handles, ncol=3, loc='lower center', bbox_to_anchor=(.5, 0))
fig.suptitle('Independent PMU reference: timing scope and gate uncertainty remain explicit\n'
             'Body and output are separate captures; vendor-reported frequency; not unperturbed busy time',
             fontsize=12)
a.output.mkdir(parents=True, exist_ok=True)
for ext in ['pdf', 'png', 'svg']:
    fig.savefig(a.output / (a.name + '.' + ext), dpi=180, bbox_inches='tight')
plt.close(fig)
