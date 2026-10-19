"""Bounded standard Perfetto TrackEvent writer for isolated counter-ns views.

Wire fields follow Perfetto da1d152cff27890903d158fe96751de3aab883cc protos.
No runtime protobuf dependency or custom viewer is required. Tests use Google's
generated protobuf reader and the actual Trace Processor independently.
"""
from dataclasses import asdict
import hashlib
import heapq
import json
import html
import struct
from pathlib import Path

from . import timeline_views, timeline_clock, timeline_events
from .timeline_events import _integer
from .timeline_views import CounterUnitProof, derive_counter_ns_views

PERFETTO_SCHEMA_COMMIT = 'da1d152cff27890903d158fe96751de3aab883cc'
TRACE_FILE_CLOCK = 11  # BuiltinClock: a synthetic per-file axis, not BOOTTIME.


def _varint(value):
    _integer(value, 'protobuf uint64')
    data = bytearray()
    while value > 127:
        data.append((value & 127) | 128)
        value >>= 7
    data.append(value)
    return bytes(data)


def _uint(field, value):
    return _varint(field << 3) + _varint(value)


def _fixed64(field, value):
    _integer(value, 'protobuf fixed64')
    return _varint((field << 3) | 1) + struct.pack('<Q', value)


def _bytes(field, value):
    return _varint((field << 3) | 2) + _varint(len(value)) + value


def _text(field, value):
    data = str(value).encode('utf-8')
    if len(data) > 65536:
        raise ValueError(
            'Perfetto annotation exceeds its bounded string budget')
    return _bytes(field, data)


def _annotation(name, value, intern=None):
    if type(value) is bool:
        payload = _uint(2, int(value))
    elif type(value) is int and 0 <= value < 1 << 63:
        payload = _uint(3, value)
    else:
        if value is None:
            value = 'unknown'
        elif type(value) in (dict, list, tuple):
            value = json.dumps(value,
                               ensure_ascii=False,
                               separators=(',', ':'),
                               allow_nan=False)
        payload = _uint(17, intern(
            'string', str(value))) if intern is not None else _text(6, value)
    key = _uint(1, intern('name', name)) if intern is not None else _text(
        10, name)
    return _bytes(4, key + payload)


def validate_counter_view(view, canonical, proof):
    """Recompute from the provider's proof, never from untrusted view JSON.

    The caller must obtain that proof through its backend's evidence validator.
    This codec validates projection fidelity, not the hardware evidence itself.
    """
    if (type(view) is not dict or type(view.get('schema_version')) is not int
            or view['schema_version'] != 1):
        raise ValueError('Unknown counter ns view')
    if not isinstance(proof, CounterUnitProof):
        raise TypeError(
            'Obtain unit evidence from the provider before rendering')
    expected = derive_counter_ns_views(canonical, [proof])
    if len(expected) != 1 or view != expected[0]:
        raise ValueError(
            'Counter ns view differs from its canonical/proof projection')
    return expected[0]


def encode_counter_trace(view,
                         canonical,
                         *,
                         proof,
                         max_bytes=16 * 1024 * 1024):
    """Encode one observer; no clocks are aligned and no flows are invented.

    Same-site overlapping intervals occupy independent lanes, preserving every
    endpoint without violating Perfetto's begin/end stack. Raw append order is
    untouched; this is a separate chronological export projection.
    """
    view = validate_counter_view(view, canonical, proof)
    return _encode_counter_views([view], max_bytes=max_bytes)


