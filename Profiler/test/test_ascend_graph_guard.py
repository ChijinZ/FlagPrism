"""CPU capture-state faults reject before any debugger preparation."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from contextlib import contextmanager

import pytest

SOURCE = Path(
    __file__).parents[2] / 'Debugger/python/flagtree_debugger/graph_guard.py'


@pytest.fixture
def guard():
    spec = importlib.util.spec_from_file_location('ascend_graph_guard_test',
                                                  SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_runtime(monkeypatch, query):
    calls = []

    @contextmanager
    def stream(handle):
        calls.append(('enter', handle))
        try:
            yield
        finally:
            calls.append(('restore', handle))

    runtime = SimpleNamespace(is_current_stream_capturing=query,
                              ExternalStream=lambda value: ('external', value),
                              stream=stream)
    torch = ModuleType('torch')
    torch.npu = runtime
    monkeypatch.setitem(sys.modules, 'torch', torch)
    monkeypatch.setitem(sys.modules, 'torch_npu', ModuleType('torch_npu'))
    return calls


@pytest.mark.parametrize('backend', ['cuda', 'instrumentation', None])
def test_other_backends_do_not_import_torchnpu(guard, monkeypatch, backend):
    monkeypatch.setitem(sys.modules, 'torch_npu', None)
    guard.require_eager(backend)


def test_capture_is_not_cached_and_stream_is_restored(guard, monkeypatch):
    values = iter([False, True, False])
    calls = fake_runtime(monkeypatch, lambda: next(values))
    guard.require_eager('ascend', stream=17)
    with pytest.raises(RuntimeError, match='eager launches only'):
        guard.require_eager('cann', stream=23)
    guard.require_eager('npu', stream=17)
    assert calls == [
        ('enter', ('external', 17)), ('restore', ('external', 17)),
        ('enter', ('external', 23)), ('restore', ('external', 23)),
        ('enter', ('external', 17)), ('restore', ('external', 17))
    ]


def test_failed_query_preserves_original_cause_and_restores_stream(
        guard, monkeypatch):
    original = ValueError('original SDK query failed')

    def query():
        raise original

    calls = fake_runtime(monkeypatch, query)
    with pytest.raises(RuntimeError, match='cannot verify') as caught:
        guard.require_eager('ascend', stream=77)
    assert caught.value.__cause__ is original
    assert calls[-1] == ('restore', ('external', 77))


@pytest.mark.parametrize('state', [None, 0, 1, 'false'])
def test_indeterminate_query_is_fail_closed(guard, monkeypatch, state):
    fake_runtime(monkeypatch, lambda: state)
    with pytest.raises(RuntimeError, match='indeterminate'):
        guard.require_eager('ascend')


def test_missing_torchnpu_or_query_does_not_assume_eager(guard, monkeypatch):
    monkeypatch.setitem(sys.modules, 'torch', ModuleType('torch'))
    monkeypatch.setitem(sys.modules, 'torch_npu', None)
    with pytest.raises(RuntimeError, match='cannot verify') as caught:
        guard.require_eager('ascend')
    assert isinstance(caught.value.__cause__, ImportError)
    fake_runtime(monkeypatch, lambda: False)
    del sys.modules['torch'].npu.is_current_stream_capturing
    with pytest.raises(RuntimeError, match='cannot verify') as caught:
        guard.require_eager('ascend')
    assert isinstance(caught.value.__cause__, AttributeError)


def test_gcu_query_never_imports_torchnpu(guard, monkeypatch):
    calls = fake_runtime(monkeypatch, lambda: False)
    fake = sys.modules['torch']
    fake.gcu = fake.npu
    del fake.npu
    monkeypatch.setitem(sys.modules, 'torch_npu', None)
    monkeypatch.setitem(sys.modules, 'torch_gcu', ModuleType('torch_gcu'))
    guard.require_eager('enflame')
    guard.require_eager('gcu', stream=17)
    assert calls[-1] == ('restore', ('external', 17))
    fake.gcu.is_current_stream_capturing = lambda: True
    with pytest.raises(RuntimeError, match='GCU graph capture is unsupported'):
        guard.require_eager('tops')


@pytest.mark.parametrize('state', [False, True])
def test_actual_current_handle_does_not_require_external_stream(
        guard, monkeypatch, state):
    calls = fake_runtime(monkeypatch, lambda: state)
    runtime = sys.modules['torch'].npu
    del runtime.ExternalStream
    runtime.current_stream = lambda: SimpleNamespace(npu_stream=37)
    if state:
        with pytest.raises(RuntimeError, match='eager launches only'):
            guard.require_eager('cann', stream=37)
    else:
        guard.require_eager('cann', stream=37)
    assert calls == []


def test_noncurrent_handle_without_external_stream_is_fail_closed(
        guard, monkeypatch):
    calls = fake_runtime(monkeypatch, lambda: False)
    runtime = sys.modules['torch'].npu
    del runtime.ExternalStream
    runtime.current_stream = lambda: SimpleNamespace(npu_stream=37)
    with pytest.raises(RuntimeError, match='cannot verify') as caught:
        guard.require_eager('cann', stream=38)
    assert isinstance(caught.value.__cause__, AttributeError)
    assert calls == []


@pytest.mark.parametrize('state', [None, 0, 'false'])
def test_matching_current_handle_still_rejects_indeterminate(
        guard, monkeypatch, state):
    fake_runtime(monkeypatch, lambda: state)
    runtime = sys.modules['torch'].npu
    del runtime.ExternalStream
    runtime.current_stream = lambda: SimpleNamespace(npu_stream=37)
    with pytest.raises(RuntimeError, match='indeterminate'):
        guard.require_eager('cann', stream=37)


def test_matching_current_query_failure_preserves_cause(guard, monkeypatch):
    original = ValueError('current query failed')

    def query():
        raise original

    fake_runtime(monkeypatch, query)
    runtime = sys.modules['torch'].npu
    del runtime.ExternalStream
    runtime.current_stream = lambda: SimpleNamespace(npu_stream=37)
    with pytest.raises(RuntimeError, match='cannot verify') as caught:
        guard.require_eager('cann', stream=37)
    assert caught.value.__cause__ is original
