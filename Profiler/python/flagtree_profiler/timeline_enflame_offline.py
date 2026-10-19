"""Enflame retained-timeline decoding and time-view providers; no device replay."""
import base64
from pathlib import Path
from .timeline_store import sha256
from .timeline_views import derive_counter_ns_views


def decode_capture(capture, raw):
    from .timeline_events_enflame import canonicalize_enflame_capture
    owner = capture['owner']
    native = owner['native_export_metadata']
    runtime = dict(native['runtime_metadata'])
    runtime.update(profiler_invocation_id=capture['launch']['invocation_id'],
                   profiler_association_evidence=capture['launch'])
    return canonicalize_enflame_capture(
        dict(capture_status='raw_complete',
             record_layout=capture['metadata']['compiler_metadata']
             ['debug_record_layout'],
             runtime_metadata=runtime,
             raw_base64=base64.b64encode(raw).decode(),
             raw_sha256=sha256(raw)),
        compiler_metadata=capture['metadata']['compiler_metadata'],
        capture_id=owner['capture_id'])


def decoder_rules(capture):
    from . import (timeline_events_enflame, timeline_events_enflame_native,
                   timeline_enflame_offline)
    return (timeline_events_enflame, timeline_events_enflame_native,
            timeline_enflame_offline)


backend_name = 'enflame'


def matches(capture):
    return 'native_export_metadata' in capture['owner']


def reexport_views(directory, capture, raw, batch, sources, retain):
    owner, metadata = capture['owner'], capture['metadata']
    rows, reason, control_file = [], None, None
    shared_rows, shared_reason = [], None
    dependency_rows, dependency_reason = [], None
    try:
        retain(metadata['clock_calibration_file'])
        from .timeline_unit_enflame import load_counter_unit_proofs
        from .timeline_perfetto import write_counter_exports
        proofs = load_counter_unit_proofs(directory, capture, batch)
        views = derive_counter_ns_views(batch, proofs)
        rows = write_counter_exports(directory,
                                     Path('captures') / owner['invocation_id'],
                                     views,
                                     batch,
                                     proofs=proofs)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        reason = 'GCU counter calibration unavailable: ' + str(error)
    try:
        from .timeline_enflame_dependencies import load_observed_dependency_inputs
        from .timeline_dependency_perfetto import write_dependency_exports
        dependency_batch, dependency_proofs = load_observed_dependency_inputs(
            directory, capture, raw, canonical=batch)
        dependency_rows = write_dependency_exports(directory, dependency_batch,
                                                   dependency_proofs)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        dependency_reason = 'GCU observed dependencies unavailable: ' + str(
            error)

    result = dict(wait_control_file=control_file,
                  exports=rows,
                  shared_exports=shared_rows,
                  shared_counter_reason=shared_reason,
                  observed_dependency_exports=dependency_rows,
                  observed_dependency_reason=dependency_reason,
                  reason=reason)
    return result