def _encode_counter_views(views, *, max_bytes, shared=None, dependencies=None):
    _integer(max_bytes, 'Perfetto byte budget', 1, 64 * 1024 * 1024)
    output = bytearray()
    first = True
    names, strings = {}, {}
    interned_bytes = 0

    def intern(kind, value):
        nonlocal interned_bytes
        table = names if kind == 'name' else strings
        if value not in table:
            encoded = str(value).encode('utf-8')
            if len(encoded) > 65536 or len(table) >= 65536:
                raise ValueError('Perfetto interned string budget exceeded')
            interned_bytes += len(encoded) + 16
            if interned_bytes > max_bytes:
                raise ValueError(
                    'Perfetto interned table exceeds trace budget')
            table[value] = len(table) + 1
        return table[value]

    annotation_intern = intern if dependencies is not None else None

    def packet(payload, timestamp=None):
        nonlocal first
        value = _uint(10, 1)  # trusted_packet_sequence_id
        if first:
            value += _uint(13, 1)  # SEQ_INCREMENTAL_STATE_CLEARED
            first = False
        if timestamp is not None:
            if annotation_intern is not None:
                value += _uint(13, 2)  # SEQ_NEEDS_INCREMENTAL_STATE
            _integer(timestamp, 'relative timestamp ns', 0, (1 << 63) - 1)
            value += _uint(8, timestamp) + _uint(58, TRACE_FILE_CLOCK)
        value += payload
        encoded = _bytes(1, value)  # Trace.packet
        if len(output) + len(encoded) > max_bytes:
            raise ValueError(
                'Perfetto trace exceeds byte budget; originals remain intact')
        output.extend(encoded)

    # Declare the trace-file clock explicitly. No host/device ClockSnapshot or
    # cross-observer offset is fabricated. This clock is file-index scoped in TP.
    packet(_bytes(6, _uint(2, TRACE_FILE_CLOCK)))
    uuids = {}

    def track(key, name, parent=None):
        digest = hashlib.sha256(key.encode()).digest()
        uuid = int.from_bytes(digest[:8], 'little') or 1
        if uuid in uuids and uuids[uuid] != key:
            raise ValueError('Perfetto track UUID collision')
        if uuid not in uuids:
            uuids[uuid] = key
            descriptor = _uint(1, uuid) + _text(2, name)
            if parent is not None:
                descriptor += _uint(5, parent)
            packet(_bytes(60, descriptor))
        return uuid

    pending = []
    pending_bytes = 0
    ordinal = 0
    observer_tracks = {}
    for view in views:
        identity = view['identity']
        observer = view['observer']
        namespace = ':'.join([
            identity['capture_id'], identity['invocation_id'], observer['id']
        ])
        if shared is None:
            root = track(namespace,
                         identity['invocation_id'] + ' — isolated counter ns')
        else:
            root = track(
                shared['domain_id'], identity['invocation_id'] +
                ' / program ' + str(shared['program_coordinates']) +
                (' — single observer counter ns (precision unverified)'
                 if shared.get('clock_scope_kind') == 'single_observer' else
                 ' — shared counter ns (precision unverified)'))
        observer_track = track(
            namespace + ':observer',
            ('Observer ' + observer['local_id'] if dependencies is not None
             else 'program ' + str(observer['program_coordinates']) + ' / ' +
             observer['kind'] + ' ' + observer['local_id']), root)
        observer_tracks[observer['id']] = (namespace, observer_track)
        sites = {row['id']: row for row in view['sites']}
        sources = {row['id']: row for row in view['sources']}
        records = {row['id']: row for row in view['records']}

        def presentation(site):
            if shared is not None and shared.get(
                    'clock_scope_kind') != 'single_observer':
                return 'observer-order', 'Observed internal operations', False
            group = site.get('attributes', {}).get('display.track_group')
            if group is None:
                return site['id'], site['name'], False
            if type(group) is not str or not group or len(
                    group.encode('utf-8')) > 1024:
                raise ValueError(
                    'Display track group must be a bounded nonempty string')
            return 'display-group:' + json.dumps([site['semantic'], group
                                                  ]), group, True

        assignments, lanes, lane_counts = {}, {}, {}
        ordered = sorted(
            view['events'],
            key=lambda e:
            (e['start_ns'], e['end_ns'] or e['start_ns'], e['id']))
        for event in ordered:
            site = sites[event['site_id']]
            display_key, _, grouped = presentation(site)
            key = (display_key, event['semantic']
                   if shared is None else 'counter_observations')
            available = lanes.setdefault(key, [])
            if available and available[0][0] <= event['start_ns']:
                _, lane = heapq.heappop(available)
            else:
                lane = lane_counts.get(key, 0)
                lane_counts[key] = lane + 1
            occupied_until = event['end_ns'] if event[
                'end_ns'] is not None else event['start_ns']
            if grouped and occupied_until == event['start_ns']:
                # Give coincident points separate visual lanes without moving time.
                occupied_until += 1
            heapq.heappush(available, (occupied_until, lane))
            assignments[event['id']] = (*key, lane)
        for event in ordered:
            site = sites[event['site_id']]
            display_key, display_name, _ = presentation(site)
            lane = assignments[event['id']][2]
            tid = track(
                namespace + ':' + display_key + ':' + str(lane),
                ((event['semantic'] + ' / ') if shared is None else '') +
                display_name + ' / lane ' + str(lane), observer_track)
            refs = [records[key] for key in event['record_ids']]
            annotations = dict(
                event_id=event['id'],
                invocation_id=identity['invocation_id'],
                binary_id=identity['binary_id'],
                observer_id=observer['id'],
                site_id=site['id'],
                semantic=event['semantic'],
                time_quality=('counter_unit_only_precision_unverified'
                              if shared is None else
                              'shared_counter_epoch_precision_unverified'),
                source_boundary_status=view['source_boundary_status'],
                source_locations=[
                    sources[key]['location'] for key in site['source_ids']
                ],
                raw_sha256=view['raw_artifact']['sha256'],
                raw_record_ids=event['record_ids'],
                raw_offsets=[row['offset'] for row in refs],
                raw_ticks=[str(row['tick']) for row in refs],
                occurrence=event['occurrence'],
                iteration_id=event['iteration_id'],
                coverage=event['coverage'],
                missing_reason=event['missing_reason'],
                endpoint_error_ns=None,
                period_numerator_ns=view['unit_proof']['period_numerator_ns'],
                period_denominator=view['unit_proof']['period_denominator'],
                unit_provider=view['unit_proof']['provider'],
                unit_evidence_ids=view['unit_proof']['evidence_ids'])
            if shared is not None:
                annotations.update(counter_domain_id=shared['domain_id'],
                                   counter_epoch_id=shared['epoch_id'],
                                   shared_origin_tick=str(
                                       shared['origin_tick']),
                                   physical_temporal_comparison_verified=False,
                                   time_arrows_verified=False)
            if dependencies is not None:
                # Keep exact endpoints and source locations in the trace. The
                # complete repeated coverage/unit documents remain losslessly
                # available in the immutable canonical/dependency sidecars.
                annotations.pop('coverage')
                annotations[
                    'coverage_sha256'] = timeline_views.document_sha256(
                        event['coverage'])
                annotations.pop('unit_evidence_ids')
                annotations[
                    'unit_proof_sha256'] = timeline_views.document_sha256(
                        view['unit_proof'])
            event_type = 1 if event['kind'] == 'interval' else 3
            label = ('counter bracket: ' if event_type == 1 else
                     'observed endpoint: ') + site['name']
            message = _uint(9, event_type) + _uint(11, tid) + _text(
                23, label) + _text(22, event['semantic'])
            for name, value in annotations.items():
                message += _annotation(name, value, annotation_intern)
            estimate = len(message) + 128
            if len(output) + pending_bytes + estimate > max_bytes:
                raise ValueError(
                    'Perfetto trace exceeds byte budget; originals remain intact'
                )
            pending_bytes += estimate
            pending.append(
                (event['start_ns'], tid, ordinal, _bytes(11, message)))
            ordinal += 1
            if event_type == 1:
                pending.append((event['end_ns'], tid, ordinal,
                                _bytes(11,
                                       _uint(9, 2) + _uint(11, tid))))
                ordinal += 1
    if dependencies is not None:
        incoming, outgoing, flow_ids, incident = {}, {}, {}, {}
        dependency_digest = timeline_views.document_sha256(dependencies)
        for edge in dependencies['edges']:
            number = int.from_bytes(
                hashlib.sha256(edge['id'].encode()).digest()[:8],
                'little') or 1
            if number in flow_ids and flow_ids[number] != edge['id']:
                raise ValueError('Perfetto flow ID collision')
            flow_ids[number] = edge['id']
            outgoing.setdefault(edge['source'], []).append(number)
            incoming.setdefault(edge['target'], []).append(number)
            incident.setdefault(edge['source'], []).append(edge)
            incident.setdefault(edge['target'], []).append(edge)
        for node in dependencies['nodes']:
            namespace, parent = observer_tracks[node['observer_id']]
            tid = track(namespace + ':dependency-endpoints',
                        'Observed dependency checkpoints', parent)
            message = _uint(9, 3) + _uint(11, tid) + _text(
                23, node['label']) + _text(22, 'observed_dependency')
            for number in sorted(outgoing.get(node['id'], [])):
                message += _fixed64(47, number)
            for number in sorted(incoming.get(node['id'], [])):
                message += _fixed64(48, number)
            annotations = dict(
                node_id=node['id'],
                event_id=node['event_id'],
                observer_id=node['observer_id'],
                site_id=node['site_id'],
                raw_record_id=node['id'],
                raw_offset=node['raw_offset'],
                raw_length=node['raw_length'],
                raw_tick=str(node['tick']),
                occurrence=node['occurrence'],
                phase=node['phase'],
                source_locations=node['source_locations'],
                raw_sha256=dependencies['raw_artifact']['sha256'],
                invocation_id=dependencies['identity']['invocation_id'],
                counter_domain_id=dependencies['domain_id'],
                counter_epoch_id=dependencies['epoch_id'],
                dynamic_dependencies_verified=True,
                physical_temporal_comparison_verified=False,
                source_cost_qualified=False,
                hardware_busy_qualified=False,
                dependency_view_sha256=dependency_digest,
                dependency_relations=sorted(
                    set(('outgoing' if edge['source'] ==
                         node['id'] else 'incoming') + ': ' +
                        edge['relation'] + ' / ' + edge['display_label']
                        for edge in incident[node['id']])),
                outgoing_dependency_ids=[
                    flow_ids[n] for n in sorted(outgoing.get(node['id'], []))
                ],
                incoming_dependency_ids=[
                    flow_ids[n] for n in sorted(incoming.get(node['id'], []))
                ])
            evidence = [
                edge['attributes']['backend_evidence']
                for edge in incident[node['id']]
                if 'backend_evidence' in edge['attributes']
            ]
            if evidence:
                annotations['backend_evidence'] = evidence
            if dependencies.get('clock_scope_kind') == 'single_observer':
                annotations['clock_scope_kind'] = 'single_observer'
                annotations['observer_epoch_alignment_verified'] = False
            for name, value in annotations.items():
                message += _annotation(name, value, annotation_intern)
            # Base slice lanes and checkpoint lanes are independent. Equal-ns
            # dependency endpoints follow their verified DAG order, not UUIDs.
            pending.append((node['time_ns'], -1, node['topological_rank'],
                            _bytes(11, message)))
    if annotation_intern is not None:
        # Same trusted sequence, after its initial state reset and before any
        # referring event. These are standard Perfetto dictionaries, preserving
        # annotation names/values exactly rather than dropping repeated fields.
        dictionary = b''.join(
            _bytes(3,
                   _uint(1, iid) + _text(2, name))
            for name, iid in names.items())
        dictionary += b''.join(
            _bytes(29,
                   _uint(1, iid) + _text(2, value))
            for value, iid in strings.items())
        packet(_bytes(12, dictionary))
    for timestamp, _, _, payload in sorted(pending):
        packet(payload, timestamp)
    return bytes(output)


