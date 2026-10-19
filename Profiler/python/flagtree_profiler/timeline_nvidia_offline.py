"""NVIDIA record-layout selection for shared offline consumers.

The exporter does not interpret native packet layouts, marker phases or wait
instructions. Legacy and late producers keep their own decoder/proof rules.
"""
from pathlib import Path
import json
from .timeline_store import export_lock, json_bytes, persist, read_artifact, sha256
from .timeline_views import derive_counter_ns_views


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


def control_evidence(capture,
                     machine_map,
                     *,
                     sass_lines,
                     sass_json,
                     directory=None):
    if _late(capture):
        from . import timeline_nvidia_late_control
        report = timeline_nvidia_late_control.inspect_late_wait_control(
            machine_map=machine_map,
            sass_lines=sass_lines,
            sass_json=sass_json,
            plan=capture['owner']['plan'])
        if directory is not None:
            from .timeline_nvidia_late_origins import inspect_native_header_origins
            report['native_header_origins'] = inspect_native_header_origins(
                directory, capture, machine_map)
        if directory is not None:
            from .timeline_nvidia_late_boundaries import load_native_boundary_report
            report['native_boundaries'] = load_native_boundary_report(
                directory, capture, machine_map)
            from .timeline_nvidia_late_records import load_control_payload_agreement
            try:
                report[
                    'native_control_payloads'] = load_control_payload_agreement(
                        directory, capture,
                        report['native_boundaries']['relative_record_fields'])
            except (ValueError, OSError, KeyError, TypeError) as error:
                report['native_control_payloads'] = dict(
                    status='native_control_payloads_unverified',
                    reason=str(error),
                    time_flows_qualified=False)
        if directory is not None:
            from .timeline_nvidia_late_payloads import load_shared_payload_bindings
            try:
                report[
                    'native_shared_payloads'] = load_shared_payload_bindings(
                        directory, capture,
                        report['native_boundaries']['shared_payload_values'])
            except (ValueError, OSError, KeyError, TypeError) as error:
                report['native_shared_payloads'] = dict(
                    status='native_shared_payload_bindings_unverified',
                    reason=str(error),
                    time_flows_qualified=False)
        if directory is not None:
            from .timeline_nvidia_late_addresses import load_record_ordinal_bindings
            try:
                report['native_record_ordinals'] = load_record_ordinal_bindings(
                    directory, capture,
                    report['native_boundaries']['record_address_arithmetic'])
            except (ValueError, OSError, KeyError, TypeError) as error:
                report['native_record_ordinals'] = dict(
                    status='native_record_ordinal_bindings_unverified',
                    reason=str(error),
                    time_flows_qualified=False)
        return report, Path(timeline_nvidia_late_control.__file__)
    from . import timeline_nvidia_control
    return (timeline_nvidia_control.inspect_wait_control_brackets(
        machine_map=machine_map,
        sass_lines=sass_lines,
        sass_json=sass_json,
        plan=capture['owner']['plan']), Path(timeline_nvidia_control.__file__))


def shared_counter_inputs(directory, capture, raw):
    if not _late(capture):
        return None
    from .timeline_nvidia_shared import load_shared_counter_inputs
    return load_shared_counter_inputs(directory, capture, raw)


def observed_dependency_inputs(directory, capture, raw):
    """Qualify retained late-native dependencies without application replay."""
    if not _late(capture):
        return None
    from .timeline_nvidia_dependencies import load_observed_dependency_inputs
    return load_observed_dependency_inputs(directory, capture, raw)


backend_name = 'nvidia'


def matches(capture):
    return (isinstance(capture['metadata']['compiler_metadata'].get('target'),
                       dict) and
            capture['metadata']['compiler_metadata']['target'].get('backend')
            == 'cuda')


