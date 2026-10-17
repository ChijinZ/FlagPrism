"""Canonical raw time events shared by backend adapters and future exporters.

Validation proves identity, references, pairing and raw bounds. It does not
certify clocks, machine boundaries, engine activity or source cost attribution.
Raw tick fields remain integers; a certified ns view must be derived separately.
"""
import copy
import hashlib
import json

SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = (1, 2)
SEMANTICS = frozenset({'observer_region_elapsed', 'issue_interval', 'wait_bracket',
                      'completion_checkpoint', 'native_engine_activity'})


def stable_id(identity, kind, *parts):
    payload = json.dumps([*identity, kind, *parts], ensure_ascii=False,
                         separators=(',', ':')).encode()
    return kind + '-' + hashlib.sha256(payload).hexdigest()


def _text(value, name):
    if type(value) is not str or not value:
        raise ValueError(f'{name} must be a nonempty string')
    return value


def _integer(value, name, low=0, high=(1 << 64)-1):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in [{low}, {high}]')
    return value


def _sha(value):
    if (type(value) is not str or len(value) != 64 or
            any(c not in '0123456789abcdef' for c in value)):
        raise ValueError('Invalid raw/source SHA256')
    return value


def _table(rows, name):
    if type(rows) is not list:
        raise ValueError(name + ' must be an array')
    table = {}
    for row in rows:
        if type(row) is not dict:
            raise ValueError(name + ' contains an invalid object')
        key = _text(row.get('id'), name + '.id')
        if key in table:
            raise ValueError(name + ' contains duplicate identities')
        table[key] = row
    return table


def _keys(row, allowed):
    if set(row) - set(allowed.split()):
        raise ValueError('Unknown required canonical field; use a versioned schema')


def _refs(value, table):
    return (type(value) is list and all(type(v) is str for v in value) and
            len(set(value)) == len(value) and all(v in table for v in value))


def _attributes(value):
    if type(value) is not dict or any(type(k) is not str or '.' not in k for k in value):
        raise ValueError('Descriptive backend attributes require explicit namespaces')


