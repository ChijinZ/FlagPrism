"""Observed GCU tag generations on a single actual issuer's counter.

An arrow ends at a recorded wait return. It does not describe engine busy,
precise hardware completion, or a buffer's readiness for an unobserved reader.
"""
import base64
from collections import defaultdict
import hashlib
from pathlib import Path

from .timeline_dependencies import ObservedDependencyProof
from .timeline_events import stable_id, validate_raw_batch
from .timeline_events_enflame import canonicalize_enflame_capture
from .timeline_events_enflame_native import decode_execution_capture
from .timeline_shared import SharedCounterProof
from .timeline_store import read_artifact
from .timeline_unit_enflame import load_counter_unit_proofs
from .timeline_views import document_sha256


def _need(value, message):
    if not value:
        raise ValueError(message)


def load_observed_dependency_inputs(directory,
                                    capture,
                                    raw,
                                    *,
                                    canonical=None):
    """Match observed submissions to waits by actual tag storage and index.

    The SDK DTE event contract permits one outstanding operation per context.
    A reused tag acquires a new generation only after its observed wait returns.
    Multiple outstanding submissions on the same tag are ambiguous here and
    remain unqualified; their original intervals/raw are still available.
    """
    owner, metadata = capture['owner'], capture['metadata'][
        'compiler_metadata']
    _need(
        owner.get('submission_outcome') == 'returned'
        and owner.get('readback_integrity', {}).get('status') != 'invalid',
        'GCU dependency capture did not complete with valid retained bytes')
    _need(
        type(raw) is bytes
        and raw == read_artifact(directory, capture['raw_file'])
        and hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'GCU dependency bytes differ from the retained invocation')
    manifest = metadata.get('debug_execution_manifest', {})
    _need(
        metadata.get('arch') == 'gcu300'
        and type(metadata.get('debug_execution_version')) is int
        and metadata['debug_execution_version'] == 1
        and manifest.get('buffer_arguments_version') == 2
        and manifest.get('buffer_address_encoding') == 'gcu_ptr2int_i64_v1'
        and manifest.get('queue_address_encoding') == 'sdk_private_tag_index',
        'GCU tag dependencies require the full-width execution recorder')
    _need(
        type(manifest.get('unobserved_primitives')) is list
        and not manifest['unobserved_primitives'],
        'Unobserved execution primitives prevent tag generation reconstruction'
    )
    association = capture['launch']
    runtime = dict(owner['native_export_metadata']['runtime_metadata'])
    runtime.update(profiler_invocation_id=association['invocation_id'],
                   profiler_association_evidence=association)
    # Use the ordinary capture validator for its actual launch/session identity.
    if canonical is None:
        canonical = canonicalize_enflame_capture(
            dict(record_layout=metadata['debug_record_layout'],
                 runtime_metadata=runtime,
                 raw_base64=base64.b64encode(raw).decode(),
                 raw_sha256=capture['raw_sha256']),
            compiler_metadata=metadata,
            capture_id=owner['capture_id'])
    canonical = validate_raw_batch(canonical)
    _need(
        association.get('evidence') == 'same_launch_metadata_object' and
        association.get('binary_id') == owner['binary_id'] == metadata['hash']
        and canonical['identity'] == dict(
            capture_id=owner['capture_id'],
            binary_id=owner['binary_id'],
            invocation_id=stable_id(
                (owner['capture_id'], ), 'enflame-invocation',
                association['invocation_id'], association['scope_id'],
                sorted(association['session_ids']))),
        'GCU tag records belong to another actual launch')
    decoded = decode_execution_capture(raw,
                                       compiler_metadata=metadata,
                                       identity=canonical['identity'],
                                       association=association,
                                       grid=runtime['grid'])
    _need(decoded['canonical'] == canonical,
          'GCU dependency canonical records differ from the original bytes')
    _need(canonical['complete'],
          'Incomplete GCU records cannot close tag generations')
    binary = base64.b64decode(
        capture['metadata']['compiled_snapshot']['binary_base64'],
        validate=True)
    _need(
        binary and hashlib.sha256(binary).hexdigest()
        == owner['function']['binary_sha256'],
        'GCU dependency executable differs from the actual launch')
    units = {
        proof.observer_id: proof
        for proof in load_counter_unit_proofs(directory, capture, canonical)
    }
    implementation = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    identity = tuple(canonical['identity'][key]
                     for key in ('capture_id', 'invocation_id', 'binary_id'))
    events = {event['id']: event for event in canonical['events']}
    commands = defaultdict(list)
    for command in decoded['commands']:
        commands[command['observer_id']].append(command)
    proofs = []
    for observer in canonical['observers']:
        oid = observer['id']
        _need(oid in units and observer['complete'],
              'GCU observer has no enclosed counter unit')
        pending, generations, writes, edges = {}, defaultdict(
            int), defaultdict(int), []
        for command in commands[oid]:
            if command['kind'] not in (1, 2):
                continue
            queue = command['queue']
            _need(queue['index'] != 0xffffffff,
                  'Native DTE tag identity is unavailable')
            key = queue['base'], queue['index']
            event = events[command['event_id']]
            if command['kind'] == 1:
                _need(
                    key not in pending,
                    'Multiple outstanding submissions reuse one observed DTE tag; no generation is guessed'
                )
                destination = command['destination']
                buffer = destination['space'], destination['address']
                pending[key] = command, writes[buffer]
                writes[buffer] += 1
                continue
            submission = pending.pop(key, None)
            if submission is None:
                # An initially idle context may legitimately be waited on.
                # Do not invent a producer or connect it to a previous capture.
                continue
            before, write_generation = submission
            source = events[before['event_id']]
            _need(
                source['end_tick'] <= event['start_tick'],
                'DTE submission and its observed wait are out of issuer order')
            generation = generations[key]
            generations[key] += 1
            edges.append(
                dict(source=source['record_ids'][-1],
                     target=event['record_ids'][-1],
                     relation='gcu_submission_before_observed_tag_wait_return',
                     association_key=stable_id(identity, 'gcu-tag-generation',
                                               oid, *key, generation),
                     display_label='DTE tag generation ' + str(generation) +
                     ': submit → wait returned',
                     attributes=dict(backend_evidence=dict(
                         queue_base=queue['base'],
                         queue_index=queue['index'],
                         tag_generation=generation,
                         observed_destination_descriptor_write_generation=
                         write_generation,
                         destination=before['destination'],
                         source_buffer=before['source'],
                         submit_raw_offset=before['raw_offset'],
                         wait_raw_offset=command['raw_offset'],
                         completion_observed_at='wait_return',
                         precise_hardware_completion_time_verified=False,
                         consumer_readiness_verified=False,
                         engine_busy_verified=False))))
        _need(not pending,
              'Unmatched observed DTE submissions remain at return')
        if not edges:
            continue
        unit = units[oid]
        clock = SharedCounterProof(
            **canonical['identity'],
            raw_sha256=canonical['raw_artifact']['sha256'],
            canonical_sha256=document_sha256(canonical),
            observer_ids=(oid, ),
            program_coordinates=tuple(observer['program_coordinates']),
            domain_id=stable_id(identity, 'gcu-issuer-counter-scope', oid),
            epoch_id=stable_id(identity, 'gcu-issuer-capture-epoch', oid),
            period_numerator_ns=unit.period_numerator_ns,
            period_denominator=unit.period_denominator,
            period_uncertainty_numerator_ns=unit.
            period_uncertainty_numerator_ns,
            period_uncertainty_denominator=unit.period_uncertainty_denominator,
            max_elapsed_ns=unit.max_elapsed_ns,
            provider='enflame.gcu300.single_issuer_counter.v1',
            implementation_sha256=document_sha256(
                dict(mapper=implementation, unit=unit.implementation_sha256)),
            evidence_ids=unit.evidence_ids +
            ('execution_manifest:' + document_sha256(manifest), ),
            scope_kind='single_observer')
        proofs.append(
            ObservedDependencyProof(
                clock=clock,
                provider='enflame.gcu300.observed_private_tag_generations.v1',
                implementation_sha256=implementation,
                evidence_ids=(
                    'sdk_DTE_event_wait_contract:one_operation_per_context',
                    'execution_manifest:' + document_sha256(manifest)),
                edges=tuple(edges)))
    _need(proofs, 'No complete observed DTE tag generations')
    return canonical, proofs
