#!/usr/bin/env python3
"""Single-column distributions from matched, real three-backend port captures."""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from observations import native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cuda', type=Path, required=True)
    parser.add_argument('--enflame', type=Path, required=True)
    parser.add_argument('--cann', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    roots = {key: getattr(args, key) for key in ['cuda', 'enflame', 'cann']}
    rows, groups, plan_hashes, input_hashes = [], {}, {}, {}
    kernel_source_hash = None
    common = None
    for backend, root in roots.items():
        plan = json.loads((root / 'plan.json').read_text())
        plan_hashes[backend] = hashlib.sha256((root / 'plan.json').read_bytes()).hexdigest()
        identity = {(c['operator'], c['shape'], c['variant']): c['config'] for c in plan['cases']}
        if common is None:
            common = identity
        elif common != identity:
            raise ValueError('Requested source configurations differ across backends')
        for case in plan['cases']:
            samples = []
            for batch in range(plan['batches']):
                directory = root / f"{case['operator']}-{case['shape']}-v{case['variant']}-b{batch}"
                result_path = directory / 'result.json'
                result = json.loads(result_path.read_text())
                if result['status'] != 'passed' or not result['validation']['passed']:
                    raise ValueError(f'Unverified port {directory}; do not fill missing data')
                key = (case['operator'], case['shape'])
                hashes = result.get('input_hashes')
                if not hashes:
                    raise ValueError(f'Missing immutable input identities {directory}')
                if key in input_hashes and input_hashes[key] != hashes:
                    raise ValueError(f'Input mismatch at {directory}')
                input_hashes[key] = hashes
                source_hash = result.get('source_hashes', {}).get('kernels.py')
                if not source_hash:
                    raise ValueError(f'Missing source identity {directory}')
                if kernel_source_hash is not None and kernel_source_hash != source_hash:
                    raise ValueError(f'Operator source mismatch at {directory}')
                kernel_source_hash = source_hash
                events = [e for e in native(directory, backend)
                          if e.get('kind') == 'kernel' and e.get('duration_us', 0) > 0]
                if len(events) != plan['launches']:
                    raise ValueError(f'Unexpected capture coverage {directory}')
                for invocation, event in enumerate(events):
                    value = float(event['duration_us'])
                    samples.append(value)
                    rows.append({'backend': backend, 'operator': case['operator'],
                                 'shape': case['shape'], 'variant': case['variant'],
                                 'measurement_batch': batch, 'invocation': invocation,
                                 'duration_us': value, 'source': str(result_path),
                                 'requested_config': json.dumps(case['config'], sort_keys=True)})
            groups[(backend, case['operator'], case['shape'], case['variant'])] = samples
    plt.rcParams.update({'font.size': 8, 'axes.titlesize': 8, 'axes.labelsize': 8,
                         'xtick.labelsize': 8, 'ytick.labelsize': 8,
                         'legend.fontsize': 8, 'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False})
    operators = ['gemm', 'gemm_bias_gelu', 'softmax', 'layernorm', 'reduce_sum', 'transpose']
    names = ['GEMM', 'Fused GEMM', 'Softmax', 'LayerNorm', 'Reduce-sum', 'Transpose']
    colors = {'cuda': '#16836b', 'enflame': '#c55a42', 'cann': '#28689d'}
    fig, axes = plt.subplots(3, 2, figsize=(3.3, 5.3), layout='constrained')
    fig.get_layout_engine().set(rect=(0, .19, 1, .76), h_pad=.05, w_pad=.03)
    fig.suptitle('Transferred NVIDIA configurations\nImplementation latency', fontsize=8, y=.995)
    rng = np.random.default_rng(17)
    for ax, op, title in zip(axes.flat, operators, names):
        shapes = (['128x128x128', '512x512x512', '257x193x320'] if op.startswith('gemm')
                  else ['256x256', '1024x1024', '513x257'] if op == 'transpose'
                  else ['32x256', '256x1024', '127x769'])
        for index, shape in enumerate(shapes):
            variants = sorted(v for o, s, v in common if o == op and s == shape)
            if not variants:
                raise ValueError(f'Missing workload {op} {shape}')
            for backend_index, backend in enumerate(roots):
                for variant in variants:
                    samples = groups[(backend, op, shape, variant)]
                    x = index + (backend_index - 1) * .23 + (variant - .5) * .09
                    median = statistics.median(samples)
                    ax.vlines(x, min(samples), max(samples), color=colors[backend], lw=.65)
                    ax.scatter(x + rng.uniform(-.012, .012, len(samples)), samples,
                               s=2, alpha=.16, color=colors[backend], linewidths=0,
                               rasterized=True)
                    ax.plot(x, median, 'o' if variant == 0 else 's', ms=3,
                            color=colors[backend], markeredgewidth=.4,
                            markeredgecolor='white')
        ax.set(title=title, yscale='log', xlim=(-.45, 2.45))
        ax.set_xticks(range(3), ['Small', 'Large', 'Tail'])
        ax.grid(axis='y', alpha=.18, lw=.4)
        if op == 'gemm':
            ax.annotate('Non-2D path', xy=(.78, 94740), xytext=(.04, .68),
                        textcoords='axes fraction', fontsize=8, color=colors['enflame'],
                        arrowprops={'arrowstyle':'->','lw':.6,'color':colors['enflame']})
        if ax in axes[:, 0]:
            ax.set_ylabel('Latency (µs)')
    handles = [Line2D([], [], color=colors[b], marker='o', ls='', ms=3, label=n) for b, n in
               [('cuda', 'RTX PRO 6000'), ('enflame', 'GCU300'), ('cann', 'Ascend 910B')]]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .047),
               ncol=1, frameon=False, handlelength=1.5, labelspacing=.3)
    fig.text(.5, .006, '○ / □: frozen NVIDIA configurations 0 / 1',
             ha='center', va='bottom', fontsize=8)
    args.output.mkdir(parents=True, exist_ok=True)
    for extension in ['pdf', 'svg', 'png']:
        fig.savefig(args.output / f'study-porting-overview.{extension}', dpi=300)
    plt.close(fig)
    with (args.output / 'study-porting-overview-data.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output / 'study-porting-overview-provenance.json').write_text(json.dumps({
        'plan_sha256': plan_hashes, 'samples': len(rows), 'width_inches': 3.3,
        'kernel_source_sha256': kernel_source_hash,
        'scope': 'Uninstrumented native kernel/task intervals; min--max spans are '
                 'descriptive, not confidence intervals; exact shapes/configs '
                 'and source records are in the companion data CSV'}, indent=2) + '\n')


if __name__ == '__main__':
    main()
