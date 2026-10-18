"""Driver isolation, failure, and compile identity regressions."""
import importlib.util
import sys
import types
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

namespace = types.ModuleType('_ascend_test_package')
namespace.__path__ = [
    str(Path(__file__).parents[1] / 'python/flagtree_profiler')
]
sys.modules['_ascend_test_package'] = namespace
spec = importlib.util.spec_from_file_location(
    '_ascend_test_package.ascend_compiler',
    Path(__file__).parents[1] / 'python/flagtree_profiler/ascend_compiler.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_prepare_copies_compile_configuration_and_uses_unique_output(
        tmp_path, monkeypatch):
    plugin = tmp_path / 'plugin.so'
    plugin.write_bytes(b'actual-plugin-placeholder')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN', str(plugin))
    monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILER_CAPTURE',
                       str(tmp_path / 'captures'))
    monkeypatch.setattr(
        m.shutil, 'which', lambda name, **kw: '/sdk/bisheng'
        if name == 'bisheng' else '/llvm/opt-15')
    events = [
        SimpleNamespace(backend='ascend',
                        metadata={},
                        command=['bishengir-compile', 'input.mlir'],
                        environment={'PATH': '/sdk'}) for _ in range(2)
    ]
    for event in events:
        m.prepare(event)
    assert events[0].metadata['flagprism_ascend_handoff'][
        'compile_id'] != events[1].metadata['flagprism_ascend_handoff'][
            'compile_id']
    assert events[0].command[2:] == [
        'bishengir-compile', 'input.mlir',
        '--bishengir-print-ir-after=hivm-graph-sync-solver'
    ]
    assert events[0].command[1].endswith('ascend_sdk_driver.py')
    assert events[0].environment[
        'FLAGPRISM_ASCEND_REAL_BISHENG'] == '/sdk/bisheng'
    output = Path(events[0].metadata['flagprism_ascend_handoff']['output'])
    assert (output / 'bin/bisheng').stat().st_mode & 0o111
    with pytest.raises(RuntimeError, match='no final actor LLVM'):
        m.finish(events[0], returncode=0)
    assert json.loads((output / 'driver.json').read_text())['returncode'] == 0


def test_cache_identity_changes_with_trace_capacity_and_plugin(
        tmp_path, monkeypatch):
    plugin = tmp_path / 'plugin.so'
    plugin.write_bytes(b'first')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN', str(plugin))
    first = m.cache_key()
    monkeypatch.setenv('FLAGPRISM_ASCEND_TRACE_CAPACITY', '64')
    second = m.cache_key()
    assert first != second
    plugin.write_bytes(b'second')
    assert second != m.cache_key()
    third = m.cache_key()
    monkeypatch.setenv('FLAGPRISM_ASCEND_TRACE_SEMANTICS', 'wait_bracket')
    assert third != m.cache_key()


def test_unrequested_backend_does_not_change_driver():
    event = SimpleNamespace(backend='cuda',
                            metadata={},
                            command=['nvcc'],
                            environment={})
    m.prepare(event)
    assert event.environment == {} and event.metadata == {}


def test_requested_finish_cannot_accept_an_old_compiler_route():
    event = SimpleNamespace(backend='ascend',
                            metadata={
                                'flagprism_ascend_observation_request': {
                                    'semantics': ['issue']
                                }
                            })
    with pytest.raises(RuntimeError,
                       match='did not prepare a late compiler handoff'):
        m.finish(event, returncode=0)


