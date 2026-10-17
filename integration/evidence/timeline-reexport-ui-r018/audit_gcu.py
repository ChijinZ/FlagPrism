"""Stdlib raw-byte and retained-revision audit; no product imports/math replay."""
import argparse, hashlib, json, struct, tarfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('archive', type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
with tarfile.open(a.archive) as t:

    def raw(name):
        return t.extractfile(name).read()

    def load(name):
        return json.loads(raw(name))

    base = 'chijin-timeline-r018/'
    rows = []
    seen = set()
    for phase in ['api-cold', 'api-warm']:
        root = base + 'runs/public-timeline-v1/output/' + phase + '/timeline'
        index = load(root + '/index.json')
        if len(index['captures']) != 3 or index['retained_owners'] or index[
                'pending_decode'] or index['failures']:
            raise RuntimeError('Default capture/owner failure')
        for item in index['captures']:
            capture = load(root + '/' + item['capture_file'])
            batch = load(root + '/' + capture['events_file'])
            blob = raw(root + '/' + capture['raw_file'])
            if hashlib.sha256(blob).hexdigest(
            ) != batch['raw_artifact']['sha256'] or len(blob) != batch[
                    'raw_artifact']['bytes'] or not batch['complete']:
                raise RuntimeError('Raw binding/completeness mismatch')
            if batch['clock_status'] != 'unverified' or batch[
                    'boundary_status'] != 'unverified':
                raise RuntimeError('Raw gained an unproven qualification')
            ids = {r['id']
                   for r in batch['records']
                   } | {e['id']
                        for e in batch['events']}
            if ids & seen: raise RuntimeError('Invocation namespace collision')
            seen.update(ids)
            by_id = {r['id']: r for r in batch['records']}
            for endpoint in batch['records']:
                if endpoint['length'] != 8 or struct.unpack_from(
                        '<Q', blob, endpoint['offset'])[0] != endpoint['tick']:
                    raise RuntimeError(
                        'Canonical endpoint differs from actual field')
            for event in batch['events']:
                points = [by_id[key] for key in event['record_ids']]
                if [r['phase'] for r in points] != ['entry', 'exit'] or [
                        r['tick'] for r in points
                ] != [event['start_tick'], event['end_tick']]:
                    raise RuntimeError('Actual pair mismatch')
            counts = [
                sum(e['observer_id'] == o['id'] for e in batch['events'])
                for o in batch['observers']
            ]
            if not all(n >= 2 for n in counts):
                raise RuntimeError(
                    'Host header without actual observer events')
            md = capture['metadata']['compiler_metadata']
            stride = md['debug_dynamic_slot_bytes']
            grid = capture['owner']['layout']['grid']
            total = grid[0] * grid[1] * grid[2]
            programs = [0] if total == 1 else [0, total - 1]
            if stride % 4 or len(blob) != stride * len(programs):
                raise RuntimeError('GCU slot extent/units mismatch')
            for slot, program in enumerate(programs):
                header = struct.unpack_from('<8I', blob, slot * stride)
                if not header[3] & 32 or header[7] != program or not header[0]:
                    raise RuntimeError(
                        'Selected writer did not actually arrive/publish')
            rows.append(
                dict(phase=phase,
                     invocation_id=batch['identity']['invocation_id'],
                     raw_sha256=batch['raw_artifact']['sha256'],
                     events_per_observer=counts,
                     endpoints=len(batch['records']),
                     intervals=len(batch['events']),
                     positive_intervals=sum(e['end_tick'] > e['start_tick']
                                            for e in batch['events'])))
    if [r['events_per_observer']
            for r in rows] != [[10, 10], [14, 14], [18]] * 2:
        raise RuntimeError('Actual runtime occurrence structure changed')
    install = load(base + 'runs/install-v1/output/result.json')
    if install['installed_members_byte_verified'] != 455 or any(
            r['returncode'] for r in install['steps']):
        raise RuntimeError('Independent install/CPU failure')
    for job in [
            'install-v1', 'public-timeline-v1', 'offline-v1', 'clock-api-v1'
    ]:
        terminal = load(base + 'runs/' + job + '/terminal.json')
        if terminal['state'] != 'terminal' or terminal['returncode'] != 0:
            raise RuntimeError('Accepted job is not successful terminal')
    offline_root = base + 'runs/offline-v1/output/'
    reports = [
        load(offline_root + name + '.stdout.log')
        for name in ['public-module', 'isolated-normal', 'isolated-optimized']
    ]
    if not reports[0] == reports[1] == reports[2] or reports[0][
            'application_replayed'] or len(reports[0]['captures']) != 3:
        raise RuntimeError('Offline fresh-process replay/identity failure')
    for capture in reports[0]['captures']:
        if capture['status'] != 'raw_only' or capture[
                'exports'] or not capture['reason']:
            raise RuntimeError('Unknown unit became a trace')
        canonical = load(offline_root + 'retained-timeline/' +
                         capture['canonical_file'])
        source = next(
            r for r in rows
            if r['invocation_id'] == canonical['identity']['invocation_id'])
        if source['raw_sha256'] != canonical['raw_artifact']['sha256']:
            raise RuntimeError('Offline raw binding differs')
        receipt_path = capture['canonical_file'].rsplit(
            '/', 1)[0] + '/complete.json'
        receipt = load(offline_root + 'retained-timeline/' + receipt_path)
        for file in receipt['files']:
            blob = raw(offline_root + 'retained-timeline/' + file['file'])
            if len(blob) != file['bytes'] or hashlib.sha256(
                    blob).hexdigest() != file['sha256']:
                raise RuntimeError('Offline canonical receipt mismatch')
    processes = load(base + 'process-audit.json')
    if processes['live_matching_processes']:
        raise RuntimeError('Live matching owned process remains')
    output = dict(
        status='actual_GCU_raw_and_offline_revision_bytes_audited_not_full_P01',
        archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
        archive_bytes=a.archive.stat().st_size,
        archive_members=len(t.getmembers()),
        real_captures=len(rows),
        physical_endpoint_references=sum(r['endpoints'] for r in rows),
        real_intervals=sum(r['intervals'] for r in rows),
        positive_intervals=sum(r['positive_intervals'] for r in rows),
        installed_members_verified=455,
        wheel_sha256=install['wheel_sha256'],
        offline_capture_reexports=3,
        offline_fresh_processes=3,
        captures=rows,
        SDK_clock_investigation=load(base +
                                     'runs/clock-api-v1/output/result.json'),
        limitations=[
            'Stdlib audit only; no product import or math replay on workstation',
            'No clock-unit/source-boundary/allocation-guard/async/Perfetto/independent-math qualification'
        ])
a.output.write_text(json.dumps(output, indent=2) + '\n')
