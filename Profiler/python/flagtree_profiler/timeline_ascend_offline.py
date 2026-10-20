"""Ascend retained-timeline decoding and time-view providers; no device replay."""
from pathlib import Path
from .timeline_store import export_lock, json_bytes, persist, sha256
from .timeline_views import derive_counter_ns_views


def decode_capture(capture, raw):
    from .timeline_events_ascend import canonicalize_ascend_capture
    return canonicalize_ascend_capture(
        raw,
        owner=capture['owner'],
        metadata=capture['metadata']['compiler_metadata'],
        association=capture['launch'])


def decoder_rules(capture):
    from . import timeline_events_ascend, timeline_ascend_offline
    return (timeline_events_ascend, timeline_ascend_offline)


backend_name = 'ascend'


def matches(capture):
    return capture['metadata']['compiler_metadata'].get(
        'debug_record_layout') == 'ascend_source_timeline_v1'


def reexport_views(directory, capture, raw, batch, sources, retain):
    owner = capture['owner']
    rows, reason, control_file, machine_file = [], None, None, None
    shared_rows, shared_reason = [], None
    dependency_rows, dependency_reason = [], None
    from . import timeline_ascend_machine
    binary = owner['binary_id']
    machine_base = 'machine/' + binary
    try:
        for name in ('loaded.elf', 'dwarf.stdout'):
            retain(machine_base + '/' + name)
        actual_map = timeline_ascend_machine.load_counter_machine_map(
            directory, capture)
        machine_inputs = dict(
            schema_version=1,
            original_inputs=dict(sorted(sources.items())),
            machine_map_sha256=sha256(json_bytes(actual_map)),
            rules_sha256=sha256(
                Path(timeline_ascend_machine.__file__).read_bytes()))
        derived = 'derived/machine/' + sha256(json_bytes(machine_inputs))
        with export_lock(directory):
            persist(directory, derived + '/inputs.json',
                    json_bytes(machine_inputs))
            persist(directory, derived + '/counter-map.json',
                    json_bytes(actual_map))
        machine_file = derived + '/counter-map.json'
        from .timeline_unit_ascend import load_counter_unit_proofs
        from .timeline_perfetto import write_counter_exports
        proofs = load_counter_unit_proofs(directory, capture, batch)
        views = derive_counter_ns_views(batch, proofs)
        rows = write_counter_exports(directory,
                                     Path('captures') / owner['invocation_id'],
                                     views,
                                     batch,
                                     proofs=proofs)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        reason = 'Ascend counter mapping unavailable: ' + str(error)
    try:
        from .timeline_ascend_native import load_observed_dependency_inputs
        from .timeline_dependency_perfetto import write_dependency_exports
        dependency_batch, dependency_proofs = load_observed_dependency_inputs(
            directory, capture, raw)
        dependency_rows = write_dependency_exports(directory, dependency_batch,
                                                   dependency_proofs)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        dependency_reason = 'Ascend observed dependencies unavailable: ' + str(
            error)

    result = dict(wait_control_file=control_file,
                  exports=rows,
                  shared_exports=shared_rows,
                  shared_counter_reason=shared_reason,
                  observed_dependency_exports=dependency_rows,
                  observed_dependency_reason=dependency_reason,
                  reason=reason)
    result['machine_counter_map_file'] = machine_file
    try:
        from .timeline_ascend_fragment_store import load_fragment_paths
        result['source_fragment_paths'] = load_fragment_paths(directory,
                                                              capture,
                                                              retain=retain)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError,
            RecursionError) as error:
        result['source_fragment_paths'] = dict(
            status='fragment_paths_unavailable',
            reason=str(error),
            native_schedule_qualified=False)
    return result
