"""NVIDIA record-layout selection for shared offline consumers.

The exporter does not interpret native packet layouts, marker phases or wait
instructions. Legacy and late producers keep their own decoder/proof rules.
"""
from pathlib import Path


def _late(capture):
    return capture['owner']['layout'].get('storage_version') == 'nvidia-late-1'


def decode_capture(capture, raw):
    owner, metadata = capture['owner'], capture['metadata']
    if _late(capture):
        from .timeline_events_nvidia_late import canonicalize_late_capture
        return canonicalize_late_capture(raw, owner=owner, metadata=metadata)
    from .timeline_nvidia import decode_timeline_ring
    from .timeline_events_nvidia import canonicalize_nvidia_capture
    import hashlib
    layout = owner['layout']
    warps = metadata['compiler_metadata']['num_warps']
    decoded = decode_timeline_ring(
        raw,
        scratch_size=layout['scratch_size'],
        total_warps=warps,
        selected_warps=tuple(range(warps)),
        slots=tuple(tuple(slot) for slot in layout['slots']),
        scope_ids=frozenset(int(key) for key, _ in metadata['scope_id_names']),
        record_version=owner['plan']['timeline_record_version'])
    return canonicalize_nvidia_capture(
        decoded,
        owner=owner,
        metadata=metadata,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        raw_bytes=len(raw))


def decoder_rules(capture):
    from . import timeline_nvidia_offline
    if _late(capture):
        from . import timeline_events_nvidia_late, timeline_nvidia_late_raw, timeline_nvidia_late_storage, timeline_nvidia_late_async, timeline_nvidia_late_model
        return (timeline_nvidia_offline, timeline_events_nvidia_late,
                timeline_nvidia_late_raw, timeline_nvidia_late_storage,
                timeline_nvidia_late_async, timeline_nvidia_late_model)
    from . import timeline_events_nvidia, timeline_nvidia, timeline_nvidia_async
    return (timeline_nvidia_offline, timeline_events_nvidia, timeline_nvidia,
            timeline_nvidia_async)


def load_counter_machine_map(directory, capture):
    if _late(capture):
        from .timeline_unit_nvidia_late import load_late_machine_map
        return load_late_machine_map(directory, capture)
    from .timeline_unit_nvidia import load_counter_machine_map as legacy
    return legacy(directory, capture)


def load_counter_unit_proofs(directory, capture, batch):
    if _late(capture):
        from .timeline_unit_nvidia_late import load_late_counter_unit_proofs
        return load_late_counter_unit_proofs(directory, capture, batch)
    from .timeline_unit_nvidia import load_counter_unit_proofs as legacy
    return legacy(directory, capture, batch)


def control_evidence(capture, machine_map, *, sass_lines, sass_json):
    if _late(capture):
        from . import timeline_nvidia_late_control
        return (timeline_nvidia_late_control.inspect_late_wait_control(
            machine_map=machine_map,
            sass_lines=sass_lines,
            sass_json=sass_json,
            plan=capture['owner']['plan']),
                Path(timeline_nvidia_late_control.__file__))
    from . import timeline_nvidia_control
    return (timeline_nvidia_control.inspect_wait_control_brackets(
        machine_map=machine_map,
        sass_lines=sass_lines,
        sass_json=sass_json,
        plan=capture['owner']['plan']), Path(timeline_nvidia_control.__file__))
