"""Preserve compiler-emitted Proton scope locations and immutable source bytes."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path


def _files(location):
    if not isinstance(location, dict):
        return []
    if location.get('kind') == 'file_line_column':
        return [location]
    result = []
    for key in ('callee', 'caller', 'child'):
        result.extend(_files(location.get(key)))
    for child in location.get('candidates', []):
        result.extend(_files(child))
    return result


def _origin_files(location):
    # A caller location is context, not a replacement for a missing callee.
    if not isinstance(location, dict):
        return []
    if location.get('kind') == 'callsite':
        return _origin_files(location.get('callee'))
    if location.get('kind') == 'named':
        return _origin_files(location.get('child'))
    if location.get('kind') == 'fused':
        return [file for child in location.get('candidates', [])
                for file in _origin_files(child)]
    return _files(location)


def _ambiguous(location):
    if not isinstance(location, dict):
        return False
    if location.get('kind') == 'fused' and len(location.get('candidates', [])) > 1:
        return True
    return any(_ambiguous(location.get(key)) for key in ('callee', 'caller', 'child'))


def capture_scope_origins(origins, *, binary_id, compiler_ir_path=None):
    """Capture files once at binary registration; never infer neighboring sites."""
    result, sources = {}, {}
    for scope_id, origin in origins.items():
        value = {**origin, 'binary_id': binary_id, 'scope_id': int(scope_id)}
        phases = {phase: list(origin.get(phase, [])) for phase in ('entry', 'exit')}
        def original_files(location):
            files = _origin_files(location)
            if compiler_ir_path is None:
                return files
            return [item for item in files
                    if Path(item['file']).resolve() != Path(compiler_ir_path).resolve()]
        known = {phase: any(original_files(location) for location in locations)
                 for phase, locations in phases.items()}
        if compiler_ir_path is not None and any(_origin_files(location) and not original_files(location)
                                               for locations in phases.values() for location in locations):
            value['capture_notes'] = ['Serialized IR parser locations are preserved as compiler locations; they do not identify original source.']
        ambiguous = any(len(locations) > 1 or any(_ambiguous(location) for location in locations)
                        for locations in phases.values())
        value['status'] = ('unknown' if not any(known.values()) else 'multiple_candidates' if ambiguous
                           else 'source_region_origin' if all(known.values()) else 'partial')
        value['source_capture'] = []
        for locations in phases.values():
            for location in locations:
                for file_location in _files(location):
                    filename = file_location.get('file')
                    if not isinstance(filename, str):
                        continue
                    if filename not in sources:
                        try:
                            data = Path(filename).read_bytes()
                        except (OSError, ValueError):
                            sources[filename] = {'file': filename, 'status': 'unavailable'}
                        else:
                            digest = hashlib.sha256(data).hexdigest()
                            sources[filename] = {'file': filename, 'status': 'captured',
                                                 'sha256': digest, 'encoding': 'base64',
                                                 'capture_boundary': 'binary_registration_filesystem_snapshot',
                                                 'compiled_text_alignment': 'not_independently_verified',
                                                 'content': base64.b64encode(data).decode('ascii')}
                    source = sources[filename]
                    reference = {**file_location, 'source_capture_status': source['status'],
                                 'source_sha256': source.get('sha256'),
                                 'source_text_relation': 'file_snapshot_at_binary_registration'}
                    if reference not in value['source_capture']:
                        value['source_capture'].append(reference)
        result[str(scope_id)] = value
    return result, list(sources.values())
