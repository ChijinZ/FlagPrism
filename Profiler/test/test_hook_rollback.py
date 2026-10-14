"""A rejected later hook must release earlier scopes and preserve its error."""
import pytest

from flagtree.profiler.hooks.hook import Hook, HookManager


def test_enter_failure_rolls_back_successful_hooks_in_reverse(monkeypatch):
    events = []
    original = ValueError('buffer is in use')

    class Probe(Hook):
        def __init__(self, name, fail=False):
            self.name, self.fail = name, fail

        def enter(self, metadata):
            events.append(('enter', self.name))
            if self.fail:
                raise original

        def abort_enter(self, metadata, error):
            assert error is original
            events.append(('abort', self.name))

    monkeypatch.setattr(HookManager, 'active_hooks',
                        [Probe('scope'), Probe('observer'), Probe('reject', True)])
    with pytest.raises(ValueError) as caught:
        HookManager.enter(None)
    assert caught.value is original
    assert events == [('enter', 'scope'), ('enter', 'observer'), ('enter', 'reject'),
                      ('abort', 'observer'), ('abort', 'scope')]