def validate_raw_batch(batch, *, max_records=65536, max_events=32768):
    """Validate a backend-independent document and return an isolated snapshot.

    A raw-complete stream can still have unverified physical timing. Missing
    history never creates an end or a loop iteration. Unknown physical identity
    is nullable; the common contract does not require a vendor topology tree.
    """
    _integer(max_records, 'max_records', 1)
    _integer(max_events, 'max_events', 1)
    if (type(batch) is not dict or type(batch.get('schema_version')) is not int or
            batch['schema_version'] not in SUPPORTED_SCHEMA_VERSIONS):
        raise ValueError('Unsupported canonical raw event schema')
    version = batch['schema_version']
    _keys(batch, 'schema_version identity raw_artifact clock_status boundary_status sources sites observers records events complete notes backend_record_map')
    identity = batch.get('identity')
    if type(identity) is not dict:
        raise ValueError('Canonical capture identity is missing')
    _keys(identity, 'capture_id invocation_id binary_id')
    for key in ('capture_id', 'invocation_id', 'binary_id'):
        _text(identity.get(key), key)
    namespace = tuple(identity[k] for k in ('capture_id', 'invocation_id', 'binary_id'))
    artifact = batch.get('raw_artifact')
    if type(artifact) is not dict:
        raise ValueError('Raw artifact identity is missing')
    _keys(artifact, 'sha256 bytes')
    _sha(artifact.get('sha256'))
    raw_size = _integer(artifact.get('bytes'), 'raw artifact bytes')
    if batch.get('clock_status') != 'unverified' or batch.get('boundary_status') != 'unverified':
        raise ValueError('Raw validation cannot authorize clock/boundary certification')
    sources = _table(batch.get('sources'), 'sources')
    sites = _table(batch.get('sites'), 'sites')
    observers = _table(batch.get('observers'), 'observers')
    records = _table(batch.get('records'), 'records')
    events = _table(batch.get('events'), 'events')
    if len(records) > max_records or len(events) > max_events:
        raise ValueError('Canonical event/record budget exceeded')
    for source in sources.values():
        _keys(source, 'id source_sha256 relation location provenance')
        if source.get('source_sha256') is not None:
            _sha(source['source_sha256'])
        if source.get('relation') != 'compiler_origin_navigation':
            raise ValueError('Source navigation does not establish precise execution cost')
    for site in sites.values():
        _keys(site, 'id name semantic source_ids backend_site_id attributes')
        _text(site.get('name'), 'site name')
        _attributes(site.get('attributes', {}))
        _text(site.get('backend_site_id'), 'backend site identity')
        if site['id'] != stable_id((identity['binary_id'],), 'site', site['backend_site_id']):
            raise ValueError('Site identity belongs to a different binary')
        if site.get('semantic') not in SEMANTICS:
            raise ValueError('Unknown required time semantic')
        refs = site.get('source_ids')
        if not _refs(refs, sources):
            raise ValueError('Site has invalid source references')
    for observer in observers.values():
        common = 'id kind local_id clock_domain_id epoch_id timer_bits complete overwritten_records saturated program_coordinates physical_identity attributes retained_records'
        _keys(observer, common + (' written_records' if version == 1 else
              ' attempted_records committed_records dropped_records filtered_records record_order'))
        _attributes(observer.get('attributes', {}))
        if observer.get('physical_identity') is not None:
            _attributes(observer['physical_identity'])
        for key in ('kind', 'local_id', 'clock_domain_id', 'epoch_id'):
            _text(observer.get(key), key)
        _integer(observer.get('timer_bits'), 'timer_bits', 1, 64)
        if type(observer.get('complete')) is not bool:
            raise ValueError('Observer completeness must be explicit')
        for field in ('overwritten_records', 'retained_records'):
            _integer(observer.get(field), field)
        if type(observer.get('saturated')) is not bool:
            raise ValueError('Observer saturation must be explicit')
        if version == 1:
            _integer(observer.get('written_records'), 'written_records')
            if observer['retained_records'] > observer['written_records']:
                raise ValueError('Observer retained count exceeds its written count')
            if observer['complete'] and observer['retained_records'] != observer['written_records']:
                raise ValueError('Complete observer cannot have missing written records')
            lost = observer['overwritten_records']
        else:
            for field in ('attempted_records', 'committed_records', 'dropped_records', 'filtered_records'):
                _integer(observer.get(field), field)
            if observer.get('record_order') not in ('endpoint_stream', 'paired_endpoints'):
                raise ValueError('Unknown canonical endpoint ordering')
            if (observer['committed_records'] < observer['overwritten_records'] or
                    observer['retained_records'] != observer['committed_records']-observer['overwritten_records']):
                raise ValueError('Retained/committed/overwritten counts disagree')
            accounted = observer['committed_records']+observer['dropped_records']+observer['filtered_records']
            if not observer['saturated'] and observer['attempted_records'] != accounted:
                raise ValueError('Attempted/committed/dropped/filtered counts disagree')
            if observer['saturated'] and observer['attempted_records'] < observer['retained_records']:
                raise ValueError('Reported saturated attempts cannot be below retained records')
            lost = observer['overwritten_records']+observer['dropped_records']
        if observer['complete'] and (lost or observer['saturated']):
            raise ValueError('Lost observer cannot claim completeness')
        coordinates = observer.get('program_coordinates')
        if type(coordinates) is not list:
            raise ValueError('Program coordinates must be an explicit array')
        for coordinate in coordinates:
            _integer(coordinate, 'program coordinate')
        if observer['id'] != stable_id(namespace, 'observer', observer['kind'],
                                      observer['local_id'], coordinates):
            raise ValueError('Observer identity belongs to a different invocation')
    sequences, spans = {}, []
    by_observer = {key: [] for key in observers}
    for record in records.values():
        _keys(record, 'id observer_id site_id phase tick sequence offset length')
        observer_id = record.get('observer_id')
        site_id = record.get('site_id')
        if observer_id not in observers or site_id not in sites:
            raise ValueError('Record has a dangling observer/site')
        observer = observers[observer_id]
        _integer(record.get('tick'), 'raw tick', 0, (1 << observer['timer_bits'])-1)
        sequence = _integer(record.get('sequence'), 'record sequence')
        if record['id'] != stable_id(namespace, 'record', observer_id, sequence):
            raise ValueError('Raw record identity is not invocation bound')
        key = (observer_id, sequence)
        if key in sequences:
            raise ValueError('Observer aliases raw record sequence')
        sequences[key] = record
        by_observer[observer_id].append(record)
        offset = _integer(record.get('offset'), 'raw offset')
        length = _integer(record.get('length'), 'raw length', 1)
        if offset + length > raw_size:
            raise ValueError('Raw record extends past artifact bounds')
        spans.append((offset, offset+length))
        if record.get('phase') not in ('entry', 'exit', 'point'):
            raise ValueError('Invalid raw record phase')
    spans.sort()
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError('Canonical record byte spans overlap')
    positions = {}
    for observer_id, observer in observers.items():
        ordered = sorted(by_observer[observer_id], key=lambda r: r['sequence'])
        if len(ordered) != observer['retained_records']:
            raise ValueError('Canonical observer count disagrees with its records')
        pair_order = version == 2 and observer['record_order'] == 'paired_endpoints'
        if pair_order:
            if len(ordered) % 2 or any(
                    left['phase'] != 'entry' or right['phase'] != 'exit' or
                    left['sequence'] % 2 or right['sequence'] != left['sequence']+1 or
                    left['site_id'] != right['site_id'] or left['tick'] > right['tick']
                    for left, right in zip(ordered[::2], ordered[1::2])):
                raise ValueError('Invalid atomic pair endpoint order')
            # An appended pair is published after its end read. An enclosing
            # interval may start earlier than a previously appended inner pair.
            ends = ordered[1::2]
            if any(a['tick'] > b['tick'] for a, b in zip(ends, ends[1:])):
                raise ValueError('Pair completion clock regressed')
        elif any(a['tick'] > b['tick'] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('Observer raw timer regressed')
        if observer['complete'] and [r['sequence'] for r in ordered] != list(range(len(ordered))):
            raise ValueError('Complete observer has missing history')
        for index, record in enumerate(ordered):
            positions[record['id']] = index
    interval_pairs, used_records = set(), set()
    occurrence_groups = {}
    for event in events.values():
        _keys(event, 'id observer_id site_id semantic kind start_tick end_tick occurrence occurrence_basis iteration_id record_ids missing_reason coverage')
        observer_id = event.get('observer_id')
        site_id = event.get('site_id')
        if observer_id not in observers or site_id not in sites:
            raise ValueError('Event has dangling execution identity')
        if event.get('semantic') != sites[site_id]['semantic']:
            raise ValueError('Event changed the manifest semantic')
        if event.get('iteration_id') is not None:
            raise ValueError('This raw event schema does not infer loop iteration IDs')
        _integer(event.get('occurrence'), 'retained occurrence')
        pair_order = version == 2 and observers[observer_id]['record_order'] == 'paired_endpoints'
        bases = (('complete_pair_order', 'retained_pair_order') if pair_order else
                 ('complete_entry_order', 'complete_boundary_order', 'retained_entry_order', 'retained_boundary_order'))
        if event.get('occurrence_basis') not in bases:
            raise ValueError('Unknown occurrence basis')
        refs = event.get('record_ids')
        if not refs or not _refs(refs, records):
            raise ValueError('Event has invalid raw record references')
        points = [records[r] for r in refs]
        if used_records.intersection(refs):
            raise ValueError('A raw boundary was assigned to multiple events')
        used_records.update(refs)
        if event['id'] != stable_id(namespace, 'event', *refs):
            raise ValueError('Event identity is not bound to its raw boundaries')
        occurrence_groups.setdefault((observer_id, site_id), []).append(event)
        if any(p['observer_id'] != observer_id or p['site_id'] != site_id for p in points):
            raise ValueError('Event crosses observer/site identity')
        kind = event.get('kind')
        if pair_order and (kind != 'interval' or len(points) != 2 or
                           points[0]['sequence'] % 2 or points[1]['sequence'] != points[0]['sequence']+1):
            raise ValueError('Event crosses atomic pair boundaries')
        start, end = event.get('start_tick'), event.get('end_tick')
        if start is not None:
            _integer(start, 'interval start tick')
        if end is not None:
            _integer(end, 'interval end tick')
        if kind == 'interval':
            if (len(points) != 2 or points[0]['phase'] != 'entry' or points[1]['phase'] != 'exit' or
                    start != points[0]['tick'] or end != points[1]['tick'] or
                    type(start) is not int or type(end) is not int or end < start or
                    points[0]['sequence'] >= points[1]['sequence']):
                raise ValueError('Interval endpoints disagree with actual raw boundaries')
            if points[1]['sequence'] - points[0]['sequence'] != positions[refs[1]] - positions[refs[0]]:
                raise ValueError('An interval cannot cross missing raw history')
            key = tuple(refs)
            if key in interval_pairs:
                raise ValueError('Duplicated duration from the same physical boundaries')
            interval_pairs.add(key)
        elif kind == 'incomplete':
            if len(points) != 1:
                raise ValueError('Incomplete interval needs one actual endpoint and a reason')
            _text(event.get('missing_reason'), 'missing endpoint reason')
            point = points[0]
            if (point['phase'] == 'entry' and (start != point['tick'] or end is not None) or
                    point['phase'] == 'exit' and (start is not None or end != point['tick']) or
                    point['phase'] == 'point'):
                raise ValueError('Incomplete interval synthesized an endpoint')
        elif kind == 'instant':
            if len(points) != 1 or points[0]['phase'] != 'point' or start != points[0]['tick'] or end is not None:
                raise ValueError('Instant must reference an actual point record')
        else:
            raise ValueError('Unknown canonical event kind')
    if used_records != set(records):
        raise ValueError('Canonical events silently discarded raw records')
    for group in occurrence_groups.values():
        ordered = sorted(group, key=lambda e: records[e['record_ids'][0]]['sequence'])
        if [e['occurrence'] for e in ordered] != list(range(len(ordered))):
            raise ValueError('Occurrence is not actual retained boundary order')
    backend_map = batch.get('backend_record_map', {})
    if type(backend_map) is not dict:
        raise ValueError('Backend record maps must have explicit namespaces')
    for name, refs in backend_map.items():
        if type(name) is not str or '.' not in name or type(refs) is not dict:
            raise ValueError('Invalid backend record namespace')
        if any(type(k) is not str or v not in records for k, v in refs.items()):
            raise ValueError('Backend record map has dangling canonical references')
    complete = batch.get('complete')
    if type(complete) is not bool or complete != (
            all(o['complete'] for o in observers.values()) and
            all(e['kind'] != 'incomplete' for e in events.values())):
        raise ValueError('Batch completeness disagrees with retained event coverage')
    # JSON validates finite, bounded description values without serializing any
    # device resource. No arbitrary class is retained in an accepted batch.
    payload = json.dumps(batch, allow_nan=False).encode()
    if len(payload) > 16 * 1024 * 1024:
        raise ValueError('Canonical raw document exceeds its 16 MiB budget')
    return copy.deepcopy(batch)
