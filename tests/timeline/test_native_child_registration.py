"""Registration faults after real Popen; no SDK or device execution.

The child is an owned Python sleep process, even for compiler call sites.
SDK paths/identities are explicit fixtures so the tests isolate cleanup.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.mark.parametrize(
    'target', ['gcu_rewrite', 'gcu_clock', 'ascend_reader', 'nvidia_compile'])
@pytest.mark.parametrize(
    'fault',
    ['process_identity', 'persistent_process_identity', 'first_receipt'])
def test_registration_fault_reaps_direct_child(tmp_path, monkeypatch, target,
                                               fault):
    from flagtree.debugger import gcu_timeline, gcu_clock
    from flagtree.profiler import timeline_ascend_machine, timeline_nvidia_late_compile
    modules = dict(gcu_rewrite=gcu_timeline,
                   gcu_clock=gcu_clock,
                   ascend_reader=timeline_ascend_machine,
                   nvidia_compile=timeline_nvidia_late_compile)
    module = modules[target]
    real_popen, real_read, real_write = subprocess.Popen, Path.read_text, Path.write_text
    children, injected = [], []

    def start(argv, **kwargs):
        child = real_popen(
            [sys.executable, '-I', '-c', 'import time; time.sleep(30)'],
            **kwargs)
        children.append(child)
        fields = real_read(Path('/proc/' + str(child.pid) + '/stat')).rsplit(
            ')', 1)[1].split()
        (tmp_path / 'fixture-child.json').write_text(
            json.dumps(dict(pid=child.pid,
                            pgid=int(fields[2]),
                            startticks=int(fields[19]),
                            argv=child.args,
                            target=target,
                            fault=fault),
                       indent=2))
        return child

    def read(path, *args, **kwargs):
        if (children and fault
                in ('process_identity', 'persistent_process_identity')
                and (not injected or fault == 'persistent_process_identity')
                and str(path) == '/proc/' + str(children[0].pid) + '/stat'):
            injected.append(fault)
            raise OSError('Injected process registration failure')
        return real_read(path, *args, **kwargs)

    def write(path, *args, **kwargs):
        if (children and fault == 'first_receipt' and not injected
                and path.name
                in ('launch.json', 'commands.json', 'compile-receipt.json')):
            injected.append(fault)
            raise OSError('Injected receipt registration failure')
        return real_write(path, *args, **kwargs)

    # Fixtures never use these fake paths to compile or execute SDK code.
    tops = tmp_path / 'tops'
    (tops / 'bin').mkdir(parents=True)
    (tops / 'bin/opt').symlink_to(sys.executable)
    sdk = tops / 'llvm11/lib/krt/gcu300_api_profile.bc'
    sdk.parent.mkdir(parents=True)
    sdk.write_bytes(b'CPU cleanup fixture, not SDK bitcode')
    identity = {'cpu_cleanup_fixture': True}
    monkeypatch.setattr(gcu_timeline, 'tool_identity', lambda: identity)
    monkeypatch.setattr(gcu_timeline, 'packaged_tool',
                        lambda: Path(sys.executable))
    monkeypatch.setattr(module.subprocess, 'Popen', start)
    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr(Path, 'write_text', write)
    started = time.monotonic()
    try:
        with pytest.raises(OSError, match='Injected'):
            if target == 'gcu_rewrite':
                module.rewrite_execution_ir(
                    'CPU fixture',
                    dict(debug_execution_version=1,
                         debug_execution_tool_identity=identity,
                         debug_execution_hidden_argument=0,
                         debug_record_capacity=1,
                         debug_execution_max_sites=8))
            elif target == 'gcu_clock':
                module.identity_library(tops_home=tops,
                                        cache_root=tmp_path / 'clock-cache')
            elif target == 'ascend_reader':
                module._run(Path(sys.executable),
                            ['-I', '-c', 'import time; time.sleep(30)'],
                            tmp_path, 'reader',
                            time.monotonic() + 5, [])
            else:
                transform = module.LateLLVMTransform(sys.executable,
                                                     tmp_path / 'compile',
                                                     timeout=5)
                transform('define void @fixture() { ret void }', {})
        assert injected and set(injected) == {fault}
        assert time.monotonic() - started < 10
        assert len(children) == 1
        assert children[0].returncode is not None
        if target == 'gcu_clock':
            assert children[0].stdout.closed and children[0].stderr.closed
        with pytest.raises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)
    finally:
        # A regression must not leave a live test child behind.
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)
