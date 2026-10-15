"""Snapshot compiler-referenced files once at actual binary registration."""
import base64
import hashlib
from pathlib import Path


def capture_metadata_sources(*documents):
    from .fine_grained import _location_candidates
    from .execution_enflame import _location_evidence

    files = set()

    def visit(node):
        if isinstance(node, dict):
            location = node.get('sourceLoc')
            if isinstance(location, str):
                evidence, _ = _location_evidence(location, {})
                files.update(row['file']
                             for row in evidence.get('locations', []))
            for child in node.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    for document in documents:
        files.update(row['file'] for row in _location_candidates(document))
        visit(document)
    snapshots = []
    for filename in sorted(files):
        entry = dict(
            file=filename,
            capture_boundary='binary_registration_filesystem_snapshot',
            compiled_text_alignment='not_independently_verified')
        try:
            payload = Path(filename).read_bytes()
        except (OSError, ValueError) as error:
            entry.update(status='unavailable',
                         reason=f'{type(error).__name__}: {error}')
        else:
            entry.update(status='captured',
                         sha256=hashlib.sha256(payload).hexdigest(),
                         encoding='base64',
                         content=base64.b64encode(payload).decode('ascii'))
        snapshots.append(entry)
    return snapshots


def export_metadata_sources(snapshots, output):
    """Replace encoded payloads with bundle references after digest validation."""
    output = Path(output)
    result = []
    for snapshot in snapshots:
        entry = dict(snapshot)
        if entry.get('status') == 'captured':
            payload = base64.b64decode(entry.pop('content'), validate=True)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != entry.get('sha256'):
                raise ValueError(
                    'Compiler-referenced source snapshot digest mismatch')
            reference = f'ai/sources/{digest}.py'
            target = output / reference
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.read_bytes() != payload:
                raise ValueError(
                    'Source snapshot digest path contains different bytes')
            target.write_bytes(payload)
            entry['snapshot_file'] = reference
        result.append(entry)
    return result
