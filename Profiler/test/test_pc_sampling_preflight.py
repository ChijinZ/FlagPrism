"""Public start must validate exact requested PC configuration before mutation.

Native SDK-shim tests separately prove that this boundary refuses conflicts
without touching a live collector. These CPU tests exercise public argument and
side-effect ordering; no device or native session is started.
"""
import importlib
from types import SimpleNamespace

import pytest


@pytest.fixture
def profile(monkeypatch):
    module = importlib.import_module('flagtree.profiler.profile')
    monkeypatch.setattr(module, '_active_sessions', {})
    monkeypatch.setattr(module, '_get_backend_default_path', lambda _: '/sdk')
    return module


@pytest.mark.parametrize('backend,mode,expected', [
    ('cupti_pcsampling', None, 'pcsampling'),
    ('cupti_pcsampling', 'pcsampling:interval=1000',
     'pcsampling:interval=1000'),
    ('cupti', 'pcsampling:interval=2000', 'pcsampling:interval=2000'),
])
def test_public_pc_request_reaches_native_guard_before_any_session_side_effect(
        profile, monkeypatch, tmp_path, backend, mode, expected):
    calls = []
    live = {
        'session': 7,
        'backend': 'cupti',
        'active': True,
        'effective_mode': '',
        'bundle_output': tmp_path / 'existing'
    }
    profile._active_sessions[7] = live.copy()

    def validate(path, requested_mode=""):
        calls.append((path, requested_mode))
        raise RuntimeError('native collector configuration conflict')

    def forbidden(*args, **kwargs):
        raise AssertionError('rejected probe mutated public session state')

    monkeypatch.setattr(
        profile, 'profiler_native',
        SimpleNamespace(validate_pc_sampling_support=validate,
                        start=forbidden))
    monkeypatch.setattr(profile, 'set_profiling_on', forbidden)
    monkeypatch.setattr(profile.LaunchHook, 'reset_capture', forbidden)
    output = tmp_path / 'new'
    with pytest.raises(RuntimeError,
                       match='native collector configuration conflict'):
        profile.start(str(output), backend=backend, mode=mode)
    assert calls == [('/sdk', expected)]
    assert profile._active_sessions == {7: live}
    assert not output.exists()


def test_same_pc_output_reuse_keeps_exact_mode_at_native_guard(
        profile, monkeypatch, tmp_path):
    output = (tmp_path / 'existing').resolve()
    live = {
        'session': 7,
        'backend': 'cupti_pcsampling',
        'active': True,
        'effective_mode': 'pcsampling:interval=1000',
        'context': 'shadow',
        'data': 'tree',
        'hook': None,
        'observation_request': None,
        'bundle_output': output
    }
    profile._active_sessions[7] = live.copy()
    calls = []
    monkeypatch.setattr(
        profile, 'profiler_native',
        SimpleNamespace(validate_pc_sampling_support=lambda path, mode: calls.
                        append((path, mode))))
    monkeypatch.setattr(profile, 'activate', lambda sid: calls.append(
        ('activate', sid)))
    result = profile.start(str(output),
                           backend='cupti_pcsampling',
                           mode='pcsampling:interval=1000')
    assert result == 7
    assert calls == [('/sdk', 'pcsampling:interval=1000'), ('activate', 7)]
    assert profile._active_sessions == {7: live}
