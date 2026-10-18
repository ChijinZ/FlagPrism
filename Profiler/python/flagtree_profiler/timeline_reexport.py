"""Re-export retained timeline inputs without executing the application.

Usage: python -m flagtree.profiler.timeline_reexport BUNDLE/timeline
NVIDIA currently supports target-validated isolated counter-ns traces. GCU
supports canonical raw revisions; its missing unit proof stays explicit.
"""
import argparse
import base64
import json
from pathlib import Path

from .timeline_events import validate_raw_batch
from .timeline_store import (bundle_path, export_lock, json_bytes, persist,
                             read_artifact, sha256)
from .timeline_views import derive_counter_ns_views


def _json(directory, name):
    return json.loads(read_artifact(directory, name, limit=8 * 1024 * 1024))


def _nvidia(capture, raw):
    from .timeline_nvidia import decode_timeline_ring
    from .timeline_events_nvidia import canonicalize_nvidia_capture
    owner, metadata = capture['owner'], capture['metadata']
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
    return canonicalize_nvidia_capture(decoded,
                                       owner=owner,
                                       metadata=metadata,
                                       raw_sha256=sha256(raw),
                                       raw_bytes=len(raw))


def _enflame(capture, raw):
    from .timeline_events_enflame import canonicalize_enflame_capture
    owner = capture['owner']
    native = owner['native_export_metadata']
    runtime = dict(native['runtime_metadata'])
    runtime.update(profiler_invocation_id=capture['launch']['invocation_id'],
                   profiler_association_evidence=capture['launch'])
    return canonicalize_enflame_capture(
        dict(capture_status='raw_complete',
             record_layout='gcu_first_last_timeline_v2',
             runtime_metadata=runtime,
             raw_base64=base64.b64encode(raw).decode(),
             raw_sha256=sha256(raw)),
        compiler_metadata=capture['metadata']['compiler_metadata'],
        capture_id=owner['capture_id'])


def _ascend(capture, raw):
    from .timeline_events_ascend import canonicalize_ascend_capture
    return canonicalize_ascend_capture(
        raw,
        owner=capture['owner'],
        metadata=capture['metadata']['compiler_metadata'],
        association=capture['launch'])


def _original(directory, name):
    capture = _json(directory, name)
    owner = capture['owner']
    invocation = owner['invocation_id']
    if name != 'captures/' + invocation + '.input.json':
        raise ValueError('Original capture filename/identity mismatch')
    if owner.get('submission_outcome') != 'returned':
        raise ValueError('Capture did not complete a returned submission: ' +
                         invocation)
    if owner.get('readback_integrity', {}).get('status') == 'invalid':
        raise ValueError('Capture readback integrity is invalid: ' +
                         invocation)
    inputs = {}

    def retain(relative, *, digest=None, size=None):
        raw = read_artifact(directory, relative)
        actual = sha256(raw)
        if ((digest is not None and actual != digest)
                or (size is not None and
                    (type(size) is not int or len(raw) != size))):
            raise ValueError('Retained input differs from its capture: ' +
                             relative)
        inputs[relative] = dict(sha256=actual, bytes=len(raw))
        return raw

    retain(name)
    raw = retain(capture['raw_file'],
                 digest=capture['raw_sha256'],
                 size=owner['layout']['raw_bytes'])
    guard = capture.get('readback_guard')
    if guard is not None:
        retain(guard['file'], digest=guard['sha256'], size=guard['bytes'])
    for artifact in capture['metadata'].get('timeline_artifacts', []):
        retain(artifact['retained_file'], digest=artifact['sha256'])
    return capture, raw, inputs, retain