def test_prepare_retains_exact_crlf_source_bytes(tmp_path, monkeypatch):
    import hashlib
    source = b'func.func @source(%lock: memref<?xi8>, %work: memref<?xi8>, %x: memref<?xf32>) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, global_kernel = "local"} {\r\n return\r\n}\r\n'
    input_path = tmp_path / 'input.mlir'
    input_path.write_bytes(source)
    plugin = tmp_path / 'plugin.so'
    plugin.write_bytes(b'fixture-plugin')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN', str(plugin))
    monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILER_CAPTURE',
                       str(tmp_path / 'captures'))
    monkeypatch.setattr(
        m.shutil, 'which', lambda name, **kw: '/sdk/bisheng'
        if name == 'bisheng' else '/llvm/opt-15')
    fake_driver = tmp_path / 'driver.py'
    fake_driver.write_bytes(b'actual fixture launch source')
    utils = SimpleNamespace(__file__=str(tmp_path / 'utils.py'),
                            get_ascend_arch_from_env=lambda: 'c220',
                            is_ffts_supported=lambda arch: True,
                            force_disable_ffts=lambda: False)
    backend = types.ModuleType('triton.backends.ascend')
    backend.utils = utils
    monkeypatch.setitem(sys.modules, 'triton.backends.ascend', backend)
    event = SimpleNamespace(backend='ascend',
                            metadata={},
                            command=['bishengir-compile',
                                     str(input_path)],
                            environment={'PATH': '/sdk'})
    m.prepare(event)
    handoff = event.metadata['flagprism_ascend_handoff']
    snapshot = handoff['source_snapshot']
    assert snapshot['ir'].encode('utf-8') == source
    assert snapshot['ir_sha256'] == hashlib.sha256(source).hexdigest()
    assert (Path(handoff['output']) / 'source.mlir').read_bytes() == source


def test_finish_embeds_exact_manifest_bytes_for_portable_validation(tmp_path):
    import hashlib
    llir = 'define void @actual_actor() { ret void }\n'
    module_sha = hashlib.sha256(llir.encode()).hexdigest()
    metadata = {
        'module_sha256': module_sha,
        'compile_id': 'fixture-compile',
        'actors': []
    }
    raw = (json.dumps(metadata, sort_keys=True, indent=2) + '\r\n').encode()
    (tmp_path / 'actor.ll').write_bytes(llir.encode())
    (tmp_path / 'actor.json').write_bytes(raw)
    handoff = {
        'compile_id': 'fixture-compile',
        'output': str(tmp_path),
        'phase': 'prepared'
    }
    event = SimpleNamespace(backend='ascend',
                            metadata={'flagprism_ascend_handoff': handoff})
    m.finish(event, returncode=0)
    artifact, = handoff['artifacts']
    assert artifact['manifest_text'].encode('utf-8') == raw
    assert artifact['manifest_sha256'] == hashlib.sha256(raw).hexdigest()
    assert artifact['metadata'] == metadata


@pytest.mark.parametrize('raw', [
    b'; raw CRLF\r\ndefine void @k() { ret void }\r\n', b'BC\xc0\xde\x00\xff'
])
def test_finish_retains_raw_input_and_exact_final_binary(tmp_path, raw):
    """CPU artifact fixtures check retention, not real SDK compilation."""
    import base64
    import hashlib
    job = tmp_path / 'jobs/compile-fixture'
    job.mkdir(parents=True)
    original = job / 'original-input-0.bc'
    original.write_bytes(raw)
    raw_sha = hashlib.sha256(raw).hexdigest()
    canonical = '; canonical LLVM\ndefine void @k() { ret void }\n'
    actor = job / 'actor.ll'
    actor.write_text(canonical)
    manifest = dict(module_sha256=hashlib.sha256(
        canonical.encode()).hexdigest(),
                    module_input_sha256=raw_sha,
                    module_identifier='/gone/input.bc',
                    compile_id='fixture-compile',
                    actors=[])
    actor.with_suffix('.json').write_text(json.dumps(manifest))
    (job / 'receipt.json').write_text(
        json.dumps(
            dict(inputs=[
                dict(path='/gone/input.bc',
                     retained_path=str(original),
                     sha256=raw_sha,
                     bytes=len(raw))
            ])))
    binary = tmp_path / 'sdk-final.o'
    binary_bytes = b'\x7fELF\x00\xfffinal SDK fixture\r\n'
    binary.write_bytes(binary_bytes)
    handoff = dict(compile_id='fixture-compile',
                   output=str(tmp_path),
                   phase='prepared')
    event = SimpleNamespace(backend='ascend',
                            output_files={'binary': str(binary)},
                            metadata={'flagprism_ascend_handoff': handoff})
    m.finish(event, returncode=0)
    artifact, = handoff['artifacts']
    assert base64.b64decode(artifact['original_input']['data']) == raw
    assert artifact['original_input_sha256'] == raw_sha
    assert artifact[
        'sha256'] != raw_sha  # Canonical text is a different representation.
    assert base64.b64decode(
        handoff['final_outputs']['binary']['data']) == binary_bytes
    assert handoff['final_outputs']['binary']['sha256'] == hashlib.sha256(
        binary_bytes).hexdigest()
    assert len(handoff['codegen_jobs']) == 1


