"""Bundle and qualification guards for automatic native location retention."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
from unittest.mock import Mock, patch

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
                    debug_execution_tool_identity={},
                    debug_execution_manifest=dict(sites=[dict(id=7)]))
    binary = bundle([(TARGET, b'\x7fELFfake-parser-fixture')])
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(bridge,
                          '_native_shape_stage',
                          return_value={
                              'status': 'fixture_unverified',
                              'source_region_qualified': False
                          }), patch.object(bridge.tempfile,
                                           'mkdtemp',
                                           return_value=tmp), patch.object(
                                               bridge,
                                               '_native_file_stage',
                                               return_value=(json.dumps(
                                                   report()).encode(), {})):
            bridge.bind_native_clock_locations(binary, metadata)
    mapped = metadata['debug_execution_native_locations']
    assert mapped['missing_phase_locations'] == [
        dict(site_id=7, columns=[2, 3, 4])
    ]
    assert mapped['report']['source_region_qualified'] is False
    assert mapped['report']['reader_valueflow_qualified'] is False
    assert metadata['debug_execution_native_analysis'][
        'source_region_qualified'] is False


def test_reinspection_retains_producer_metadata_and_uses_current_analyzer():
    elf = b'\x7fELFfake-parser-fixture'
    binary = bundle([(TARGET, elf)])
    metadata = dict(debug_execution_version=1,
                    debug_execution_native_locations=dict(
                        fatbin_sha256=hashlib.sha256(binary).hexdigest(),
                        elf_sha256=hashlib.sha256(elf).hexdigest(),
                        target=TARGET),
                    debug_execution_tool_identity={'version': 'old'})
    original = copy.deepcopy(metadata)

    def inspect(binary, current):
        assert current['debug_execution_tool_identity'] == {'version': 'new'}
        current.update(
            debug_execution_native_locations={'status': 'fixture'},
            debug_execution_native_analysis={'status': 'fixture_unverified'})

    with patch.object(bridge, 'tool_identity', return_value={'version': 'new'}), \
            patch.object(bridge, 'bind_native_clock_locations', side_effect=inspect):
        result = bridge.inspect_native_execution(binary, metadata)
    assert metadata == original
    assert result['analysis']['status'] == 'fixture_unverified'


def test_reinspection_snapshots_mutable_bytes_before_identity_check():
    elf = b'\x7fELFfake-parser-fixture'
    binary = bundle([(TARGET, elf)])
    mutable = bytearray(binary)
    metadata = dict(debug_execution_version=1,
                    debug_execution_native_locations=dict(
                        fatbin_sha256=hashlib.sha256(binary).hexdigest(),
                        elf_sha256=hashlib.sha256(elf).hexdigest(),
                        target=TARGET))

    def identity():
        mutable[-1] ^= 1
        return {}

    def inspect(snapshot, current):
        assert type(snapshot) is bytes and snapshot == binary
        current['debug_execution_native_analysis'] = {
            'status': 'fixture_unverified'
        }
    with patch.object(bridge, 'tool_identity', side_effect=identity), \
            patch.object(bridge, 'bind_native_clock_locations', side_effect=inspect):
        result = bridge.inspect_native_execution(mutable, metadata)
    assert bytes(mutable) != binary
    assert result['fatbin_sha256'] == hashlib.sha256(binary).hexdigest()


@pytest.mark.parametrize(
    'fault', ['missing', 'fatbin', 'elf', 'target', 'bool_version'])
def test_reinspection_rejects_unbound_capture_before_running_tools(fault):
    elf = b'\x7fELFfake-parser-fixture'
    binary = bundle([(TARGET, elf)])
    captured = dict(fatbin_sha256=hashlib.sha256(binary).hexdigest(),
                    elf_sha256=hashlib.sha256(elf).hexdigest(),
                    target=TARGET)
    metadata = dict(debug_execution_version=1,
                    debug_execution_native_locations=captured)
    if fault == 'missing':
        metadata.pop('debug_execution_native_locations')
    elif fault == 'fatbin':
        binary = bundle([(TARGET, elf + b'different-valid-image')])
    elif fault == 'elf':
        captured['elf_sha256'] = '0' * 64
    elif fault == 'target':
        captured['target'] = 'other-target'
    else:
        metadata['debug_execution_version'] = True
    with patch.object(bridge, 'bind_native_clock_locations') as bind:
        with pytest.raises(ValueError):
            bridge.inspect_native_execution(binary, metadata)
    bind.assert_not_called()


@pytest.mark.parametrize('fault', ['registration', 'timeout'])
def test_native_decoder_cleanup_is_bounded_and_retains_pid(tmp_path, fault):
    child = Mock(pid=os.getpid(), returncode=None)
    child.poll.return_value = None
    expired = bridge.subprocess.TimeoutExpired('fixture-decoder', 20)
    child.wait.side_effect = [expired, expired
                              ] if fault == 'timeout' else [expired]
    root = tmp_path / 'analysis'
    with patch.object(bridge, 'tool_identity', return_value={}), \
            patch.object(bridge, '_file_hash', return_value='fixture'), \
            patch.object(bridge.subprocess, 'Popen', return_value=child):
        if fault == 'registration':
            original = Path.read_text

            def read(path, *args, **kwargs):
                if str(path).startswith('/proc/'):
                    raise OSError('fixture registration failed')
                return original(path, *args, **kwargs)

            with patch.object(Path, 'read_text', read):
                report = bridge._native_shape_stage(b'fixture', {}, {},
                                                    expected={},
                                                    root=root)
        else:
            report = bridge._native_shape_stage(b'fixture', {}, {},
                                                expected={},
                                                root=root)
    child.kill.assert_called_once_with()
    assert [call.kwargs['timeout'] for call in child.wait.call_args_list
            ] == ([20, 3] if fault == 'timeout' else [3])
    assert report['status'] == 'unavailable'
    assert report['decoder_receipt']['pid'] == child.pid
    assert report['decoder_receipt']['state'] == 'termination_pending'
    assert json.loads((root / 'terminal.json').read_text())['pid'] == child.pid


def test_ordinary_path_does_not_inspect_binary():
    with patch.object(bridge, '_native_file_stage') as child:
        bridge.bind_native_clock_locations(b'ordinary-not-a-timeline', {})
    child.assert_not_called()


@pytest.mark.parametrize('fault', ['none', 'IR', 'manifest'])
def test_structure_binary_attach_checks_actual_IR_and_manifest(
        tmp_path, fault):
    manifest = dict(sites=[dict(id=7)])
    index = dict(llvm_ir_sha256='a' * 64,
                 manifest_sha256=hashlib.sha256(
                     json.dumps(manifest,
                                sort_keys=True).encode()).hexdigest())
    original = copy.deepcopy(index)
    metadata = dict(debug_execution_version=1,
                    debug_execution_tool_identity={},
                    debug_execution_manifest=manifest,
                    debug_execution_native_ir_sha256='a' * 64,
                    debug_execution_llvm_structure=index)
    if fault == 'IR':
        metadata['debug_execution_native_ir_sha256'] = 'b' * 64
    elif fault == 'manifest':
        metadata['debug_execution_manifest']['new_property'] = True
    elf = b'\x7fELFfake-parser-fixture'
    binary = bundle([(TARGET, elf)])
    with patch.object(bridge.tempfile, 'mkdtemp', return_value=str(tmp_path)), \
            patch.object(bridge, '_native_file_stage', return_value=(json.dumps(report()).encode(), {})), \
            patch.object(bridge, '_native_shape_stage', return_value={'status': 'fixture_unverified'}):
        if fault == 'none':
            bridge.bind_native_clock_locations(binary, metadata)
            bound = metadata['debug_execution_llvm_structure']
            assert bound['fatbin_sha256'] == hashlib.sha256(binary).hexdigest()
            assert bound['elf_sha256'] == hashlib.sha256(elf).hexdigest()
            assert bound['target'] == TARGET
        else:
            with pytest.raises(RuntimeError, match='retained at'):
                bridge.bind_native_clock_locations(binary, metadata)
    assert index == original


@pytest.mark.parametrize('mode',
                         ['missing', 'fresh', 'different', 'legacy_fallback'])
def test_offline_boundaries_recompute_from_exact_input_and_ignore_cached_status(
        mode):
    elf = b'\x7fELFfake-parser-fixture'
    binary = bundle([(TARGET, elf)])
    text = 'fixture-retained-final-LLVM'
    metadata = dict(debug_execution_version=1,
                    debug_execution_tool_identity={'version': 'old'},
                    debug_execution_native_ir_sha256=hashlib.sha256(
                        text.encode()).hexdigest(),
                    debug_execution_native_locations=dict(
                        fatbin_sha256=hashlib.sha256(binary).hexdigest(),
                        elf_sha256=hashlib.sha256(elf).hexdigest(),
                        target=TARGET),
                    debug_execution_llvm_structure={
                        'boundary_report': {
                            'status': 'cached-untrusted'
                        }
                    })
    if mode == 'legacy_fallback':
        metadata['debug_math_compat'] = 'scalar_fabs'
    original = copy.deepcopy(metadata)

    def structure(source, current):
        assert source == text
        current['debug_execution_llvm_structure'] = {
            'boundary_report': {
                'status': 'fresh-fixture'
            }
        }

    def native(snapshot, current):
        assert snapshot == binary
        current['debug_execution_native_analysis'] = {
            'status': 'fixture_unverified'
        }

    with patch.object(bridge, 'tool_identity', return_value={'version': 'new'}), \
            patch.object(bridge, 'bind_execution_structure', side_effect=structure) as index, \
            patch.object(bridge, 'bind_native_clock_locations', side_effect=native) as mapping:
        if mode == 'different':
            with pytest.raises(ValueError,
                               match='LLVM input identity differs'):
                bridge.inspect_native_execution(binary,
                                                metadata,
                                                llvm_ir=text + 'changed')
            index.assert_not_called()
            mapping.assert_not_called()
        else:
            result = bridge.inspect_native_execution(
                binary, metadata, llvm_ir=None if mode == 'missing' else text)
            if mode == 'fresh':
                index.assert_called_once()
                assert result['llvm_boundaries']['status'] == 'fresh-fixture'
            else:
                index.assert_not_called()
                assert result['llvm_boundaries']['status'] == 'unverified'
                assert result['llvm_boundaries']['reason'] == (
                    'legacy_fallback_final_input_not_retained'
                    if mode == 'legacy_fallback' else
                    'captured_final_llvm_input_not_supplied')
    assert metadata == original
