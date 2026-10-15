"""Independent installed-default CLI qualification. Execute ONLY in server Docker.

Requires explicit freeze/booking documents; never selects sites or imports profiler APIs.
Every first-pass case remains in the summary, including failures.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import check_common_report as checker

HERE = Path(__file__).resolve().parent
COHORT = HERE / 'common-cohort-baseline-freeze-Q2.json'
COHORT_SHA = 'e07fd43544532cb0abc25cc22615d18dd1e43188cf8076c0d999e09b80395432'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--backend', choices=['nvidia', 'enflame', 'ascend'], required=True)
    p.add_argument('--device', type=int, required=True)
    p.add_argument('--freeze', type=Path, required=True)
    p.add_argument('--booking', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--pass-kind', choices=['first', 'repair'], required=True)
    args = p.parse_args()
    if not Path('/.dockerenv').exists():
        p.error('qualification runs only inside server Docker')
    checker.require(checker.digest(COHORT) == COHORT_SHA, 'frozen cohort changed')
    cohort = checker.load(COHORT)
    for source, expected in cohort['source_sha256'].items():
        checker.require(checker.digest(HERE / source) == expected, f'frozen source changed: {source}')
    freeze, booking = checker.load(args.freeze), checker.load(args.booking)
    checker.require(freeze.get('candidate_frozen') is True, 'candidate has not been frozen')
    checker.require(all(freeze.get(k) for k in ['product_revision', 'public_docs_sha256', 'installed_native_sha256']), 'incomplete freeze provenance')
    checker.require(booking.get('exclusive') is True and booking.get('backend') == args.backend
                    and booking.get('device') == args.device and booking.get('owner') == 'usability_qualification', 'missing exclusive device booking')
    checker.require(not args.output.exists(), 'refuse to overwrite earlier pass')
    args.output.mkdir(parents=True)
    write(args.output / 'authorization.json', {'freeze': freeze, 'booking': booking,
          'freeze_document_sha256': checker.digest(args.freeze), 'booking_document_sha256': checker.digest(args.booking),
          'cohort_sha256': COHORT_SHA, 'pass_kind': args.pass_kind, 'runner_sha256': checker.digest(Path(__file__)),
          'checker_sha256': checker.digest(HERE / 'check_common_report.py'), 'python': sys.executable})
    env = os.environ.copy()
    for name in list(env):
        if name == 'PYTHONPATH' or name.startswith(('FLAGPRISM_', 'TRITON_PROTON_', 'PROTON_')):
            env.pop(name)
    env.pop('FLAGTREE_BACKEND', None)
    if args.backend != 'nvidia':
        env['FLAGTREE_BACKEND'] = args.backend
    if args.backend == 'ascend':
        env['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
    rows = cohort['backend_evidence'][args.backend]
    results = []
    for baseline in rows['common_combinations'] + rows['runtime_probe']:
        case, si, ci = baseline['case'], baseline['shape_index'], baseline['config_index']
        key = f'{case}-s{si}-c{ci}'
        cache = args.output / 'caches' / key
        cache.mkdir(parents=True)
        env['TRITON_CACHE_DIR'] = str(cache.resolve())
        if case == 'cubic_window':
            script = 'ascend_window_startup.py' if args.backend == 'ascend' else 'reserve_window.py'
            case_args = []
        elif case in ['symmetric_cross', 'bilinear_difference']:
            script, case_args = 'reserve_matrix.py', ['--case', case]
        else:
            script = 'ascend_startup.py' if args.backend == 'ascend' else 'workload.py'
            case_args = ['--case', case]
        for repetition in ['cold', 'warm']:
            directory = args.output / key / repetition
            directory.mkdir(parents=True)
            receipt, ledger, bundle = [directory / n for n in ['receipt.json', 'startup-ledger.jsonl', 'bundle']]
            command = [sys.executable, '-m', 'flagtree.profiler.cli', '--detail', 'auto', '--device', str(args.device),
                       '-n', str(bundle.resolve()), str(HERE / script), *case_args,
                       '--backend', args.backend, '--device', str(args.device), '--shape-index', str(si),
                       '--config-index', str(ci), '--receipt', str(receipt.resolve()), '--startup-ledger', str(ledger.resolve())]
            result = {'case': case, 'shape_index': si, 'config_index': ci, 'repetition': repetition,
                      'baseline_eligible': True, 'status': 'fail', 'command': command}
            started = time.monotonic()
            # The public CLI supervises startup/compile/export independently. This outer guard
            # only detects a stuck supervisor; it does not redefine per-phase deadlines.
            guard = 120 + baseline['cold_timeout_s'] + 60 + 60
            with (directory / 'stdout.log').open('wb') as out, (directory / 'stderr.log').open('wb') as err:
                proc = subprocess.Popen(command, stdout=out, stderr=err, env=env, start_new_session=True)
                write(directory / 'process.json', {'pid': proc.pid, 'outer_guard_seconds': guard, 'command': command})
                try:
                    result['returncode'] = proc.wait(timeout=guard)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                    result['returncode'], result['outer_timeout'] = proc.returncode, True
            result['process_wall_s'] = time.monotonic() - started
            try:
                checker.require(result['returncode'] == 0, 'default public CLI failed or timed out')
                checker.require(len(ledger.read_text().splitlines()) == 1, 'application host side effect was repeated or absent')
                result['verification'] = checker.verify(bundle, receipt, COHORT, args.backend, case, si, ci)
                result['status'] = 'pass'
            except (checker.ContractError, KeyError, TypeError, ValueError, OSError, StopIteration) as error:
                result['error'] = f'{type(error).__name__}: {error}'
            write(directory / 'qualification.json', result)
            results.append(result)
            write(args.output / 'summary.json', {'status': 'running', 'pass_kind': args.pass_kind, 'results': results})
    summary = {'status': 'pass' if all(r['status'] == 'pass' for r in results) else 'fail',
               'expected_runs': 56, 'resolved_runs': len(results), 'pass_kind': args.pass_kind,
               'baseline_eligible_cases_removed': 0, 'results': results}
    write(args.output / 'summary.json', summary)
    raise SystemExit(0 if summary['status'] == 'pass' and len(results) == 56 else 1)


if __name__ == '__main__':
    main()
