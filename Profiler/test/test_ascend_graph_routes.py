"""Public paths reject capture before callbacks or native preparation."""
from types import SimpleNamespace
import pytest


def test_public_launch_context_rejects_before_prepare_or_lazy_metadata(
        monkeypatch):
    from flagtree.debugger import api
    from flagtree.debugger import graph_guard
    calls = []
    original = RuntimeError('capture is unsupported')

    def reject(*args, **kwargs):
        raise original

    monkeypatch.setattr(graph_guard, 'require_eager', reject)
    monkeypatch.setattr(api, 'prepare_kernel_launch',
                        lambda *a, **k: calls.append('prepare'))
    monkeypatch.setattr(api, '_materialize_launch_metadata',
                        lambda *a: calls.append('lazy'))
    with pytest.raises(RuntimeError) as caught:
        with api.launch_context('ascend', SimpleNamespace(debug_enabled=True),
                                (1, ), 17):
            calls.append('launch')
    assert caught.value is original and calls == []


@pytest.mark.parametrize('backend,options', [
    ('cann', {
        'detail': 'auto'
    }),
    ('cann', {
        'hook': 'instrumentation',
        'mode': 'runtime_base'
    }),
    ('cann', {
        'hook': 'triton'
    }),
    ('enflame', {
        'detail': 'auto'
    }),
    ('enflame', {
        'hook': 'instrumentation',
        'mode': 'runtime_base'
    }),
])
def test_public_start_rejects_before_activation_native_start_and_directory(
        monkeypatch, tmp_path, backend, options):
    import importlib
    profile = importlib.import_module('flagtree.profiler.profile')
    from flagtree.debugger import graph_guard
    calls = []
    monkeypatch.delenv(profile._CANN_TRITON_LEGACY_ENV, raising=False)

    def reject(*args, **kwargs):
        raise RuntimeError('capture is unsupported')

    monkeypatch.setattr(graph_guard, 'require_eager', reject)
    monkeypatch.setattr(profile, '_activate_instrumentation',
                        lambda *a, **k: calls.append('activate'))
    monkeypatch.setattr(profile.profiler_native, 'start',
                        lambda *a: calls.append('native'))
    output = tmp_path / 'not-created'
    with pytest.raises(RuntimeError, match='capture is unsupported'):
        profile.start(str(output), backend=backend, **options)
    assert calls == [] and not output.exists()


def test_metadata_guard_precedes_existing_metadata_callbacks(monkeypatch):
    from flagtree.profiler.hooks.launch import LaunchHook, CompiledKernel
    from flagtree.debugger import graph_guard
    calls = []

    def previous(*args, **kwargs):
        calls.append('previous')

    def reject(*args, **kwargs):
        raise RuntimeError('capture is unsupported')

    monkeypatch.setattr(CompiledKernel, 'launch_metadata', previous)
    monkeypatch.setattr(graph_guard, 'require_eager', reject)
    hook = LaunchHook()
    hook.activate()
    try:
        kernel = SimpleNamespace(metadata=SimpleNamespace(
            debug_enabled=True, target=SimpleNamespace(backend='ascend')))
        with pytest.raises(RuntimeError, match='capture is unsupported'):
            CompiledKernel.launch_metadata(kernel, (1, ), 17)
        assert calls == []
    finally:
        hook.deactivate()


def test_jit_guard_precedes_original_run_and_restores_ownership(monkeypatch):
    from flagtree.profiler.hooks.graph_guard import DetailedGraphGuard, JITFunction
    from flagtree.debugger import graph_guard
    calls = []

    def previous(*args, **kwargs):
        calls.append('original_compile_or_launch')
        return 71

    def reject(*args, **kwargs):
        raise RuntimeError('capture is unsupported')

    monkeypatch.setattr(JITFunction, 'run', previous)
    monkeypatch.setattr(graph_guard, 'require_eager', reject)
    hook = DetailedGraphGuard('cann')
    hook.activate()
    try:
        with pytest.raises(RuntimeError, match='capture is unsupported'):
            JITFunction.run(object())
        assert calls == []
        monkeypatch.setattr(graph_guard, 'require_eager', lambda *a, **k: None)
        assert JITFunction.run(object()) == 71
        assert calls == ['original_compile_or_launch']
        wrapper = JITFunction.run

        def third_party(*a, **k):
            return wrapper(*a, **k)

        monkeypatch.setattr(JITFunction, 'run', third_party)
        hook.deactivate()
        monkeypatch.setattr(graph_guard, 'require_eager', reject)
        assert JITFunction.run(object()) == 71
        assert JITFunction.run is third_party
    finally:
        hook.deactivate()


def test_jit_user_parameter_named_stream_is_forwarded_without_interpretation(
        monkeypatch):
    from flagtree.profiler.hooks.graph_guard import DetailedGraphGuard, JITFunction
    from flagtree.debugger import graph_guard
    scalar_or_tensor = object()
    seen = []

    def previous(kernel, *args, **kwargs):
        assert kwargs['stream'] is scalar_or_tensor
        return 'unchanged'

    def check(backend, **kwargs):
        seen.append((backend, kwargs))

    monkeypatch.setattr(JITFunction, 'run', previous)
    monkeypatch.setattr(graph_guard, 'require_eager', check)
    hook = DetailedGraphGuard('cann')
    hook.activate()
    try:
        assert JITFunction.run(object(),
                               stream=scalar_or_tensor) == 'unchanged'
        assert seen == [('cann', {})]
    finally:
        hook.deactivate()


def test_native_only_start_does_not_use_detailed_graph_guard(
        monkeypatch, tmp_path):
    import importlib
    profile = importlib.import_module('flagtree.profiler.profile')
    from flagtree.debugger import graph_guard
    calls = []

    def unexpected(*a, **k):
        calls.append('detailed_guard')
        raise AssertionError('native-only mode was guarded')

    def stop_before_runtime(*a, **k):
        raise RuntimeError('CPU environment checkpoint')

    monkeypatch.setattr(graph_guard, 'require_eager', unexpected)
    monkeypatch.setattr(profile, '_check_env', stop_before_runtime)
    with pytest.raises(RuntimeError, match='CPU environment checkpoint'):
        profile.start(str(tmp_path / 'native-only'), backend='cann', hook=None)
    assert calls == []
