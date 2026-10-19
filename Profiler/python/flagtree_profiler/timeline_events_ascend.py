"""Pure Ascend paired-log decoder; no device access or clock authorization."""
import base64
from collections import Counter
import hashlib
import json
import re
import struct

from .timeline_events import stable_id, validate_raw_batch, _integer, _sha, _text

LAYOUT = 'ascend_source_timeline_v1'
MAGIC = 0x46505441314c4f47
COMMIT = 0x46505441434f4d31
NATIVE_CONTROL_FILE = '__flagprism_native_control_v1__'
PIPE_NAMES = {
    0: 'PIPE_S',
    1: 'PIPE_V',
    2: 'PIPE_M',
    3: 'PIPE_MTE1',
    4: 'PIPE_MTE2',
    5: 'PIPE_MTE3',
    6: 'PIPE_ALL',
    7: 'PIPE_MTE4',
    8: 'PIPE_MTE5',
    9: 'PIPE_V2',
    10: 'PIPE_FIX'
}
MAX_COUNT = (1 << 63) - 1


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def compiler_actors(metadata):
    """Check actual retained compiler inputs, mappings and ABI composition.

    This establishes emission provenance, not machine region bounds, exclusive
    writers for every target transformation, or a comparable physical clock.
    """
    _need(
        type(metadata) is dict
        and metadata.get('debug_record_layout') == LAYOUT,
        'Ascend timeline compiler layout mismatch')
    capacity = _integer(metadata.get('debug_record_capacity'), 'pair capacity',
                        1, 16384)
    for key in ('debug_timeline_storage_version',
                'debug_timeline_publisher_version',
                'flagprism_ascend_source_timeline_version'):
        _need(
            type(metadata.get(key)) is int and metadata[key] == 1,
            'Unsupported Ascend timeline ' + key)
    _need(
        type(metadata.get('debug_record_size')) is int
        and metadata['debug_record_size'] == 64
        and type(metadata.get('debug_records_per_instance')) is int
        and metadata['debug_records_per_instance'] == 3 * capacity,
        'Ascend physical record declaration contradicts its publisher')
    request = metadata.get('flagprism_ascend_observation_request') or {}
    _need(
        request.get('program_policy') == 'runtime_first_last'
        and request.get('semantics') == ['source_control_interval']
        and request.get('programs') is None
        and request.get('automatic') is True
        and type(request.get('sample_every')) is int
        and request['sample_every'] == 1
        and type(request.get('max_events_per_instance')) is int
        and request['max_events_per_instance'] == capacity,
        'Ascend timeline request does not match the producer')
    selected = (metadata.get('debug_automatic_plan')
                or {}).get('selected_sites')
    _need(
        type(selected) is list and 1 <= len(selected) <= 128,
        'Actual frontend selection is required')
    for source in selected:
        _integer(source, 'source identity', 1, 0x7fffffff)
    _need(
        len(set(selected)) == len(selected),
        'Aliased frontend source identities')
    abi = metadata.get('debug_frontend_marker_abi') or {}
    _need(
        abi.get('version') == 3
        and abi.get('record_layout') == 'ascend_source_census_v3'
        and abi.get('site_count') == len(selected)
        and metadata.get('debug_census_columns') == len(selected),
        'Actual frontend carrier ABI is required independently of storage')
    tracked = metadata.get('debug_tracked_table')
    _need(type(tracked) is list, 'Tracked source table is required')
    origins = {}
    for row in tracked:
        _need(type(row) is dict, 'Malformed source table')
        _integer(row.get('opId'), 'tracked source identity', 1, 0x7fffffff)
        if row.get('opId') in selected:
            _need(row['opId'] not in origins, 'Ambiguous source origin')
            origins[row['opId']] = row
    _need(set(origins) == set(selected), 'Selected source origin missing')
    handoff = metadata.get('flagprism_ascend_handoff') or {}
    _need(
        handoff.get('phase') == 'finished'
        and type(handoff.get('returncode')) is int
        and handoff['returncode'] == 0,
        'Actual successful compiler handoff is required')
    compile_id = _text(handoff.get('compile_id'), 'compile identity')
    snapshot = handoff.get('source_snapshot') or {}
    _need(
        type(snapshot.get('ir')) is str
        and _digest(snapshot['ir'].encode()) == snapshot.get('ir_sha256')
        and _digest(
            json.dumps(tracked, sort_keys=True,
                       separators=(',', ':')).encode())
        == snapshot.get('tracked_ops_sha256'),
        'Frontend source snapshot changed')
    artifacts = handoff.get('artifacts')
    _need(
        type(artifacts) is list and 1 <= len(artifacts) <= 8,
        'Actual actor compiler artifacts are required')
    actors = {}
    for artifact in artifacts:
        manifest = artifact.get('metadata') or {}
        text = artifact.get('manifest_text')
        original = artifact.get('llir')
        adapted = artifact.get('adapted') or {}
        _need(
            all(type(v) is str for v in (text, original, adapted.get('llir'))),
            'Retained actor LLVM and manifest text are required')
        original_hash = _digest(original.encode())
        _need(
            json.loads(text) == manifest
            and _digest(text.encode()) == artifact.get('manifest_sha256')
            and original_hash == artifact.get('sha256') ==
            manifest.get('module_sha256')
            and _digest(adapted['llir'].encode()) == adapted.get('sha256')
            and manifest.get('compile_id') == compile_id,
            'Actor compiler provenance mismatch')
        binding = manifest.get('runtime_actor_binding') or {}
        kind = binding.get('actor_kind')
        slots = [0] if kind == 'AIC' else [1, 2] if kind == 'AIV' else []
        expression = (dict(
            kind='constant_i64', value=0) if kind == 'AIC' else dict(
                kind='add_i64', call='llvm.hivm.GET.SUBBLOCKID', constant=1))
        _need(
            slots and binding.get('layout') == LAYOUT
            and type(binding.get('schema_version')) is int
            and binding['schema_version'] == 1
            and binding.get('header_bytes') == 64
            and binding.get('record_bytes') == 64
            and binding.get('segment_count') == 3
            and binding.get('segment_words') == 8 + capacity * 8
            and binding.get('max_program_slots') == 2
            and binding.get('selection') == 'runtime_first_last'
            and binding.get('admissible_slots') == slots
            and binding.get('expression') == expression
            and binding.get('module_sha256') == original_hash
            and binding.get('compile_id') == compile_id,
            'Actor layout/selection binding mismatch')
        entries = [
            a for a in manifest.get('actors', [])
            if a.get('function') == binding.get('function')
            and a.get('actor_kind') == kind
            and a.get('dynamic_observation_prepared') is True
        ]
        _need(len(entries) == 1, 'Actual actor entry is ambiguous')
        coordinates = binding.get('source_program_binding') or {}
        _need(
            binding.get('frontend_carrier') == 'source_census_site.v3'
            and coordinates.get('basis')
            == 'actual_selected_source_site_marker_operands'
            and coordinates.get('linear_expression')
            == 'x + grid_x * (y + grid_y * z)',
            'Source coordinates are not bound to actual carriers')
        anchors = {}
        for anchor in coordinates.get('anchors', []):
            source = anchor.get('source_op_id')
            column = _integer(anchor.get('census_column'), 'carrier column', 0,
                              len(selected) - 1)
            _need(
                selected[column] == source
                and anchor.get('source_site_count') == len(selected)
                and anchor.get('operand_roles')
                == ['x', 'y', 'z', 'grid_x', 'grid_y', 'grid_z']
                and type(anchor.get('operands')) is list
                and len(anchor['operands']) == 6,
                'Carrier source/coordinate mapping mismatch')
            anchors[source, column] = True
        native_version = binding.get('native_control_version')
        _need(
            native_version is None
            or (type(native_version) is int and native_version in (1, 2)),
            'Unsupported Ascend native control feature version')
        sites = {}
        for site in manifest.get('dynamic_sites', []):
            sid = _integer(site.get('site_id'), 'backend site', 1, 0xffffffff)
            source = site.get('source_op_id')
            column = site.get('frontend_column')
            _need(
                sid not in sites and (source, column) in anchors
                and site.get('public_semantic') == 'source_control_interval'
                and type(site.get('semantic_code')) is int and
                (site.get('semantic_code') == 1
                 and site.get('operation_class') == 'lowered_source_fragment'
                 or native_version in (1, 2) and site.get('semantic_code') in
                 (2, 3) and site.get('operation_class')
                 == 'native_control_scalar_bracket')
                and site.get('boundary_status') == 'unverified',
                'Unknown or unbound actor fragment')
            _need(
                type(site.get('original_instructions')) is str
                and _digest(site['original_instructions'].encode())
                == site.get('original_instructions_sha256'),
                'Original lowered fragment changed')
            if site['semantic_code'] in (2, 3):
                operation = 'set_flag' if site[
                    'semantic_code'] == 2 else 'wait_flag'
                intrinsic = 'llvm.hivm.' + ('SET' if operation == 'set_flag'
                                            else 'WAIT') + '.FLAG.IMM'
                arguments = site.get('native_arguments')
                _need(
                    site.get('native_operation') == operation
                    and site.get('intrinsic') == intrinsic
                    and site.get('completion_status') == 'unverified'
                    and site.get('scope')
                    == 'scalar_issue_of_original_native_control'
                    and site.get('source_binding')
                    in ('containing_original_block_fragment_navigation',
                        'dominating_source_coordinates_only')
                    and type(arguments) is list and len(arguments) == 3
                    and all(
                        type(a) is int and 0 <= a <= 0x7fffffff
                        for a in arguments),
                    'Invalid Ascend native control binding')
                pattern = re.escape(
                    '@' + intrinsic) + r'\(i64 (\d+), i64 (\d+), i64 (\d+)\)'
                matches = re.findall(pattern, site['original_instructions'])
                _need(
                    len(matches) == 1
                    and list(map(int, matches[0])) == arguments
                    and re.sub(r', ![\w.]+ ![0-9]+', '',
                               site['original_instructions']) in re.sub(
                                   r', ![\w.]+ ![0-9]+', '', original),
                    'Native control arguments differ from retained original LLVM'
                )
            if native_version == 2 and site['semantic_code'] in (2, 3):
                marker = site.get('native_instruction_marker') or {}
                _need(
                    type(marker.get('version')) is int
                    and marker['version'] == 1
                    and marker.get('file') == NATIVE_CONTROL_FILE
                    and type(marker.get('line')) is int
                    and 0 <= marker['line'] <= 0x7fffffff
                    and ((marker.get('status') == 'debug_locations_emitted'
                          and marker['line'] == sid) or
                         (marker.get('status') == 'missing_debug_scope'
                          and marker['line'] == 0)),
                    'Invalid native instruction marker declaration')
            sites[sid] = dict(site,
                              origin=origins[source],
                              backend_identity=kind + ':' + original_hash +
                              ':' + binding['function'] + ':' + str(sid))
        for slot in slots:
            _need(slot not in actors,
                  'Multiple actor functions alias one physical log slot')
            actors[slot] = dict(kind=kind,
                                native_control_version=native_version,
                                function=binding['function'],
                                sites=sites,
                                manifest_sha256=artifact['manifest_sha256'])
    return actors


