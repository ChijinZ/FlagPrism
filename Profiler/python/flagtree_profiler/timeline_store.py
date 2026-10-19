"""Local, bounded, crash-recoverable publication of immutable derived traces.

This is a storage contract, not a provider of clock or source-boundary proof.
Only a complete, content-checked receipt makes a revision discoverable. The
bundle lock is advisory: all cooperating writers must use this module.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import tempfile
import time


def json_bytes(value):
    return (json.dumps(value,
                       sort_keys=True,
                       separators=(',', ':'),
                       ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def bundle_path(directory, relative):
    """Reject absolute, traversal and symlink paths, including missing leaves."""
    root = Path(directory).resolve()
    if type(relative) is not str or not relative or '\\' in relative:
        raise ValueError('A relative bundle file is required')
    path = Path(relative)
    if path.is_absolute() or str(path) != relative or any(p in ('.', '..')
                                                          for p in path.parts):
        raise ValueError('Unsafe bundle file: ' + relative)
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Bundle artifacts cannot traverse symlinks: ' +
                             relative)
    return root / path


def read_artifact(directory, relative, *, limit=64 * 1024 * 1024):
    path = bundle_path(directory, relative)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing or oversized bundle artifact: ' + relative)
    with path.open('rb') as source:
        payload = source.read(limit + 1)
    if len(payload) > limit:
        raise ValueError('Bundle artifact exceeded read budget: ' + relative)
    return payload


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def export_lock(directory, timeout=5.0):
    if type(timeout) not in (
            int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError(
            'Export lock timeout must be finite and within (0,60]')
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = bundle_path(root, '.timeline-export.lock')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Timeline export lock is not a regular file')
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        'Timeline bundle is locked by another exporter')
                time.sleep(min(0.01, remaining))
        yield root
    finally:
        # Closing also releases this process's lock on exceptions/termination.
        os.close(fd)


def persist(directory, relative, payload, *, replace=False):
    """Call while holding export_lock. Never overwrite immutable evidence."""
    if type(payload) is not bytes:
        raise TypeError('Artifact payload must be bytes')
    path = bundle_path(directory, relative)
    # Persist the parent links as well as file contents: fsync of only the leaf
    # directory would leave a just-created revision undiscoverable after crash.
    current = Path(directory).resolve()
    for part in Path(relative).parts[:-1]:
        parent, current = current, current / part
        if not current.exists():
            current.mkdir()
            _sync_directory(parent)
    if path.exists():
        if read_artifact(directory, relative) == payload:
            return
        if not replace:
            raise ValueError(
                'Refusing to overwrite different timeline evidence: ' +
                relative)
    fd, temporary = tempfile.mkstemp(prefix='.timeline-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            # link is an atomic create-if-absent; unlike replace it cannot
            # overwrite even a non-cooperating writer's completed artifact.
            try:
                os.link(temporary, path)
            except FileExistsError:
                if read_artifact(directory, relative) != payload:
                    raise ValueError(
                        'Conflicting immutable timeline artifact: ' + relative)
        _sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _receipt(directory, relative, *, byte_budget=64 * 1024 * 1024):
    payload = read_artifact(directory, relative, limit=1024 * 1024)
    data = json.loads(payload)
    if (type(data) is not dict or type(data.get('schema_version')) is not int
            or data['schema_version'] != 1
            or type(data.get('files')) is not list or not data['files']
            or len(data['files']) > 256
            or type(data.get('exports')) is not list):
        raise ValueError('Malformed timeline derivative receipt: ' + relative)
    prefix = str(Path(relative).parent)
    files = {}
    remaining = byte_budget
    for row in data['files']:
        if (type(row) is not dict or type(row.get('file')) is not str
                or type(row.get('bytes')) is not int or row['bytes'] < 0
                or row['file'] in files
                or not row['file'].startswith(prefix + '/')):
            raise ValueError('Invalid receipt artifact identity: ' + relative)
        remaining -= row['bytes']
        if remaining < 0:
            raise ValueError('Timeline derivative read budget exceeded')
        raw = read_artifact(directory, row['file'])
        if len(raw) != row['bytes'] or sha256(raw) != row.get('sha256'):
            raise ValueError('Timeline derivative receipt artifact changed: ' +
                             row['file'])
        files[row['file']] = row
    inputs_file = prefix + '/inputs.json'
    inputs = json.loads(
        read_artifact(directory, inputs_file, limit=1024 * 1024))
    if (inputs_file not in files
            or sha256(json_bytes(inputs)) != data.get('revision_id')
            or Path(prefix).name != data['revision_id']):
        raise ValueError('Timeline derivative input/revision mismatch')
    for row in data['exports']:
        if (type(row) is not dict
                or row.get('revision_id') != data['revision_id']
                or row.get('receipt_file') != relative
                or row.get('view_file') not in files
                or row.get('trace_file') not in files
                or row.get('sha256') != files[row['trace_file']]['sha256']
                or row.get('bytes') != files[row['trace_file']]['bytes']):
            raise ValueError(
                'Timeline receipt export differs from committed artifacts')
    return data


def committed_exports(directory):
    """Discover only complete revisions. A broken receipt is an explicit error."""
    root = Path(directory).resolve()
    paths = sorted(root.glob('derived/counter-ns/*/complete.json'))
    if len(paths) > 128:
        raise ValueError('Too many retained timeline derivative revisions')
    remaining, exports = 64 * 1024 * 1024, []
    for path in paths:
        data = _receipt(root,
                        str(path.relative_to(root)),
                        byte_budget=remaining)
        remaining -= sum(row['bytes'] for row in data['files'])
        exports.extend(data['exports'])
    return exports


def find_committed_canonical(directory, canonical):
    """Reuse exact serialized fresh output, never infer facts from cached JSON.

    The caller holds export_lock and has decoded/validated canonical from raw.
    Receipts authenticate candidate bytes; equality binds every identity, raw
    reference and event field to the caller's freshly computed document.
    """
    expected = json_bytes(canonical)
    candidates = sorted({
        str(Path(row['view_file']).parent.parent / 'canonical.json')
        for row in committed_exports(directory)
    })
    for relative in candidates:
        payload = read_artifact(directory, relative)
        if payload == expected:
            return dict(file=relative,
                        bytes=len(payload),
                        sha256=sha256(payload))
    return None


def publish_revision(directory, inputs, files, exports):
    """Publish under an existing export_lock; a receipt is the commit point.

    Files/exports use paths relative to this revision. Failed writes retain
    recoverable files but publish no receipt. Same inputs/outputs are idempotent.
    """
    encoded = json_bytes(inputs)
    if len(encoded) > 1024 * 1024 or type(files) is not dict or len(
            files) > 255:
        raise ValueError('Timeline derivative input/file budget exceeded')
    revision = sha256(encoded)
    base = 'derived/counter-ns/' + revision
    payloads = {base + '/inputs.json': encoded}
    for name, payload in files.items():
        bundle_path(directory, name)
        if name == 'inputs.json' or type(payload) is not bytes:
            raise ValueError('Invalid timeline derivative payload')
        payloads[base + '/' + name] = payload
    rows = []
    for original in exports:
        row = dict(original,
                   revision_id=revision,
                   receipt_file=base + '/complete.json')
        for field in ('view_file', 'trace_file'):
            if row[field] not in files:
                raise ValueError('Export references an uncommitted artifact')
            row[field] = base + '/' + row[field]
        rows.append(row)
    receipt = dict(schema_version=1,
                   revision_id=revision,
                   files=[
                       dict(file=name, bytes=len(raw), sha256=sha256(raw))
                       for name, raw in sorted(payloads.items())
                   ],
                   exports=rows)
    # Existing receipts must still be intact, even for an idempotent re-export.
    receipt_path = bundle_path(directory, base + '/complete.json')
    if receipt_path.exists():
        if _receipt(directory, base + '/complete.json') != receipt:
            raise ValueError(
                'Same derivative inputs produced different outputs')
        return rows
    previous = committed_exports(directory)
    # A new rule implementation can reproduce every output byte exactly.
    # Preserve the original receipt and avoid storing/counting duplicate traces.
    # Retain the new validation inputs separately; never label the old receipt
    # as having been produced by the new implementation.
    for old_receipt in sorted({row['receipt_file'] for row in previous}):
        old = _receipt(directory, old_receipt)
        old_base = str(Path(old_receipt).parent) + '/'
        old_files = {
            row['file'][len(old_base):]: row
            for row in old['files']
            if row['file'].startswith(old_base) and row['file'] != old_base +
            'inputs.json'
        }
        if set(old_files) != set(files) or any(
                old_files[name]['sha256'] != sha256(raw)
                or old_files[name]['bytes'] != len(raw)
                for name, raw in files.items()):
            continue
        expected_rows = [
            dict(row,
                 view_file=old_base + row['view_file'],
                 trace_file=old_base + row['trace_file'],
                 revision_id=old['revision_id'],
                 receipt_file=old_receipt) for row in exports
        ]
        if expected_rows != old['exports']:
            continue
        revalidation = dict(schema_version=1,
                            kind='byte_identical_derivative_revalidation',
                            original_receipt_file=old_receipt,
                            original_receipt_sha256=sha256(
                                read_artifact(directory, old_receipt)),
                            validated_inputs=inputs)
        evidence = json_bytes(revalidation)
        name = 'derived/revalidations/' + sha256(evidence) + '.json'
        existing = list(
            Path(directory).resolve().glob('derived/revalidations/*.json'))
        if any(p.is_symlink() for p in existing):
            raise ValueError('Timeline revalidation contains a symlink')
        if len(existing) >= 128 and not bundle_path(directory, name).exists():
            raise ValueError('Timeline revalidation count budget exceeded')
        if len(evidence) > 1024 * 1024 or sum(
                p.stat().st_size
                for p in existing) + (0 if bundle_path(directory, name).exists(
                ) else len(evidence)) > 8 * 1024 * 1024:
            raise ValueError('Timeline revalidation byte budget exceeded')
        persist(directory, name, evidence)
        return [dict(row, revalidation_file=name) for row in old['exports']]
    if sum(row['bytes']
           for row in previous) + sum(row['bytes']
                                      for row in rows) > 16 * 1024 * 1024:
        raise ValueError(
            'Retained timeline traces exceed the session byte budget')
    # Bound all retained derivative files, including an interrupted writer's
    # uncommitted files. A retry of the same bytes does not count them twice.
    retained, visited = 0, 0
    base_root = Path(directory).resolve() / 'derived/counter-ns'
    if base_root.exists():
        for path in base_root.rglob('*'):
            visited += 1
            if visited > 8192 or path.is_symlink():
                raise ValueError(
                    'Timeline derivative tree exceeds traversal budget or contains a symlink'
                )
            if path.is_file():
                retained += path.stat().st_size
    additions = {**payloads, base + '/complete.json': json_bytes(receipt)}
    retained += sum(
        len(raw) for name, raw in additions.items()
        if not bundle_path(directory, name).exists())
    if retained > 64 * 1024 * 1024:
        raise ValueError('Retained timeline derivatives exceed byte budget')
    for name, raw in payloads.items():
        persist(directory, name, raw)
    persist(directory, base + '/complete.json', json_bytes(receipt))
    return rows
