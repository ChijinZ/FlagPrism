"""Audit final formatted installs and byte-identical re-exports; stdlib only."""
import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
parser.add_argument('--backend', choices=['nvidia', 'gcu'], required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
with tarfile.open(args.archive) as archive:

    def read(name):
        return archive.extractfile('chijin-timeline-r018/' + name).read()

    def load(name):
        return json.loads(read(name))

    install = load('runs/install-v3/output/result.json')
    offline = load('runs/offline-v3/output/result.json')
    counts = {'normal': 0, 'optimized': 0}
    for step in install['steps']:
        if step['returncode']:
            raise RuntimeError('Final install or CPU step failed')
        for mode in counts:
            if not step['name'].endswith('-' + mode):
                continue
            prefix = 'runs/install-v3/output/' + step['name']
            text = ''.join(
                read(prefix + suffix).decode()
                for suffix in ['.stdout.log', '.stderr.log'])
            matches = re.findall(r'Ran (\d+) tests? in|(?<!\d)(\d+) passed',
                                 text)
            if len(matches) != 1:
                raise RuntimeError('Missing or ambiguous CPU count')
            counts[mode] += int(matches[0][0] or matches[0][1])
    expected = 113 if args.backend == 'nvidia' else 89
    if counts != {'normal': expected, 'optimized': expected}:
        raise RuntimeError('Final CPU coverage differs')
    for job in ['install-v3', 'offline-v3']:
        terminal = load('runs/' + job + '/terminal.json')
        if terminal['state'] != 'terminal' or terminal['returncode']:
            raise RuntimeError('Final accepted job is not successful terminal')
    reports = [
        load('runs/offline-v3/output/' + name + '.stdout.log')
        for name in ['public-module', 'isolated-normal', 'isolated-optimized']
    ]
    if not reports[0] == reports[1] == reports[2] or reports[0][
            'application_replayed']:
        raise RuntimeError('Fresh offline processes differ or replay')
    if len(offline['forbidden_environment_roots']) != 2:
        raise RuntimeError(
            'Original source and cache restrictions are missing')
    if args.backend == 'nvidia' and not offline[
            'trace_bytes_match_prior_bundle']:
        raise RuntimeError('Prior UI trace byte equivalence missing')
    hashes = set()
    for capture in reports[0]['captures']:
        if args.backend == 'gcu' and (capture['status'] != 'raw_only'
                                      or capture['exports']):
            raise RuntimeError('GCU invented ns')
        for export in capture['exports']:
            prefix = 'runs/offline-v3/output/retained-timeline/'
            blob = read(prefix + export['trace_file'])
            if hashlib.sha256(blob).hexdigest() != export['sha256']:
                raise RuntimeError('Trace bytes differ')
            hashes.add(export['sha256'])
            receipt = load(prefix + export['receipt_file'])
            for artifact in receipt['files']:
                blob = read(prefix + artifact['file'])
                if len(blob) != artifact['bytes'] or hashlib.sha256(
                        blob).hexdigest() != artifact['sha256']:
                    raise RuntimeError('Committed receipt artifact differs')
    if args.backend == 'nvidia':
        tp = load('runs/offline-v3/output/TP/result.json')
        if len(tp['checks']) != 32 or {row['sha256']
                                       for row in tp['checks']} != hashes:
            raise RuntimeError('TP checked different traces')
        if any(row['importer_errors'] or row['flows']
               or not row['exact_ns_and_raw_references']
               for row in tp['checks']):
            raise RuntimeError('Final TP check failed')
        style = load('runs/style-v2/output/result.json')
        if len(style['files']) != 18 or not all(row['AST_unchanged']
                                                for row in style['files']):
            raise RuntimeError('Format AST preservation missing')
        if read('runs/style-v2/output/versions.stdout.log').strip(
        ) != b'0.9.1 0.43.0':
            raise RuntimeError('Pinned formatter/linter version differs')
        if load('runs/style-v2/output/ruff.stdout.log') or read(
                'runs/style-v2/output/yapf-check.stdout.log'):
            raise RuntimeError('Format/lint output is not clean')
    processes = load('process-audit-v3.json')
    if processes['live_matching_processes']:
        raise RuntimeError('Matching owned process remains live')
    result = dict(
        status='final_formatted_install_and_offline_bytes_audited_not_full_P01',
        backend=args.backend,
        archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        archive_bytes=args.archive.stat().st_size,
        archive_members=len(archive.getmembers()),
        cpu_checks_per_mode=counts,
        installed_members=install['installed_members_byte_verified'],
        wheel_sha256=install['wheel_sha256'],
        source_commit=install['source_commit'],
        native_commit=install['native_commit'],
        offline=offline,
        live_matching_processes=[])
args.output.write_text(json.dumps(result, indent=2) + '\n')
