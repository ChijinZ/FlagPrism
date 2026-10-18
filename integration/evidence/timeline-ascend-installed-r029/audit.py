"""Stdlib byte audit only: no product imports, tests, math or qualification."""
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT / 'artifacts/timeline/run-029/preflight/ascend-installed-retention-evidence-v1.tgz'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    payload = ARCHIVE.read_bytes()
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        files = {}
        for member in archive.getmembers():
            path = Path(member.name)
            if not member.isfile() or path.is_absolute(
            ) or '..' in path.parts or member.name in files:
                raise ValueError('Unsafe or duplicate member')
            files[member.name] = archive.extractfile(member).read()

    def document(name):
        return json.loads(files[name])

    collection = document('collection.json')
    if collection['reference_v2_started']:
        raise ValueError('Unexpected new reference run')
    for owner in collection['owners']:
        if owner['terminal']['state'] != 'terminal':
            raise ValueError('Unexpected terminal state')
        for row in owner['identities']:
            actual = row['actual']
            if actual and actual['startticks'] == row['expected'][
                    'startticks'] and actual['state'] != 'Z':
                raise ValueError('Live owned identity')
    final = document('runs/install-v2/output/result.json')
    if final[
            'checks'] != 'installed_real_default_capture_object_retention_offline_passed_not_P01':
        raise ValueError('Installed checks incomplete')
    for mode in ('normal', 'optimized'):
        if b'102 passed' not in files['runs/install-v2/output/cpu-' + mode +
                                      '.stdout']:
            raise ValueError('Missing actual contract tests')
    source = document('input-v2/source-manifest.json')
    for name, expected in source['files'].items():
        raw = files['input-v2/component/' + name]
        if digest(raw) != expected or raw != (ROOT / 'FlagPrism-method' /
                                              name).read_bytes():
            raise ValueError('Current source differs ' + name)
    for name, expected in collection['source_installed_python'].items():
        raw = files['input-v2/component/' + name]
        part, relative = name.split('/python/flagtree_', 1)
        suffix = relative.split('/', 1)[1]
        installed = 'installed/flagtree/' + part.lower() + '/' + suffix
        if digest(raw) != expected or files[installed] != raw:
            raise ValueError('Installed module differs ' + name)
    captures = []
    prefix = 'runs/install-v2/output/device-probe/'
    for name, raw in files.items():
        if not name.startswith(prefix) or not name.endswith('.input.json'):
            continue
        capture = json.loads(raw)
        directory = name.split('/captures/')[0] + '/'
        batch = document(
            directory +
            str(Path(capture['raw_file']).with_suffix('.events.json')))
        actual_raw = files[directory + capture['raw_file']]
        if digest(actual_raw) != capture['raw_sha256']:
            raise ValueError('Raw identity')
        for record in batch['records']:
            if struct.unpack_from('<Q', actual_raw,
                                  record['offset'])[0] != record['tick']:
                raise ValueError(
                    'Canonical record differs from actual raw bytes')
        guard = capture['readback_guard']
        if files[directory + guard['file']] != bytes([165]) * 128:
            raise ValueError('Invalid guard')
        metadata = capture['metadata']['compiler_metadata']
        binary = metadata['flagprism_ascend_handoff']['final_outputs'][
            'binary']
        executable = capture['metadata']['compiled_snapshot']['executable']
        loaded = base64.b64decode(
            capture['metadata']['compiled_snapshot']['binary_base64'],
            validate=True)
        if loaded != base64.b64decode(binary['data'], validate=True) or digest(
                loaded) != executable['binary_sha256'] or digest(
                    loaded) != binary['sha256']:
            raise ValueError('Loaded/retained binary mismatch')
        objects = []
        for artifact in metadata['flagprism_ascend_handoff']['artifacts']:
            if artifact['compiled_object_status'] != 'retained':
                raise ValueError('Missing compiled object')
            sealed = artifact['compiled_object']
            receipt = artifact['driver_job']['object']
            data = base64.b64decode(sealed['data'], validate=True)
            if digest(data) != sealed['sha256'] or digest(data) != receipt[
                    'sha256'] or len(data) != sealed['bytes'] or len(
                        data) != receipt['bytes']:
                raise ValueError('Actor object differs from actual receipt')
            objects.append(dict(bytes=len(data), sha256=digest(data)))
        captures.append(
            dict(invocation_id=capture['owner']['invocation_id'],
                 binary_id=capture['owner']['binary_id'],
                 intervals=len(batch['events']),
                 endpoint_records=len(batch['records']),
                 objects=objects))
    if len(captures) != 3:
        raise ValueError('Wrong capture count')
    offline = document('runs/install-v2/output/offline/result.json')
    if offline['captures'] != 2 or offline['application_replayed'] is not False:
        raise ValueError('Wrong offline result')
    for mode in ('public', 'normal', 'optimized'):
        report = document('runs/install-v2/output/offline/' + mode + '.json')
        if any(r['status'] != 'raw_only' for r in report['captures']):
            raise ValueError('Unqualified time export')
    reference = document('runs/reference-v1/output/result.json')
    if any(r['returncode'] != 0 for r in reference['steps']):
        raise ValueError('Reference compile failed')
    return dict(
        scope=
        'installed object retention and real raw/offline math, not clock/source/async qualification',
        archive=dict(file=str(ARCHIVE.relative_to(ROOT)),
                     bytes=len(payload),
                     members=len(files),
                     sha256=digest(payload)),
        source_commit=source['commit'],
        matching_source_files=len(source['files']),
        matching_installed_python_files=len(
            collection['source_installed_python']),
        wheel_sha256=final['wheel_sha256'],
        installed_members=final['installed_members'],
        captures=sorted(captures, key=lambda r: r['invocation_id']),
        offline=offline,
        reference_instructions=[
            dict(name=row['name'], code_sections=row['sections'])
            for row in reference['steps']
        ],
        owned_identity_count=sum(
            len(x['identities']) for x in collection['owners']),
        source_boundary_status='unverified',
        clock_status='unverified',
        full_P01=False)


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
