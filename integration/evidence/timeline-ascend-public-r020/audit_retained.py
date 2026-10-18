"""Stdlib retained-byte audit; never imports FlagPrism or executes a workload."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tarfile.open(args.archive) as archive:
        blobs = {}
        for member in archive.getmembers():
            path = Path(member.name)
            require(member.isfile() and not path.is_absolute() and '..' not in path.parts,
                    'Invalid archive entry')
            require(member.name not in blobs, 'Duplicate archive entry')
            blobs[member.name] = archive.extractfile(member).read()
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    document = lambda name: json.loads(blobs[name])
    for name, row in document('audit/inventory.json').items():
        require(len(blobs[name]) == row['bytes'] and sha(blobs[name]) == row['sha256'],
                'Retained inventory mismatch: ' + name)
    processes = document('audit/processes.json')
    require(all(not p['same_startticks'] or p['current_state'] == 'Z' for p in processes),
            'Owned process remained live')
    for name in ['install-v1', 'install-v2', 'recovery-v2', 'legacy-v1']:
        terminal = document('runs/' + name + '/terminal.json')
        require(terminal['state'] == 'terminal' and terminal['returncode'] == 0,
                'Missing actual successful terminal: ' + name)
    failed = document('runs/public-checks-v1/terminal.json')
    require(failed['returncode'] == 1, 'First failed recovery harness was erased')
    steps = document('runs/public-checks-v1/output/steps.json')
    require([(s['name'], s['returncode']) for s in steps] ==
            [('cli', 0), ('offline', 0), ('recovery', 1)], 'First attempt identity changed')
    prefix = 'runs/install-v2/output/device-probe/'
    results = document(prefix + 'result.json')
    require([r['intervals'] for r in results['recurrence']] == [16, 24] and
            results['recurrence'][0]['binary_id'] == results['recurrence'][1]['binary_id'],
            'Runtime-K binary or real occurrence result changed')
    intervals = refs = 0
    for sample in ['recurrence', 'softmax']:
        directory = prefix + sample + '/timeline/'
        index = document(directory + 'index.json')
        for row in index['captures']:
            capture = document(directory + row['capture_file'])
            raw = blobs[directory + capture['raw_file']]
            require(sha(raw) == capture['raw_sha256'], 'Raw bytes changed')
            guard = capture['readback_guard']
            require(blobs[directory + guard['file']] == bytes([165]) * 128,
                    'Actual allocation guard changed')
            batch = document(directory + capture['events_file'])
            for record in batch['records']:
                require(struct.unpack_from('<Q', raw, record['offset'])[0] == record['tick'],
                        'Endpoint does not reference its actual raw tick')
            observed = [o for o in batch['observers'] if o['retained_records']]
            expected = [[0, 0, 0], [4 if sample == 'recurrence' else 2, 0, 0]]
            require([o['program_coordinates'] for o in observed] == expected,
                    'Actual first/last programs are absent')
            require(sum(o['attributes']['ascend.writer_state'] == 'unobserved'
                        for o in batch['observers']) == 2 and not batch['complete'],
                    'Unobserved actors became execution or complete coverage')
            binary = capture['metadata']['compiler_metadata'][
                'flagprism_ascend_handoff']['final_outputs']['binary']
            data = base64.b64decode(binary['data'], validate=True)
            require(sha(data) == binary['sha256'] and len(data) == binary['bytes'],
                    'Retained final binary changed')
            intervals += len(batch['events'])
            refs += len(batch['records'])
    require((intervals, refs) == (50, 100), 'Actual default capture count changed')
    offline = document('runs/public-checks-v1/output/offline/result.json')
    require(offline['captures'] == 2 and offline['application_replayed'] is False and
            all(s['returncode'] == 0 for s in offline['steps']), 'Offline public paths failed')
    recovery = document('runs/recovery-v2/output/result.json')
    require(recovery['user_kernel_calls'] == 4 and recovery['decode_calls_salvaged'] == 2 and
            recovery['invalid_guard_rejected'] and not recovery['application_replayed'],
            'Actual controlled host fault recovery failed')
    for mode in ['normal', 'optimized']:
        require(b'95 passed' in blobs['runs/install-v2/output/cpu-' + mode + '.stdout'],
                'Installed CPU test evidence differs')
    report = dict(status='retained_byte_audit_passed_not_hardware_qualification',
                  archive_bytes=args.archive.stat().st_size,
                  archive_sha256=sha(args.archive.read_bytes()), retained_files=len(blobs),
                  default_intervals=intervals, default_endpoint_refs=refs,
                  process_identities_checked=len(processes),
                  cpu_normal=95, cpu_optimized=95,
                  offline_captures=2, controlled_fault_user_calls=4,
                  limitations=['No unit, boundary, epoch or async qualification',
                               'Does not execute or independently requalify the recorded math',
                               'Host faults do not prove hardware fault recovery'])
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
