"""Real worker processes verify deadline isolation, replay and retained evidence."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

MODULE = Path(__file__).parents[1] / 'python/flagtree_profiler/_deadline.py'


@pytest.fixture
def deadline():
    spec = importlib.util.spec_from_file_location('deadline_test', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(tmp_path, body):
    source = tmp_path / 'worker.py'
    source.write_text(
        'import importlib.util, os, time\n'
        f'spec=importlib.util.spec_from_file_location("worker_deadline", {str(MODULE)!r})\n'
        'd=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(d)\n'
        'os.environ[d.OWNER]=str(os.getpid())\n' + textwrap.dedent(body))
    return [sys.executable, str(source)]


def test_application_executes_once_without_application_runtime_deadline(
        deadline, tmp_path):
    ledger = tmp_path / 'ledger'
    code = deadline.supervise(command(
        tmp_path, f'''
        from pathlib import Path
        d.phase('application')
        with open({str(ledger)!r}, 'a') as file: file.write('once\\n')
        time.sleep(1.2)
    '''),
                              compile_seconds=1,
                              export_seconds=1)
    assert code == 0
    assert ledger.read_text() == 'once\n'


def test_compile_timeout_retains_own_evidence(deadline, tmp_path, capsys):
    code = deadline.supervise(command(
        tmp_path, '''
        d.phase('compile', staging='retained-stage')
        time.sleep(15)
    '''),
                              compile_seconds=1)
    assert code == 124
    assert 'retained-stage' in capsys.readouterr().err


def test_split_export_phases_share_one_budget(deadline, tmp_path):
    code = deadline.supervise(command(
        tmp_path, '''
        with d.export_phase(): time.sleep(.7)
        time.sleep(.1)
        with d.export_phase(): time.sleep(.7)
    '''),
                              export_seconds=1)
    assert code == 124


def test_nested_export_context_does_not_remove_outer_deadline(
        deadline, tmp_path):
    code = deadline.supervise(command(
        tmp_path, '''
        with d.export_phase():
            with d.export_phase(): time.sleep(.1)
            time.sleep(10)
    '''),
                              export_seconds=1)
    assert code == 124


def test_original_failure_is_forwarded(deadline, tmp_path):
    assert deadline.supervise(command(tmp_path, "raise SystemExit(7)")) == 7


@pytest.mark.parametrize('values', [{
    'compile_seconds': 0
}, {
    'compile_seconds': 301
}, {
    'export_seconds': 61
}, {
    'export_seconds': True
}])
def test_invalid_deadline_never_launches_worker(deadline, tmp_path, values):
    with pytest.raises(ValueError):
        deadline.supervise(['cannot-exist'], **values)


def test_descendant_in_separate_session_stops_and_unrelated_survives(
        deadline, tmp_path):
    pidfile = tmp_path / 'descendant'
    unrelated = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(20)'])
    try:
        code = deadline.supervise(command(
            tmp_path, f'''
            import subprocess, sys
            child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], start_new_session=True)
            from pathlib import Path
            Path({str(pidfile)!r}).write_text(str(child.pid))
            d.phase('compile')
            time.sleep(20)
        '''),
                                  compile_seconds=1)
        assert code == 124
        assert unrelated.poll() is None
        pid = int(pidfile.read_text())
        stat = Path(f'/proc/{pid}/stat')
        assert not stat.exists() or stat.read_text().split(
            ') ', 1)[1].startswith('Z ')
    finally:
        unrelated.kill()
        unrelated.wait()


def test_worker_keeps_interpreter_isolation_and_debug_flags(
        deadline, monkeypatch):
    monkeypatch.setattr(deadline.subprocess, '_args_from_interpreter_flags',
                        lambda: ['-I', '-O'])
    command = deadline.worker_command('flagtree.profiler.cli',
                                      ['--detail', 'auto', 'app.py'])
    assert command == [
        sys.executable, '-I', '-O', '-m', 'flagtree.profiler.cli', '--detail',
        'auto', 'app.py'
    ]


def test_native_call_holding_python_gil_is_still_stopped(deadline, tmp_path):
    code = deadline.supervise(command(
        tmp_path, '''
        import ctypes
        d.phase('export')
        ctypes.PyDLL(None).sleep(15)
    '''),
                              export_seconds=1)
    assert code == 124


def test_success_receipt_and_manifest_are_consistent(deadline, tmp_path):
    output = tmp_path / 'bundle'
    (output / 'ai').mkdir(parents=True)
    (output / 'manifest.json').write_text('{"files":{}}')
    assert deadline.supervise(
        command(tmp_path,
                f"d.phase('application', output={str(output)!r})")) == 0
    receipt = json.loads((output / 'ai/deadlines.json').read_text())
    assert receipt['enforced'] and receipt['supervisor_worker_launches'] == 1
    import hashlib
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['files']['ai/deadlines.json']['sha256'] == hashlib.sha256(
        (output / 'ai/deadlines.json').read_bytes()).hexdigest()


def test_status_write_failure_preserves_original_exception(
        deadline, monkeypatch):

    def fake_phase(name, **context):
        if name != 'export':
            raise OSError('phase disk failure')

    monkeypatch.setattr(deadline, 'phase', fake_phase)
    with pytest.raises(ValueError, match='original app failure'):
        with deadline.export_phase():
            raise ValueError('original app failure')


def test_controller_sigterm_cleans_worker_and_preserves_other_process(
        tmp_path):
    import os
    import signal
    import time
    pidfile = tmp_path / 'worker-pid'
    worker = command(
        tmp_path,
        f"from pathlib import Path; Path({str(pidfile)!r}).write_text(str(os.getpid())); d.phase('application'); time.sleep(30)"
    )
    controller = tmp_path / 'controller.py'
    controller.write_text(
        'import importlib.util\n'
        f'spec=importlib.util.spec_from_file_location("controller_deadline", {str(MODULE)!r})\n'
        'd=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(d)\n'
        f'raise SystemExit(d.supervise({worker!r}))\n')
    unrelated = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(30)'])
    process = subprocess.Popen([sys.executable, str(controller)])
    try:
        deadline_at = time.monotonic() + 5
        while not pidfile.exists() and time.monotonic() < deadline_at:
            time.sleep(.02)
        assert pidfile.exists()
        os.kill(process.pid, signal.SIGTERM)
        assert process.wait(timeout=10) == 143
        worker_pid = int(pidfile.read_text())
        stat = Path(f'/proc/{worker_pid}/stat')
        assert not stat.exists() or stat.read_text().split(
            ') ', 1)[1].startswith('Z ')
        assert unrelated.poll() is None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        unrelated.kill()
        unrelated.wait()
