#!/usr/bin/env python3
"""Actual GCU native matrix: original six mathematical operators, tails/configs.

Run inside Docker, with current compiler/tool PYTHONPATH and device zero reserved.
Canonical input bytes and tolerances are inherited from Study, not regenerated.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--input-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--mode',
               choices=('native', 'selected_detail'),
               default='native')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
runner = Path(__file__).parent / 'fixtures/enflame_method/run_case.py'
plan = []
for op in ('gemm', 'gemm_bias_gelu', 'softmax', 'layernorm', 'reduce_sum',
           'transpose'):
    shapes = ('128x128x128', '512x512x512',
              '257x193x320') if op.startswith('gemm') else (
                  '256x256', '1024x1024',
                  '513x257') if op == 'transpose' else ('32x256', '256x1024',
                                                        '127x769')
    for shape in shapes:
        for variant in (0, 1):
            plan.append({'operator': op, 'shape': shape, 'variant': variant})
(a.output / 'plan.json').write_text(
    json.dumps(
        {
            'cases':
            plan,
            'launches_per_case':
            3,
            'config_semantics':
            'Study original v0/v1; GEMM stage1/2 tile16, rows1/2 workitems4, transpose M tile16/32',
            'mode':
            a.mode,
            'native_source':
            'formal current tool, explicit native or selected detail hook'
        },
        indent=2))
for case in plan:
    name = f'{case["operator"]}-{case["shape"]}-v{case["variant"]}'
    command = [
        sys.executable,
        str(runner), '--backend', 'enflame', '--operator', case['operator'],
        '--shape', case['shape'], '--variant',
        str(case['variant']), '--phase', a.mode, '--profile-launches', '3',
        '--input-dir',
        str(a.input_dir), '--output',
        str(a.output / name)
    ]
    print('RUN', name, flush=True)
    start = time.perf_counter()
    with (a.output / (name + '.log')).open('w') as f:
        try:
            code = subprocess.run(command,
                                  stdout=f,
                                  stderr=subprocess.STDOUT,
                                  timeout=900).returncode
        except subprocess.TimeoutExpired:
            code = 124
    with (a.output / 'execution.jsonl').open('a') as f:
        f.write(
            json.dumps({
                'case': case,
                'command': command,
                'returncode': code,
                'elapsed_seconds': time.perf_counter() - start
            }) + '\n')
    print('DONE', name, code, flush=True)
    if code: raise SystemExit(code)
(a.output / 'complete.json').write_text(
    json.dumps({
        'cases_passed': len(plan),
        'mode': a.mode,
        'native_launches': 3 * len(plan)
    }))
