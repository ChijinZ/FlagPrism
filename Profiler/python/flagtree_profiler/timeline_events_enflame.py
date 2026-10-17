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


def canonicalize_enflame_capture(capture, *, compiler_metadata, capture_id):
    _text(capture_id, 'owning capture namespace')
    _need(type(capture) is dict and capture.get('capture_status') == 'decoded',
          'A successfully published GCU capture is required')
    _need(capture.get('record_layout') == 'selected_dynamic_timeline_v1', 'Capture layout mismatch')
    metadata = compiler_metadata
    _need(type(metadata) is dict and metadata.get('debug_record_layout') == 'selected_dynamic_timeline_v1' and
          type(metadata.get('debug_protocol_version')) is int and metadata['debug_protocol_version'] == 2,
          'Unknown GCU dynamic protocol')
    _need(type(metadata.get('debug_clock_bits')) is int and metadata['debug_clock_bits'] == 46 and
          metadata.get('debug_clock_domain') == 'enflame.sdk.global_timer', 'Unknown GCU timer encoding')
    runtime = capture.get('runtime_metadata')
    _need(type(runtime) is dict and runtime.get('record_layout') == 'selected_dynamic_timeline_v1',
          'Actual GCU launch layout is required')
    association = runtime.get('profiler_association_evidence')
    _need(type(association) is dict and association.get('evidence') == 'same_launch_metadata_object',
          'GCU capture lacks an actual launch association')
    binary = _sha(metadata.get('hash'))
    native_invocation = _text(runtime.get('profiler_invocation_id'), 'native invocation')
    _need(association.get('binary_id') == binary and association.get('invocation_id') == native_invocation,
          'GCU launch/compiler identity mismatch')
    scope = _integer(association.get('scope_id'), 'native scope')
    sessions = association.get('session_ids')
    _need(type(sessions) is list and sessions, 'Actual session membership is required')
    for session in sessions:
        _integer(session, 'native session')
    _need(len(set(sessions)) == len(sessions), 'Duplicate native session membership')
    invocation = stable_id((capture_id,), 'enflame-invocation', native_invocation, scope, sorted(sessions))
    identity = (capture_id, invocation, binary)
    program = _integer(metadata.get('debug_dynamic_selected_program'), 'selected program', 0, 0x7fffffff)
    actor = _integer(metadata.get('debug_dynamic_selected_actor'), 'selected work-item', 0, 0)
    sample = _integer(metadata.get('debug_dynamic_sample_every'), 'sample every', 1, 0x7fffffff)
    grid = runtime.get('grid')
    _need(type(grid) is list and len(grid) == 3, 'Actual launch grid is required')
    total = 1
    for dim in grid:
        total *= _integer(dim, 'grid dimension', 1, 0x7fffffff)
    _need(total <= 0x7fffffff and program < total, 'Selected program exceeds actual grid')
    encoded = capture.get('raw_base64')
    _need(type(encoded) is str and len(encoded) <= 12*1024*1024, 'GCU raw input budget exceeded')
    raw = base64.b64decode(encoded, validate=True)
    _need(32 <= len(raw) <= 8*1024*1024 and hashlib.sha256(raw).hexdigest() == _sha(capture.get('raw_sha256')),
          'GCU raw identity or extent mismatch')
    written, capacity, dropped, flags, stride, payload, attempted, reserved = struct.unpack_from('<8I', raw)
    _need(capacity > 0 and stride == 64 and payload == len(raw) == 32+capacity*64 and
          reserved == 0 and not flags & ~0x13 and dropped == max(0, written-capacity) and
          bool(flags & 1) == bool(dropped) and attempted >= written,
          'Invalid GCU append header')
    _need(type(metadata.get('debug_record_capacity')) is int and metadata['debug_record_capacity'] == capacity,
          'Compiler/runtime capacity mismatch')
    retained = min(written, capacity)
    _need(retained <= 32768, 'GCU canonical endpoint budget exceeded')
    saturated = bool(flags & 16)
    if not saturated:
        _need(written == (attempted+sample-1)//sample, 'Sampling/attempt counters disagree')
    plan = metadata.get('debug_automatic_plan')
    _need(type(plan) is dict and type(plan.get('selected_sites')) is list and plan['selected_sites'],
          'Automatic source manifest is required')
    selected = plan['selected_sites']
    for site in selected:
        _integer(site, 'selected source site', 1, 0xffffffff)
    _need(len(selected) <= 128 and len(set(selected)) == len(selected), 'Aliased or excessive source sites')
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
    _need(type(record_plan) is list and len(record_plan) == len(selected),
          'Actual runtime record plan differs from compiler selection')
    for row in record_plan:
        _need(type(row) is dict, 'Invalid runtime source record descriptor')
        site = _integer(row.get('op_id'), 'runtime source site', 1, 0xffffffff)
        _integer(row.get('record_kind'), 'runtime record kind', 7, 7)
        _integer(row.get('scope_id'), 'runtime source scope')
        _need(site in origins and row['scope_id'] == origins[site].get('scopeId'),
              'Runtime/compiler source scope mismatch')
    _need({r['op_id'] for r in record_plan} == set(selected), 'Runtime/compiler site selection mismatch')
    sources, sites, ids = [], [], {}
    for site in selected:
        origin = origins[site]
        sid = stable_id((binary,), 'site', str(site))
        source = stable_id((binary,), 'source', str(site), origin.get('sourceLoc'))
        ids[site] = sid
        sources.append(dict(id=source, source_sha256=None, relation='compiler_origin_navigation',
                            location=origin.get('sourceLoc'), provenance='actual_compiler_tracked_location'))
        sites.append(dict(id=sid, name=origin.get('mlirOpName') or str(site),
            semantic='observer_region_elapsed', source_ids=[source], backend_site_id=str(site),
            attributes={'enflame.operation': origin.get('mlirOpName')}))
    coords = [program % grid[0], (program//grid[0]) % grid[1], program//(grid[0]*grid[1])]
    observer = stable_id(identity, 'observer', 'enflame.work_item', str(actor), coords)
    complete = not dropped and not saturated
    observers = [dict(id=observer, kind='enflame.work_item', local_id=str(actor),
        program_coordinates=coords, physical_identity=None,
        clock_domain_id=stable_id(identity, 'unverified-observer-domain', program, actor),
        epoch_id=stable_id(identity, 'capture-epoch-unverified', program, actor), timer_bits=46,
        record_order='paired_endpoints', attempted_records=2*attempted,
        committed_records=2*retained, retained_records=2*retained,
        dropped_records=2*dropped, filtered_records=2*(attempted-written), overwritten_records=0,
        saturated=saturated, complete=complete,
        attributes={'enflame.native_association': association, 'enflame.sample_every': sample,
                    'enflame.physical_pair_bytes': 64, 'enflame.physical_pairs_retained': retained,
                    'enflame.endpoint_count_basis': 'two_real_field_references_per_committed_pair'})]
    records, events, mapping, occurrences = [], [], {}, defaultdict(int)
    previous_ordinal = -1
    for slot in range(retained):
        offset = 32+slot*64
        kind, zero, site, pid, begin, end, duration, who, sequence, ordinal, commit = struct.unpack_from('<HHIQQQQIIQQ', raw, offset)
        _need(kind == 7 and zero == 0 and site in ids and pid == program and who == actor and
              sequence == slot and ordinal == sequence*sample and ordinal > previous_ordinal and ordinal < attempted and
              ordinal % sample == 0 and commit == 0x465044594e563031 and
              0 <= begin <= end < 1 << 46 and duration == end-begin, 'Invalid committed GCU pair payload')
        previous_ordinal = ordinal
        refs = []
        for phase_index, (phase, tick, field_offset) in enumerate([('entry', begin, 16), ('exit', end, 24)]):
            seq = 2*sequence+phase_index
            rid = stable_id(identity, 'record', observer, seq)
            records.append(dict(id=rid, observer_id=observer, site_id=ids[site], phase=phase,
                                tick=tick, sequence=seq, offset=offset+field_offset, length=8))
            mapping[str(sequence)+'.'+phase] = rid
            refs.append(rid)
        occurrence = occurrences[site]
        occurrences[site] += 1
        events.append(dict(id=stable_id(identity, 'event', *refs), observer_id=observer,
            site_id=ids[site], semantic='observer_region_elapsed', kind='interval',
            start_tick=begin, end_tick=end, occurrence=occurrence,
            occurrence_basis='complete_pair_order' if complete else 'retained_pair_order',
            iteration_id=None, record_ids=refs, missing_reason=None,
            coverage='complete_selected_pair_stream' if complete else 'retained_pair_prefix'))
    return validate_raw_batch(dict(schema_version=2,
        identity=dict(zip(('capture_id','invocation_id','binary_id'), identity)),
        raw_artifact=dict(sha256=capture['raw_sha256'], bytes=len(raw)),
        clock_status='unverified', boundary_status='unverified', sources=sources, sites=sites,
        observers=observers, records=records, events=events, complete=complete,
        backend_record_map={'enflame.dynamic_pairs.v1': mapping},
        notes=['Endpoint sequences index real fields in append pairs, not the chronological order of all reads.',
               'Counts use canonical endpoint references; each native committed pair contributes two.',
               'Source locations support navigation, not source cost or hardware-completion attribution.',
               'Raw units/epoch and final source-region boundaries are unverified.']))
