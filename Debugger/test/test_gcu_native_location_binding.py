"""Bundle and qualification guards for automatic native location retention."""
import copy
import json
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch

import pytest
from flagtree.debugger import gcu_timeline as bridge

MAGIC = b'__CLANG_OFFLOAD_BUNDLE__'
TARGET = 'tops-dtu-enflame-tops--gcu300'


def bundle(entries):
    header_size = len(MAGIC) + 8 + sum(24 + len(t.encode())
                                       for t, _ in entries)
    header, data = bytearray(MAGIC +
                             struct.pack('<Q', len(entries))), bytearray()
    for target, payload in entries:
        name = target.encode()
        header.extend(
            struct.pack('<QQQ', header_size + len(data) if payload else 0,
                        len(payload), len(name)))
        header.extend(name)
        data.extend(payload)
    return bytes(header + data)


def test_exact_image_among_other_targets():
    image = b'\x7fELFfake-parser-fixture'
    binary = bundle([('host-x86_64', b'host'), (TARGET, image)])
    assert bridge._gcu300_bundle_image(binary) == (image, TARGET)


@pytest.mark.parametrize('binary', [
    b'not a bundle',
    MAGIC + struct.pack('<Q', 33),
    MAGIC + struct.pack('<Q', 1),
    bundle([('other-gpu', b'data')]),
    bundle([(TARGET, b'one'), (TARGET, b'two')]),
    bundle([(TARGET, b'payload')])[:-1],
])
def test_ambiguous_or_truncated_bundle_is_rejected(binary):
    with pytest.raises(ValueError):
        bridge._gcu300_bundle_image(binary)


def test_payload_cannot_overlap_its_header():
    binary = bytearray(bundle([(TARGET, b'payload')]))
    struct.pack_into('<Q', binary, len(MAGIC) + 8, 0)
    with pytest.raises(ValueError, match='Overlapping'):
        bridge._gcu300_bundle_image(bytes(binary))


def test_payloads_cannot_alias_each_other():
    binary = bytearray(bundle([('other', b'one'), (TARGET, b'two')]))
    first_offset = struct.unpack_from('<Q', binary, len(MAGIC) + 8)[0]
    second_header = len(MAGIC) + 8 + 24 + len('other')
    struct.pack_into('<Q', binary, second_header, first_offset)
    with pytest.raises(ValueError, match='Overlapping'):
        bridge._gcu300_bundle_image(bytes(binary))


def report():
    return dict(schema_version=1,
                status='compiler_locations_mapped',
                semantics='compiler_debug_location_rows',
                marker_file='__flagprism_gcu_clock_v1__',
                source_region_qualified=False,
                reader_valueflow_qualified=False,
                hardware_busy_qualified=False,
                locations=[
                    dict(site_id=7,
                         column=1,
                         phase='begin_counter',
                         address=16,
                         section_offset=16)
                ])


@pytest.mark.parametrize(
    'mutation', ['source_rights', 'wrong_site', 'bool_column', 'wrong_phase'])
def test_native_report_cannot_escalate_or_change_manifest(mutation):
    row = copy.deepcopy(report())
    if mutation == 'source_rights':
        row['source_region_qualified'] = True
    elif mutation == 'wrong_site':
        row['locations'][0]['site_id'] = 8
    elif mutation == 'bool_column':
        row['locations'][0]['column'] = True
    else:
        row['locations'][0]['phase'] = 'end_counter'
    metadata = dict(debug_execution_version=1,
                    debug_execution_manifest=dict(sites=[dict(id=7)]))
    binary = bundle([(TARGET, b'\x7fELFfake-parser-fixture')])
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(bridge.tempfile, 'mkdtemp',
                          return_value=tmp), patch.object(
                              bridge,
                              '_native_file_stage',
                              return_value=(json.dumps(row).encode(), {})):
            with pytest.raises(RuntimeError, match='retained at'):
                bridge.bind_native_clock_locations(binary, metadata)
        assert (Path(tmp) / 'input.fatbin').read_bytes() == binary
    assert 'debug_execution_native_locations' not in metadata


def test_missing_phases_remain_explicit_without_timing_rights():
    metadata = dict(debug_execution_version=1,
                    debug_execution_manifest=dict(sites=[dict(id=7)]))
    binary = bundle([(TARGET, b'\x7fELFfake-parser-fixture')])
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(bridge.tempfile, 'mkdtemp',
                          return_value=tmp), patch.object(
                              bridge,
                              '_native_file_stage',
                              return_value=(json.dumps(report()).encode(),
                                            {})):
            bridge.bind_native_clock_locations(binary, metadata)
    mapped = metadata['debug_execution_native_locations']
    assert mapped['missing_phase_locations'] == [
        dict(site_id=7, columns=[2, 3, 4])
    ]
    assert mapped['report']['source_region_qualified'] is False
    assert mapped['report']['reader_valueflow_qualified'] is False


def test_ordinary_path_does_not_inspect_binary():
    with patch.object(bridge, '_native_file_stage') as child:
        bridge.bind_native_clock_locations(b'ordinary-not-a-timeline', {})
    child.assert_not_called()