def reexport_capture(directory, original_file):
    """Decode actual bytes anew; cached canonical/view JSON cannot grant proof."""
    from . import timeline_events_nvidia, timeline_events_enflame, timeline_nvidia, timeline_events_ascend, timeline_nvidia_async
    directory = Path(directory).resolve()
    capture, raw, sources, retain = _original(directory, original_file)
    owner, metadata = capture['owner'], capture['metadata']
    target = metadata['compiler_metadata'].get('target') or {}
    if type(target) is not dict:
        target = {}
    if target.get('backend') == 'cuda':
        backend, decoder = 'nvidia', _nvidia
        rules = (timeline_events_nvidia, timeline_nvidia,
                 timeline_nvidia_async)
    elif metadata['compiler_metadata'].get(
            'debug_record_layout') == 'ascend_source_timeline_v1':
        backend, decoder, rules = 'ascend', _ascend, (timeline_events_ascend, )
    elif 'native_export_metadata' in owner:
        backend, decoder, rules = 'enflame', _enflame, (
            timeline_events_enflame, )
    else:
        raise ValueError('No offline decoder for this retained producer')
    batch = validate_raw_batch(decoder(capture, raw))
    if batch['identity']['binary_id'] != owner['binary_id']:
        raise ValueError(
            'Decoded canonical binary differs from the retained owner')
    # This revision is independent of any historical .events.json. New decoder
    # implementations can coexist without rewriting the first canonical result.
    decoder_inputs = dict(schema_version=1,
                          kind='canonical_timeline',
                          original_inputs=dict(sorted(sources.items())),
                          raw_sha256=sha256(raw),
                          canonical_sha256=sha256(json_bytes(batch)),
                          implementation_sha256={
                              Path(module.__file__).name:
                              sha256(Path(module.__file__).read_bytes())
                              for module in rules
                          })
    decoder_inputs['implementation_sha256']['timeline_reexport.py'] = sha256(
        Path(__file__).read_bytes())
    canonical_revision = sha256(json_bytes(decoder_inputs))
    canonical_base = 'derived/canonical/' + canonical_revision
    canonical_files = {
        canonical_base + '/inputs.json': json_bytes(decoder_inputs),
        canonical_base + '/events.json': json_bytes(batch)
    }
    receipt = dict(schema_version=1,
                   revision_id=canonical_revision,
                   identity=batch['identity'],
                   files=[
                       dict(file=name,
                            bytes=len(payload),
                            sha256=sha256(payload))
                       for name, payload in sorted(canonical_files.items())
                   ])
    with export_lock(directory):
        for name, payload in canonical_files.items():
            persist(directory, name, payload)
        persist(directory, canonical_base + '/complete.json',
                json_bytes(receipt))
    rows, reason, control_file = [], None, None
    if backend == 'nvidia':
        from .timeline_unit_nvidia import load_counter_unit_proofs, load_counter_machine_map
        from .timeline_perfetto import write_counter_exports
        binary = owner['binary_id']
        machine_base = 'machine/' + binary
        # All provider input paths are prechecked against symlink/traversal,
        # then independently parsed again by the target-specific provider.
        for name in ('status.json', 'lines.stdout', 'json.stdout'):
            retain(machine_base + '/' + name)
        capture['machine_counter_mapping'] = _json(
            directory, machine_base + '/status.json')
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
        from . import timeline_nvidia_control
        control = timeline_nvidia_control.inspect_wait_control_brackets(
            machine_map=actual_map,
            sass_lines=read_artifact(directory,
                                     machine_base + '/lines.stdout'),
            sass_json=read_artifact(directory, machine_base + '/json.stdout'),
            plan=owner['plan'])
        control_inputs = dict(
            schema_version=1,
            machine_revision=machine_revision,
            plan_sha256=sha256(json_bytes(owner['plan'])),
            report_sha256=sha256(json_bytes(control)),
            implementation_sha256=sha256(
                Path(timeline_nvidia_control.__file__).read_bytes()))
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
    else:
        reason = 'No validated counter-unit provider for this target; raw canonical revision retained'
    return dict(invocation_id=owner['invocation_id'],
                backend=backend,
                canonical_file=canonical_base + '/events.json',
                canonical_revision=canonical_revision,
                wait_control_file=control_file,
                exports=rows,
                status='counter_unit_only' if rows else 'raw_only',
                reason=reason)


def reexport_bundle(directory, *, invocation_id=None):
    directory = Path(directory).resolve()
    originals = sorted(directory.glob('captures/*.input.json'))
    if not originals or len(originals) > 128:
        raise ValueError('Missing or excessive retained original captures')
    if invocation_id is not None:
        relative = 'captures/' + invocation_id + '.input.json'
        bundle_path(directory, relative)
        originals = [
            p for p in originals if str(p.relative_to(directory)) == relative
        ]
        if len(originals) != 1:
            raise ValueError('Requested invocation original is absent')
    rows = [
        reexport_capture(directory, str(p.relative_to(directory)))
        for p in originals
    ]
    # Reports have deterministic names and retain the first attempt unchanged.
    report = dict(schema_version=1, application_replayed=False, captures=rows)
    relative = 'derived/reexports/' + sha256(json_bytes(report)) + '.json'
    with export_lock(directory):
        persist(directory, relative, json_bytes(report))
    return dict(report_file=relative, **report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline_directory', type=Path)
    parser.add_argument('--invocation-id')
    args = parser.parse_args()
    print(
        json.dumps(reexport_bundle(args.timeline_directory,
                                   invocation_id=args.invocation_id),
                   indent=2))


if __name__ == '__main__':
    main()