def test_changed_retained_artifact_is_rejected(tmp_path):
    import hashlib
    path = tmp_path / 'original.bc'
    path.write_bytes(b'changed')
    info = dict(path='/gone/original.bc',
                retained_path=str(path),
                sha256=hashlib.sha256(b'original').hexdigest(),
                bytes=8)
    with pytest.raises(RuntimeError, match='artifact changed'):
        m._portable_file(info)


@pytest.fixture
def sdk_producer_fixture(tmp_path):
    """Explicit CPU receipts; these do not certify an SDK/compiler run."""
    import hashlib
    job = tmp_path / 'jobs/actor-fixture'
    job.mkdir(parents=True)
    original = job / 'original-input-0.ll'
    original.write_bytes(b'; original source bytes\r\n')
    raw_sha = hashlib.sha256(original.read_bytes()).hexdigest()
    canonical = '; canonical\ndefine void @k() { ret void }\n'
    actor = job / 'actor.ll'
    actor.write_text(canonical)
    actor.with_suffix('.json').write_text(
        json.dumps(
            dict(module_identifier='/gone/input.ll',
                 module_input_sha256=raw_sha,
                 module_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
                 compile_id='compile-fixture',
                 actors=[{
                     'dynamic_observation_prepared': True
                 }])))
    receipt = dict(compile_id='compile-fixture',
                   process_group_id=77,
                   state='finished',
                   exit_code=0,
                   inputs=[
                       dict(path='/gone/input.ll',
                            retained_path=str(original),
                            sha256=raw_sha,
                            bytes=original.stat().st_size)
                   ])
    (job / 'receipt.json').write_text(json.dumps(receipt))
    binary = tmp_path / 'final.o'
    binary.write_bytes(b'actual fixture final binary\x00')
    sdk = dict(state='finished',
               returncode=0,
               compile_id='compile-fixture',
               process_group_id=77,
               outputs={
                   'binary':
                   dict(path=str(binary),
                        bytes=binary.stat().st_size,
                        sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
               })
    (tmp_path / 'sdk-compiler.json').write_text(json.dumps(sdk))
    (tmp_path / 'sdk-stderr.txt').write_text('CPU fixture\n')
    handoff = dict(compile_id='compile-fixture',
                   output=str(tmp_path),
                   phase='prepared')
    event = SimpleNamespace(backend='ascend',
                            output_files={'binary': str(binary)},
                            metadata={
                                'flagprism_ascend_handoff': handoff,
                                'flagprism_ascend_observation_request': {
                                    'semantics': ['counter']
                                }
                            })
    return event, job, tmp_path, sdk, receipt


def test_successful_enclosing_sdk_output_association(sdk_producer_fixture):
    event, job, root, sdk, receipt = sdk_producer_fixture
    m.finish(event, returncode=0)
    association = event.metadata['flagprism_ascend_handoff'][
        'producer_association']
    assert association['sdk_process_group_id'] == 77
    assert association['final_binary_sha256'] == sdk['outputs']['binary'][
        'sha256']
    assert association['codegen_job_count'] == 1


@pytest.mark.parametrize('changed', [False, True])
def test_timeline_seals_actor_object_before_scratch_cleanup(
        sdk_producer_fixture, changed):
    """Retention fixtures are not final-machine clock qualification."""
    import base64
    import hashlib
    event, job, root, sdk, receipt = sdk_producer_fixture
    event.metadata['debug_record_layout'] = 'ascend_source_timeline_v1'
    data = b'\x7fELF actor object fixture\x00\xff\r\n'
    retained = job / 'output.bin'
    retained.write_bytes(data + b'changed' if changed else data)
    receipt['object'] = dict(path='/gone/kernel.o',
                             retained_path=str(retained),
                             sha256=hashlib.sha256(data).hexdigest(),
                             bytes=len(data))
    (job / 'receipt.json').write_text(json.dumps(receipt))
    if changed:
        with pytest.raises(RuntimeError, match='artifact changed'):
            m.finish(event, returncode=0)
        return
    m.finish(event, returncode=0)
    retained.unlink()
    artifact, = event.metadata['flagprism_ascend_handoff']['artifacts']
    assert artifact['compiled_object_status'] == 'retained'
    obj = artifact['compiled_object']
    assert base64.b64decode(obj['data'], validate=True) == data
    assert obj['sha256'] == receipt['object']['sha256']
    assert obj['bytes'] == len(data)


def test_timeline_missing_actor_object_is_explicit(sdk_producer_fixture):
    event, job, root, sdk, receipt = sdk_producer_fixture
    event.metadata['debug_record_layout'] = 'ascend_source_timeline_v1'
    m.finish(event, returncode=0)
    artifact, = event.metadata['flagprism_ascend_handoff']['artifacts']
    assert artifact['compiled_object_status'] == 'missing'
    assert 'compiled_object' not in artifact


def test_actor_object_retention_is_bounded(tmp_path):
    path = tmp_path / 'oversized.bin'
    path.write_bytes(b'oversized')
    with pytest.raises(RuntimeError, match='exceeds byte budget'):
        m._portable_file(dict(path=str(path)), max_bytes=4)


@pytest.mark.parametrize(
    'mutation', ['group', 'compile', 'failed-job', 'binary', 'failed-sdk'])
def test_missing_producer_relation_fails_closed(sdk_producer_fixture,
                                                mutation):
    event, job, root, sdk, receipt = sdk_producer_fixture
    if mutation == 'group':
        receipt['process_group_id'] = 78
    elif mutation == 'compile':
        receipt['compile_id'] = 'different-compile'
    elif mutation == 'failed-job':
        receipt['exit_code'] = 7
    elif mutation == 'binary':
        sdk['outputs']['binary']['sha256'] = '0' * 64
    elif mutation == 'failed-sdk':
        sdk['returncode'] = 7
    (job / 'receipt.json').write_text(json.dumps(receipt))
    (root / 'sdk-compiler.json').write_text(json.dumps(sdk))
    with pytest.raises(RuntimeError,
                       match='enclosing SDK producer association'):
        m.finish(event, returncode=0)


def test_driver_receipt_preserves_bound_compiler_identity(
        tmp_path, monkeypatch):
    plugin = tmp_path / 'plugin.so'
    plugin.write_bytes(b'fixture-plugin')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN', str(plugin))
    monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILER_CAPTURE',
                       str(tmp_path / 'captures'))
    monkeypatch.setattr(
        m.shutil, 'which', lambda name, **kw: '/sdk/bisheng'
        if name == 'bisheng' else '/llvm/opt-15')
    identity = {'path': '/isolated/bin/bishengir-compile', 'sha256': 'b' * 64}
    event = SimpleNamespace(backend='ascend',
                            metadata={'ascend_compiler_identity': identity},
                            command=[identity['path'], 'input.mlir'],
                            environment={'PATH': '/sdk'})
    m.prepare(event)
    handoff = event.metadata['flagprism_ascend_handoff']
    receipt = json.loads((Path(handoff['output']) / 'driver.json').read_text())
    assert receipt['ascend_compiler_identity'] == identity
    assert receipt['command'][0] == identity['path']
    assert handoff['ascend_compiler_identity'] == identity


