"""Lossless content-addressed storage of repeated capture JSON subtrees.

This codec changes storage, never clock/decoder authority. Legacy inline JSON
remains readable. Object references are explicit paths in a versioned envelope;
ordinary user dictionaries are not interpreted as reference markers.
"""
import copy
import json
from pathlib import Path
import re
import zlib

from .timeline_store import export_lock, json_bytes, persist, read_artifact, sha256

LIMIT = 64 * 1024 * 1024
HEADER_LIMIT = 8 * 1024 * 1024
MAX_REFERENCES = 256
MAX_DEPTH = 64
THRESHOLD = 4096
VERSION_KEY = 'flagprism_capture_storage'


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _envelope(value, references):
    return {VERSION_KEY: 1, 'value': value, 'references': references}


def _check_depth(value):
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        _need(depth <= MAX_DEPTH, 'Capture JSON nesting exceeds its budget')
        if type(node) is dict:
            pending.extend((x, depth + 1) for x in node.values())
        elif type(node) is list:
            pending.extend((x, depth + 1) for x in node)


def _decode_json(raw):
    try:
        return json.loads(raw)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid bounded capture JSON') from error


def persist_capture(directory, relative, capture):
    """Publish shared objects before the immutable capture that references them."""
    _need(
        type(capture) is dict and VERSION_KEY not in capture,
        'Expected an expanded capture document')
    _check_depth(capture)
    _need(len(json_bytes(capture)) <= LIMIT, 'Capture exceeds decoded budget')
    objects = {}
    decoded_object_bytes = 0

    def encode(value, depth=0):
        nonlocal decoded_object_bytes
        _need(depth <= MAX_DEPTH, 'Capture nesting exceeds its budget')
        references = []
        if type(value) in (dict, list):
            small = {} if type(value) is dict else []
            entries = value.items() if type(value) is dict else enumerate(
                value)
            for key, child in entries:
                reduced, refs = encode(child, depth + 1)
                if type(value) is dict:
                    _need(
                        type(key) is str, 'Capture JSON requires string keys')
                    small[key] = reduced
                else:
                    small.append(reduced)
                references.extend(
                    dict(row, path=[key, *row['path']]) for row in refs)
        else:
            small = value
        _need(len(references) <= MAX_REFERENCES, 'Too many capture references')
        payload = json_bytes(_envelope(small, references))
        if depth and len(payload) >= THRESHOLD:
            _need(
                len(payload) <= LIMIT, 'Capture object exceeds decoded budget')
            packed = zlib.compress(payload)
            digest = sha256(packed)
            name = 'objects/capture/' + digest + '.json.zlib'
            if name not in objects:
                decoded_object_bytes += len(payload)
                _need(decoded_object_bytes <= LIMIT,
                      'Capture object read budget exceeded')
                objects[name] = packed
            _need(len(objects) <= MAX_REFERENCES, 'Too many capture objects')
            return None, [
                dict(path=[],
                     file=name,
                     bytes=len(packed),
                     sha256=digest,
                     decoded_bytes=len(payload),
                     decoded_sha256=sha256(payload))
            ]
        return small, references

    value, references = encode(capture)
    payload = json_bytes(_envelope(
        value, references)) if references else json_bytes(capture)
    _need(len(payload) <= HEADER_LIMIT, 'Capture header exceeds its budget')
    with export_lock(directory):
        for name, packed in sorted(objects.items()):
            persist(directory, name, packed)
        persist(directory, relative, payload)


