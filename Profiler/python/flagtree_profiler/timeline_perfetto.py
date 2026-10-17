"""Bounded standard Perfetto TrackEvent writer for isolated counter-ns views.

Wire fields follow Perfetto da1d152cff27890903d158fe96751de3aab883cc protos.
No runtime protobuf dependency or custom viewer is required. Tests use Google's
generated protobuf reader and the actual Trace Processor independently.
"""
import hashlib
import heapq
import json
import html
from pathlib import Path

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
    return _varint(field << 3)+_varint(value)


def _bytes(field, value):
    return _varint((field << 3) | 2)+_varint(len(value))+value


def _text(field, value):
    data = str(value).encode('utf-8')
    if len(data) > 65536:
        raise ValueError('Perfetto annotation exceeds its bounded string budget')
    return _bytes(field, data)


def _annotation(name, value):
    if type(value) is bool:
        payload = _uint(2, int(value))
    elif type(value) is int and 0 <= value < 1 << 63:
        payload = _uint(3, value)
    else:
        if value is None:
            value = 'unknown'
        elif type(value) in (dict, list, tuple):
            value = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        payload = _text(6, value)
    return _bytes(4, _text(10, name)+payload)


def validate_counter_view(view, canonical, proof):
    """Recompute from the provider's proof, never from untrusted view JSON.

    The caller must obtain that proof through its backend's evidence validator.
    This codec validates projection fidelity, not the hardware evidence itself.
    """
    if (type(view) is not dict or type(view.get('schema_version')) is not int or
            view['schema_version'] != 1):
        raise ValueError('Unknown counter ns view')
    if not isinstance(proof, CounterUnitProof):
        raise TypeError('Obtain unit evidence from the provider before rendering')
    expected = derive_counter_ns_views(canonical, [proof])
    if len(expected) != 1 or view != expected[0]:
        raise ValueError('Counter ns view differs from its canonical/proof projection')
    return expected[0]


def encode_counter_trace(view, canonical, *, proof, max_bytes=16*1024*1024):
    """Encode one observer; no clocks are aligned and no flows are invented.

    Same-site overlapping intervals occupy independent lanes, preserving every
    endpoint without violating Perfetto's begin/end stack. Raw append order is
    untouched; this is a separate chronological export projection.
    """
    view = validate_counter_view(view, canonical, proof)
    _integer(max_bytes, 'Perfetto byte budget', 1, 64*1024*1024)
    output = bytearray()
    first = True
    def packet(payload, timestamp=None):
        nonlocal first
        value = _uint(10, 1)  # trusted_packet_sequence_id
        if first:
            value += _uint(13, 1)  # SEQ_INCREMENTAL_STATE_CLEARED
            first = False
        if timestamp is not None:
            _integer(timestamp, 'relative timestamp ns', 0, (1 << 63)-1)
            value += _uint(8, timestamp)+_uint(58, TRACE_FILE_CLOCK)
        value += payload
        encoded = _bytes(1, value)  # Trace.packet
        if len(output)+len(encoded) > max_bytes:
            raise ValueError('Perfetto trace exceeds byte budget; originals remain intact')
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
            descriptor = _uint(1, uuid)+_text(2, name)
            if parent is not None:
                descriptor += _uint(5, parent)
            packet(_bytes(60, descriptor))
        return uuid

    identity = view['identity']
    observer = view['observer']
    namespace = ':'.join([identity['capture_id'], identity['invocation_id'], observer['id']])
    root = track(namespace, identity['invocation_id']+' — isolated counter ns')
    observer_track = track(namespace+':observer',
        'program '+str(observer['program_coordinates'])+' / '+observer['kind']+' '+observer['local_id'], root)
    sites = {row['id']: row for row in view['sites']}
    sources = {row['id']: row for row in view['sources']}
    records = {row['id']: row for row in view['records']}
    assignments, lanes, lane_counts = {}, {}, {}
    ordered = sorted(view['events'], key=lambda e: (e['start_ns'], e['end_ns'] or e['start_ns'], e['id']))
    for event in ordered:
        key = (event['site_id'], event['semantic'])
        available = lanes.setdefault(key, [])
        if available and available[0][0] <= event['start_ns']:
            _, lane = heapq.heappop(available)
        else:
            lane = lane_counts.get(key, 0)
            lane_counts[key] = lane+1
        heapq.heappush(available, (event['end_ns'] if event['end_ns'] is not None else event['start_ns'], lane))
        assignments[event['id']] = (*key, lane)
    pending = []
    pending_bytes = 0
    ordinal = 0
    for event in ordered:
        site = sites[event['site_id']]
        lane = assignments[event['id']][2]
        tid = track(namespace+':'+site['id']+':'+str(lane),
                    event['semantic']+' / '+site['name']+' / lane '+str(lane), observer_track)
        refs = [records[key] for key in event['record_ids']]
        annotations = dict(event_id=event['id'], invocation_id=identity['invocation_id'],
            binary_id=identity['binary_id'], observer_id=observer['id'], site_id=site['id'],
            semantic=event['semantic'], time_quality='counter_unit_only_precision_unverified',
            source_boundary_status=view['source_boundary_status'],
            source_locations=[sources[key]['location'] for key in site['source_ids']],
            raw_sha256=view['raw_artifact']['sha256'], raw_record_ids=event['record_ids'],
            raw_offsets=[row['offset'] for row in refs],
            raw_ticks=[str(row['tick']) for row in refs], occurrence=event['occurrence'],
            iteration_id=event['iteration_id'], coverage=event['coverage'],
            missing_reason=event['missing_reason'], endpoint_error_ns=None,
            period_numerator_ns=view['unit_proof']['period_numerator_ns'],
            period_denominator=view['unit_proof']['period_denominator'],
            unit_provider=view['unit_proof']['provider'],
            unit_evidence_ids=view['unit_proof']['evidence_ids'])
        event_type = 1 if event['kind'] == 'interval' else 3
        label = ('counter bracket: ' if event_type == 1 else 'observed endpoint: ')+site['name']
        message = _uint(9, event_type)+_uint(11, tid)+_text(23, label)+_text(22, event['semantic'])
        for name, value in annotations.items():
            message += _annotation(name, value)
        estimate = len(message)+128
        if len(output)+pending_bytes+estimate > max_bytes:
            raise ValueError('Perfetto trace exceeds byte budget; originals remain intact')
        pending_bytes += estimate
        pending.append((event['start_ns'], tid, ordinal, _bytes(11, message)))
        ordinal += 1
        if event_type == 1:
            pending.append((event['end_ns'], tid, ordinal,
                            _bytes(11, _uint(9, 2)+_uint(11, tid))))
            ordinal += 1
    for timestamp, _, _, payload in sorted(pending):
        packet(payload, timestamp)
    return bytes(output)


