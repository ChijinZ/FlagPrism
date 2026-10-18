"""Public timeline rejection/finalization contracts, no device qualification."""
import importlib
from types import SimpleNamespace
import pytest


def test_export_failure_still_finalizes_native_and_drops_session(monkeypatch):
    profile = importlib.import_module('flagtree.profiler.profile')
    actions = []

    def fail_export(_):
        raise OSError('injected timeline export failure')

    state = dict(session=37,
                 name='capture',
                 timeline_hook=SimpleNamespace(flush_timeline=fail_export))
    monkeypatch.setattr(profile, '_active_sessions', {37: state})
    monkeypatch.setattr(profile, 'is_command_line', lambda: False)
    monkeypatch.setattr(
        profile, 'profiler_native',
        SimpleNamespace(
            finalize=lambda *args: actions.append('native_finalized')))
    monkeypatch.setattr(profile, '_snapshot_session', lambda state: None)
    monkeypatch.setattr(profile, '_snapshot_cann_launch_receipts',
                        lambda state: None)
    monkeypatch.setattr(profile, '_export_native_observations',
                        lambda state: None)
    monkeypatch.setattr(profile, '_drop_session',
                        lambda session: actions.append('dropped'))
    with pytest.raises(RuntimeError, match='injected timeline export failure'):
        profile._finalize_impl(37)
    if actions != ['native_finalized', 'dropped']:
        raise RuntimeError('Export failure leaked native session lifecycle')


def test_old_launcher_rejected_before_hook_activation(monkeypatch):
    from flagtree.profiler.hooks import instrumentation
    import triton.backends.nvidia.driver as driver
    from flagtree.profiler.flags import get_instrumentation_on
    hook = instrumentation.InstrumentationHook(
        None,
        observation_plan=dict(automatic=True,
                              timeline=True,
                              output_selection={'programs': None}))
    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    monkeypatch.setattr(driver.CudaLauncher, 'profile_admission_version', 1)
    with pytest.raises(RuntimeError, match='preallocation-admission.patch v2'):
        hook.activate()
    if instrumentation.InstrumentationHook.active_count or get_instrumentation_on(
    ):
        raise RuntimeError(
            'Old launcher rejection left instrumentation active')


def test_old_boundary_compiler_rejected_before_hook_activation(monkeypatch):
    from flagtree.profiler.hooks import instrumentation
    from flagtree.profiler.flags import get_instrumentation_on
    from flagtree.profiler.native import compiler_binding
    hook = instrumentation.InstrumentationHook(
        None,
        observation_plan=dict(automatic=True,
                              timeline=True,
                              output_selection={'programs': None}))
    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    monkeypatch.setattr(compiler_binding(), 'TIMELINE_BOUNDARY_VERSION', 0)
    with pytest.raises(RuntimeError, match='matching native compiler ABI'):
        hook.activate()
    if instrumentation.InstrumentationHook.active_count or get_instrumentation_on(
    ):
        raise RuntimeError(
            'Boundary ABI rejection left instrumentation active')


def test_old_marker_compiler_rejected_before_hook_activation(monkeypatch):
    from flagtree.profiler.hooks import instrumentation
    from flagtree.profiler.flags import get_instrumentation_on
    from flagtree.profiler.native import compiler_binding
    hook = instrumentation.InstrumentationHook(
        None,
        observation_plan=dict(automatic=True,
                              timeline=True,
                              output_selection={'programs': None}))
    monkeypatch.setattr(instrumentation, '_get_backend_name', lambda: 'nvidia')
    monkeypatch.setattr(compiler_binding(), 'TIMELINE_MARKER_VERSION', 0)
    with pytest.raises(RuntimeError, match='matching native compiler ABI'):
        hook.activate()
    if instrumentation.InstrumentationHook.active_count or get_instrumentation_on(
    ):
        raise RuntimeError('Marker ABI rejection left instrumentation active')


@pytest.mark.parametrize('value', [True, False, 0, -1, 129, 1.5, '8'])
def test_timeline_density_rejected_before_runtime_discovery(
        monkeypatch, value):
    profile = importlib.import_module('flagtree.profiler.profile')
    monkeypatch.setattr(profile, 'is_command_line', lambda: False)

    def no_runtime(*args, **kwargs):
        raise RuntimeError('invalid request reached runtime discovery')

    monkeypatch.setattr(profile, '_automatic_backend', no_runtime)
    with pytest.raises(ValueError, match='timeline_max_sites'):
        profile.start('not-created',
                      detail='timeline',
                      timeline_max_sites=value)


@pytest.mark.parametrize('detail', [None, 'auto'])
def test_timeline_density_cannot_change_other_modes(monkeypatch, detail):
    profile = importlib.import_module('flagtree.profiler.profile')
    monkeypatch.setattr(profile, 'is_command_line', lambda: False)
    with pytest.raises(ValueError, match='requires detail'):
        profile.start('not-created', detail=detail, timeline_max_sites=4)


def test_cli_density_rejected_before_backend_discovery(monkeypatch):
    from flagtree.profiler import cli

    def no_runtime(*args, **kwargs):
        raise RuntimeError('invalid CLI reached runtime discovery')

    monkeypatch.setattr(cli, '_select_backend', no_runtime)
    with pytest.raises(ValueError, match='timeline_max_sites'):
        cli.run_profiling(
            SimpleNamespace(detail='timeline', timeline_max_sites=0), [])
