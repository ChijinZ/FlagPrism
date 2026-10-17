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

    root = 'runs/counter-perfetto-v2/output/capture/timeline'
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
    tp = load('runs/counter-perfetto-v2/output/TP/result.json')
    checks = [r for r in tp['checks'] if not r['fixture']]
    if len(exports) != 32 or refs != 1344 or events != 672 or len(
            checks) != 32 or sum(r['slices'] for r in checks) != 672:
        raise RuntimeError('Trace/real endpoint counts mismatch')
    if {r['sha256'] for r in exports} != {r['sha256'] for r in checks}:
        raise RuntimeError('TP checked different bytes')
    if any(r['importer_errors'] or r['flows']
           or not r['exact_ns_and_raw_references'] for r in checks):
        raise RuntimeError('Actual TP import/semantic failure')
    installed = load('runs/install-v4/output/result.json')
    if installed['installed_members_byte_verified'] != 597 or any(
            s['returncode'] for s in installed['steps']):
        raise RuntimeError('Independent installation/CPU failure')
    for job in ['install-v4', 'counter-perfetto-v2']:
        d = load('runs/' + job + '/terminal.json')
        if d['state'] != 'terminal' or d['returncode'] != 0:
            raise RuntimeError('Accepted job is not successful terminal')
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
        installed_members_verified=597,
        wheel_sha256=installed['wheel_sha256'],
        traces=exports,
        limitations=[
            'Workstation audit only uses stdlib bytes, no product import or math replay',
            'No read precision/source boundary/async or UI qualification'
        ])
a.output.write_text(json.dumps(result, indent=2) + '\n')
