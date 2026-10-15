"""Raw SYS extraction contracts; execute only in a backend Docker."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import types

import pytest


def load():
    directory = Path(
        __file__).resolve().parents[1] / 'python/flagtree_profiler'
    name = 'cann_raw_sys_contract_package'
    package = types.ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package
    spec = importlib.util.spec_from_file_location(
        name + '.cann_raw_sys', directory / 'cann_raw_sys.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def record(kind, tick, stream=0, task=0):
    return struct.pack('=4HQHH11L', kind, 0, stream, task, tick, 0, 0,
                       *([0] * 11))


def prepare(tmp_path):
    spec = importlib.util.spec_from_file_location(
        'cann_joint_raw_fixture',
        Path(__file__).with_name('test_cann_joint.py'))
    fixture_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture_module)
    capture, receipt = fixture_module.fixture(tmp_path)
    device_info = {
        'platform_version': '5',
        'DeviceInfo': [{
            'id': 4,
            'ctrl_cpu_endian_little': 1
        }]
    }
    (capture / 'device_4/info.json.4').write_text(json.dumps(device_info))
    seal = json.loads(receipt['sdk_capture_binding_evidence'])
    seal['device_info_snapshot'] = device_info
    receipt['sdk_capture_binding_evidence'] = json.dumps(seal)
    receipts = tmp_path / 'capture.cann-launch-receipts.json'
    receipts.write_text(
        json.dumps({
            'schema_version': 1,
            'receipts': [receipt]
        }))
    data = capture / 'device_4/data'
    data.mkdir()
    raw = data / 'stars_soc.data.4.slice_0'
    raw.write_bytes(record(0, 100) + record(1, 120))
    module = load()
    schema = tmp_path / 'sdk_analysis'
    for name in module._SCHEMA_FILES:
        path = schema / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# Contract fixture; not hardware evidence.\n')
    (schema / module._SCHEMA_FILES[0]).write_text(
        "class StructFmt:\n    BYTE_ORDER_CHAR = '='\n    ACSQ_TASK_FMT = '4HQHH11L'\n"
    )
    return module, capture, receipts, raw, schema


def test_original_zero_task_sys_bytes_do_not_certify_alignment(tmp_path):
    module, capture, receipts, raw, schema = prepare(tmp_path)
    output = module.build_raw_task_sys(capture, receipts, schema)
    envelope = output['task_sys_envelopes'][0]
    assert envelope['status'] == 'raw_task_envelope_extracted'
    assert envelope['duration_scope'] == 'whole_dispatch_not_compute_or_actor'
    assert envelope['start']['raw_sys_counter'] == 100
    assert envelope['end']['raw_sys_counter'] == 120
    assert bytes.fromhex(
        envelope['start']['raw_record_hex']) == raw.read_bytes()[:64]
    assert envelope['end']['byte_offset'] == 64
    assert output['clock_status'] == envelope['clock_alignment'] == 'unverified'
    assert output['receipt_sha256'] and len(
        output['schema']['sources']) == len(module._SCHEMA_FILES)


@pytest.mark.parametrize('payload,reason', [
    (record(0, 100), 'missing or ambiguous'),
    (record(0, 100) + record(0, 110) + record(1, 120), 'missing or ambiguous'),
    (record(0, 100) + record(1, 120) + record(1, 130), 'missing or ambiguous'),
    (record(0, 120) + record(1, 100), 'reverses or wraps'),
    (record(0, 100) + b'bad', 'truncated'),
    (record(40, 100) + record(1, 120), '128-byte'),
    (record(0, 100, stream=4096) + record(1, 120), 'expanded'),
    (record(0, 100, stream=1) + record(1, 120, stream=1),
     'missing or ambiguous'),
])
def test_raw_negative_cases_do_not_upgrade_task_clock(tmp_path, payload,
                                                      reason):
    module, capture, receipts, raw, schema = prepare(tmp_path)
    raw.write_bytes(payload)
    result = module.build_raw_task_sys(capture, receipts,
                                       schema)['task_sys_envelopes'][0]
    assert result['status'] == 'unassociated' and reason in result['reason']
    assert result['clock_alignment'] == 'unverified'


def test_wrong_worker_identity_cannot_be_rescued_by_exact_sys_ticks(tmp_path):
    module, capture, receipts, raw, schema = prepare(tmp_path)
    document = json.loads(receipts.read_text())
    document['receipts'][0]['worker']['thread_id'] = 99
    receipts.write_text(json.dumps(document))
    result = module.build_raw_task_sys(capture, receipts,
                                       schema)['task_sys_envelopes'][0]
    assert result['status'] == 'unassociated'
    assert 'start' not in result


def test_native_alignment_format_is_rejected(tmp_path):
    module, capture, receipts, raw, schema = prepare(tmp_path)
    (schema / module._SCHEMA_FILES[0]
     ).write_text("BYTE_ORDER_CHAR = '@'\nACSQ_TASK_FMT = '4HQHH11L'\n")
    with pytest.raises(ValueError, match='unsupported installed'):
        module.build_raw_task_sys(capture, receipts, schema)


def test_sdk_nonexpanded_bit13_swap_retains_original_fields(tmp_path):
    module, capture, receipts, raw, schema = prepare(tmp_path)
    # Encoded low task0 in stream bit13, physical stream0 in task field.
    raw.write_bytes(
        record(0, 100, stream=0x2000, task=0) +
        record(1, 120, stream=0x2000, task=0))
    output = module.build_raw_task_sys(capture, receipts, schema)
    entry = output['task_sys_envelopes'][0]
    assert entry['status'] == 'raw_task_envelope_extracted'
    assert entry['start']['encoded_stream_id'] == 0x2000
    assert entry['start']['stream_id'] == entry['start']['task_id'] == 0
    assert entry['stream_encoding']['expand_status'] == 0
    assert entry['duration_scope'] == 'whole_dispatch_not_compute_or_actor'


@pytest.mark.parametrize('values', [(1, ), (0, 1)])
def test_expanded_or_ambiguous_sdk_mode_is_not_guessed(tmp_path, values):
    import sqlite3
    module, capture, receipts, raw, schema = prepare(tmp_path)
    database = capture / 'device_4/stream_expand_spec.db'
    connection = sqlite3.connect(database)
    connection.execute('CREATE TABLE StreamExpandSpec(expand_status)')
    connection.executemany('INSERT INTO StreamExpandSpec VALUES (?)',
                           [(value, ) for value in values])
    connection.commit()
    connection.close()
    entry = module.build_raw_task_sys(capture, receipts,
                                      schema)['task_sys_envelopes'][0]
    assert entry['status'] == 'unassociated'
    assert 'stream mode' in entry['reason']