def reexport_views(directory, capture, raw, batch, sources, retain):
    owner = capture['owner']
    rows, reason, control_file = [], None, None
    shared_rows, shared_reason = [], None
    dependency_rows, dependency_reason = [], None
    from .timeline_nvidia_offline import load_counter_unit_proofs, load_counter_machine_map, control_evidence
    from .timeline_perfetto import write_counter_exports
    binary = owner['binary_id']
    machine_base = 'machine/' + binary
    # All provider input paths are prechecked against symlink/traversal,
    # then independently parsed again by the target-specific provider.
    for name in ('status.json', 'lines.stdout', 'json.stdout'):
        retain(machine_base + '/' + name)
    capture['machine_counter_mapping'] = json.loads(
        read_artifact(directory,
                      machine_base + '/status.json',
                      limit=8 * 1024 * 1024))
    expected = machine_base + '/counter-map.json'
    if capture['machine_counter_mapping'].get(
            'status') == 'counter_mapping_complete_region_unverified':
        if capture['machine_counter_mapping'].get(
                'counter_map_file') != expected:
            raise ValueError(
                'Machine evidence references another capture binary')
        retain(expected)
    actual_map = load_counter_machine_map(directory, capture)
    # An upgraded rule creates a derived map, never replacing the first
    # (possibly failed) machine diagnostic. All inputs remain inspectable.
    from . import timeline_nvidia_machine
    machine_inputs = dict(
        schema_version=1,
        original_inputs=dict(sorted(sources.items())),
        machine_map_sha256=sha256(json_bytes(actual_map)),
        rules_sha256=sha256(
            Path(timeline_nvidia_machine.__file__).read_bytes()))
    machine_revision = sha256(json_bytes(machine_inputs))
    machine_derived = 'derived/machine/' + machine_revision
    with export_lock(directory):
        persist(directory, machine_derived + '/inputs.json',
                json_bytes(machine_inputs))
        persist(directory, machine_derived + '/counter-map.json',
                json_bytes(actual_map))
    control, control_rules = control_evidence(
        capture,
        actual_map,
        sass_lines=read_artifact(directory, machine_base + '/lines.stdout'),
        sass_json=read_artifact(directory, machine_base + '/json.stdout'),
        directory=directory)
    control_inputs = dict(schema_version=1,
                          machine_revision=machine_revision,
                          plan_sha256=sha256(json_bytes(owner['plan'])),
                          report_sha256=sha256(json_bytes(control)),
                          implementation_sha256=sha256(
                              control_rules.read_bytes()))
    control_base = 'derived/control/' + sha256(json_bytes(control_inputs))
    control_file = control_base + '/wait-control.json'
    with export_lock(directory):
        persist(directory, control_base + '/inputs.json',
                json_bytes(control_inputs))
        persist(directory, control_file, json_bytes(control))
    proofs = load_counter_unit_proofs(directory, capture, batch)
    views = derive_counter_ns_views(batch, proofs)
    rows = write_counter_exports(directory,
                                 Path('captures') / owner['invocation_id'],
                                 views,
                                 batch,
                                 proofs=proofs)
    from .timeline_nvidia_offline import observed_dependency_inputs
    from .timeline_dependency_perfetto import write_dependency_exports
    try:
        dependencies = observed_dependency_inputs(directory, capture, raw)
        if dependencies is not None:
            dependency_rows = write_dependency_exports(directory,
                                                       *dependencies)
    except (ValueError, OSError, KeyError, TypeError) as error:
        dependency_reason = str(error)
    if not dependency_rows:
        from .timeline_nvidia_offline import shared_counter_inputs
        from .timeline_perfetto import write_shared_counter_exports
        try:
            shared = shared_counter_inputs(directory, capture, raw)
            if shared is not None:
                shared_rows = write_shared_counter_exports(directory, *shared)
        except (ValueError, OSError, KeyError, TypeError) as error:
            shared_reason = str(error)

    result = dict(wait_control_file=control_file,
                  exports=rows,
                  shared_exports=shared_rows,
                  shared_counter_reason=shared_reason,
                  observed_dependency_exports=dependency_rows,
                  observed_dependency_reason=dependency_reason,
                  reason=reason)
    return result
