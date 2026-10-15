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
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_prepare_copies_compile_configuration_and_uses_unique_output(tmp_path, monkeypatch):
    plugin=tmp_path/'plugin.so';plugin.write_bytes(b'actual-plugin-placeholder')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN',str(plugin));monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILER_CAPTURE',str(tmp_path/'captures'))
    monkeypatch.setattr(m.shutil,'which',lambda name,**kw:'/sdk/bisheng' if name=='bisheng' else '/llvm/opt-15')
    events=[SimpleNamespace(backend='ascend',metadata={},command=['bishengir-compile','input.mlir'],environment={'PATH':'/sdk'}) for _ in range(2)]
    for event in events:m.prepare(event)
    assert events[0].metadata['flagprism_ascend_handoff']['compile_id']!=events[1].metadata['flagprism_ascend_handoff']['compile_id']
    assert events[0].command[2:] == [
        'bishengir-compile', 'input.mlir',
        '--bishengir-print-ir-after=hivm-graph-sync-solver'
    ]
    assert events[0].command[1].endswith('ascend_sdk_driver.py')
    assert events[0].environment['FLAGPRISM_ASCEND_REAL_BISHENG']=='/sdk/bisheng'
    output=Path(events[0].metadata['flagprism_ascend_handoff']['output'])
    assert (output/'bin/bisheng').stat().st_mode&0o111
    with pytest.raises(RuntimeError,match='no final actor LLVM'):m.finish(events[0],returncode=0)
    assert json.loads((output/'driver.json').read_text())['returncode']==0


def test_cache_identity_changes_with_trace_capacity_and_plugin(tmp_path, monkeypatch):
    plugin=tmp_path/'plugin.so';plugin.write_bytes(b'first')
    monkeypatch.setenv('FLAGPRISM_ASCEND_LATE_PLUGIN',str(plugin));first=m.cache_key()
    monkeypatch.setenv('FLAGPRISM_ASCEND_TRACE_CAPACITY','64');second=m.cache_key();assert first!=second
    plugin.write_bytes(b'second');assert second!=m.cache_key()
    third = m.cache_key()
    monkeypatch.setenv('FLAGPRISM_ASCEND_TRACE_SEMANTICS', 'wait_bracket')
    assert third != m.cache_key()


def test_unrequested_backend_does_not_change_driver():
    event=SimpleNamespace(backend='cuda',metadata={},command=['nvcc'],environment={})
    m.prepare(event);assert event.environment=={} and event.metadata=={}


def test_requested_finish_cannot_accept_an_old_compiler_route():
    event=SimpleNamespace(backend='ascend',metadata={'flagprism_ascend_observation_request':{'semantics':['issue']}})
    with pytest.raises(RuntimeError,match='did not prepare a late compiler handoff'):
        m.finish(event,returncode=0)


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