def write_counter_exports(directory, prefix, views, canonical, *, proofs):
    """Publish one immutable revision, bound to actual rules and provider input.

    No clock qualification is inferred here. Provider validation precedes this
    function; the codec independently checks each supplied projection.
    """
    from . import timeline_store
    directory = Path(directory)
    by_observer = {}
    for proof in proofs:
        if not isinstance(
                proof, CounterUnitProof) or proof.observer_id in by_observer:
            raise ValueError('Invalid or duplicate provider proof')
        by_observer[proof.observer_id] = proof
    files, rows, total = {
        'canonical.json': timeline_store.json_bytes(canonical)
    }, [], 0
    seen = set()
    # Provider enumeration order is not semantic. Keep receipts deterministic
    # for the same observer/proof set, including independent concurrent callers.
    for view in sorted(
            views,
            key=lambda item:
        (tuple(item['observer']['program_coordinates']), item['observer'][
            'kind'], item['observer']['local_id'], item['observer']['id'])):
        observer = view['observer']['id']
        if observer in seen or observer not in by_observer:
            raise ValueError(
                'Duplicate view or missing independently provided proof')
        seen.add(observer)
        # IDs are generated by the canonical contract; still validate them as
        # relative paths before constructing a derivative artifact filename.
        timeline_store.bundle_path(directory, observer)
        view_file, trace_file = 'views/' + observer + '.json', 'traces/' + observer + '.pftrace'
        data = encode_counter_trace(view,
                                    canonical,
                                    proof=by_observer[observer],
                                    max_bytes=16 * 1024 * 1024 - total)
        total += len(data)
        files[view_file] = timeline_store.json_bytes(view)
        files[trace_file] = data
        rows.append(
            dict(observer_id=observer,
                 invocation_id=canonical['identity']['invocation_id'],
                 program_coordinates=view['observer']['program_coordinates'],
                 view_file=view_file,
                 trace_file=trace_file,
                 bytes=len(data),
                 sha256=hashlib.sha256(data).hexdigest(),
                 clock_status='counter_unit_only',
                 read_precision_status='unverified',
                 time_arrows_verified=False))
    if not rows:
        return []
    # Rule identities depend on installed implementation bytes as well as
    # human-readable versions. Deployment paths do not enter the identity.
    modules = {
        'exporter': Path(__file__),
        'store': Path(timeline_store.__file__),
        'views': Path(timeline_views.__file__),
        'clock': Path(timeline_clock.__file__),
        'events': Path(timeline_events.__file__)
    }
    inputs = dict(schema_version=1,
                  kind='isolated_counter_ns',
                  identity=canonical['identity'],
                  canonical_sha256=timeline_views.document_sha256(canonical),
                  raw_artifact=canonical['raw_artifact'],
                  proofs=[asdict(by_observer[key]) for key in sorted(seen)],
                  implementation_sha256={
                      key: hashlib.sha256(path.read_bytes()).hexdigest()
                      for key, path in sorted(modules.items())
                  },
                  perfetto_schema_commit=PERFETTO_SCHEMA_COMMIT)
    with timeline_store.export_lock(directory):
        rows = timeline_store.publish_revision(directory, inputs, files, rows)
        _write_committed_index(directory)
    return rows


