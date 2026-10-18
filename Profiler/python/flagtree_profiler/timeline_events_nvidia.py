"""Map the actual NVIDIA record protocol to the common raw event contract."""
from collections import defaultdict

from .timeline_events import stable_id, validate_raw_batch


def canonicalize_nvidia_capture(decoded, *, owner, metadata, raw_sha256,
                                raw_bytes):
    identity = tuple(
        owner.get(k) for k in ('capture_id', 'invocation_id', 'binary_id'))
    if any(type(v) is not str or not v for v in identity):
        raise ValueError('Actual invocation identity is required')
    plan = owner.get('plan')
    if (type(plan) is not dict or plan.get('binary_id') != identity[2]
            or metadata.get('binary_id') != identity[2]
            or type(plan.get('timeline_record_version')) is not int
            or plan.get('timeline_record_version') not in (2, 3) or
            decoded.get('record_version') != plan['timeline_record_version']):
        raise ValueError(
            'NVIDIA canonical adapter has a mismatched binary/record plan')
    layout = owner.get('layout') or {}
    grid = layout.get('grid')
    if (type(grid) not in (list, tuple) or len(grid) != 3
            or any(type(v) is not int or v <= 0 for v in grid)
            or layout.get('raw_bytes') != raw_bytes):
        raise ValueError(
            'Actual nonempty launch geometry and physical size are required')
    sources, sites, site_ids = {}, [], {}
    origins = metadata.get('scope_id_origins') or {}
    inventory = plan.get('inventory')
    if type(inventory) is not list:
        raise ValueError('Actual selected compiler inventory is required')
    for candidate in inventory:
        if type(candidate) is not dict or type(
                candidate.get('selected')) is not bool:
            raise ValueError('Malformed compiler inventory entry')
        if not candidate['selected']:
            continue
        site = candidate.get('scope_id')
        if type(site
                ) is not int or not 0 <= site < (1 << 31) or site in site_ids:
            raise ValueError('Invalid or aliased backend site identity')
        sid = stable_id((identity[2], ), 'site', str(site))
        site_ids[site] = sid
        origin = origins.get(str(site), origins.get(site, {}))
        captures = origin.get('source_capture') or []
        if not captures:
            captures = [
                dict(source_sha256=None, ir_location=candidate.get('location'))
            ]
        refs = []
        for source in captures:
            source_sha = source.get('source_sha256')
            key = stable_id(
                (), 'source', source_sha, source.get('file'),
                source.get('line'), source.get('column'),
                candidate.get('location') if source_sha is None else None)
            sources[key] = dict(
                id=key,
                source_sha256=source_sha,
                relation='compiler_origin_navigation',
                location=source,
                provenance=(
                    'actual_compiler_origin_and_retained_source_snapshot'
                    if source_sha is not None else
                    'actual_compiler_location_without_retained_source_snapshot'
                ))
            if key not in refs:
                refs.append(key)
        sites.append(
            dict(id=sid,
                 name=candidate.get('selected_scope_name')
                 or candidate['operation'],
                 semantic=candidate.get('timeline_semantic'),
                 source_ids=refs,
                 backend_site_id=str(site),
                 attributes={
                     'nvidia.operation':
                     candidate['operation'],
                     'nvidia.timeline_mechanism':
                     candidate.get('timeline_mechanism')
                 }))
    observers, records, events = [], [], []
    mapping, streams = {}, defaultdict(list)
    decoded_observers = decoded.get('observers')
    if type(decoded_observers) is not list:
        raise ValueError('Decoded observer descriptors are required')
    for row in decoded_observers:
        key = (row.get('program'), row.get('warp'))
        if any(type(v) is not int or v < 0 for v in key) or key in mapping:
            raise ValueError('Invalid or duplicate decoded observer')
        program, warp = key
        if program >= grid[0] * grid[1] * grid[2]:
            raise ValueError('Observer belongs to a different launch grid')
        coordinates = [
            program % grid[0], (program // grid[0]) % grid[1],
            program // (grid[0] * grid[1])
        ]
        oid = stable_id(identity, 'observer', 'nvidia.recording_warp',
                        str(warp), coordinates)
        mapping[key] = oid
        observers.append(
            dict(
                id=oid,
                kind='nvidia.recording_warp',
                local_id=str(warp),
                program_coordinates=coordinates,
                # No shared epoch is inferred from a getter name or header SM ID.
                clock_domain_id=stable_id(identity,
                                          'unverified-observer-domain',
                                          program, warp),
                epoch_id=stable_id(identity, 'capture-epoch-unverified',
                                   program, warp),
                timer_bits=64,
                complete=row['complete'],
                overwritten_records=row['overwritten_records'],
                saturated=row['saturated'],
                written_records=row['written_records'],
                retained_records=row['retained_records'],
                physical_identity={'nvidia.finalize_smid': row['sm']},
                attributes={'nvidia.logical_program': program}))
    backend_records = {}
    if type(decoded.get('complete')) is not bool or decoded['complete'] != all(
            o['complete'] for o in observers):
        raise ValueError(
            'Decoded capture completeness disagrees with observer status')
    for row in decoded.get('records', []):
        key = (row.get('program'), row.get('warp'))
        if key not in mapping or row.get('site') not in site_ids:
            raise ValueError('Decoded record has no bound observer/site')
        rid = stable_id(identity, 'record', mapping[key], row['sequence'])
        backend_records[stable_id(identity, 'record', *key,
                                  row['sequence'])] = rid
        record = dict(id=rid,
                      observer_id=mapping[key],
                      site_id=site_ids[row['site']],
                      phase=row['phase'],
                      tick=row['tick'],
                      sequence=row['sequence'],
                      offset=row['raw_byte_offset'],
                      length=row['raw_byte_length'])
        records.append(record)
        streams[mapping[key]].append(record)
    from .timeline_nvidia_async import validate_shared_view_associations
    validate_shared_view_associations(decoded, plan)
    site_map = {site['id']: site for site in sites}
    for observer in observers:
        stream = sorted(streams[observer['id']], key=lambda r: r['sequence'])
        stack, occurrences = [], defaultdict(int)
        previous = None

        def emit(begin, end, occurrence, reason=None):
            actual = begin or end
            refs = [r['id'] for r in (begin, end) if r is not None]
            event = dict(id=stable_id(identity, 'event', *refs),
                         observer_id=observer['id'],
                         site_id=actual['site_id'],
                         semantic=site_map[actual['site_id']]['semantic'],
                         kind='interval' if begin is not None
                         and end is not None else 'incomplete',
                         start_tick=begin['tick'] if begin else None,
                         end_tick=end['tick'] if end else None,
                         occurrence=occurrence,
                         occurrence_basis='complete_entry_order' if
                         observer['complete'] else 'retained_boundary_order',
                         iteration_id=None,
                         record_ids=refs,
                         missing_reason=reason,
                         coverage='complete_observer_stream'
                         if observer['complete'] else 'retained_window')
            events.append(event)

        def invalidate(reason):
            while stack:
                begin, occurrence = stack.pop()
                emit(begin, None, occurrence, reason)

        for record in stream:
            if previous is not None and record['sequence'] != previous + 1:
                if observer['complete']:
                    raise ValueError(
                        'Complete NVIDIA observer lost record history')
                invalidate('missing_raw_history')
            previous = record['sequence']
            if record['phase'] == 'entry':
                occurrence = occurrences[record['site_id']]
                occurrences[record['site_id']] += 1
                stack.append((record, occurrence))
            elif record['phase'] == 'exit':
                if not stack or stack[-1][0]['site_id'] != record['site_id']:
                    if observer['complete']:
                        raise ValueError(
                            'Complete NVIDIA interval stream is not nested')
                    invalidate('missing_or_mismatched_exit_history')
                    occurrence = occurrences[record['site_id']]
                    occurrences[record['site_id']] += 1
                    emit(None, record, occurrence, 'entry_not_retained')
                else:
                    begin, occurrence = stack.pop()
                    emit(begin, record, occurrence)
            else:
                raise ValueError('NVIDIA ring has no point-record encoding')
        if stack and observer['complete']:
            raise ValueError('Complete NVIDIA stream has an unclosed region')
        invalidate('exit_not_retained')
    batch = dict(
        schema_version=1,
        identity=dict(
            zip(('capture_id', 'invocation_id', 'binary_id'), identity)),
        raw_artifact=dict(sha256=raw_sha256, bytes=raw_bytes),
        clock_status='unverified',
        boundary_status='unverified',
        sources=list(sources.values()),
        sites=sites,
        observers=observers,
        records=records,
        events=events,
        backend_record_map={
            ('nvidia.cp_async.shared_views.v2' if decoded['record_version'] == 3 else 'nvidia.cp_async.groups.v1'):
            backend_records
        },
        complete=all(o['complete'] for o in observers)
        and all(e['kind'] != 'incomplete' for e in events),
        notes=[
            'Occurrence is retained boundary order, not a proven loop iteration.',
            'Source links support navigation, not exact source cost attribution.',
            'Physical time units/epoch and final instruction boundaries are unverified.'
        ])
    return validate_raw_batch(batch)
