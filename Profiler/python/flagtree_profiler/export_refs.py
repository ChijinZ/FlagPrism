"""Lossless references from derived views to the complete observation artifact.

References use RFC 6901 pointers and SHA-256 of compact, sorted-key UTF-8 JSON.
Only export copies change; analysis and HTML rendering use original dictionaries.
"""
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value,
                      sort_keys=True,
                      separators=(',', ':'),
                      ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def compact(document, observations, *, fields):
    """Return an export copy replacing selected large fields by exact references."""
    catalog = {}

    def index(value, pointer=''):
        if isinstance(value,
                      (dict, list, str)) and len(canonical(value)) >= 512:
            catalog.setdefault(digest(value), pointer)
        if isinstance(value, dict):
            for key, child in value.items():
                index(
                    child,
                    pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                index(child, pointer + '/' + str(i))

    index(observations)
    used = False

    def visit(value, field=None):
        nonlocal used
        if field in fields and isinstance(value, (dict, list, str)):
            sha = digest(value)
            if sha in catalog:
                used = True
                return {
                    '$observation_ref': {
                        'pointer': catalog[sha],
                        'sha256': sha
                    }
                }
        if isinstance(value, dict):
            return {key: visit(child, key) for key, child in value.items()}
        if isinstance(value, list):
            return [visit(child) for child in value]
        return value

    result = visit(document)
    if used:
        result['export_references'] = {
            'schema_version': 1,
            'file': 'observations.json',
            'sha256': digest(observations),
            'digest_encoding': 'sorted-key compact ASCII JSON UTF-8',
            'pointer_encoding': 'RFC6901',
        }
    return result


def restore(document, observations):
    """Restore the pre-export dictionary, rejecting changed evidence or pointers."""
    contract = document.get('export_references')
    if contract is None:
        return document
    if (not isinstance(contract, dict)
            or type(contract.get('schema_version')) is not int
            or contract['schema_version'] != 1
            or contract.get('digest_encoding')
            != 'sorted-key compact ASCII JSON UTF-8'
            or contract.get('pointer_encoding') != 'RFC6901'):
        raise ValueError('Unsupported observation reference contract')
    if contract.get('file') != 'observations.json' or digest(
            observations) != contract.get('sha256'):
        raise ValueError('Observation reference artifact digest mismatch')

    def visit(value):
        if isinstance(value, dict) and set(value) == {'$observation_ref'}:
            ref = value['$observation_ref']
            if not isinstance(ref, dict) or not isinstance(
                    ref.get('pointer'), str):
                raise ValueError('Invalid observation reference pointer')
            pointer = ref['pointer']
            if pointer and not pointer.startswith('/'):
                raise ValueError('Invalid observation reference pointer')
            node = observations
            for part in pointer.split('/')[1:]:
                if re.search(r'~(?![01])', part):
                    raise ValueError(
                        'Invalid observation reference pointer escape')
                part = part.replace('~1', '/').replace('~0', '~')
                if isinstance(node, list) and not re.fullmatch(
                        r'0|[1-9][0-9]*', part):
                    raise ValueError(
                        'Invalid observation reference array index')
                try:
                    node = node[int(part)] if isinstance(node,
                                                         list) else node[part]
                except (KeyError, IndexError, TypeError) as error:
                    raise ValueError(
                        'Invalid observation reference pointer target'
                    ) from error
            if digest(node) != ref.get('sha256'):
                raise ValueError('Observation reference field digest mismatch')
            return node
        if isinstance(value, dict):
            return {key: visit(child) for key, child in value.items()}
        if isinstance(value, list):
            return [visit(child) for child in value]
        return value

    return visit({
        key: value
        for key, value in document.items() if key != 'export_references'
    })
