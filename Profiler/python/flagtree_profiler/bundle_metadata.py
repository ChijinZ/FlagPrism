"""Lossless references between the three derived compiler-metadata views.

Raw collector artifacts and execution.json are never rewritten. References are
registered in a bounded sidecar, so arbitrary user dictionaries are not treated
as references merely because they resemble a marker.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

from .export_refs import canonical, digest

FILES = frozenset(
    ('ai/execution.json', 'ai/binaries.json', 'report/report.json'))
CATALOG = 'ai/metadata_refs.json'
LIMIT = 64 * 1024 * 1024
MARKER = '$flagprism_bundle_ref'


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _path(root, name):
    _need(name in FILES or name == CATALOG, 'Unknown metadata view path')
    path = (root / name).resolve()
    _need(path.is_relative_to(root), 'Metadata path escapes the bundle')
    return path


def _read(root, name, limit=LIMIT):
    path = _path(root, name)
    _need(path.is_file() and path.stat().st_size <= limit,
          'Missing or oversized metadata view')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    _need(len(raw) <= limit, 'Oversized metadata view')
    return raw


def _parts(pointer):
    _need(
        isinstance(pointer, str)
        and (pointer == '' or pointer.startswith('/')),
        'Invalid metadata pointer')
    parts = pointer.split('/')[1:] if pointer else []
    _need(len(parts) <= 64, 'Metadata pointer is too deep')
    _need(all(not re.search(r'~(?![01])', p) for p in parts),
          'Invalid metadata pointer escape')
    return [p.replace('~1', '/').replace('~0', '~') for p in parts]


def _key(node, part):
    if isinstance(node, list):
        _need(
            re.fullmatch(r'0|[1-9][0-9]*', part) is not None,
            'Invalid metadata array index')
        return int(part)
    _need(isinstance(node, dict), 'Metadata pointer traverses a scalar')
    return part


def _node(document, parts):
    try:
        for part in parts:
            document = document[_key(document, part)]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('Missing metadata pointer target') from error
    return document


def load_bundle_json(output, name):
    """Read a derived view, restoring exact logical values and checking hashes.

    Legacy bundles without the sidecar retain their ordinary JSON semantics.
    This reads only the three declared metadata views, never SDK/cache files.
    """
    root = Path(output).resolve()
    if not _path(root, CATALOG).exists():
        return json.loads(_read(root, name))
    catalog = json.loads(_read(root, CATALOG, 1024 * 1024))
    _need(
        type(catalog) is dict and catalog.get('schema_version') == 1
        and type(catalog.get('schema_version')) is int
        and set(catalog) == {'schema_version', 'files'},
        'Unknown metadata reference catalog')
    files = catalog['files']
    _need(
        type(files) is dict and set(files) <= FILES,
        'Invalid metadata reference files')
    cache, active = {}, set()
    reference_count = 0
    for filename, row in files.items():
        _need(
            type(row) is dict and set(row) == {'sha256', 'references'}
            and type(row['references']) is list,
            'Invalid metadata reference file entry')
        reference_count += len(row['references'])
        pointers = []
        for ref in row['references']:
            _need(
                type(ref) is dict and set(ref)
                == {'pointer', 'file', 'target_pointer', 'sha256'}
                and ref['file'] in files, 'Invalid metadata reference')
            parts = _parts(ref['pointer'])
            _parts(ref['target_pointer'])
            _need(
                parts and all(parts[:len(p)] != p and p[:len(parts)] != parts
                              for p in pointers),
                'Overlapping metadata reference locations')
            pointers.append(parts)
    _need(reference_count <= 256, 'Too many metadata references')

    def load(filename):
        if filename in cache:
            return cache[filename]
        _need(filename not in active, 'Cyclic metadata references')
        active.add(filename)
        raw = _read(root, filename)
        row = files.get(filename)
        if row is not None:
            _need(
                hashlib.sha256(raw).hexdigest() == row['sha256'],
                'Metadata view digest mismatch')
        document = json.loads(raw)
        expanded_bytes = len(raw)
        for ref in row['references'] if row is not None else []:
            parts = _parts(ref['pointer'])
            expected = {
                MARKER: {
                    k: ref[k]
                    for k in ('file', 'target_pointer', 'sha256')
                }
            }
            _need(
                _node(document, parts) == expected,
                'Metadata reference marker differs from its catalog')
            value = _node(load(ref['file']), _parts(ref['target_pointer']))
            encoded = canonical(value)
            _need(
                len(encoded) <= LIMIT
                and hashlib.sha256(encoded).hexdigest() == ref['sha256'],
                'Metadata reference target digest mismatch')
            expanded_bytes += len(encoded)
            _need(expanded_bytes <= LIMIT,
                  'Restored metadata view exceeds its size bound')
            parent = _node(document, parts[:-1])
            parent[_key(parent, parts[-1])] = copy.deepcopy(value)
        _need(
            len(canonical(document)) <= LIMIT,
            'Restored metadata view exceeds its size bound')
        active.remove(filename)
        cache[filename] = document
        return document

    return load(name)


def compact_timeline_metadata(output):
    """Reference only exact duplicate blocks in derived timeline metadata."""
    root = Path(output).resolve()
    _need(not _path(root, CATALOG).exists(),
          'Metadata compaction must not overwrite a reference catalog')
    if not all(_path(root, name).is_file() for name in FILES):
        return
    raw = {name: _read(root, name) for name in FILES}
    documents = {name: json.loads(value) for name, value in raw.items()}
    execution = documents['ai/execution.json']
    binaries = documents['ai/binaries.json']
    report = documents['report/report.json']
    if not (type(execution) is dict and type(execution.get('binaries')) is list
            and type(binaries) is list and type(report) is dict):
        return
    original_binaries = digest(binaries)
    mappings = {
        digest(value): (i, value)
        for i, value in enumerate(execution['binaries'])
    }
    references = {name: [] for name in FILES}

    def replace(filename, document, pointer, value, target, target_pointer):
        if len(canonical(value)) < 4096:
            return
        ref = dict(pointer=pointer,
                   file=target,
                   target_pointer=target_pointer,
                   sha256=digest(value))
        parts = _parts(pointer)
        parent = _node(document, parts[:-1])
        parent[_key(parent, parts[-1])] = {
            MARKER: {
                k: ref[k]
                for k in ('file', 'target_pointer', 'sha256')
            }
        }
        references[filename].append(ref)

    for i, binary in enumerate(binaries):
        if type(binary) is not dict or 'execution_manifest' not in binary:
            continue
        match = mappings.get(digest(binary['execution_manifest']))
        if match is None:
            continue
        index, mapping = match
        pointer = '/binaries/' + str(index)
        body = mapping.get('mapping') if type(mapping) is dict else None
        resources = body.get('resources') if type(body) is dict else None
        resources = resources if type(resources) is dict else {}
        if ('compiler_metadata' in binary and 'values' in resources and digest(
                binary['compiler_metadata']) == digest(resources['values'])):
            replace('ai/binaries.json', binaries,
                    '/' + str(i) + '/compiler_metadata',
                    binary['compiler_metadata'], 'ai/execution.json',
                    pointer + '/mapping/resources/values')
        replace('ai/binaries.json', binaries,
                '/' + str(i) + '/execution_manifest',
                binary['execution_manifest'], 'ai/execution.json', pointer)
    if 'binaries' in report and digest(
            report['binaries']) == original_binaries:
        replace('report/report.json', report, '/binaries', report['binaries'],
                'ai/binaries.json', '')
    if not any(references.values()):
        return
    encoded = {
        name:
        canonical(documents[name]) + b'\n' if references[name] else raw[name]
        for name in FILES
    }
    catalog = dict(schema_version=1,
                   files={
                       name:
                       dict(sha256=hashlib.sha256(encoded[name]).hexdigest(),
                            references=references[name])
                       for name in FILES
                   })
    # These are derived views in a new output directory. Raw input is retained
    # by the enclosing export path if writing any derived view fails.
    for name in FILES:
        if references[name]:
            _path(root, name).write_bytes(encoded[name])
    _path(root, CATALOG).write_bytes(canonical(catalog) + b'\n')
