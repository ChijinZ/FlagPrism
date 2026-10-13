#!/usr/bin/env python3
"""Run frozen NVIDIA configurations on one backend, inside its server Docker.

No target-specific configuration substitutions are made automatically. Every
failed port and measured call remains attributable to its frozen source choice.
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from observations import native


def options(config):
    flags = {'BM': '--tile-m', 'BN': '--tile-n', 'BK': '--k-tile',
             'ROWS': '--rows', 'num_stages': '--stages', 'num_warps': '--num-warps'}
    return [part for key, flag in flags.items() if key in config
            for part in [flag, str(config[key])]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['cuda', 'enflame', 'cann'], required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--batches', type=int, default=3)
    parser.add_argument('--launches', type=int, default=30)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--operator', nargs='+')
    parser.add_argument('--include-long-k', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = json.loads(args.selection.read_text())
    choices = []
    for entry in source:
        if args.operator and entry['operator'] not in args.operator:
            continue
        if not args.include_long_k and entry['shape'] == '512x512x4096':
            continue
        best = entry['config']
        alternatives = sorted(entry['native_candidates'],
                              key=lambda r: r['native_median_of_batch_medians_us'])
        configs = [best]
        configs.extend(r['config'] for r in alternatives if r['config'] != best)
        for variant, config in enumerate(configs[:2]):
            choices.append({'operator': entry['operator'], 'shape': entry['shape'],
                            'variant': variant, 'config': config,
                            'nvidia_selection': entry['source_result']})
    if not choices:
        raise ValueError('No frozen configurations selected')
    plan = {'backend': args.backend, 'device': args.device, 'batches': args.batches,
            'launches': args.launches, 'cases': choices,
            'selection_sha256': hashlib.sha256(args.selection.read_bytes()).hexdigest(),
            'semantics': 'NVIDIA native-selected winner and next distinct shortlisted '
                         'configuration; unchanged requested configurations on target'}
    plan_file = args.output / 'plan.json'
    if plan_file.exists() and json.loads(plan_file.read_text()) != plan:
        raise ValueError('Existing plan differs; use a fresh output directory')
    plan_file.write_text(json.dumps(plan, indent=2) + '\n')
    for batch in range(args.batches):
        order = list(choices)
        random.Random(20261013 + batch).shuffle(order)
        for case in order:
            name = f"{case['operator']}-{case['shape']}-v{case['variant']}-b{batch}"
            output = args.output / name
            result_file = output / 'result.json'
            if output.exists():
                if not result_file.exists():
                    raise RuntimeError(f'Incomplete existing case {output}; inspect first')
                previous = json.loads(result_file.read_text())
                if previous.get('status') != 'passed':
                    print('RETAINED FAILED CASE', name, flush=True)
                    continue
                records = [e for e in native(output, args.backend)
                           if e.get('kind') == 'kernel' and e.get('duration_us', 0) > 0]
                if len(records) != args.launches:
                    raise RuntimeError(f'Incomplete native capture at {output}')
                print('VERIFIED EXISTING CASE', name, flush=True)
                continue
            command = [sys.executable, str(Path(__file__).with_name('run_case.py')),
                       '--backend', args.backend, '--operator', case['operator'],
                       '--shape', case['shape'], '--variant', str(case['variant']),
                       '--device', str(args.device), '--phase', 'native',
                       '--profile-launches', str(args.launches),
                       '--input-dir', str(args.input_dir), '--output', str(output),
                       *options(case['config'])]
            print('RUN', name, flush=True)
            with (args.output / f'{name}.log').open('w') as log:
                try:
                    code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                          timeout=args.timeout).returncode
                except subprocess.TimeoutExpired:
                    code = 124
            result = json.loads(result_file.read_text()) if result_file.exists() else {}
            records = [e for e in native(output, args.backend)
                       if e.get('kind') == 'kernel' and e.get('duration_us', 0) > 0] if code == 0 else []
            report = {'case': name, 'batch': batch, 'choice': case, 'command': command,
                      'returncode': code, 'status': result.get('status', 'missing'),
                      'native_records': len(records),
                      'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
            with (args.output / 'execution.jsonl').open('a') as stream:
                stream.write(json.dumps(report) + '\n')
            print('DONE', name, code, len(records), flush=True)
            if code == 0 and len(records) != args.launches:
                raise RuntimeError(f'Expected {args.launches} native records at {output}')
            log_text = (args.output / f'{name}.log').read_text(errors='replace').lower()
            if code == 124 or any(message in log_text for message in
                                     ['illegal memory', 'device-side assert',
                                      'aicore exception', 'segmentation fault']):
                raise RuntimeError(f'Stopped after device fault or timeout at {output}')
    (args.output / 'sweep-terminal.json').write_text(json.dumps({
        'status': 'terminal', 'scope': 'Every requested case attempted or retained; '
                                    'not a claim that every port passed'}) + '\n')


if __name__ == '__main__':
    main()
