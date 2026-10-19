"""CPU fault injection for an actually started optional inspection child."""
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from flagtree.profiler import timeline_nvidia_machine as machine


@pytest.mark.parametrize(
    'fault',
    ['process_identity', 'persistent_process_identity', 'command_receipt'])
def test_registration_failure_reaps_owned_child(tmp_path, monkeypatch, fault):
    popen = subprocess.Popen
    read_text = Path.read_text
    write_text = Path.write_text
    children = []
    injected = []

    def start(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child

    def read(path, *args, **kwargs):
        if (fault in ('process_identity', 'persistent_process_identity')
                and children
                and (not injected or fault == 'persistent_process_identity')
                and str(path) == '/proc/' + str(children[0].pid) + '/stat'):
            injected.append(fault)
            raise OSError('Injected process registration failure')
        return read_text(path, *args, **kwargs)

    def write(path, *args, **kwargs):
        if fault == 'command_receipt' and path.name == 'commands.json' and not injected:
            injected.append(fault)
            raise OSError('Injected receipt registration failure')
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(machine.subprocess, 'Popen', start)
    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr(Path, 'write_text', write)
    started = time.monotonic()
    try:
        with pytest.raises(OSError, match='Injected'):
            machine._run_tool(Path(sys.executable),
                              ['-I', '-c', 'import time; time.sleep(30)'],
                              tmp_path, 'source-lines',
                              time.monotonic() + 5, [])
        assert injected and set(injected) == {fault}
        assert time.monotonic() - started < 10
        assert len(children) == 1
        assert children[0].returncode is not None
        with pytest.raises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)
    finally:
        # Avoid leaving a test child if this regression ever returns.
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