def write_counter_exports(directory, prefix, views, canonical, *, proofs):
    """Retain derived inputs and standard traces; raw/canonical never change."""
    from .hooks.timeline import _persist
    directory, prefix = Path(directory), Path(prefix)
    by_observer = {}
    for proof in proofs:
        if not isinstance(proof, CounterUnitProof) or proof.observer_id in by_observer:
            raise ValueError('Invalid or duplicate provider proof')
        by_observer[proof.observer_id] = proof
    rows, total = [], 0
    for view in views:
        base = prefix.with_suffix('.counter-ns')/view['observer']['id']
        view_file, trace_file = base.with_suffix('.json'), base.with_suffix('.pftrace')
        data = encode_counter_trace(view, canonical, proof=by_observer[view['observer']['id']],
                                    max_bytes=16*1024*1024-total)
        total += len(data)
        _persist(directory/view_file, (json.dumps(view, indent=2)+'\n').encode())
        _persist(directory/trace_file, data)
        rows.append(dict(observer_id=view['observer']['id'],
            program_coordinates=view['observer']['program_coordinates'],
            view_file=str(view_file), trace_file=str(trace_file), bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(), clock_status='counter_unit_only',
            read_precision_status='unverified', time_arrows_verified=False))
    return rows


def write_trace_index(directory, capture_rows):
    """Local file index, linking standard traces rather than drawing a viewer."""
    from .hooks.timeline import _persist
    directory = Path(directory)
    links = []
    for row in capture_rows:
        capture = json.loads((directory/row['capture_file']).read_text())
        exports = capture.get('counter_ns_exports', [])
        for item in exports:
            label = row['invocation_id']+' / program '+str(item['program_coordinates'])+' / '+item['observer_id']
            links.append('<li><a href="'+html.escape(item['trace_file'], quote=True)+'">'+html.escape(label)+'</a></li>')
    body = ('<!doctype html><html><head><meta charset="utf-8"><title>Internal timeline files</title></head>'
        '<body><h1>Internal timeline files</h1><p>Each trace has an isolated observer-relative ns axis. '
        'Read precision and source-region boundaries remain unverified. These are counter brackets, '
        'not certified source costs or engine busy. Do not compare origins across files.</p>'
        '<p>Open a downloaded .pftrace in the standard <a href="https://ui.perfetto.dev/">Perfetto UI</a>. '
        'No data is uploaded by this index.</p><ul>'+''.join(links)+'</ul>'
        '<p><a href="index.json">Raw capture index and qualification status</a></p></body></html>')
    if not links:
        body = body.replace('<ul></ul>', '<p>Raw observations are retained; no ns trace is available.</p>')
    _persist(directory/'index.html', body.encode(), replace=True)
