"""Automatic NVIDIA activation and pre-launch rejection contracts."""
import pytest


@pytest.fixture(autouse=True)
def require_nvidia_compiler():
    # Do not import the NVIDIA hook in a vendor-only compiler installation.
    # These are NVIDIA binding tests; a skip is not NVIDIA qualification.
    from triton._C import libtriton
    if not hasattr(libtriton, 'nvidia'):
        pytest.skip(
            'NVIDIA compiler bindings are required for NVIDIA hook tests')


def test_old_inventory_plugin_is_rejected_before_activation(monkeypatch):
    import pytest
    from flagtree.profiler.hooks import instrumentation
    from flagtree.profiler.observations_nvidia import lower_request
    from flagtree.profiler.flags import get_instrumentation_on
    plan = lower_request({'automatic': True})
    hook = instrumentation.InstrumentationHook(None, observation_plan=plan)
    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    monkeypatch.setattr(instrumentation.triton_proton,
                        'AUTOMATIC_INVENTORY_VERSION', 1)
    with pytest.raises(RuntimeError,
                       match='matching FlagPrism compiler plugin'):
        hook.activate()
    assert instrumentation.InstrumentationHook.active_count == 0
    assert not get_instrumentation_on()


def test_old_control_policy_plugin_is_rejected_before_activation(monkeypatch):
    import pytest
    from flagtree.profiler.hooks import instrumentation
    from flagtree.profiler.observations_nvidia import lower_request
    from flagtree.profiler.flags import get_instrumentation_on
    plan = lower_request({'automatic': True})
    hook = instrumentation.InstrumentationHook(None, observation_plan=plan)
    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    monkeypatch.setattr(instrumentation.triton_proton,
                        'AUTOMATIC_SELECTION_POLICY_VERSION', 1)
    with pytest.raises(RuntimeError,
                       match='matching FlagPrism compiler plugin'):
        hook.activate()
    assert instrumentation.InstrumentationHook.active_count == 0
    assert not get_instrumentation_on()


def test_raw_capture_rejects_graph_before_original_run_and_recovers(
        monkeypatch):
    from types import SimpleNamespace
    import pytest
    import torch
    from flagtree.profiler.hooks import instrumentation
    state = {'capturing': True, 'calls': 0}

    def original(jit, *args, **kwargs):
        state['calls'] += 1
        return 'eager-result'

    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    active = SimpleNamespace(
        get_current_device=lambda: 0,
        utils=SimpleNamespace(
            get_device_properties=lambda device: {'max_shared_mem': 65536}))
    monkeypatch.setattr(instrumentation.triton.runtime, 'driver',
                        SimpleNamespace(active=active))
    monkeypatch.setattr(instrumentation, 'set_profile_allocator',
                        lambda allocator: None)
    monkeypatch.setattr(instrumentation.profiler_native,
                        'set_raw_capture_enabled', lambda enabled: None)
    monkeypatch.setattr(instrumentation.profiler_native,
                        'set_observation_programs', lambda programs: None)
    monkeypatch.setattr(instrumentation.JITFunction, 'run', original)
    monkeypatch.setattr(torch.cuda, 'is_current_stream_capturing',
                        lambda: state['capturing'])
    hook = instrumentation.InstrumentationHook(None)
    hook.activate()
    try:
        with pytest.raises(
                RuntimeError,
                match='eager launches only.*native-only CUDA graph'):
            instrumentation.JITFunction.run(object())
        assert state['calls'] == 0
        assert not hook._observation_run_lock.locked()
        state['capturing'] = False
        assert instrumentation.JITFunction.run(object()) == 'eager-result'
        assert state['calls'] == 1
    finally:
        hook.deactivate()
    assert instrumentation.InstrumentationHook.active_count == 0