def canonicalize_ascend_capture(raw, *, owner, metadata, association):
    """Decode actual published pairs into shared schema2, retaining empty slots.

    An empty admissible actor is explicitly unobserved, never proof of execution.
    No hardware units, region boundary or dynamic async flow is inferred here.
    """
    _need(type(raw) is bytes, 'Immutable Ascend raw bytes are required')
    identity = tuple(
        _text(owner.get(k), k)
        for k in ('capture_id', 'invocation_id', 'binary_id'))
    _sha(identity[2])
    _need(
        metadata.get('hash') == identity[2] and type(association) is dict
        and association.get('evidence') == 'same_launch_metadata_object'
        and association.get('binary_id') == identity[2]
        and association.get('invocation_id'),
        'Actual launch/compiler identity is required')
    actors = compiler_actors(metadata)
    retained_binary(metadata)
    layout = owner.get('layout') or {}
    grid = layout.get('grid')
    _need(
        type(grid) in (list, tuple) and len(grid) == 3,
        'Actual grid is required')
    volume = 1
    for dim in grid:
        volume *= _integer(dim, 'actual grid', 1, 0x7fffffff)
    _need(volume <= 0x7fffffff, 'Actual grid exceeds bounded indexing')
    programs = [0] if volume == 1 else [0, volume - 1]
    runtime = (owner.get('plan') or {}).get('runtime_metadata') or {}
    _need(
        type(runtime.get('grid')) in (list, tuple)
        and list(runtime['grid']) == list(grid)
        and runtime.get('record_layout') == LAYOUT
        and owner['plan'].get('binary_id') == identity[2],
        'Actual launch geometry/plan identity differs from its retained owner')
    capacity = metadata['debug_record_capacity']
    stride = 64 + capacity * 64
    _need(
        type(layout.get('storage_version')) is int
        and layout['storage_version'] == 1
        and type(layout.get('publisher_version')) is int
        and layout['publisher_version'] == 1 and layout.get('alignment') == 64
        and layout.get('scratch_size') == stride
        and list(layout.get('programs', [])) == programs
        and [list(slot) for slot in layout.get('slots', [])
             ] == [list(slot) for slot in enumerate(programs)],
        'Retained compact storage composition is inconsistent')
    _need(
        layout.get('raw_bytes') == len(raw) == len(programs) * 3 * stride,
        'Actual raw extent differs from compact ABI')
    sources, sites, site_map = {}, {}, {}
    for slot, actor in sorted(actors.items()):
        for sid, site in actor['sites'].items():
            local = site['backend_identity']
            source = site['origin']
            native = site['semantic_code'] in (2, 3)
            location = source.get('sourceLoc')
            if native and site.get('source_file'):
                location = str(site['source_file']) + ':' + str(
                    site.get('line')) + ':' + str(site.get('column'))
            source_id = stable_id((identity[2], ), 'source', source['opId'],
                                  location)
            sources[source_id] = dict(
                id=source_id,
                source_sha256=None,
                relation='compiler_origin_navigation',
                location=location,
                provenance=('native_debug_location_with_coordinate_carrier'
                            if native and site.get('source_file') else
                            'coordinate_carrier_navigation_only' if native else
                            'actual_frontend_and_lowered_fragment_manifest'))
            site_id = stable_id((identity[2], ), 'site', local)
            sites[site_id] = dict(id=site_id,
                                  name=source.get('mlirOpName') or str(sid),
                                  semantic='observer_region_elapsed',
                                  source_ids=[source_id],
                                  backend_site_id=local,
                                  attributes={
                                      'ascend.source_op_id':
                                      source['opId'],
                                      'ascend.fragment_scope':
                                      site['scope'],
                                      'ascend.original_block':
                                      site['original_block'],
                                      'ascend.manifest_sha256':
                                      actor['manifest_sha256']
                                  })
            if site['semantic_code'] in (2, 3):
                native_arguments = site['native_arguments']
                sites[site_id]['name'] = ('Native ' +
                                          site['native_operation'].upper() +
                                          ' ' + str(native_arguments) +
                                          ' (scalar control)')
                sites[site_id]['attributes'].update({
                    'ascend.native_control_version':
                    actor['native_control_version'],
                    'ascend.native_operation':
                    site['native_operation'],
                    'ascend.native_source_pipe':
                    native_arguments[0],
                    'ascend.native_destination_pipe':
                    native_arguments[1],
                    'ascend.native_event_id':
                    native_arguments[2],
                    'ascend.native_intrinsic':
                    site['intrinsic'],
                    'ascend.source_binding':
                    site['source_binding'],
                    'ascend.completion_status':
                    'unverified',
                    'ascend.engine_activity_verified':
                    False
                })
            if native and actor['native_control_version'] == 2:
                attrs = sites[site_id]['attributes']
                attrs['ascend.coordinate_carrier_source_op_id'] = attrs.pop(
                    'ascend.source_op_id')
                src, dst, event = site['native_arguments']
                src_name = PIPE_NAMES.get(src, 'pipe_id_' + str(src))
                dst_name = PIPE_NAMES.get(dst, 'pipe_id_' + str(dst))
                attrs.update({
                    'ascend.native_source_pipe_name':
                    src_name,
                    'ascend.native_destination_pipe_name':
                    dst_name,
                    'ascend.pipe_name_basis':
                    'compiler_hivm_pipe_enum',
                    'ascend.native_instruction_marker':
                    site['native_instruction_marker'],
                    'display.track_group':
                    'Native controls ' + src_name + ' -> ' + dst_name +
                    ' (scalar observer)'
                })
                sites[site_id]['name'] = ('Native ' +
                                          site['native_operation'].upper() +
                                          ' ' + src_name + ' -> ' + dst_name +
                                          ' (event ' + str(event) +
                                          ', scalar control)')
            site_map[slot, sid] = site_id
    observers, records, events, mapping = [], [], [], {}
    complete = True
    for physical_slot, program in enumerate(programs):
        coords = [
            program % grid[0], (program // grid[0]) % grid[1],
            program // (grid[0] * grid[1])
        ]
        for actor_slot in range(3):
            base = (physical_slot * 3 + actor_slot) * stride
            segment = raw[base:base + stride]
            actor = actors.get(actor_slot)
            if actor is None:
                _need(not any(segment), 'Unassigned actor slot contains data')
                continue
            header = struct.unpack_from('<8Q', segment)
            arrived = bool(any(header))
            magic, committed, attempted, dropped, pid, who, block, flags = header
            if arrived:
                _need(
                    magic == MAGIC and committed <= capacity and flags & 1
                    and not flags & ~7 and pid == program and who == actor_slot
                    and attempted <= MAX_COUNT and dropped <= MAX_COUNT,
                    'Invalid Ascend actor header')
                _need(
                    bool(flags & 4) == bool(dropped)
                    and (bool(flags & 2) or attempted == committed + dropped),
                    'Actor attempts/commits/loss disagree')
                _need(
                    (not dropped or committed == capacity)
                    and (not flags & 2 or attempted == MAX_COUNT),
                    'Actor overflow/saturation does not follow its publisher')
                _need(not any(segment[64 + committed * 64:]),
                      'Unused pair tail contains data')
            else:
                _need(not any(segment), 'Unpublished actor contains payload')
            saturated = bool(flags & 2)
            actor_complete = arrived and not dropped and not saturated
            complete = complete and actor_complete
            kind = 'ascend.' + actor['kind'] + '.scalar_observer'
            oid = stable_id(identity, 'observer', kind, str(actor_slot),
                            coords)
            observers.append(
                dict(id=oid,
                     kind=kind,
                     local_id=str(actor_slot),
                     program_coordinates=coords,
                     physical_identity={'ascend.block_id': block}
                     if arrived else None,
                     clock_domain_id=stable_id(identity,
                                               'unverified-observer-domain',
                                               program, actor_slot),
                     epoch_id=stable_id(identity, 'unverified-capture-epoch',
                                        program, actor_slot),
                     timer_bits=64,
                     record_order='paired_endpoints',
                     attempted_records=2 * attempted,
                     committed_records=2 * committed,
                     retained_records=2 * committed,
                     dropped_records=2 * dropped,
                     filtered_records=0,
                     overwritten_records=0,
                     saturated=saturated,
                     complete=actor_complete,
                     attributes={
                         'ascend.writer_state':
                         'arrived' if arrived else 'unobserved',
                         'ascend.native_pair_count': committed,
                         'ascend.function': actor['function']
                     }))
            occurrences = Counter()
            for index in range(committed):
                offset = base + 64 + index * 64
                descriptor, sequence, start, end, p, a, physical, tag = struct.unpack_from(
                    '<8Q', raw, offset)
                sid = descriptor & 0xffffffff
                _need((actor_slot, sid) in site_map and descriptor >> 32
                      == actor['sites'][sid]['semantic_code']
                      and sequence == index
                      and (p, a, physical) == (program, actor_slot, block)
                      and start <= end and tag
                      == (COMMIT ^ descriptor ^ sequence ^ p ^ a ^ physical),
                      'Invalid or unbound published Ascend pair')
                site_id = site_map[actor_slot, sid]
                refs = []
                for phase_index, (phase, tick,
                                  field) in enumerate([('entry', start, 16),
                                                       ('exit', end, 24)]):
                    seq = 2 * sequence + phase_index
                    rid = stable_id(identity, 'record', oid, seq)
                    records.append(
                        dict(id=rid,
                             observer_id=oid,
                             site_id=site_id,
                             phase=phase,
                             tick=tick,
                             sequence=seq,
                             offset=offset + field,
                             length=8))
                    mapping[str(program) + '.' + str(actor_slot) + '.' +
                            str(index) + '.' + phase] = rid
                    refs.append(rid)
                occurrence = occurrences[sid]
                occurrences[sid] += 1
                events.append(
                    dict(id=stable_id(identity, 'event', *refs),
                         observer_id=oid,
                         site_id=site_id,
                         semantic='observer_region_elapsed',
                         kind='interval',
                         start_tick=start,
                         end_tick=end,
                         occurrence=occurrence,
                         occurrence_basis='complete_pair_order'
                         if actor_complete else 'retained_pair_order',
                         iteration_id=None,
                         record_ids=refs,
                         missing_reason=None,
                         coverage='complete_selected_pair_stream'
                         if actor_complete else 'retained_pair_prefix'))
    return validate_raw_batch(
        dict(
            schema_version=2,
            identity=dict(
                zip(('capture_id', 'invocation_id', 'binary_id'), identity)),
            raw_artifact=dict(sha256=_digest(raw), bytes=len(raw)),
            clock_status='unverified',
            boundary_status='unverified',
            sources=list(sources.values()),
            sites=list(sites.values()),
            observers=observers,
            records=records,
            events=events,
            complete=complete,
            backend_record_map={'ascend.paired.v1': mapping},
            notes=[
                'Unobserved actor slots are not evidence of execution.',
                'Physical counts are pairs; canonical counts are endpoint references.',
                'Lowered fragments support navigation, not certified source cost or hardware busy.',
                'Units, read precision, final boundaries and cross-observer epoch remain unverified.'
            ]))


def retained_binary(metadata):
    info = (metadata.get('flagprism_ascend_handoff')
            or {}).get('final_outputs', {}).get('binary', {})
    _need(
        info.get('encoding') == 'base64' and type(info.get('data')) is str
        and len(info['data']) <= 48 * 1024 * 1024,
        'Retained final compiler binary is required')
    data = base64.b64decode(info['data'], validate=True)
    _integer(info.get('bytes'), 'compiled binary bytes', 1, 32 * 1024 * 1024)
    _need(
        len(data) == info['bytes']
        and _digest(data) == _sha(info.get('sha256')),
        'Retained compiler binary changed')
    return data


def attach_ascend_timeline_export(raw, *, owner, metadata, association):
    """Use the ordinary bundle/source pipeline after durable original retention."""
    import copy
    from .observations import observation
    batch = canonicalize_ascend_capture(raw,
                                        owner=owner,
                                        metadata=metadata,
                                        association=association)
    runtime = copy.deepcopy(owner['plan']['runtime_metadata'])
    runtime.update(capture_id=owner['capture_id'],
                   profiler_invocation_id=association['invocation_id'],
                   profiler_association_evidence=association)
    observers = {r['id']: r for r in batch['observers']}
    sites = {r['id']: r for r in batch['sites']}
    refs = {r['id']: r for r in batch['records']}
    rows = []
    grid = owner['layout']['grid']
    for event in batch['events']:
        observer = observers[event['observer_id']]
        x, y, z = observer['program_coordinates']
        rows.append(
            observation(
                dict(
                    id=event['id'],
                    capture_id=owner['capture_id'],
                    invocation_id=association['invocation_id'],
                    binary_id=owner['binary_id'],
                    canonical_invocation_id=batch['identity']['invocation_id'],
                    association_status='verified',
                    association_evidence=association,
                    source='flagtree_ir_dynamic',
                    semantic='observer_region_elapsed',
                    storage=LAYOUT,
                    program=x + grid[0] * (y + grid[1] * z),
                    actor=int(observer['local_id']),
                    site=int(sites[event['site_id']]['backend_site_id'].rsplit(
                        ':', 1)[-1]),
                    occurrence=event['occurrence'],
                    iteration=None,
                    start_tick=event['start_tick'],
                    end_tick=event['end_tick'],
                    clock=dict(domain=observer['clock_domain_id'],
                               scope=observer['id'],
                               alignment='unverified',
                               tick_ns=None,
                               wrap_bits=64),
                    original_record=dict(
                        canonical_event=event,
                        raw_fields=[refs[r] for r in event['record_ids']],
                        raw_artifact=batch['raw_artifact']),
                    observer_complete=observer['complete'],
                    dropped_endpoint_references=observer['dropped_records'],
                    limits=[
                        'Lowered fragment counter bracket; source boundary remains unverified.',
                        'SYS_CNT ticks have no certified unit or shared epoch in this capture.'
                    ])))
    return dict(raw_buffer=raw,
                runtime_metadata=runtime,
                record_layout=LAYOUT,
                debug_kernel_name=metadata.get('debug_kernel_name', ''),
                debug_tracked_table=copy.deepcopy(
                    metadata.get('debug_tracked_table', [])),
                canonical_timeline=batch,
                semantic_observations=rows,
                capture_status='decoded',
                decoded=dict(records=[],
                             dropped=sum(o['dropped_records'] // 2
                                         for o in batch['observers']),
                             complete=batch['complete']))
