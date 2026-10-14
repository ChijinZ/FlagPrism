"""Raw SDK actor clocks with explicit invocation identity and bounded alignment.

DeviceProf is a replay artifact. This module never assigns it to a foreground
call by directory order, kernel name, or timestamp proximity.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
from .observations import observation

_SCHEMA_SOURCE = 'https://github.com/Ascend/msopprof/blob/b28488fa3ac6e42683bf2917c9d3149993942332/csrc/op_profiling/profiling/device/data_parse/data_bean.cpp'


def import_deviceprof(path, *, chip='910B', device_id=None, capture_id=None):
    """Read the public SDK A2 128-byte schema, preserving each replay separately.

    device/capture are not stored in these records and remain unknown unless
    the collector supplies their actual enclosing SDK capture identity.
    """
    if chip != '910B':
        raise ValueError('unsupported DeviceProf schema; explicitly select 910B')
    file = Path(path)
    data = file.read_bytes()
    if not data or len(data) % 128:
        raise ValueError('incomplete 910B DeviceProf records')
    digest = hashlib.sha256(data).hexdigest()
    records = []
    for offset in range(0, len(data), 128):
        hardware_stream, hardware_task = struct.unpack_from('<HH', data, offset + 4)
        if hardware_stream & 0x1000:
            stream = hardware_stream % 2048
            task = (hardware_task & 0x1fff) | (hardware_stream & 0xe000)
        elif hardware_stream & 0x2000:
            stream = hardware_task & 0xfff
            task = (hardware_task & 0xf000) | (hardware_stream & 0xfff)
        else:
            stream, task = hardware_stream % 2048, hardware_task
        bits = struct.unpack_from('<H', data, offset + 20)[0]
        subblock, program = struct.unpack_from('<HH', data, offset + 28)
        cycles = struct.unpack_from('<Q', data, offset + 32)[0]
        start, end = struct.unpack_from('<QQ', data, offset + 112)
        if end < start:
            raise ValueError(f'{file}:{offset}: decreasing task SYS timestamps')
        records.append({'capture_id': capture_id, 'device_id': device_id,
                        'stream_id': stream, 'task_id': task, 'program': program,
                        'actor_kind': 'AIV' if bits & 1 else 'AIC',
                        'subblock': subblock, 'physical_core': (bits >> 1) & 127,
                        'start_tick': start, 'end_tick': end, 'total_cycles': cycles,
                        'hardware_stream_id': hardware_stream, 'hardware_task_id': hardware_task,
                        'record_byte_offset': offset, 'raw_sha256': digest})
    return {'schema': 'msopprof.910B.ffts128', 'schema_source': _SCHEMA_SOURCE,
            'raw_path': str(file), 'raw_sha256': digest, 'records': records,
            'clock_domain': 'SDK.FftsBlockBean.startSystemTime',
            'replay_scope': 'one_raw_packet_file', 'foreground_association': 'unassociated'}


def read_hwts_frequency(info_path, *, device_id):
    """Frequency from the actual capture, never the PMU AIC/AIV frequency."""
    file = Path(info_path)
    value = json.loads(file.read_text())
    matches = [item for item in value.get('DeviceInfo', []) if item.get('id') == device_id]
    if len(matches) != 1:
        raise ValueError('device frequency identity is missing or ambiguous')
    from decimal import Decimal
    frequency = Decimal(str(matches[0]['hwts_frequency']))
    if not frequency.is_finite() or frequency <= 0:
        raise ValueError('invalid SDK hardware timestamp frequency')
    return {'tick_ns': float(Decimal(1000) / frequency), 'conversion_evidence': {
        'kind': 'sdk_capture_reported_hwts_frequency', 'device_id': device_id,
        'frequency_mhz': str(frequency), 'raw_path': str(file),
        'raw_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
        'limits': 'Reported frequency; no independent physical oscillator calibration.'}}


def align_same_call(events, packet, *, identity=None, frequency=None):
    """Attach shared epoch only after a collector supplies exact same-call proof.

    identity must bind this packet hash to the actual source invocation and
    native capture/device/stream/task/connection/scope. Time containment is a
    consistency check after that binding, never an invocation selector.
    """
    required = ('invocation_id', 'capture_id', 'device_id', 'stream_id', 'task_id',
                'connection_id', 'scope_id', 'packet_sha256', 'evidence',
                'counter_domain_evidence')
    if (not identity or any(identity.get(key) is None for key in required)
            or not isinstance(identity.get('evidence'), dict) or not identity['evidence']
            or not isinstance(identity.get('counter_domain_evidence'), dict)
            or not identity['counter_domain_evidence']):
        return {'status': 'unassociated', 'observations': list(events),
                'reason': 'missing explicit SDK packet to same-call identity proof'}
    if identity['packet_sha256'] != packet['raw_sha256']:
        raise ValueError('same-call identity names a different raw packet')
    by_actor = {}
    for record in packet['records']:
        if any(record.get(key) != identity[key] for key in ('capture_id', 'device_id', 'stream_id', 'task_id')):
            continue
        key = (record['program'], record['actor_kind'], record['subblock'])
        by_actor.setdefault(key, []).append(record)
    events = list(events)
    matches, verified_actors = {}, {}
    for index, event in enumerate(events):
        actor = event.get('actor_slot')
        key = (event.get('program'), 'AIC' if actor == 0 else 'AIV', 0 if actor == 0 else actor - 1) if type(actor) is int else None
        candidates = by_actor.get(key, [])
        if event.get('invocation_id') != identity['invocation_id'] or len(candidates) != 1:
            continue
        native = candidates[0]
        if not native['start_tick'] <= event['start_tick'] <= event['end_tick'] <= native['end_tick']:
            continue
        matches[index] = native
        verified_actors[key] = native
    if not matches:
        return {'status': 'partial', 'unknown_count': len(events),
                'observations': events, 'packet_sha256': packet['raw_sha256']}
    selected_programs = {key[0] for key in verified_actors}
    bound_actors = [records[0] for key, records in sorted(by_actor.items())
                    if key[0] in selected_programs and len(records) == 1]
    origin = min(record['start_tick'] for record in bound_actors)
    proof = {'kind': 'explicit_same_call_sdk_actor_sys_window',
             'invocation_id': identity['invocation_id'],
             'packet_sha256': packet['raw_sha256'], 'identity': dict(identity),
             'verified_actors': [dict(verified_actors[key]) for key in sorted(verified_actors)],
             'bound_native_actors': [dict(record) for record in bound_actors],
             'counter_domain_evidence': identity['counter_domain_evidence'],
             'schema_source': packet['schema_source'],
             'limits': 'Shared reported epoch requires the supplied same-call and counter-domain proof. Scalar control brackets are not engine busy time.'}
    clock = {'domain': 'ascend.SYS_CNT', 'scope': 'same_invocation',
             'alignment': 'verified_shared', 'alignment_evidence': proof,
             'origin_tick': origin, 'tick_ns': None, 'wrap_bits': 64}
    if frequency is not None:
        if frequency['conversion_evidence']['device_id'] != identity['device_id']:
            raise ValueError('frequency belongs to another device')
        clock.update(frequency)
    aligned = []
    for index, event in enumerate(events):
        if index not in matches:
            aligned.append(event)
            continue
        adapted = dict(event, clock=dict(clock), clock_alignment_event_evidence={
            'native_record': dict(matches[index]), 'containment': True,
            'packet_sha256': packet['raw_sha256']})
        aligned.append(observation(adapted))
    unknown = len(events) - len(matches)
    return {'status': 'partial' if unknown else 'verified_shared',
            'unknown_count': unknown, 'observations': aligned,
            'packet_sha256': packet['raw_sha256']}


def import_sdk_task_capture(capture_path):
    """Retain SDK parsed task/connection/time anchors as read-only evidence.

    SQLite task times are SDK-converted nanoseconds. They do not contain the
    original device SYS counts, so this importer cannot prove a SYS epoch join.
    """
    import sqlite3
    root = Path(capture_path).resolve()
    inputs, tasks, anchors = [], [], []
    def rows(path, table):
        if not path.exists():
            return []
        inputs.append({'path': str(path.relative_to(root)),
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        try:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute('SELECT * FROM "'+table+'"')]
        finally:
            connection.close()
    host = rows(root/'host/sqlite/runtime.db', 'HostTask')
    for directory in sorted(root.glob('device_*')):
        try:
            device = int(directory.name.removeprefix('device_'))
        except ValueError:
            continue
        frequency = read_hwts_frequency(directory/f'info.json.{device}', device_id=device)
        inputs.append({'path': str((directory/f'info.json.{device}').relative_to(root)),
                       'sha256': frequency['conversion_evidence']['raw_sha256']})
        for anchor in rows(directory/'sqlite/time.db','Time'):
            anchors.append({'capture_id': root.name, 'device_id': device,
                            'sdk_time_anchor': anchor, **frequency,
                            'sys_origin_verification': 'not_established'})
        for task in rows(directory/'sqlite/ascend_task.db','AscendTask'):
            matches = [entry for entry in host if all(entry.get(field) == task.get(field)
                       for field in ('stream_id','task_id','connection_id'))
                       and entry.get('device_id') == device]
            tasks.append({'capture_id': root.name, 'device_id': device,
                          'sdk_device_task': task,
                          'sdk_host_task': matches[0] if len(matches) == 1 else None,
                          'task_connection_status': 'verified_sdk_identity' if len(matches) == 1 else 'ambiguous' if matches else 'unassociated',
                          'clock_domain': 'cann.sdk.converted_nanoseconds',
                          'raw_sys_ticks': None})
    return {'schema_version': 1, 'capture_id': root.name, 'tasks': tasks,
            'clock_anchors': anchors, 'raw_inputs': inputs,
            'sys_clock_alignment': 'unverified',
            'limits': ['Host/device connection is matched by actual SDK identities.',
                       'SDK converted nanoseconds do not independently establish the source SYS_CNT origin.']}
