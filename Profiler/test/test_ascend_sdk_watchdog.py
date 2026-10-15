"""Exercise the real SDK wrapper's child group and retained stream protocol."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest

DRIVER = Path(__file__).parents[1] / 'python/flagtree_profiler/ascend_sdk_driver.py'


def run(tmp_path, code, timeout='120'):
    env = dict(os.environ, FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(tmp_path),
               FLAGPRISM_ASCEND_COMPILE_ID='watchdog-test',
               FLAGPRISM_ASCEND_COMPILE_TIMEOUT_S=timeout)
    result = subprocess.run([sys.executable, str(DRIVER), sys.executable, '-c', code],
                            env=env, capture_output=True, timeout=15)
    return result


@pytest.mark.parametrize('exit_code', [0, 7])
def test_normal_exit_preserves_original_exit_and_streams(tmp_path, exit_code):
    result = run(tmp_path, 'import sys; print("sdk stdout",flush=True); print("sdk stderr",file=sys.stderr,flush=True); sys.exit(' + str(exit_code) + ')')
    receipt = json.loads((tmp_path / 'sdk-compiler.json').read_text())
    assert result.returncode == exit_code
    assert receipt['state'] == ('failed' if exit_code else 'finished') and receipt['returncode'] == exit_code
    assert receipt['timeout_s'] == 120
    assert (tmp_path / 'sdk-stdout.txt').read_text() == 'sdk stdout\n'
    assert (tmp_path / 'sdk-stderr.txt').read_text() == 'sdk stderr\n'
    assert not any(stream['truncated'] for stream in receipt['streams'].values())


def test_deadline_kills_sdk_descendants_and_keeps_partial_logs(tmp_path):
    child_pid_file = tmp_path / 'descendant.pid'
    child = 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("descendant started",flush=True);time.sleep(60)'
    code = ('import subprocess,sys,time,pathlib;'
            f'p=subprocess.Popen([sys.executable,"-c",{child!r}]);'
            f'pathlib.Path({str(child_pid_file)!r}).write_text(str(p.pid));'
            'print("compiler started",flush=True);time.sleep(60)')
    started = time.monotonic()
    result = run(tmp_path, code, timeout='1')
    assert result.returncode == 124 and time.monotonic() - started < 10
    receipt = json.loads((tmp_path / 'sdk-compiler.json').read_text())
    assert receipt['state'] == 'timed_out' and receipt['returncode'] == 124
    assert receipt['sdk_process_returncode'] == -signal.SIGKILL
    assert receipt['process_group_id'] == receipt['process_id']
    assert receipt['timeout_s'] == 1
    stdout = (tmp_path / 'sdk-stdout.txt').read_text()
    assert 'compiler started' in stdout and 'descendant started' in stdout
    assert b'evidence retained at' in result.stderr
    descendant = int(child_pid_file.read_text())
    # A killed descendant may briefly remain an init-owned zombie. It must no
    # longer execute or retain its output descriptors after the wrapper returns.
    stat = Path(f'/proc/{descendant}/stat')
    assert not stat.exists() or stat.read_text().split()[2] == 'Z'


@pytest.mark.parametrize('timeout', ['0', '301', 'nan', '-1'])
def test_invalid_deadline_cannot_start_sdk_process(tmp_path, timeout):
    marker = tmp_path / 'should-not-run'
    result = run(tmp_path, f'open({str(marker)!r},"w").write("ran")', timeout)
    assert result.returncode != 0 and not marker.exists()


def test_cancelled_wrapper_cleans_only_its_sdk_group_and_keeps_error(tmp_path):
    env = dict(os.environ, FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(tmp_path),
               FLAGPRISM_ASCEND_COMPILE_ID='cancel-test')
    code = 'import time;print("SDK active",flush=True);time.sleep(60)'
    process = subprocess.Popen([sys.executable, str(DRIVER), sys.executable, '-c', code],
                               env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'])
    try:
        receipt_path = tmp_path / 'sdk-compiler.json'
        deadline = time.monotonic() + 5
        receipt = {}
        while time.monotonic() < deadline:
            try:
                receipt = json.loads(receipt_path.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            if receipt.get('process_id') and (tmp_path / 'sdk-stdout.txt').exists():
                break
            time.sleep(.01)
        assert receipt.get('process_id'), 'SDK did not start'
        # Wait for a concrete SDK log line before interruption, rather than
        # relying on startup scheduling or a fabricated retained stream.
        while time.monotonic() < deadline:
            if (tmp_path / 'sdk-stdout.txt').stat().st_size:
                break
            # Capture writes are buffered; the live forwarded pipe is the
            # authoritative startup marker even before the file is flushed.
            import select
            if select.select([process.stdout], [], [], .05)[0]:
                assert b'SDK active' in process.stdout.readline()
                break
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=10)
        receipt = json.loads(receipt_path.read_text())
        assert process.returncode != 0 and 'KeyboardInterrupt' in receipt['error']
        assert receipt['state'] == 'failed'
        assert receipt['sdk_process_returncode'] == -signal.SIGKILL
        assert 'SDK active' in (tmp_path / 'sdk-stdout.txt').read_text()
        assert unrelated.poll() is None, 'cleanup escaped the owned SDK group'
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        unrelated.terminate()
        unrelated.wait(timeout=5)
