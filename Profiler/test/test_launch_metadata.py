"""Lifecycle and coexistence of the FlagPrism-owned launch metadata wrapper."""
from types import SimpleNamespace

import pytest
from triton.compiler import CompiledKernel, LazyDict
from flagtree.profiler.hooks.launch import LaunchHook
from flagtree.profiler.hooks.hook import HookManager


@pytest.fixture
def launch_adapter(monkeypatch):
    assert LaunchHook._metadata_wrapper is None
    calls = []

    def previous(kernel, grid, stream, *args, **kwargs):
        calls.append((kernel, grid, stream, args, kwargs))
        metadata = LazyDict({"name": "probe", "stream": stream})
        metadata.add(lambda: {"user_value": 17}, ())
        return metadata

    monkeypatch.setattr(CompiledKernel, "launch_metadata", previous)
    kernel = SimpleNamespace(src=SimpleNamespace(fn=SimpleNamespace(
        arg_names=["X", "N"])))
    hook = LaunchHook()
    try:
        yield hook, kernel, previous, calls
    finally:
        HookManager.unregister()
        hook.deactivate()


def test_metadata_is_lazy_and_user_keys_are_unchanged(launch_adapter):
    hook, kernel, previous, calls = launch_adapter
    value = object()
    hook.activate()
    wrapper = CompiledKernel.launch_metadata
    hook.activate()
    assert CompiledKernel.launch_metadata is wrapper
    metadata = CompiledKernel.launch_metadata(kernel, (1, 2, 3), 7, value, 32)
    assert len(calls) == 1 and len(metadata.extras) == 1
    assert metadata._flagprism_launch_context == {
        "kernel": kernel,
        "grid": (1, 2, 3),
        "arguments": {
            "X": value,
            "N": 32
        }
    }
    assert metadata.get() == {"name": "probe", "stream": 7, "user_value": 17}
    assert not metadata.extras
    hook.deactivate()
    assert CompiledKernel.launch_metadata is previous
    assert not hasattr(
        CompiledKernel.launch_metadata(kernel, (1, ), 7, value, 32),
        "_flagprism_launch_context")


def test_multiple_sessions_pause_resume_and_finalize(launch_adapter):
    hook, kernel, previous, _ = launch_adapter
    HookManager.register(hook, 11)
    wrapper = CompiledKernel.launch_metadata
    HookManager.register(hook, 12)
    HookManager.deactivate(11)
    assert CompiledKernel.launch_metadata is wrapper
    HookManager.deactivate(12)
    assert CompiledKernel.launch_metadata is previous
    HookManager.activate(11)
    assert CompiledKernel.launch_metadata is not previous
    assert hasattr(CompiledKernel.launch_metadata(kernel, (1, ), 0, 1, 2),
                   "_flagprism_launch_context")
    HookManager.unregister(12)
    assert CompiledKernel.launch_metadata is not previous
    HookManager.unregister(11)
    assert CompiledKernel.launch_metadata is previous


def test_later_third_party_wrapper_is_not_overwritten(launch_adapter):
    hook, kernel, previous, _ = launch_adapter
    hook.activate()
    ours = CompiledKernel.launch_metadata
    calls = []

    def external(*args, **kwargs):
        calls.append(True)
        return ours(*args, **kwargs)

    CompiledKernel.launch_metadata = external
    hook.deactivate()
    assert CompiledKernel.launch_metadata is external
    assert not hasattr(external(kernel,
                                (1, ), 0, 1, 2), "_flagprism_launch_context")
    hook.activate()
    assert hasattr(CompiledKernel.launch_metadata(kernel, (1, ), 0, 1, 2),
                   "_flagprism_launch_context")
    hook.deactivate()
    assert CompiledKernel.launch_metadata is external
    assert len(calls) == 2


def test_original_exception_and_method_are_preserved(launch_adapter,
                                                     monkeypatch):
    hook, kernel, _, _ = launch_adapter
    error = ValueError("user metadata failure")

    def failing(*args, **kwargs):
        raise error

    monkeypatch.setattr(CompiledKernel, "launch_metadata", failing)
    hook.activate()
    with pytest.raises(ValueError) as caught:
        CompiledKernel.launch_metadata(kernel, (1, ), 0)
    assert caught.value is error
    hook.deactivate()
    assert CompiledKernel.launch_metadata is failing


@pytest.mark.parametrize("result", [None, {"name": "other"}])
def test_unrecognized_result_is_not_modified(launch_adapter, monkeypatch,
                                             result):
    hook, kernel, _, _ = launch_adapter
    monkeypatch.setattr(CompiledKernel, "launch_metadata",
                        lambda *args, **kwargs: result)
    hook.activate()
    assert CompiledKernel.launch_metadata(kernel, (1, ), 0) is result


def test_user_metadata_error_balances_profiler_state(launch_adapter,
                                                     monkeypatch):
    import flagtree.profiler.hooks.launch as launch
    hook, _, _, _ = launch_adapter
    calls = []
    monkeypatch.setattr(launch, "enter_state",
                        lambda name: calls.append("enter"))
    monkeypatch.setattr(launch, "exit_state", lambda: calls.append("exit"))
    metadata = LazyDict({"name": "probe"})

    def failing():
        raise ValueError("callback failed")

    metadata.add(failing, ())
    with pytest.raises(ValueError, match="callback failed"):
        hook.enter(metadata)
    assert calls == ["enter", "exit"]


@pytest.mark.parametrize("result", [None, {"name": "other"}])
def test_unrecognized_metadata_skips_enter_and_exit(launch_adapter,
                                                    monkeypatch, result):
    import flagtree.profiler.hooks.launch as launch
    hook, _, _, _ = launch_adapter
    monkeypatch.setattr(launch, "profiler_native", SimpleNamespace())
    hook.enter(result)
    hook.exit(result)


@pytest.mark.parametrize("callback_error", [False, True])
def test_consumed_context_does_not_retain_arguments(launch_adapter,
                                                    monkeypatch,
                                                    callback_error):
    import weakref
    import flagtree.profiler.hooks.launch as launch
    hook, _, _, _ = launch_adapter
    monkeypatch.setattr(launch, "enter_state", lambda name: None)
    monkeypatch.setattr(launch, "exit_state", lambda: None)
    monkeypatch.setattr(
        launch, "profiler_native",
        SimpleNamespace(record_scope=lambda: 1,
                        enter_op=lambda *args: None,
                        exit_op=lambda *args: None,
                        add_metrics=lambda *args: None))
    monkeypatch.setattr(hook, "record_launch", lambda *args: None)

    class Argument:
        pass

    value = Argument()
    reference = weakref.ref(value)
    metadata = LazyDict({"name": "probe"})
    metadata._flagprism_launch_context = {"arguments": {"X": value}}
    del value
    if callback_error:

        def failing():
            raise ValueError("callback failed")

        metadata.add(failing, ())
        with pytest.raises(ValueError, match="callback failed"):
            hook.enter(metadata)
    else:
        hook.enter(metadata)
        hook.exit(metadata)
    assert not hasattr(metadata, "_flagprism_launch_context")
    assert reference() is None


def test_pointer_wrapper_description_is_optional():
    from flagtree.profiler.hooks.launch import _argument

    class Pointer:
        dtype = "float32"
        shape = (16, )

        def data_ptr(self):
            return 16

        def stride(self):
            return (1, )

    assert _argument(Pointer()) == {"status": "unavailable", "type": "Pointer"}
