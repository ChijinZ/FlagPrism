#!/usr/bin/env python3
"""Source-to-actor dependency diagram, using verified compiled operator paths.

Visual references: KPerfIR (OSDI25), Figures1/2/3/4/6:
https://www.usenix.org/system/files/osdi25-guan.pdf
Corresponding source colors, grouped panels and actor lanes are used here.
Positions and widths encode no runtime or overlap; this is an original diagram.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

PALETTE = {'matrix': '#b9d9f3', 'output': '#ffe2a4',
           'memory': '#e7ecef', 'sync': '#f3c8c8'}


def render_pipeline(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.8, 7.1))
    ax.set(xlim=(0, 15), ylim=(0, 7.7))
    ax.axis('off')

    def box(x, y, w, h, text, kind, size=12):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle='round,pad=.025,rounding_size=.05',
                     facecolor=PALETTE[kind], edgecolor='#333333', lw=.9))
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=size)

    def arrow(x0, y0, x1, y1, dashed=False, color='#333333'):
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops={'arrowstyle': '-|>', 'lw': 1.2,
                                'linestyle': '--' if dashed else '-', 'color': color})

    def panel(y, h, title, subtitle):
        ax.add_patch(Rectangle((.12, y), 14.72, h, facecolor='#fafbfc',
                              edgecolor='#555555', lw=.9))
        ax.text(.35, y+h-.22, title, fontsize=13, weight='bold', va='center')
        ax.text(14.56, y+h-.22, subtitle, fontsize=11, ha='right', va='center')

    ax.text(7.5, 7.47, 'One source program, different compiled execution objects',
            ha='center', fontsize=16, weight='bold')
    ax.text(.35, 6.89, 'Source program p\n(one output tile)', va='center', fontsize=12, weight='bold')
    box(2.8, 6.56, 3.6, .66, 'acc = GEMM(A, B)', 'matrix', 13)
    box(8.5, 6.56, 5.1, .66, 'out = GELU(acc + bias)', 'output', 13)
    arrow(6.48, 6.89, 8.42, 6.89)
    ax.text(7.46, 6.29, 'Compile the same source for each backend',
            ha='center', fontsize=11)

    # The two source regions stay on one program path in these GPU cases.
    for y, title, lane in [(4.96, '(a) NVIDIA V100S', 'CTA p'),
                            (3.55, '(b) Enflame GCU300', 'Program p')]:
        panel(y, 1.18, title, 'Both source regions on one program path')
        center = y + .40
        ax.text(.5, center, lane, va='center', fontsize=12)
        ops = [(2.8, 1.3, 'Load /\nstage A, B', 'memory'),
               (4.8, 1.5, 'GEMM', 'matrix'),
               (9.1, 2.1, 'Bias + GELU', 'output'),
               (12.4, 1.55, 'Store out', 'memory')]
        for x, w, text, kind in ops:
            box(x, center-.24, w, .48, text, kind)
        for left, right in zip(ops, ops[1:]):
            arrow(left[0]+left[1]+.05, center, right[0]-.05, center)
        ax.text(7.7, center+.18, 'acc', ha='center', fontsize=11)

    # One logical program becomes a producer and two consumer subinstances.
    panel(.54, 2.78, '(c) Ascend 910B4-1', 'One program p → one AIC + two AIV actors')
    producer = 2.52
    ax.text(.5, producer, 'AIC p', va='center', fontsize=12, weight='bold')
    ops = [(2.8, 1.3, 'Load A, B', 'memory'),
           (4.8, 1.5, 'GEMM', 'matrix'),
           (6.8, 1.1, 'Write X', 'memory'),
           (8.35, 1.05, 'Signal', 'sync')]
    for x, w, text, kind in ops:
        box(x, producer-.24, w, .48, text, kind)
    for left, right in zip(ops, ops[1:]):
        arrow(left[0]+left[1]+.05, producer, right[0]-.05, producer)
    ax.text(5.3, 1.32, 'X = intermediate matrix\nin global-memory workspace',
            ha='center', va='center', fontsize=11, color='#444444')

    for center, sub in [(1.70, 0), (.94, 1)]:
        ax.text(.5, center, f'AIV p, s{sub}', va='center', fontsize=12, weight='bold')
        ops = [(8.35, 1.05, 'Wait', 'sync'),
               (9.75, 1.1, 'Read X', 'memory'),
               (11.15, 1.7, 'Bias + GELU', 'output'),
               (13.15, 1.4, 'Store out', 'memory')]
        for x, w, text, kind in ops:
            box(x, center-.24, w, .48, text, kind, 11.5)
        for left, right in zip(ops, ops[1:]):
            arrow(left[0]+left[1]+.05, center, right[0]-.05, center)
    # Independent dashed channels keep the two release dependencies legible.
    ax.plot([8.86, 8.0, 8.0], [2.25, 2.25, .94], color='#b14b4b', ls='--', lw=1.1)
    arrow(8.0, 1.70, 8.29, 1.70, True, '#b14b4b')
    arrow(8.0, .94, 8.29, .94, True, '#b14b4b')
    ax.text(7.65, 1.35, 'release', fontsize=10, rotation=90, va='center', color='#a13d3d')

    ax.text(7.5, .26, 'Blue = matrix computation; yellow = output computation; grey = data movement; pink = synchronization.',
            ha='center', fontsize=10.5)
    ax.text(7.5, .02, 'Static compiler mapping: arrows are dependencies; block widths and lane alignment are not a time axis.',
            ha='center', fontsize=10.5)
    for ext in ['pdf', 'png', 'svg']:
        fig.savefig(output / ('study-pipeline-structure.'+ext), dpi=190, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    ptx = (a.raw/'cuda/full/gemm_bias_gelu-128x128x128-v0-baseline/asm/ptx').read_text()
    gcu = (a.raw/'enflame/full/gemm_bias_gelu-128x128x128-v0-baseline/asm/gcuir').read_text()
    asc = (a.bundle/'evidence/fused-128-debug.hivm.mlir').read_text()
    assert all(t in ptx for t in ['ld.global', 'fma.rn.f32', 'st.global'])
    assert all(t in gcu for t in ['gpu.barrier', 'gcu.matmul', 'math.exp', 'triton_gcu.store'])
    assert all(t in asc for t in ['mmadL1', 'fixpipe', 'sync_block_set', 'sync_block_wait', 'vexp', 'store'])
    render_pipeline(a.output)
