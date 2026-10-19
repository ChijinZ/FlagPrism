"""Decode published GCU atomic-pair append records into the common raw contract.

No clock/source-region/engine qualification follows from this adapter. The
capture namespace is supplied by the owning session, never a local export label.
"""
import base64
from collections import defaultdict
import hashlib
import struct

from .timeline_events import stable_id, validate_raw_batch, _integer, _text, _sha


def _need(value, message):
    if not value:
        raise ValueError(message)


def _canonicalize_slot(capture,
                       *,
                       compiler_metadata,
                       capture_id,
                       slot_index=0):
    _text(capture_id, 'owning capture namespace')
    _need(type(capture) is dict, 'A GCU capture is required')
    first_last = capture.get('record_layout') == 'gcu_first_last_timeline_v2'
    _need(
        capture.get('capture_status')
        in (('decoded', 'raw_complete') if first_last else
            ('decoded', )), 'A published GCU capture is required')
    layout = capture.get('record_layout')
    _need(
        layout
        in ('selected_dynamic_timeline_v1', 'gcu_first_last_timeline_v2'),
        'Capture layout mismatch')
    metadata = compiler_metadata
    _need(
        type(metadata) is dict
        and metadata.get('debug_record_layout') == layout
        and type(metadata.get('debug_protocol_version')) is int
        and metadata['debug_protocol_version'] == 2,
        'Unknown GCU dynamic protocol')
    _need(
        type(metadata.get('debug_clock_bits')) is int
        and metadata['debug_clock_bits'] == 46
        and metadata.get('debug_clock_domain') == 'enflame.sdk.global_timer',
        'Unknown GCU timer encoding')
    runtime = capture.get('runtime_metadata')
    _need(
        type(runtime) is dict and runtime.get('record_layout') == layout,
        'Actual GCU launch layout is required')
    association = runtime.get('profiler_association_evidence')
    _need(
        type(association) is dict
        and association.get('evidence') == 'same_launch_metadata_object',
        'GCU capture lacks an actual launch association')
    binary = _sha(metadata.get('hash'))
    native_invocation = _text(runtime.get('profiler_invocation_id'),
                              'native invocation')
    _need(
        association.get('binary_id') == binary
        and association.get('invocation_id') == native_invocation,
        'GCU launch/compiler identity mismatch')
    scope = _integer(association.get('scope_id'), 'native scope')
    sessions = association.get('session_ids')
    _need(
        type(sessions) is list and sessions,
        'Actual session membership is required')
    for session in sessions:
        _integer(session, 'native session')
    _need(
        len(set(sessions)) == len(sessions),
        'Duplicate native session membership')
    invocation = stable_id((capture_id, ), 'enflame-invocation',
                           native_invocation, scope, sorted(sessions))
    identity = (capture_id, invocation, binary)
    actor = _integer(metadata.get('debug_dynamic_selected_actor'),
                     'selected work-item', 0, 0)
    clock_identity = metadata.get('debug_clock_identity_version')
    if clock_identity is not None:
        _need(
            type(clock_identity) is int and clock_identity == 1 and first_last
            and metadata.get('debug_clock_identity_primitive')
            == 'llvm.dtu.movs.sipinfo',
            'Unknown compact GCU clock identity feature')
        _sha(metadata.get('debug_clock_identity_library_sha256'))
    sample = _integer(metadata.get('debug_dynamic_sample_every'),
                      'sample every', 1, 0x7fffffff)
    grid = runtime.get('grid')
    _need(
        type(grid) is list and len(grid) == 3,
        'Actual launch grid is required')
    total = 1
    for dim in grid:
        total *= _integer(dim, 'grid dimension', 1, 0x7fffffff)
    _need(total <= 0x7fffffff, 'Actual grid exceeds bounded indexing')
    if first_last:
        _need(
            type(metadata.get('debug_dynamic_storage_version')) is int
            and metadata['debug_dynamic_storage_version'] == 2
            and type(metadata.get('debug_dynamic_publisher_version')) is int
            and metadata['debug_dynamic_publisher_version'] == 2
            and type(metadata.get('debug_dynamic_index_bits')) is int
            and metadata['debug_dynamic_index_bits'] == 32
            and metadata.get('debug_dynamic_program_policy')
            == 'runtime_first_last'
            and 'debug_dynamic_selected_program' not in metadata,
            'Unknown GCU first/last storage policy')
        slots = [0] if total == 1 else [0, total - 1]
        _need(
            type(slot_index) is int and 0 <= slot_index < len(slots),
            'Invalid physical ring slot')
        program = slots[slot_index]
    else:
        program = _integer(metadata.get('debug_dynamic_selected_program'),
                           'selected program', 0, 0x7fffffff)
        _need(slot_index == 0 and program < total,
              'Selected program exceeds actual grid')
    encoded = capture.get('raw_base64')
    _need(
        type(encoded) is str and len(encoded) <= 12 * 1024 * 1024,
        'GCU raw input budget exceeded')
    raw = base64.b64decode(encoded, validate=True)
    _need(
        32 <= len(raw) <= 8 * 1024 * 1024
        and hashlib.sha256(raw).hexdigest() == _sha(capture.get('raw_sha256')),
        'GCU raw identity or extent mismatch')
    raw_bytes = len(raw)
    raw_base = 0
    if first_last:
        capacity = _integer(metadata.get('debug_record_capacity'),
                            'slot capacity', 1, 16384)
        slot_bytes = _integer(metadata.get('debug_dynamic_slot_bytes'),
                              'slot bytes', 96)
        _need(
            slot_bytes == 32 + capacity * 64
            and raw_bytes == len(slots) * slot_bytes,
            'Actual GCU compact storage extent differs from manifest/grid')
        raw_base = slot_index * slot_bytes
        raw = raw[raw_base:raw_base + slot_bytes]
    written, capacity, dropped, flags, stride, payload, attempted, reserved = struct.unpack_from(
        '<8I', raw)
    _need(
        capacity > 0 and stride == 64
        and payload == len(raw) == 32 + capacity * 64
        and reserved == (program if first_last else 0)
        and not flags & ~(0x33 if first_last else 0x13)
        and dropped == max(0, written - capacity)
        and bool(flags & 1) == bool(dropped) and attempted >= written,
        'Invalid GCU append header')
    if first_last:
        _need(flags & 32,
              'Selected GCU program did not publish its writer arrival')
    _need(
        type(metadata.get('debug_record_capacity')) is int
        and metadata['debug_record_capacity'] == capacity,
        'Compiler/runtime capacity mismatch')
    retained = min(written, capacity)
    _need(retained <= 32768, 'GCU canonical endpoint budget exceeded')
    saturated = bool(flags & 16)
    if not saturated:
        _need(written == (attempted + sample - 1) // sample,
              'Sampling/attempt counters disagree')
    plan = metadata.get('debug_automatic_plan')
    _need(
        type(plan) is dict and type(plan.get('selected_sites')) is list
        and plan['selected_sites'], 'Automatic source manifest is required')
    selected = plan['selected_sites']
    for site in selected:
        _integer(site, 'selected source site', 1, 0xffffffff)
    _need(
        len(selected) <= 128 and len(set(selected)) == len(selected),
        'Aliased or excessive source sites')
    tracked = metadata.get('debug_tracked_table')
    _need(type(tracked) is list, 'Actual tracked source table is required')
    origins = {}
    for row in tracked:
        _need(type(row) is dict, 'Invalid tracked source row')
        site = row.get('opId')
        if type(site) is not int:
            raise ValueError('Tracked operation identity must be an integer')
        if site in selected:
            _integer(row.get('scopeId'), 'compiler source scope')
            _need(site not in origins, 'Ambiguous tracked source identity')
            origins[site] = row
    _need(set(origins) == set(selected), 'Missing actual source origins')
    record_plan = runtime.get('record_plan')
    _need(
        type(record_plan) is list and len(record_plan) == len(selected),
        'Actual runtime record plan differs from compiler selection')
    for row in record_plan:
        _need(type(row) is dict, 'Invalid runtime source record descriptor')
        site = _integer(row.get('op_id'), 'runtime source site', 1, 0xffffffff)
        _integer(row.get('record_kind'), 'runtime record kind', 7, 7)
        _integer(row.get('scope_id'), 'runtime source scope')
        _need(
            site in origins
            and row['scope_id'] == origins[site].get('scopeId'),
            'Runtime/compiler source scope mismatch')
    _need({r['op_id']
           for r in record_plan} == set(selected),
          'Runtime/compiler site selection mismatch')
    sources, sites, ids = [], [], {}
    for site in selected:
        origin = origins[site]
        sid = stable_id((binary, ), 'site', str(site))
        source = stable_id((binary, ), 'source', str(site),
                           origin.get('sourceLoc'))
        ids[site] = sid
        sources.append(
            dict(id=source,
                 source_sha256=None,
                 relation='compiler_origin_navigation',
                 location=origin.get('sourceLoc'),
                 provenance='actual_compiler_tracked_location'))
        sites.append(
            dict(id=sid,
                 name=origin.get('mlirOpName') or str(site),
                 semantic='observer_region_elapsed',
                 source_ids=[source],
                 backend_site_id=str(site),
                 attributes={'enflame.operation': origin.get('mlirOpName')}))
    coords = [
        program % grid[0], (program // grid[0]) % grid[1],
        program // (grid[0] * grid[1])
    ]
    observer = stable_id(identity, 'observer', 'enflame.work_item', str(actor),
                         coords)
    complete = not dropped and not saturated
    observers = [
        dict(id=observer,
             kind='enflame.work_item',
             local_id=str(actor),
             program_coordinates=coords,
             physical_identity=None,
             clock_domain_id=stable_id(identity, 'unverified-observer-domain',
                                       program, actor),
             epoch_id=stable_id(identity, 'capture-epoch-unverified', program,
                                actor),
             timer_bits=46,
             record_order='paired_endpoints',
             attempted_records=2 * attempted,
             committed_records=2 * retained,
             retained_records=2 * retained,
             dropped_records=2 * dropped,
             filtered_records=2 * (attempted - written),
             overwritten_records=0,
             saturated=saturated,
             complete=complete,
             attributes={
                 'enflame.native_association':
                 association,
                 'enflame.sample_every':
                 sample,
                 'enflame.physical_pair_bytes':
                 64,
                 'enflame.physical_pairs_retained':
                 retained,
                 'enflame.endpoint_count_basis':
                 'two_real_field_references_per_committed_pair',
                 **({
                     'enflame.physical_slot': slot_index,
                     'enflame.raw_slot_base': raw_base
                 } if first_last else {})
             })
    ]
    records, events, mapping, occurrences = [], [], {}, defaultdict(int)
    previous_ordinal = -1
    physical_ids = set()
    for slot in range(retained):
        offset = 32 + slot * 64
        kind, zero, site, pid, begin, end, duration, who, sequence, ordinal, commit = struct.unpack_from(
            '<HHIQQQQIIQQ', raw, offset)
        _need(
            kind == 7 and zero == 0 and site in ids and pid == program
            and (clock_identity == 1 or who == actor) and sequence == slot
            and ordinal == sequence * sample and ordinal > previous_ordinal
            and ordinal < attempted and ordinal % sample == 0
            and commit == 0x465044594e563031 and 0 <= begin <= end < 1 << 46
            and duration == end - begin, 'Invalid committed GCU pair payload')
        previous_ordinal = ordinal
        if clock_identity == 1:
            physical_ids.add(who)
        refs = []
        for phase_index, (phase, tick,
                          field_offset) in enumerate([('entry', begin, 16),
                                                      ('exit', end, 24)]):
            seq = 2 * sequence + phase_index
            rid = stable_id(identity, 'record', observer, seq)
            records.append(
                dict(id=rid,
                     observer_id=observer,
                     site_id=ids[site],
                     phase=phase,
                     tick=tick,
                     sequence=seq,
                     offset=raw_base + offset + field_offset,
                     length=8))
            mapping[(str(program) + '.' if first_last else '') +
                    str(sequence) + '.' + phase] = rid
            refs.append(rid)
        occurrence = occurrences[site]
        occurrences[site] += 1
        events.append(
            dict(id=stable_id(identity, 'event', *refs),
                 observer_id=observer,
                 site_id=ids[site],
                 semantic='observer_region_elapsed',
                 kind='interval',
                 start_tick=begin,
                 end_tick=end,
                 occurrence=occurrence,
                 occurrence_basis='complete_pair_order'
                 if complete else 'retained_pair_order',
                 iteration_id=None,
                 record_ids=refs,
                 missing_reason=None,
                 coverage='complete_selected_pair_stream'
                 if complete else 'retained_pair_prefix'))
    if clock_identity == 1 and retained:
        _need(
            len(physical_ids) == 1,
            'Compact GCU observer changed physical counter identity')
        observers[0]['physical_identity'] = {
            'enflame.kind':
            'dtu.full_sipinfo.v1',
            'enflame.full_sipinfo':
            next(iter(physical_ids)),
            'enflame.evidence':
            'actual_compact_record_identity_word',
            'enflame.identity_word_offsets':
            [raw_base + 32 + slot * 64 + 40 for slot in range(retained)]
        }
    return validate_raw_batch(
        dict(
            schema_version=2,
            identity=dict(
                zip(('capture_id', 'invocation_id', 'binary_id'), identity)),
            raw_artifact=dict(sha256=capture['raw_sha256'], bytes=raw_bytes),
            clock_status='unverified',
            boundary_status='unverified',
            sources=sources,
            sites=sites,
            observers=observers,
            records=records,
            events=events,
            complete=complete,
            backend_record_map={
                ('enflame.dynamic_pairs.v2' if first_last else 'enflame.dynamic_pairs.v1'):
                mapping
            },
            notes=[
                'Endpoint sequences index real fields in append pairs, not the chronological order of all reads.',
                'Counts use canonical endpoint references; each native committed pair contributes two.',
                'Source locations support navigation, not source cost or hardware-completion attribution.',
                'Raw units/epoch and final source-region boundaries are unverified.'
            ]))


def canonicalize_enflame_capture(capture, *, compiler_metadata, capture_id):
    """Decode physical rings, preserving whole-raw offsets and per-slot loss."""
    if compiler_metadata.get(
            'debug_record_layout') == 'gcu_execution_timeline_v3':
        from .timeline_events_enflame_native import decode_execution_capture
        runtime = capture.get('runtime_metadata')
        _need(
            type(runtime) is dict
            and capture.get('record_layout') == 'gcu_execution_timeline_v3'
            and runtime.get('record_layout') == 'gcu_execution_timeline_v3',
            'GCU execution capture/runtime/compiler ABI mismatch')
        association = runtime.get('profiler_association_evidence')
        _need(
            type(association) is dict
            and association.get('evidence') == 'same_launch_metadata_object'
            and association.get('invocation_id')
            == runtime.get('profiler_invocation_id'),
            'GCU execution capture lacks its actual native launch association')
        binary = _sha(compiler_metadata.get('hash'))
        _need(
            association.get('binary_id') == binary,
            'GCU execution binary association mismatch')
        scope = _integer(association.get('scope_id'), 'native scope')
        sessions = association.get('session_ids')
        _need(
            type(sessions) is list and sessions
            and len(sessions) == len(set(sessions)),
            'GCU execution capture has no unique actual session membership')
        for session in sessions:
            _integer(session, 'native session')
        invocation = stable_id((capture_id, ), 'enflame-invocation',
                               association['invocation_id'], scope,
                               sorted(sessions))
        encoded = capture.get('raw_base64')
        _need(
            type(encoded) is str and len(encoded) <= 12 * 1024 * 1024,
            'GCU execution base64 exceeds its budget')
        raw = base64.b64decode(encoded, validate=True)
        _need(
            hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
            'GCU execution raw SHA changed')
        return decode_execution_capture(raw,
                                        compiler_metadata=compiler_metadata,
                                        identity=dict(capture_id=capture_id,
                                                      invocation_id=invocation,
                                                      binary_id=binary),
                                        association=association,
                                        grid=runtime['grid'])['canonical']
    first = _canonicalize_slot(capture,
                               compiler_metadata=compiler_metadata,
                               capture_id=capture_id)
    if capture.get('record_layout') != 'gcu_first_last_timeline_v2':
        return first
    grid = capture['runtime_metadata']['grid']
    if grid[0] * grid[1] * grid[2] == 1:
        return first
    second = _canonicalize_slot(capture,
                                compiler_metadata=compiler_metadata,
                                capture_id=capture_id,
                                slot_index=1)
    _need(
        first['identity'] == second['identity']
        and first['raw_artifact'] == second['raw_artifact'],
        'Physical rings disagree about owning capture')
    for key in ['sources', 'sites']:
        _need(first[key] == second[key],
              'Physical rings disagree about compiled sources')
    for key in ['observers', 'records', 'events']:
        first[key].extend(second[key])
    first['complete'] = first['complete'] and second['complete']
    for key, mapping in second['backend_record_map'].items():
        _need(
            set(first['backend_record_map'][key]).isdisjoint(mapping),
            'Aliased native pair identity')
        first['backend_record_map'][key].update(mapping)
    return validate_raw_batch(first)


def attach_enflame_timeline_export(exported_run,
                                   compiler_metadata,
                                   *,
                                   capture_id=None):
    """Attach validated common events and source-navigation rows to an SDK export.

    These rows carry observer elapsed semantics and unverified clocks. They do
    not turn a source location into certified operation cost or hardware busy.
    The caller owns safe device completion and durable raw retention.
    """
    import copy
    import uuid
    from .observations import observation
    _need(
        type(exported_run) is dict
        and type(exported_run.get('raw_buffer')) in (bytes, bytearray),
        'Actual exported raw bytes are required')
    raw = bytes(exported_run['raw_buffer'])
    runtime = copy.deepcopy(exported_run.get('runtime_metadata'))
    _need(type(runtime) is dict, 'Actual launch runtime metadata is required')
    runtime['grid'] = list(runtime.get('grid', ()))
    namespace = capture_id or 'gcu-timeline-' + uuid.uuid4().hex
    capture = dict(capture_status='raw_complete',
                   record_layout=runtime.get('record_layout'),
                   runtime_metadata=runtime,
                   raw_base64=base64.b64encode(raw).decode(),
                   raw_sha256=hashlib.sha256(raw).hexdigest())
    batch = canonicalize_enflame_capture(capture,
                                         compiler_metadata=compiler_metadata,
                                         capture_id=namespace)
    runtime['capture_id'] = namespace
    observers = {row['id']: row for row in batch['observers']}
    sites = {row['id']: row for row in batch['sites']}
    refs = {row['id']: row for row in batch['records']}
    grid = runtime['grid']
    rows = []
    for event in batch['events']:
        observer = observers[event['observer_id']]
        x, y, z = observer['program_coordinates']
        rows.append(
            observation(
                dict(
                    id=event['id'],
                    capture_id=namespace,
                    invocation_id=runtime['profiler_invocation_id'],
                    binary_id=batch['identity']['binary_id'],
                    canonical_invocation_id=batch['identity']['invocation_id'],
                    association_status='verified',
                    association_evidence=runtime[
                        'profiler_association_evidence'],
                    source='flagtree_ir_dynamic',
                    semantic='issue' if event['semantic'] == 'issue_interval'
                    else event['semantic'],
                    storage='gcu_local_execution_ring'
                    if compiler_metadata.get('debug_execution_version') == 1
                    else 'selected_dynamic_append',
                    program=x + grid[0] * (y + grid[1] * z),
                    actor=int(observer['local_id']),
                    site=int(sites[event['site_id']]['backend_site_id']),
                    occurrence=event['occurrence'],
                    iteration=None,
                    start_tick=event['start_tick'],
                    end_tick=event['end_tick'],
                    clock=dict(domain=observer['clock_domain_id'],
                               scope=observer['id'],
                               alignment='unverified',
                               tick_ns=None,
                               wrap_bits=observer['timer_bits']),
                    original_record=dict(
                        canonical_event=event,
                        raw_fields=[refs[r] for r in event['record_ids']],
                        raw_artifact=batch['raw_artifact']),
                    observer_complete=observer['complete'],
                    dropped_endpoint_references=observer['dropped_records'],
                    limits=[
                        'Observer counter bracket; final source-region boundary is unverified.',
                        'Raw ticks are not ns or a certified shared epoch.',
                        'Occurrence is pair completion order, not a loop iteration.'
                    ])))
    result = dict(exported_run,
                  runtime_metadata=runtime,
                  canonical_timeline=batch,
                  debug_kernel_name=compiler_metadata.get(
                      'debug_kernel_name', ''),
                  debug_tracked_table=copy.deepcopy(
                      compiler_metadata.get('debug_tracked_table', [])),
                  decoded=dict(records=[],
                               dropped=sum(o['dropped_records'] // 2
                                           for o in batch['observers']),
                               complete=batch['complete']),
                  semantic_observations=rows,
                  capture_status='decoded')
    return result
