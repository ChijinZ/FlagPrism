"""CPU-only JIT wrapper ownership; no compiler, allocator or GPU is invoked."""
import functools
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def hook_module(monkeypatch):
    native = importlib.import_module('flagtree.profiler.native')
    root = Path(__file__).parents[1] / 'python/flagtree_profiler'
    name = '_instrumentation_wrapper_ownership_test'
    package = ModuleType(name)
    package.__path__ = [str(root)]
    hooks = ModuleType(name + '.hooks')
    hooks.__path__ = [str(root / 'hooks')]
    monkeypatch.setitem(sys.modules, name, package)
    monkeypatch.setitem(sys.modules, hooks.__name__, hooks)
    monkeypatch.setitem(sys.modules, name + '.native', native)
    module = importlib.import_module(hooks.__name__ + '.instrumentation')
    monkeypatch.setattr(module, '_get_backend_name', lambda: 'amd')
    runtime = SimpleNamespace(active=SimpleNamespace(
        get_current_device=lambda: 0,
        utils=SimpleNamespace(
            get_device_properties=lambda device: {'max_shared_mem': 65536})))
    monkeypatch.setattr(module.triton.runtime, 'driver', runtime)
    monkeypatch.setattr(
        module, 'backends',
        {'amd': SimpleNamespace(compiler=SimpleNamespace(instrumentation={}))})
    monkeypatch.setattr(module, 'set_profile_allocator',
                        lambda allocator: None)
    monkeypatch.setattr(module.InstrumentationHook, 'active_count', 0)
    return module


@pytest.mark.parametrize('third_party', [False, True])
def test_teardown_preserves_other_wrapper_and_disables_retained_closure(
        hook_module, monkeypatch, third_party):
    module = hook_module
    calls, outer_calls = [], []

    def previous(jit_function, *args, **kwargs):
        calls.append((args, kwargs))
        return 'original-result'

    monkeypatch.setattr(module.JITFunction, 'run', previous)
    hook = module.InstrumentationHook(None)
    hook.activate()
    wrapped = module.JITFunction.run
    assert wrapped(object(), 17, user_option=23) == 'original-result'
    assert 'instrumentation_mode' in calls[-1][1]
    outer = None
    if third_party:

        @functools.wraps(wrapped)
        def outer(jit_function, *args, **kwargs):
            outer_calls.append(True)
            return wrapped(jit_function, *args, **kwargs)

        monkeypatch.setattr(module.JITFunction, 'run', outer)
    hook.deactivate()
    assert module.JITFunction.run is (outer if third_party else previous)
    assert module.JITFunction.run(object(), 19,
                                  user_option=29) == 'original-result'
    assert calls[-1] == ((19, ), {'user_option': 29})
    assert outer_calls == ([True] if third_party else [])
    # A caller that saved our old wrapper must also see a transparent function.
    assert wrapped(object(), 31, user_option=37) == 'original-result'
    assert calls[-1] == ((31, ), {'user_option': 37})
    hook.deactivate()
    assert module.InstrumentationHook.active_count == 0


def test_inactive_instance_cannot_deactivate_someone_elses_hook(
        hook_module, monkeypatch):
    module = hook_module
    monkeypatch.setattr(module.JITFunction, 'run',
                        lambda *args, **kwargs: kwargs)
    active = module.InstrumentationHook(None)
    inactive = module.InstrumentationHook(None)
    active.activate()
    installed = module.JITFunction.run
    inactive.deactivate()
    assert module.JITFunction.run is installed
    assert module.InstrumentationHook.active_count == 1
    active.deactivate()
    assert module.InstrumentationHook.active_count == 0