def _write_committed_index(directory):
    """Called under the same lock as receipt publication, including retries."""
    from .timeline_store import committed_exports, persist
    links = []
    entries = committed_exports(directory)
    for item in entries:
        label = item['invocation_id'] + ' / program ' + str(
            item['program_coordinates']) + ' / ' + (
                'observed dependency timeline ' if item.get('view_kind') ==
                'observed_dynamic_dependencies_ns' else 'shared counter group '
                if item.get('observer_ids') else '') + item['observer_id']
        links.append('<li><a href="' +
                     html.escape(item['trace_file'], quote=True) + '">' +
                     html.escape(label) + '</a>'
                     ' <small>revision ' +
                     html.escape(item['revision_id'][:12]) + '</small></li>')
    body = (
        '<!doctype html><html><head><meta charset="utf-8"><title>Internal timeline files</title></head>'
        '<body><h1>Internal timeline files</h1><p>Each trace has an isolated observer-relative ns axis. '
        'Read precision and source-region boundaries remain unverified. These are counter brackets, '
        'not certified source costs or engine busy. Do not compare origins across files.</p>'
        '<p>Open a downloaded .pftrace in the standard <a href="https://ui.perfetto.dev/">Perfetto UI</a>. '
        'No data is uploaded by this index.</p><ul>' + ''.join(links) + '</ul>'
        '<p><a href="index.json">Raw capture index and qualification status</a></p></body></html>'
    )
    if any(item.get('observer_ids') for item in entries):
        body = body.replace(
            'Each trace has an isolated observer-relative ns axis.',
            'Isolated traces have observer-local origins. Shared counter groups use one verified '
            'counter epoch and origin within their stated invocation/program scope; read precision remains unknown.'
        )
    if not links:
        body = body.replace(
            '<ul></ul>',
            '<p>Raw observations are retained; no ns trace is available.</p>')
    persist(directory, 'index.html', body.encode(), replace=True)