def load_capture(directory, relative, *, retain=None):
    """Restore the exact logical JSON, verifying every retained object and bound.

    ``retain`` optionally records the header and compressed objects in an offline
    export's authoritative input closure. No SDK/cache/device access is used.
    """
    # Legacy collectors wrote inline documents up to the full bundle budget.
    # The smaller header bound applies only to the new reference envelope.
    raw = read_artifact(directory, relative, limit=LIMIT)
    if retain is not None:
        retain(relative, digest=sha256(raw), size=len(raw))
    document = _decode_json(raw)
    _need(type(document) is dict, 'Capture document must be a dictionary')
    if VERSION_KEY not in document:
        _check_depth(document)
        _need(
            len(json_bytes(document)) <= LIMIT,
            'Legacy capture exceeds its budget')
        return document
    _need(len(raw) <= HEADER_LIMIT, 'Capture header exceeds its budget')
    cache, active = {}, set()
    seen = set()
    decoded_total = 0

    def expand(envelope, depth):
        nonlocal decoded_total
        _need(depth <= MAX_DEPTH, 'Capture object graph is too deep')
        _need(
            type(envelope) is dict
            and set(envelope) == {VERSION_KEY, 'value', 'references'}
            and type(envelope[VERSION_KEY]) is int
            and envelope[VERSION_KEY] == 1, 'Unknown capture storage envelope')
        refs = envelope['references']
        _need(
            type(refs) is list and len(refs) <= MAX_REFERENCES,
            'Invalid capture reference list')
        value = copy.deepcopy(envelope['value'])
        _check_depth(value)
        value_bytes = len(json_bytes(value))
        _need(value_bytes <= LIMIT, 'Capture value exceeds its budget')
        paths = []
        for row in refs:
            _need(
                type(row) is dict and set(row) == {
                    'path', 'file', 'bytes', 'sha256', 'decoded_bytes',
                    'decoded_sha256'
                }, 'Invalid capture reference descriptor')
            path = row['path']
            _need(
                type(path) is list and len(path) <= MAX_DEPTH and all(
                    type(p) is str or type(p) is int and p >= 0 for p in path),
                'Invalid capture reference path')
            _need(
                all(path[:len(p)] != p and p[:len(path)] != path
                    for p in paths), 'Overlapping capture references')
            paths.append(path)
            digest = row['sha256']
            _need(
                type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest)
                and row['file'] == 'objects/capture/' + digest + '.json.zlib',
                'Invalid capture object identity')
            _need(
                type(row['bytes']) is int and 0 < row['bytes'] <= LIMIT
                and type(row['decoded_bytes']) is int
                and 0 < row['decoded_bytes'] <= LIMIT
                and type(row['decoded_sha256']) is str
                and re.fullmatch('[0-9a-f]{64}', row['decoded_sha256']),
                'Invalid capture object extent')
            key = (digest, row['bytes'], row['decoded_sha256'],
                   row['decoded_bytes'])
            _need(digest not in active, 'Cyclic capture references')
            if key not in cache:
                seen.add(digest)
                _need(len(seen) <= MAX_REFERENCES, 'Too many capture objects')
                packed = read_artifact(directory,
                                       row['file'],
                                       limit=row['bytes'])
                _need(
                    len(packed) == row['bytes'] and sha256(packed) == digest,
                    'Capture object storage digest mismatch')
                inflater = zlib.decompressobj()
                try:
                    payload = inflater.decompress(packed,
                                                  row['decoded_bytes'] + 1)
                except zlib.error as error:
                    raise ValueError(
                        'Invalid compressed capture object') from error
                _need(
                    len(payload) == row['decoded_bytes'] and inflater.eof
                    and not inflater.unused_data
                    and not inflater.unconsumed_tail
                    and sha256(payload) == row['decoded_sha256'],
                    'Capture object decoded extent/digest mismatch')
                decoded_total += len(payload)
                _need(decoded_total <= LIMIT,
                      'Capture object read budget exceeded')
                if retain is not None:
                    retain(row['file'], digest=digest, size=len(packed))
                active.add(digest)
                expanded = expand(_decode_json(payload), depth + 1)
                cache[key] = (expanded, len(json_bytes(expanded)))
                active.remove(digest)
            expanded, expanded_bytes = cache[key]
            value_bytes += expanded_bytes - len(json_bytes(None))
            _need(value_bytes <= LIMIT, 'Restored capture exceeds its budget')
            restored = copy.deepcopy(expanded)
            if not path:
                _need(value is None,
                      'Capture root reference has a nonempty placeholder')
                value = restored
            else:
                parent = value
                try:
                    for part in path[:-1]:
                        _need((type(parent) is dict and type(part) is str)
                              or (type(parent) is list and type(part) is int),
                              'Capture reference path traverses a scalar')
                        parent = parent[part]
                    last = path[-1]
                    _need((type(parent) is dict and type(last) is str)
                          or (type(parent) is list and type(last) is int),
                          'Capture reference path has the wrong container')
                    _need(parent[last] is None,
                          'Capture reference placeholder changed')
                    parent[last] = restored
                except (KeyError, IndexError, TypeError) as error:
                    raise ValueError(
                        'Missing capture reference placeholder') from error
            _check_depth(value)
        return value

    result = expand(document, 0)
    _need(
        type(result) is dict and VERSION_KEY not in result,
        'Invalid restored capture document')
    return result


def load_capture_file(path, *, retain=None):
    """Read a standard ``BUNDLE/timeline/captures/*.json`` capture path."""
    path = Path(path)
    _need(path.parent.name == 'captures',
          'Expected a standard capture file path')
    return load_capture(path.parent.parent,
                        'captures/' + path.name,
                        retain=retain)
