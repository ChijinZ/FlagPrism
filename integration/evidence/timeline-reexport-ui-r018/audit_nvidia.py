"""Stdlib audit of retained GPU raw and counter-ns references; no product import."""
import argparse, hashlib, json, struct, tarfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('archive', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
with tarfile.open(a.archive) as tar:

    def data(name):
        return tar.extractfile(name).read()

    def load(name):
        return json.loads(data(name))

    root = 'chijin-timeline-r018/runs/counter-perfetto-v1/output/capture/timeline'
    index = load(root + '/index.json')
    refs = 0
    events = 0
    exports = []
    before_ids = set()
    if len(index['captures']
           ) != 4 or index['retained_owners'] or index['pending_decode']:
        raise RuntimeError('Default capture count/ownership mismatch')
    for row in index['captures']:
        capture = load(root + '/' + row['capture_file'])
        batch = load(root + '/' + capture['events_file'])
        raw = data(root + '/' + capture['raw_file'])
        owner = capture['owner']
        if hashlib.sha256(raw).hexdigest() != batch['raw_artifact']['sha256']:
            raise RuntimeError('Raw binding changed')
        if owner['host_completion_observed_ns'] <= owner['host_admission_ns']:
            raise RuntimeError('Independent host window missing')
        sites = {r['id']: r for r in batch['sites']}
        by_record = {r['id']: r for r in batch['records']}
        if before_ids & set(by_record):
            raise RuntimeError('Capture endpoint identities collide')
        before_ids.update(by_record)
        for record in batch['records']:
            tag, lo, hi, seq = struct.unpack_from('<4I', raw, record['offset'])
            if record['length'] != 16 or seq != record['sequence'] or record[
                    'tick'] != lo + (hi << 32) or sites[
                        record['site_id']]['backend_site_id'] != str(
                            tag & 0x7fffffff) or record['phase'] != (
                                'exit' if tag & 0x80000000 else 'entry'):
                raise RuntimeError('Physical endpoint differs')
        for event in batch['events']:
            points = [by_record[r] for r in event['record_ids']]
            if [r['tick'] for r in points
                ] != [event['start_tick'], event['end_tick']]:
                raise RuntimeError('Event/raw pair mismatch')
        refs += len(batch['records'])
        events += len(batch['events'])
        digest = hashlib.sha256(
            json.dumps(batch,
                       sort_keys=True,
                       separators=(',', ':'),
                       ensure_ascii=False,
                       allow_nan=False).encode()).hexdigest()
        for export in capture['counter_ns_exports']:
            view = load(root + '/' + export['view_file'])
            blob = data(root + '/' + export['trace_file'])
            if hashlib.sha256(blob).hexdigest(
            ) != export['sha256'] or view['canonical_sha256'] != digest:
                raise RuntimeError('Trace/view binding changed')
            if view['unit_proof']['period_numerator_ns'] != 1 or view[
                    'unit_proof']['period_denominator'] != 1 or view['unit_proof'][
                        'provider'] != 'nvidia.sm120.globaltimer_counter_unit.v1':
                raise RuntimeError('Unexpected actual unit provider')
            if view['clock_status'] != 'counter_unit_only' or view[
                    'read_precision_status'] != 'unverified' or view[
                        'time_arrows_verified'] or view[
                            'source_boundary_status'] != 'unverified':
                raise RuntimeError('Unproved qualification')
            for event in view['events']:
                if event['start_ns'] != event['start_tick'] - view[
                        'origin_tick'] or event['end_ns'] != event[
                            'end_tick'] - view['origin_tick'] or event[
                                'endpoint_error_ns'] is not None:
                    raise RuntimeError('Exact integer ns conversion mismatch')
            exports.append(
                dict(file=export['trace_file'],
                     sha256=export['sha256'],
                     events=len(view['events']),
                     bytes=len(blob)))
    tp = load(
        'chijin-timeline-r018/runs/counter-perfetto-v1/output/TP/result.json')
    checks = [r for r in tp['checks'] if not r['fixture']]
    if len(exports) != 32 or refs != 1344 or events != 672 or len(
            checks) != 32 or sum(r['slices'] for r in checks) != 672:
        raise RuntimeError('Trace/real endpoint counts mismatch')
    if {r['sha256'] for r in exports} != {r['sha256'] for r in checks}:
        raise RuntimeError('TP checked different bytes')
    if any(r['importer_errors'] or r['flows']
           or not r['exact_ns_and_raw_references'] for r in checks):
        raise RuntimeError('Actual TP import/semantic failure')
    installed = load('chijin-timeline-r018/runs/install-v1/output/result.json')
    if installed['installed_members_byte_verified'] != 599 or any(
            s['returncode'] for s in installed['steps']):
        raise RuntimeError('Independent installation/CPU failure')
    for job in [
            'install-v1', 'counter-perfetto-v1', 'offline-v1', 'browser-six-v1'
    ]:
        d = load('chijin-timeline-r018/runs/' + job + '/terminal.json')
        if d['state'] != 'terminal' or d['returncode'] != 0:
            raise RuntimeError('Accepted job is not successful terminal')
    # Verify the newly committed derivative transactions, independently of the product store.
    views = {}
    for row in index['captures']:
        capture = load(root + '/' + row['capture_file'])
        for export in capture['counter_ns_exports']:
            receipt = load(root + '/' + export['receipt_file'])
            if receipt['revision_id'] != export['revision_id']:
                raise RuntimeError('Revision identity mismatch')
            for artifact in receipt['files']:
                blob = data(root + '/' + artifact['file'])
                if len(blob) != artifact['bytes'] or hashlib.sha256(
                        blob).hexdigest() != artifact['sha256']:
                    raise RuntimeError('Committed artifact digest mismatch')
            base = export['receipt_file'].rsplit('/', 1)[0]
            inputs = load(root + '/' + base + '/inputs.json')
            encoded = (json.dumps(inputs,
                                  sort_keys=True,
                                  separators=(',', ':'),
                                  ensure_ascii=False,
                                  allow_nan=False) + '\n').encode()
            if hashlib.sha256(encoded).hexdigest() != export['revision_id']:
                raise RuntimeError('Inputs do not determine revision')
            view = load(root + '/' + export['view_file'])
            views[export['sha256']] = view
            if len(view['unit_proof']['implementation_sha256']) != 64:
                raise RuntimeError(
                    'Provider implementation fingerprint missing')
    ui = load('chijin-timeline-r018/runs/browser-six-v1/output/result.json')
    if len(ui['checks']
           ) != 6 or ui['before_bundle_files'] != ui['after_bundle_files']:
        raise RuntimeError('UI coverage or bundle immutability failure')
    for relative, digest in ui['after_bundle_files'].items():
        if hashlib.sha256(data(root + '/' + relative)).hexdigest() != digest:
            raise RuntimeError('UI inspected another bundle')
    for check in ui['checks']:
        view = views[check['trace_sha256']]
        if check['event_id'] not in {event['id']
                                     for event in view['events']
                                     } or check['page_errors']:
            raise RuntimeError('UI selected a different event or had errors')
        for item in check['screenshots'].values():
            if hashlib.sha256(
                    data('chijin-timeline-r018/runs/browser-six-v1/output/' +
                         item['file'])).hexdigest() != item['sha256']:
                raise RuntimeError('Actual UI screenshot changed')
    offline_root = 'chijin-timeline-r018/runs/offline-v1/output/'
    reports = [
        load(offline_root + name + '.stdout.log')
        for name in ['public-module', 'isolated-normal', 'isolated-optimized']
    ]
    if not reports[0] == reports[1] == reports[2] or reports[0][
            'application_replayed']:
        raise RuntimeError('Fresh-process re-export differs or reports replay')
    offline = load(offline_root + 'result.json')
    if offline['real_traces'] != 32 or not offline[
            'original_environment_denied_in_two_processes']:
        raise RuntimeError('Offline acceptance missing')
    processes = load('chijin-timeline-r018/process-audit.json')
    if processes['live_matching_processes']:
        raise RuntimeError('Own matching process remains live')
    result = dict(
        status=
        'actual_gpu_counter_ns_raw_and_importer_bytes_audited_not_full_P01',
        archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
        archive_bytes=a.archive.stat().st_size,
        archive_members=len(tar.getmembers()),
        real_captures=4,
        physical_endpoint_references=refs,
        real_intervals=events,
        real_traces=32,
        synthetic_nested_pair_fixture_traces=1,
        installed_members_verified=599,
        wheel_sha256=installed['wheel_sha256'],
        traces=exports,
        actual_UI_traces=6,
        offline_reexport_traces=32,
        limitations=[
            'Workstation audit only uses stdlib bytes, no product import or math replay',
            'No read precision/source boundary/async or full UI qualification'
        ])
a.output.write_text(json.dumps(result, indent=2) + '\n')
