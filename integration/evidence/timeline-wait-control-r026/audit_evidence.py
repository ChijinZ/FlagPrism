"""Stdlib-only retained-byte audit; never imports or qualifies the product."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tarfile.open(args.archive) as archive:

        def raw(name):
            member = archive.getmember(name)
            need(member.isfile(), 'Nonregular evidence member')
            return archive.extractfile(member).read()

        def doc(name):
            return json.loads(raw(name))

        names = archive.getnames()
        inventory = doc('inventory.json')
        need(
            len(names) == len(set(names))
            and set(names) == set(inventory) | {'inventory.json'},
            'Unexpected evidence membership')
        for name, row in inventory.items():
            data = raw(name)
            need(
                len(data) == row['bytes'] and sha(data) == row['sha256'], name)
        bridge = doc('collection/bridge.json')
        current = bridge['source_manifests']['install-input-v2']
        for name, digest in current.items():
            need(
                sha((args.source / name).read_bytes()) == digest,
                'Current source: ' + name)
        for name, digest in bridge['matching_installed_profiler_python'].items(
        ):
            need(
                sha((args.source / 'Profiler/python/flagtree_profiler' /
                     name).read_bytes()) == digest,
                'Installed Python: ' + name)
        native = doc('runs/installed-v2/output/native-source-bridge.json')
        for name, digest in native['matching_native_sources'].items():
            need(
                sha((args.source / name).read_bytes()) == digest,
                'Native source: ' + name)
        for run, code in [('source-v1', 1), ('source-v2', 1), ('source-v3', 1),
                          ('source-v4', 0), ('installed-v1', 0),
                          ('installed-v2', 0), ('browser-v1', 0)]:
            terminal = doc('runs/' + run + '/terminal.json')
            need(
                terminal['state'] == 'terminal'
                and terminal['returncode'] == code, run)
        for mode in ['normal', 'optimized']:
            need(
                b'Ran 16 tests' in
                raw('runs/installed-v2/output/test_nvidia_wait_control.py-' +
                    mode + '.stderr'), 'Missing final negative/positive tests')
            # Optimized pytest also prints its expected assert-rewrite warning.
            need(
                re.search(
                    rb'63 passed,.*32 subtests passed',
                    raw('runs/installed-v1/output/contracts-' + mode +
                        '.stdout')) is not None,
                'Missing regression contracts')
        inspection = doc('runs/installed-v2/output/inspection/result.json')
        control = inspection['control']
        need(len(control['sites']) == 2, 'Missing actual native waits')
        for row in control['sites']:
            need(
                row['status'] == 'wait_control_order_checked'
                and not any(row[key] for key in [
                    'source_region_qualified',
                    'record_value_provenance_verified', 'clock_qualified',
                    'participation_verified'
                ]), 'Overstated control qualification')
        offline = {}
        for label in ['v3', 'v2']:
            base = 'runs/installed-v2/output/offline-' + label + '/'
            summary = doc(base + 'result.json')
            checks = doc(base + 'TP/result.json')['checks']
            need(
                not summary['application_replayed']
                and summary['real_captures'] == 3
                and summary['fresh_reexport_processes'] == 3
                and len(checks) == 24, 'Offline replay or lost data')
            for row in checks:
                need(
                    row['exact_ns_and_raw_references']
                    and not row['importer_errors'] and row['flows'] == 0,
                    'Trace Processor mismatch')
            previous = {}
            for name in names:
                if name.startswith(base + 'retained-timeline/captures/'
                                   ) and name.endswith('.json'):
                    value = doc(name)
                    if type(value) is dict:
                        for row in value.get('counter_ns_exports', []):
                            previous[row['observer_id']] = row['sha256']
            for row in doc(base + 'trace-manifest.json'):
                name = row['trace_file'].split(
                    '/workspace/chijin-timeline-r026/', 1)[1]
                need(
                    sha(raw(name)) == row['sha256'] == previous.get(
                        Path(name).stem), 'Trace bytes changed')
            offline[label] = dict(real_captures=3,
                                  TP_imports=24,
                                  fresh_reexport_processes=3,
                                  trace_bytes_match_original=True,
                                  application_replayed=False)
        ui = doc('runs/browser-v1/output/result.json')
        need(
            len(ui['checks']) == 6
            and ui['before_bundle_files'] == ui['after_bundle_files']
            and not any(ui[key] for key in [
                'precision_qualified', 'source_boundaries_qualified',
                'async_and_flow_qualified'
            ]), 'UI mismatch')
        for row in ui['checks']:
            for image in row['screenshots'].values():
                need(
                    sha(raw('runs/browser-v1/output/' +
                            image['file'])) == image['sha256'],
                    'Screenshot changed')
        need(bridge['active_owned_jobs'] == [], 'Owned jobs remain')
        result = dict(
            status=
            'actual_bytes_source_install_and_control_replay_verified_not_P01',
            product_commit='df48ae5',
            archive=dict(bytes=args.archive.stat().st_size,
                         members=len(names),
                         sha256=sha(args.archive.read_bytes())),
            matching_current_source_files=len(current),
            matching_native_sources=len(native['matching_native_sources']),
            matching_installed_profiler_python=len(
                bridge['matching_installed_profiler_python']),
            core=bridge['installed_core'],
            installation=doc('runs/installed-v2/output/install-result.json'),
            wait_control=control,
            offline=offline,
            UI=dict(traces=6,
                    browser_version=ui['browser_version'],
                    ui_index_sha256=ui['ui_index_sha256']),
            owned_identities=len(bridge['owned_identities']),
            active_owned_jobs=[],
            limits=[
                'Native wait control order only; not source timing or record-value provenance',
                'No new user math; actual r024/r022 captures retained and re-exported without replay',
                'Precision, participation, cross-observer clocks, verified async flows and three-backend P01 incomplete',
                'Independent six-math qualification and final three extra specified code reviewers pending'
            ])
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
