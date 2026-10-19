"""Decode real late GCU execution records; no device, SDK or unit inference.

The protocol records local observer brackets and the actual queue/buffer words.
It does not report native engine busy or grant a shared counter epoch.
"""
from collections import defaultdict
import hashlib
import struct

from .timeline_events import stable_id, validate_raw_batch, _integer

SEMANTICS = {
    1: 'issue_interval',
    2: 'wait_bracket',
    3: 'issue_interval',
    4: 'wait_bracket',
    5: 'observer_region_elapsed'
}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def decode_execution_capture(raw, *, compiler_metadata, identity, association,
                             grid):
    """Return canonical records and raw-bound native arguments for one launch."""
    _need(
        type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024,
        'GCU execution raw input is empty or exceeds its budget')
    _need(
        type(identity) is dict
        and set(identity) == {'capture_id', 'invocation_id', 'binary_id'},
        'Missing actual capture identity')
    namespace = tuple(identity[key]
                      for key in ('capture_id', 'invocation_id', 'binary_id'))
    _need(all(type(value) is str and value for value in namespace),
          'Invalid capture identity')
    _need(
        type(association) is dict and association.get('evidence')
        in ('same_launch_metadata_object',
            'direct_owned_compiled_kernel_launch')
        and association.get('binary_id') == identity['binary_id'],
        'Native execution records lack their actual launch association')
    _need(
        type(grid) in (tuple, list) and len(grid) == 3,
        'Missing actual launch grid')
    total = 1
    for dim in grid:
        total *= _integer(dim, 'grid dimension', 1, 0x7fffffff)
    _need(total <= 0x7fffffff, 'GCU grid exceeds signed index range')
    _need(
        compiler_metadata.get('debug_record_layout') ==
        'gcu_execution_timeline_v3', 'Not the late GCU execution record ABI')
    manifest = compiler_metadata.get('debug_execution_manifest')
    _need(
        type(manifest) is dict and type(manifest.get('schema_version')) is int
        and manifest['schema_version'] == 1
        and manifest.get('record_layout') == 'gcu_execution_timeline_v3',
        'Missing actual late execution manifest')
    argument_version = manifest.get('buffer_arguments_version', 1)
    _need(
        type(argument_version) is int and argument_version in (1, 2),
        'Unknown native buffer argument version')
    capacity = _integer(manifest.get('capacity'), 'execution capacity', 1,
                        4096)
    stride = 32 + capacity * 128
    _need(
        manifest.get('record_size') == 128
        and manifest.get('slot_bytes') == stride
        and compiler_metadata.get('debug_record_size') == 128
        and compiler_metadata.get('debug_dynamic_slot_bytes') == stride,
        'Compiler and execution storage disagree')
    programs = [0] if total == 1 else [0, total - 1]
    _need(
        len(raw) == stride * len(programs),
        'Wrong execution capture byte size')
    descriptions = manifest.get('sites')
    _need(
        type(descriptions) is list and 0 < len(descriptions) <= 512,
        'Invalid execution site table')
    descriptions_by_id, sites, sources, site_ids = {}, [], [], {}
    for row in descriptions:
        _need(type(row) is dict, 'Invalid execution descriptor')
        site = _integer(row.get('id'), 'execution site', 1, 0xffffffff)
        kind = _integer(row.get('kind'), 'execution kind', 1, 5)
        _need(
            site not in descriptions_by_id
            and type(row.get('operation')) is str and row['operation']
            and type(row.get('location')) is str,
            'Aliased or incomplete execution site')
        descriptions_by_id[site] = row
        sid = stable_id((identity['binary_id'], ), 'site', str(site))
        source = stable_id((identity['binary_id'], ), 'source', str(site),
                           row['location'])
        site_ids[site] = sid
        sources.append(
            dict(id=source,
                 source_sha256=None,
                 relation='compiler_origin_navigation',
                 location=row['location'],
                 provenance='actual_SDK_execution_IR_location'))
        sites.append(
            dict(id=sid,
                 name=row['operation'],
                 semantic=SEMANTICS[kind],
                 backend_site_id=str(site),
                 source_ids=[source],
                 attributes={
                     'enflame.native_primitive': row['operation'],
                     'enflame.execution_kind': kind,
                     'enflame.source_cost_verified': False,
                     'enflame.engine_busy_verified': False
                 }))
    observers, records, events, commands, mapping = [], [], [], [], {}
    for slot, program in enumerate(programs):
        base = slot * stride
        written, actual_capacity, dropped, flags, record_size, payload, attempted, actual_program = struct.unpack_from(
            '<8I', raw, base)
        _need(
            actual_capacity == capacity and record_size == 128
            and payload == stride and actual_program == program
            and flags & ~0x30 == 0 and flags & 0x20
            and written == min(attempted, capacity)
            and dropped == attempted - written
            and bool(flags & 0x10) == (attempted == 0x7fffffff),
            'Incomplete or inconsistent execution publication')
        _need(not any(raw[base + 32 + written * 128:base + stride]),
              'Unused execution capacity contains nonzero private bytes')
        complete = not dropped and not flags & 0x10
        coords = [
            program % grid[0], (program // grid[0]) % grid[1],
            program // (grid[0] * grid[1])
        ]
        observer_id = stable_id(namespace, 'observer', 'enflame.work_item',
                                '0', coords)
        observer = dict(
            id=observer_id,
            kind='enflame.work_item',
            local_id='0',
            program_coordinates=coords,
            physical_identity=None,
            clock_domain_id=stable_id(namespace, 'unverified-observer-domain',
                                      program, 0),
            epoch_id=stable_id(namespace, 'capture-epoch-unverified', program,
                               0),
            timer_bits=46,
            record_order='paired_endpoints',
            attempted_records=2 * attempted,
            committed_records=2 * written,
            retained_records=2 * written,
            dropped_records=2 * dropped,
            filtered_records=0,
            overwritten_records=0,
            saturated=bool(flags & 0x10),
            complete=bool(complete),
            attributes={
                'enflame.native_association': association,
                'enflame.physical_slot': slot,
                'enflame.raw_slot_base': base,
                'enflame.physical_pair_bytes': 128,
                'enflame.physical_pairs_retained': written,
                'enflame.endpoint_count_basis':
                'two_real_field_references_per_committed_pair',
                'enflame.publication': manifest['publication']
            })
        physical_ids, physical_offsets = set(), []
        occurrences = defaultdict(int)
        for sequence in range(written):
            offset = base + 32 + sequence * 128
            words = struct.unpack_from('<32I', raw, offset)
            site, kind = words[1], words[3]
            _need(
                words[0] == 0x46504733 and words[2] == sequence
                and site in descriptions_by_id
                and kind == descriptions_by_id[site]['kind'] and words[24] == 0
                and words[25] == program and words[26] == 3
                and words[30:] == (0x55543033, 0x46504743)
                and all(words[i] == 0
                        for i in ((23, 27, 28,
                                   29) if argument_version == 1 else (27, ))),
                'Uncommitted, aliased or invalid execution record')
            begin = words[4] | words[5] << 32
            end = words[6] | words[7] << 32
            _need(
                0 <= begin <= end < 1 << 46
                and words[8] == words[18] == words[19],
                'Execution pair changed physical clock or regressed/wrapped')
            physical_ids.add(words[8])
            physical_offsets.extend(offset + index * 4
                                    for index in (8, 18, 19))
            refs = []
            for phase_index, (phase, tick, field) in enumerate(
                (('entry', begin, 16), ('exit', end, 24))):
                serial = 2 * sequence + phase_index
                rid = stable_id(namespace, 'record', observer_id, serial)
                records.append(
                    dict(id=rid,
                         observer_id=observer_id,
                         site_id=site_ids[site],
                         phase=phase,
                         tick=tick,
                         sequence=serial,
                         offset=offset + field,
                         length=8))
                mapping[str(program) + '.' + str(sequence) + '.' + phase] = rid
                refs.append(rid)
            event = dict(id=stable_id(namespace, 'event', *refs),
                         observer_id=observer_id,
                         site_id=site_ids[site],
                         semantic=SEMANTICS[kind],
                         kind='interval',
                         start_tick=begin,
                         end_tick=end,
                         occurrence=occurrences[site],
                         occurrence_basis='complete_pair_order'
                         if complete else 'retained_pair_order',
                         iteration_id=None,
                         record_ids=refs,
                         missing_reason=None,
                         coverage='complete_selected_pair_stream'
                         if complete else 'retained_pair_prefix')
            occurrences[site] += 1
            events.append(event)
            commands.append(
                dict(event_id=event['id'],
                     observer_id=observer_id,
                     sequence=sequence,
                     site_id=site_ids[site],
                     kind=kind,
                     raw_offset=offset,
                     raw_length=128,
                     queue=dict(base=words[10] | words[11] << 32,
                                index=words[9]) if kind in (1, 2) else None,
                     destination=dict(address=words[12] | words[13] << 32,
                                      space=words[20]),
                     source=dict(address=words[14] | words[15] << 32,
                                 space=words[21]),
                     secondary_source=dict(address=words[16] | words[17] << 32,
                                           space=words[22]),
                     accumulator=dict(address=words[28] | words[29] << 32,
                                      space=words[23])
                     if argument_version == 2 else None))
        _need(
            len(physical_ids) <= 1,
            'Execution observer changed physical clock identity')
        if physical_ids:
            observer['physical_identity'] = {
                'enflame.kind': 'dtu.full_sipinfo.v1',
                'enflame.full_sipinfo': next(iter(physical_ids)),
                'enflame.evidence': 'actual_execution_record_identity_words',
                'enflame.identity_word_offsets': physical_offsets
            }
        observers.append(observer)
    batch = validate_raw_batch(
        dict(
            schema_version=2,
            identity=identity,
            raw_artifact=dict(sha256=hashlib.sha256(raw).hexdigest(),
                              bytes=len(raw)),
            clock_status='unverified',
            boundary_status='unverified',
            sources=sources,
            sites=sites,
            observers=observers,
            records=records,
            events=events,
            complete=all(row['complete'] for row in observers),
            backend_record_map={'enflame.execution.v3': mapping},
            notes=[
                'Native brackets are observer elapsed, not engine busy or source-operation costs.',
                'Queue and buffer words describe actual runtime arguments; this raw decoder grants no dependency/clock qualification.',
                'Records are locally buffered and published at the original return.'
            ]))
    return dict(canonical=batch, commands=commands)
