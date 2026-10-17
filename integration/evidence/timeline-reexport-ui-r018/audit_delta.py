"""Audit installed delta and real re-exports using stdlib bytes only."""
import argparse, hashlib, json, re, tarfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('archive', type=Path)
p.add_argument('--backend', choices=['nvidia', 'gcu'], required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
with tarfile.open(a.archive) as t:

    def read(name):
        return t.extractfile('chijin-timeline-r018/' + name).read()

    def load(name):
        return json.loads(read(name))

    cpu = load('runs/cpu-recheck-v2/output/result.json')
    offline = load('runs/offline-v2/output/result.json')
    counts = {'normal': 0, 'optimized': 0}
    for step in cpu['steps']:
        if step['returncode'] != step['expected_returncode']:
            raise RuntimeError('Unexpected CPU result')
        name = step['name']
        if name == 'old-version-order-regression':
            if step['returncode'] != 1 or b'Same derivative inputs produced different outputs' not in read(
                    'runs/cpu-recheck-v2/output/' + name + '.stderr.log'):
                raise RuntimeError('Old regression not reproduced')
        for mode in counts:
            if not name.endswith('-' + mode): continue
            text = ''.join(
                read('runs/cpu-recheck-v2/output/' + name + s).decode()
                for s in ['.stdout.log', '.stderr.log'])
            matches = re.findall(r'Ran (\d+) tests? in|(?<!\d)(\d+) passed',
                                 text)
            if len(matches) != 1: raise RuntimeError('Missing exact CPU count')
            counts[mode] += int(matches[0][0] or matches[0][1])
    expected = 113 if a.backend == 'nvidia' else 89
    if counts != {'normal': expected, 'optimized': expected}:
        raise RuntimeError('CPU coverage count differs')
    for job in ['cpu-recheck-v2', 'offline-v2']:
        terminal = load('runs/' + job + '/terminal.json')
        if terminal['state'] != 'terminal' or terminal['returncode'] != 0:
            raise RuntimeError('Delta job not successful terminal')
    if load('runs/install-v2/terminal.json')['returncode'] != 1:
        raise RuntimeError('First fixture failure history differs')
    if len(offline['forbidden_environment_roots']
           ) != 2 or offline['application_replayed']:
        raise RuntimeError('Source/cache denial or no-replay missing')
    if a.backend == 'nvidia' and not offline['trace_bytes_match_prior_bundle']:
        raise RuntimeError('UI byte equivalence missing')
    reports = [
        load('runs/offline-v2/output/' + name + '.stdout.log')
        for name in ['public-module', 'isolated-normal', 'isolated-optimized']
    ]
    if not reports[0] == reports[1] == reports[2] or reports[0][
            'application_replayed']:
        raise RuntimeError('Fresh re-export processes differ/replay')
    for capture in reports[0]['captures']:
        if a.backend == 'gcu' and (capture['status'] != 'raw_only'
                                   or capture['exports']):
            raise RuntimeError('GCU invented ns')
        for export in capture['exports']:
            prefix = 'runs/offline-v2/output/retained-timeline/'
            if hashlib.sha256(read(
                    prefix +
                    export['trace_file'])).hexdigest() != export['sha256']:
                raise RuntimeError('Trace byte binding differs')
            receipt = load(prefix + export['receipt_file'])
            for artifact in receipt['files']:
                data = read(prefix + artifact['file'])
                if len(data) != artifact['bytes'] or hashlib.sha256(
                        data).hexdigest() != artifact['sha256']:
                    raise RuntimeError('Receipt artifact changed')
    if a.backend == 'nvidia':
        tp = load('runs/offline-v2/output/TP/result.json')
        if len(tp['checks']) != 32 or any(r['importer_errors'] or r['flows'] or
                                          not r['exact_ns_and_raw_references']
                                          for r in tp['checks']):
            raise RuntimeError('Delta TP failure')
        if {r['sha256']
                for r in tp['checks']} != {
                    r['sha256']
                    for c in reports[0]['captures']
                    for r in c['exports']
                }:
            raise RuntimeError('TP checked other traces')
    if load('process-audit-delta-v2.json')['live_matching_processes']:
        raise RuntimeError('Matching task remains live')
    result = dict(
        status=
        'installed_delta_CPU_and_offline_artifact_bytes_audited_not_full_P01',
        backend=a.backend,
        archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
        archive_bytes=a.archive.stat().st_size,
        archive_members=len(t.getmembers()),
        cpu_checks_per_mode=counts,
        expected_old_failure_retained=True,
        initial_fixture_failure_retained=True,
        independent_install_members=cpu['installed_members_byte_verified'],
        wheel_sha256=cpu['wheel_sha256'],
        offline=offline,
        live_matching_processes=[],
        product_commit=cpu['product_commit'],
        test_commit=cpu['test_commit'])
a.output.write_text(json.dumps(result, indent=2) + '\n')