def write_trace_index(directory, capture_rows):
    """Rebuild from committed receipts, never from a stale capture-row list.

    The second argument remains for collection-hook compatibility; the raw
    capture index and its historical rows remain independently retained.
    """
    from .timeline_store import export_lock
    with export_lock(directory):
        _write_committed_index(directory)


def encode_shared_counter_trace(view,
                                canonical,
                                *,
                                proof,
                                max_bytes=16 * 1024 * 1024):
    from .timeline_shared import validate_shared_counter_view
    view = validate_shared_counter_view(view, canonical, proof)
    leaves = [
        dict(view,
             observer=observer,
             records=[
                 r for r in view['records']
                 if r['observer_id'] == observer['id']
             ],
             events=[
                 e for e in view['events']
                 if e['observer_id'] == observer['id']
             ]) for observer in view['observers']
    ]
    return _encode_counter_views(leaves, max_bytes=max_bytes, shared=view)


def write_shared_counter_exports(directory, canonical, proofs):
    """Publish scoped shared-counter traces, with precision explicitly unknown."""
    from . import timeline_store, timeline_shared
    from .timeline_shared import derive_shared_counter_view, SharedCounterProof
    files = {'canonical.json': timeline_store.json_bytes(canonical)}
    if type(proofs) not in (list, tuple) or len(proofs) > 128:
        raise ValueError('Expected bounded shared counter proof set')
    rows, used, domains, total = [], set(), set(), 0
    for proof in sorted(proofs,
                        key=lambda p: (p.program_coordinates, p.domain_id)):
        if not isinstance(proof, SharedCounterProof):
            raise TypeError(
                'Shared trace requires a validated counter-domain proof')
        if proof.domain_id in domains:
            raise ValueError('Shared counter domain identity reused')
        domains.add(proof.domain_id)
        if used.intersection(proof.observer_ids):
            raise ValueError(
                'Shared trace observer appears in overlapping proof scopes')
        used.update(proof.observer_ids)
        view = derive_shared_counter_view(canonical, proof)
        payload = encode_shared_counter_trace(view,
                                              canonical,
                                              proof=proof,
                                              max_bytes=16 * 1024 * 1024 -
                                              total)
        total += len(payload)
        view_file = 'views/' + proof.domain_id + '.json'
        trace_file = 'traces/' + proof.domain_id + '.pftrace'
        files[view_file] = timeline_store.json_bytes(view)
        files[trace_file] = payload
        rows.append(
            dict(observer_id=proof.domain_id,
                 observer_ids=list(proof.observer_ids),
                 invocation_id=proof.invocation_id,
                 program_coordinates=list(proof.program_coordinates),
                 view_file=view_file,
                 trace_file=trace_file,
                 bytes=len(payload),
                 sha256=hashlib.sha256(payload).hexdigest(),
                 clock_status='shared_counter_epoch_precision_unverified',
                 read_precision_status='unverified',
                 time_arrows_verified=False))
    if not rows:
        return []
    inputs = dict(
        schema_version=2,
        kind='single_program_shared_counter_ns',
        identity=canonical['identity'],
        canonical_sha256=timeline_views.document_sha256(canonical),
        raw_artifact=canonical['raw_artifact'],
        proofs=[asdict(p) for p in sorted(proofs, key=lambda p: p.domain_id)],
        implementation_sha256={
            'clock':
            hashlib.sha256(Path(
                timeline_clock.__file__).read_bytes()).hexdigest(),
            'events':
            hashlib.sha256(Path(
                timeline_events.__file__).read_bytes()).hexdigest(),
            'views':
            hashlib.sha256(Path(
                timeline_views.__file__).read_bytes()).hexdigest(),
            'exporter':
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'shared_projection':
            hashlib.sha256(Path(
                timeline_shared.__file__).read_bytes()).hexdigest(),
            'store':
            hashlib.sha256(Path(
                timeline_store.__file__).read_bytes()).hexdigest()
        },
        perfetto_schema_commit=PERFETTO_SCHEMA_COMMIT)
    with timeline_store.export_lock(directory):
        rows = timeline_store.publish_revision(directory, inputs, files, rows)
        _write_committed_index(directory)
    return rows