def test_source_timeline_reuses_coordinates_but_not_census_storage(
        tmp_path, monkeypatch):
    plugin = tmp_path / 'plugin.so'
    plugin.write_bytes(b'explicit-test-plugin')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN', str(plugin))
    monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILER_CAPTURE',
                       str(tmp_path / 'captures'))
    monkeypatch.setattr(
        m.shutil, 'which', lambda name, **kw: '/sdk/bisheng'
        if name == 'bisheng' else '/llvm/opt-15')
    source = tmp_path / 'input.mlir'
    source.write_text(
        'func.func @entry(%lock: memref<?xi8>, %work: memref<?xi8>, %x: memref<?xf32>, %y: memref<?xf32>, %trace: memref<?xi64>) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, global_kernel = "local"} { return }'
    )
    (tmp_path / 'driver.py').write_bytes(b'explicit CPU driver fixture')
    backend = types.ModuleType('triton.backends.ascend')
    backend.utils = SimpleNamespace(__file__=str(tmp_path / 'utils.py'),
                                    get_ascend_arch_from_env=lambda: 'c220',
                                    is_ffts_supported=lambda arch: True,
                                    force_disable_ffts=lambda: False)
    monkeypatch.setitem(sys.modules, 'triton.backends.ascend', backend)
    metadata = dict(flagprism_ascend_observation_request=dict(
        program_policy='runtime_first_last',
        semantics=['source_control_interval']),
                    flagprism_ascend_trace_capacity=128,
                    flagprism_ascend_trace_source_argument_index=2,
                    flagprism_ascend_source_timeline_version=1,
                    debug_frontend_marker_abi=dict(
                        version=3,
                        site_count=2,
                        record_layout='ascend_source_census_v3'),
                    debug_census_columns=2,
                    debug_record_layout='ascend_source_timeline_v1')
    event = SimpleNamespace(backend='ascend',
                            metadata=metadata,
                            command=['bishengir-compile',
                                     str(source)],
                            environment={'PATH': '/sdk'})
    m.prepare(event)
    assert event.environment[
        'FLAGPRISM_ASCEND_TRACE_MODE'] == 'source_timeline_v1'
    assert event.environment['FLAGPRISM_ASCEND_TRACE_CAPACITY'] == '128'
    assert event.environment['FLAGPRISM_ASCEND_CENSUS_COLUMNS'] == '2'
    assert 'FLAGPRISM_ASCEND_TRACE_PROGRAM' not in event.environment
    assert metadata['debug_record_layout'] == 'ascend_source_timeline_v1'


