"""Host wall time for collection finalization and report export.

These measurements are engineering costs, not device execution measurements.
Receipt persistence itself is excluded and explicitly documented.
"""
import hashlib
import json
import math
from pathlib import Path


def write_receipt(output, *, phases, complete, scope):
    output = Path(output)
    if not phases or any(type(value) not in (int, float) or not math.isfinite(value)
                         or value < 0 for value in phases.values()):
        raise ValueError('export timing phases must be finite nonnegative seconds')
    document = {
        'schema_version': 1,
        'clock': 'host.monotonic',
        'unit': 'seconds',
        'phases': phases,
        'export_wall_s': sum(phases.values()) if complete else None,
        'complete_finalize_and_export': complete,
        'scope': scope,
        'excludes': ['application_execution', 'final_timing_receipt_persistence'],
        'meaning': 'Host finalization/export cost; not kernel latency or GPU overhead.',
    }
    payload = (json.dumps(document, indent=2, allow_nan=False) + '\n').encode()
    relative = 'ai/export_timing.json'
    (output / relative).write_bytes(payload)
    manifest_path = output / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        manifest['files'][relative] = {
            'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    return document


def finish_sessions(states, elapsed):
    """API export is inside finalize; CLI exports raw results afterwards."""
    for state in states:
        if not state.get('exported'):
            continue
        output = state.get('bundle_output')
        if output is not None:
            if (Path(output) / 'manifest.json').is_file():
                write_receipt(output, phases={'session_finalize_and_bundle_export_s': elapsed},
                              complete=True, scope='finalize_call_all_selected_sessions')
        elif state.get('name'):
            path = Path(state['name']).with_suffix('.finalization.json')
            path.write_text(json.dumps({
                'schema_version': 1, 'collector_finalize_s': elapsed,
                'scope': 'finalize_call_all_selected_sessions',
                'includes_bundle_export': False,
            }, allow_nan=False) + '\n')
