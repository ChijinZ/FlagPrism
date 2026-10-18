"""Stdlib-only archive/installed-source/raw-reference audit, not a math oracle.

Run from the workspace root with Python. It neither imports the product nor
executes kernels, tests, tools or UI; server Docker results remain authoritative.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile

p = argparse.ArgumentParser()
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--source-proof', type=Path, required=True)
p.add_argument('--repository', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
with tarfile.open(a.archive) as tar:
    inventory = json.loads(tar.extractfile('inventory.json').read())
    for row in inventory['files']:
        raw = tar.extractfile(row['file']).read()
        if len(raw) != row['bytes'] or hashlib.sha256(
                raw).hexdigest() != row['sha256']:
            raise ValueError('Archive entry differs: ' + row['file'])
    names = set(tar.getnames())
    observations = []
    prefixes = [
        'chijin-timeline-r021/runs/install-v1/output/public-math/public/timeline/',
        'chijin-timeline-r022/runs/final-v1/output/device/public/timeline/'
    ]
    for prefix in prefixes:
        index = json.loads(tar.extractfile(prefix + 'index.json').read())
        for row in index['captures']:
            capture = json.loads(
                tar.extractfile(prefix + row['capture_file']).read())
            batch = json.loads(
                tar.extractfile(prefix + capture['events_file']).read())
            raw = tar.extractfile(prefix + capture['raw_file']).read()
            if hashlib.sha256(raw).hexdigest() != batch['raw_artifact'][
                    'sha256'] or len(raw) != batch['raw_artifact']['bytes']:
                raise ValueError('Canonical raw identity changed')
            for record in batch['records']:
                offset, length = record['offset'], record['length']
                if length != 16 or not 0 <= offset <= len(raw) - length:
                    raise ValueError('Invalid record extent')
                _, low, high, sequence = struct.unpack_from('<4I', raw, offset)
                if record['tick'] != (
                        high << 32) | low or record['sequence'] != sequence:
                    raise ValueError(
                        'Canonical record differs from retained raw field')
            observations.append(
                dict(prefix=prefix,
                     binary=batch['identity']['binary_id'],
                     raw_sha256=batch['raw_artifact']['sha256'],
                     records=len(batch['records']),
                     intervals=len(batch['events']),
                     positive_intervals=sum(
                         e.get('end_tick', 0) > e.get('start_tick', 0)
                         for e in batch['events']),
                     boundary_status=batch['boundary_status'],
                     clock_status=batch['clock_status']))

    def document(suffix):
        rows = [n for n in names if n.endswith(suffix)]
        if len(rows) != 1:
            raise ValueError('Ambiguous evidence: ' + suffix)
        return json.loads(tar.extractfile(rows[0]).read())

    offline = document('consumer-v1/output/offline/result.json')
    tp = document('consumer-v1/output/offline/TP/result.json')
    final = document('final-v1/output/result.json')
    compat = document('compat-v1/output/result.json')
    install = document('install-v2/output/install-result.json')
proof = json.loads(a.source_proof.read_text())
for name, row in proof.items():
    if not isinstance(row, dict) or 'source_sha256' not in row:
        continue
    actual = hashlib.sha256((a.repository / name).read_bytes()).hexdigest()
    if actual != row['source_sha256']:
        raise ValueError('Current source differs from actual server input: ' +
                         name)
    for field in ['installed_sha256', 'native_build_input_sha256']:
        if field in row and row[field] != actual:
            raise ValueError('Installed/native source bridge differs: ' + name)
a.output.write_text(
    json.dumps(dict(
        archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
        archived_files_byte_verified=len(inventory['files']),
        owned_process_audit=inventory['processes'],
        captures=observations,
        offline=offline,
        trace_processor=tp,
        final=final,
        compatibility=compat,
        installation=install,
        claim=
        'Retained byte and source identity audit only; no source-boundary, pipeline, precision, epoch, async or full P01 qualification'
    ),
               indent=2) + '\n')
print(
    json.dumps(
        dict(files=len(inventory['files']),
             captures=len(observations),
             raw_records=sum(r['records'] for r in observations),
             offline_traces=offline['real_traces'])))
