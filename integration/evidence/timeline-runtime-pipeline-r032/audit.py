"""Retained byte/JSON audit only; does not import the profiler or run devices."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def need(value, message):
    if not value:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--repo', type=Path, required=True)
    args = p.parse_args()
    with tarfile.open(args.archive) as archive:
        files = {
            m.name: archive.extractfile(m).read()
            for m in archive.getmembers() if m.isfile()
        }

    def doc(name):
        return json.loads(files[name])

    for stage in ('installed-v5', 'views-v2', 'source-v2'):
        need(
            doc(stage + '/terminal.json')['returncode'] == 0,
            'Final stage did not finish: ' + stage)
    sources = doc('inputs/final-source-sha256.json')
    changed = [
        'Profiler/python/flagtree_profiler/' + name
        for name in ('profile.py', 'cli.py', 'timeline_nvidia_machine.py',
                     'timeline_nvidia_control.py')
    ]
    for name in changed:
        need(
            digest((args.repo / name).read_bytes()) == sources[name],
            'Current product differs from actual installed inputs: ' + name)
    bridge = doc('installed-v5/output/native-source-bridge.json')
    for name, sha in bridge['matching_native_sources'].items():
        need(
            digest((args.repo / name).read_bytes()) == sha,
            'Native source changed: ' + name)
    fresh_prefix = 'installed-v5/output/fresh-default/profile/timeline/'
    fresh = []
    for row in doc(fresh_prefix + 'index.json')['captures']:
        capture = doc(fresh_prefix + row['capture_file'])
        batch = doc(fresh_prefix + capture['events_file'])
        raw = files[fresh_prefix + capture['raw_file']]
        need(
            digest(raw) == capture['raw_sha256'] and batch['complete'],
            'Actual raw changed or incomplete')
        need(capture['counter_ns_status']['status'] == 'counter_unit_only',
             'Fresh default failed to export')
        need(
            all(
                struct.unpack_from('<Q', raw, r['offset'] + 4)[0] == r['tick']
                for r in batch['records']), 'Actual raw endpoint mismatch')
        for export in capture['counter_ns_exports']:
            view = doc(fresh_prefix + export['view_file'])
            need(
                digest(files[fresh_prefix +
                             export['trace_file']]) == export['sha256'],
                'Fresh trace changed')
            for r in view['records']:
                need(r['relative_ns'] == r['tick'] - view['origin_tick'],
                     'Wrong exact NV ns coordinate')
        fresh.append(
            dict(invocation_id=row['invocation_id'],
                 binary_id=row['binary_id'],
                 intervals=len(batch['events']),
                 traces=len(capture['counter_ns_exports'])))
    need(
        len(fresh) == 2 and len({r['binary_id']
                                 for r in fresh}) == 1,
        'Runtime K changed binary identity')
    need(sum(r['traces'] for r in fresh) == 16, 'Missing fresh observers')
    recovered = [
        doc('installed-v5/output/offline-' + str(d) + '/result.json')
        for d in (1, 8)
    ]
    need(
        all(r['real_traces'] == 16 and r['application_replayed'] is False
            for r in recovered), 'Offline recovery failed')
    old = doc('installed-v5/output/old-compat/result.json')
    need(old['real_traces'] == 24 and old['trace_bytes_match_prior_bundle'],
         'Old trace compatibility failed')
    tp_checks = []
    for name in ('installed-v5/output/offline-1/TP/result.json',
                 'installed-v5/output/offline-8/TP/result.json',
                 'installed-v5/output/old-compat/TP/result.json',
                 'views-v2/output/TP/result.json'):
        tp_checks.extend(doc(name)['checks'])
    need(
        len(tp_checks) == 72
        and all(not c['importer_errors'] and c['flows'] == 0
                and c['exact_ns_and_raw_references']
                for c in tp_checks), 'Actual TP validation failed')
    ui = doc('views-v2/output/UI/result.json')
    need(
        len(ui['checks']) == 6
        and all(not c['page_errors'] for c in ui['checks']),
        'Actual UI checks failed')
    for check in ui['checks']:
        need(any(c['sha256'] == check['trace_sha256'] for c in tp_checks),
             'UI trace was not TP checked')
    mechanisms = doc('followup-v1/output/mechanisms.json')['bodies']
    relationships = {}
    for name, body in mechanisms.items():
        need(len(body['math_loops']) == 1, 'Ambiguous actual math loop')
        events = body['math_loops'][0]['events']
        copies = [
            i for i, e in enumerate(events) if e['opcode'].startswith('LDGSTS')
        ]
        math = [
            i for i, e in enumerate(events) if e['opcode'].startswith('HMMA')
        ]
        need(
            len(copies) == 1 and len(math) == 4,
            'Unexpected actual native mechanism')
        relationships[name] = dict(
            instructions=body['instructions'],
            copy_between_math_issues=min(math) < copies[0] < max(math))
    need(
        relationships['ordinary']['copy_between_math_issues']
        and not relationships['density-1']['copy_between_math_issues']
        and not relationships['density-8']['copy_between_math_issues'],
        'Schedule limitation changed')
    print(
        json.dumps(dict(
            status='saved_byte_audit_passed_not_full_P01',
            archive=dict(bytes=args.archive.stat().st_size,
                         sha256=digest(args.archive.read_bytes())),
            product_source_sha256={name: sources[name]
                                   for name in changed},
            fresh_captures=fresh,
            recovered_traces=32,
            old_compatible_traces=24,
            TP_traces=72,
            UI_traces=6,
            actual_native_relationships=relationships,
            installation=doc('installed-v5/output/install-result.json'),
            source_boundaries_qualified=False,
            async_time_arrows_qualified=False),
                   indent=2))


if __name__ == '__main__':
    main()
