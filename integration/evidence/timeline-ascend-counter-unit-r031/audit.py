"""Audit retained bytes/JSON only; never imports the profiler or device stack."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def saved(path):
    with tarfile.open(path) as archive:
        return {
            m.name: archive.extractfile(m).read()
            for m in archive.getmembers() if m.isfile()
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    captures = saved(args.preflight / 'ascend-installed-evidence-v1.tgz')
    views = saved(args.preflight / 'ascend-TP-UI-evidence-v1.tgz')
    tests = saved(args.preflight / 'ascend-checks-evidence-v1.tgz')
    parsed = lambda files, name: json.loads(files[name])
    need(
        parsed(captures, 'installed/terminal.json')['returncode'] == 0,
        'Installation did not finish')
    need(
        parsed(views, 'browser-v2/terminal.json')['returncode'] == 0,
        'TP/UI did not finish')
    need(
        parsed(tests, 'checks-v2/terminal.json')['returncode'] == 0,
        'Installed tests did not finish')
    # Test-only whitespace was formatted after the installation source snapshot.
    source = parsed(captures, 'input/source-sha256.json')
    components = [
        'Profiler/python/flagtree_profiler/' + name
        for name in ('timeline_ascend.py', 'timeline_ascend_machine.py',
                     'timeline_unit_ascend.py', 'timeline_reexport.py')
    ]
    for name in components:
        need(
            sha((args.repo / name).read_bytes()) == source[name],
            'Current implementation differs from tested source: ' + name)
    summaries, exported = [], {}
    for label in ('recurrence', 'softmax'):
        prefix = 'installed/output/device-probe/' + label + '/timeline/'
        index = parsed(captures, prefix + 'index.json')
        for row in index['captures']:
            capture = parsed(captures, prefix + row['capture_file'])
            batch = parsed(captures, prefix + capture['events_file'])
            raw = captures[prefix + capture['raw_file']]
            need(sha(raw) == capture['raw_sha256'], 'Changed raw bytes')
            need(capture['counter_ns_status']['status'] == 'counter_unit_only',
                 'Missing actual default export')
            runtime = capture['metadata']['runtime_device']
            need(
                runtime['name'] ==
                capture['metadata']['compiler_metadata']['arch'] ==
                'Ascend910B4-1', 'Actual runtime binding is missing')
            need(runtime['device'] == capture['owner']['device'] == 4,
                 'Wrong actual NPU')
            for record in batch['records']:
                need(
                    struct.unpack_from('<Q', raw,
                                       record['offset'])[0] == record['tick'],
                    'Canonical endpoint differs from raw')
            for export in capture['counter_ns_exports']:
                view = parsed(captures, prefix + export['view_file'])
                trace = captures[prefix + export['trace_file']]
                need(sha(trace) == export['sha256'], 'Trace hash mismatch')
                need(
                    view['unit_proof']['period_numerator_ns'] == 20
                    and view['unit_proof']['period_denominator'] == 1,
                    'Wrong unit')
                for record in view['records']:
                    need(
                        record['relative_ns'] == 20 *
                        (record['tick'] - view['origin_tick']),
                        'Wrong exact ns coordinate')
                need(not export['time_arrows_verified'],
                     'Unit export acquired flow rights')
                exported[export['sha256']] = dict(
                    intervals=len(view['events']),
                    observer_id=export['observer_id'])
            summaries.append(
                dict(invocation_id=capture['owner']['invocation_id'],
                     binary_id=capture['owner']['binary_id'],
                     intervals=len(batch['events']),
                     endpoints=len(batch['records'])))
    tp = parsed(views, 'browser-v2/output/TP/result.json')
    ui = parsed(views, 'browser-v2/output/UI/result.json')
    need(
        len(exported) == len(tp['checks']) == len(ui['checks']) == 6,
        'Missing real trace')
    need({c['sha256']
          for c in tp['checks']} == set(exported) ==
         {c['trace_sha256']
          for c in ui['checks']}, 'UI/TP did not consume actual traces')
    for check in tp['checks']:
        need(
            check['exact_ns_and_raw_references'] and check['flows'] == 0
            and not check['importer_errors'], 'Actual TP contract failed')
    for check in ui['checks']:
        need(
            not check['page_errors']
            and check['actual_track_canvas']['width'] > 0, 'Actual UI failed')
    offline = parsed(captures, 'installed/output/offline/result.json')
    need(
        offline['application_replayed'] is False
        and all(s['returncode'] == 0 for s in offline['steps']),
        'Offline failed')
    print(
        json.dumps(dict(status='saved_byte_audit_passed_not_full_P01',
                        components={name: source[name]
                                    for name in components},
                        captures=summaries,
                        traces=6,
                        endpoints=sum(r['endpoints'] for r in summaries),
                        intervals=sum(r['intervals'] for r in summaries),
                        runtime_model='Ascend910B4-1',
                        device=4,
                        installed=parsed(captures,
                                         'installed/output/result.json'),
                        offline=offline,
                        unit_only=True,
                        source_boundaries_qualified=False,
                        async_qualified=False,
                        archives={
                            name:
                            dict(bytes=(args.preflight / name).stat().st_size,
                                 sha256=sha(
                                     (args.preflight / name).read_bytes()))
                            for name in ('ascend-installed-evidence-v1.tgz',
                                         'ascend-TP-UI-evidence-v1.tgz',
                                         'ascend-checks-evidence-v1.tgz')
                        }),
                   indent=2))


if __name__ == '__main__':
    main()