@pytest.mark.parametrize('field,value', [
    ('flagprism_ascend_source_timeline_version', True),
    ('debug_census_columns', 3),
    ('debug_record_layout', 'ascend_source_census_v3'),
    ('flagprism_ascend_trace_capacity', 16385),
])
def test_timeline_handoff_rejects_inconsistent_frontend_before_driver(
        tmp_path, monkeypatch, field, value):
    plugin = tmp_path / 'plugin.so'
    plugin.write_bytes(b'explicit-test-plugin')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN', str(plugin))
    monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILER_CAPTURE',
                       str(tmp_path / 'captures'))
    metadata = dict(flagprism_ascend_observation_request=dict(
        program_policy='runtime_first_last',
        semantics=['source_control_interval']),
                    flagprism_ascend_trace_capacity=128,
                    flagprism_ascend_trace_source_argument_index=2,
                    flagprism_ascend_source_timeline_version=1,
                    debug_frontend_marker_abi=dict(
                        version=3,
                        site_count=2,
                        record_layout='ascend_source_census_v3'),
                    debug_census_columns=2,
                    debug_record_layout='ascend_source_timeline_v1')
    metadata[field] = value
    event = SimpleNamespace(
        backend='ascend',
        metadata=metadata,
        command=['bishengir-compile', 'missing-fixture.mlir'],
        environment={'PATH': '/sdk'})
    with pytest.raises(ValueError):
        m.prepare(event)
    assert not (tmp_path / 'captures').exists()
