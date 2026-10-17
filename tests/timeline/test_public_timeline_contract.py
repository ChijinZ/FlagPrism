"""Public timeline rejection/finalization contracts, no device qualification."""
import importlib
from types import SimpleNamespace
import pytest


def test_export_failure_still_finalizes_native_and_drops_session(monkeypatch):
    profile = importlib.import_module('flagtree.profiler.profile')
    actions = []
    def fail_export(_):
        raise OSError('injected timeline export failure')
    state = dict(session=37, name='capture', timeline_hook=SimpleNamespace(flush_timeline=fail_export))
    monkeypatch.setattr(profile, '_active_sessions', {37: state})
    monkeypatch.setattr(profile, 'is_command_line', lambda: False)
    monkeypatch.setattr(profile, 'profiler_native', SimpleNamespace(finalize=lambda *args: actions.append('native_finalized')))
    monkeypatch.setattr(profile, '_snapshot_session', lambda state: None)
    monkeypatch.setattr(profile, '_snapshot_cann_launch_receipts', lambda state: None)
    monkeypatch.setattr(profile, '_export_native_observations', lambda state: None)
    monkeypatch.setattr(profile, '_drop_session', lambda session: actions.append('dropped'))
    with pytest.raises(RuntimeError, match='injected timeline export failure'):
        profile._finalize_impl(37)
    if actions != ['native_finalized', 'dropped']:
        raise RuntimeError('Export failure leaked native session lifecycle')


def test_old_launcher_rejected_before_hook_activation(monkeypatch):
    from flagtree.profiler.hooks import instrumentation
    import triton.backends.nvidia.driver as driver
    from flagtree.profiler.flags import get_instrumentation_on
    hook = instrumentation.InstrumentationHook(None, observation_plan=dict(
        automatic=True, timeline=True, output_selection={'programs': None}))
    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    monkeypatch.setattr(driver.CudaLauncher, 'profile_admission_version', 1)
    with pytest.raises(RuntimeError, match='preallocation-admission.patch v2'):
        hook.activate()
    if instrumentation.InstrumentationHook.active_count or get_instrumentation_on():
        raise RuntimeError('Old launcher rejection left instrumentation active')
