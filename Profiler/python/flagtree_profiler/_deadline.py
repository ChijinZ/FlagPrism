"""Linux CLI worker deadlines; user application code executes only in the worker.

Application runtime is unbounded. Compilation and export phases are bounded;
Python threads cannot safely interrupt a native collector holding the GIL.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

CONTROL = 'FLAGPRISM_DEADLINE_CONTROL'
WORKER = 'FLAGPRISM_DEADLINE_WORKER'
OWNER = 'FLAGPRISM_DEADLINE_OWNER'
_context = {}
_last_phase = None
_last_started = 0.0
_export_elapsed = 0.0


def phase(name, **context):
    global _last_phase, _last_started, _export_elapsed
    path = os.environ.get(CONTROL)
    if not path or os.environ.get(OWNER) != str(os.getpid()):
        return
    now = time.monotonic()
    if _last_phase == 'export':
        _export_elapsed += now - _last_started
    _last_phase, _last_started = name, now
    _context.update(context)
    document = dict(phase=name,
                    pid=os.getpid(),
                    started=now,
                    export_elapsed=_export_elapsed,
                    context=_context)
    target = Path(path)
    temporary = target.with_name(
        target.name + f'.{os.getpid()}.{threading.get_ident()}.writing')
    temporary.write_text(json.dumps(document))
    os.replace(temporary, target)


def _restore_phase(name):
    original_error = sys.exc_info()[1]
    try:
        phase(name)
    except Exception as error:
        if original_error is None:
            raise
        message = f'Deadline status update also failed: {error}'
        if hasattr(original_error, 'add_note'):
            original_error.add_note(message)
        else:
            print(message, file=sys.stderr)


@contextmanager
def export_phase():
    previous = _last_phase or 'application'
    phase('export')
    try:
        yield
    finally:
        _restore_phase(previous)


def bind_worker():
    os.environ[OWNER] = str(os.getpid())
    from triton.runtime.jit import JITFunction
    original = JITFunction.run
    lock = threading.Lock()

    def bounded_run(self, *args, **kwargs):
        if not lock.acquire(blocking=False):
            raise RuntimeError(
                'Concurrent automatic CLI JIT calls require separate capture processes'
            )
        try:
            phase('compile')
            return original(self, *args, **kwargs)
        finally:
            try:
                _restore_phase('application')
            finally:
                lock.release()

    # Preserve the normal run wrapper protocol used by instrumentation hooks.
    import functools
    JITFunction.run = functools.wraps(original)(bounded_run)
    phase('startup')


def _processes():
    result = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            text = path.read_text()
            fields = text[text.rindex(')') + 2:].split()
            result[int(path.parent.name)] = (int(fields[1]), int(fields[19]))
        except (OSError, ValueError, IndexError):
            continue
    return result


def _stop_worker(process):
    """Freeze and kill only this worker's descendants, including new sessions."""
    table = _processes()
    if process.pid not in table:
        return
    owned = {process.pid: table[process.pid][1]}
    for _ in range(3):
        changed = True
        while changed:
            changed = False
            for pid, (parent, started) in table.items():
                if parent in owned and pid not in owned:
                    owned[pid] = started
                    changed = True
        for pid, started in owned.items():
            current = _processes().get(pid)
            if current and current[1] == started:
                try:
                    os.kill(pid, signal.SIGSTOP)
                except ProcessLookupError:
                    pass
        table = _processes()
    for pid, started in reversed(list(owned.items())):
        current = _processes().get(pid)
        if current and current[1] == started:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    process.wait(timeout=10)


def _retain_success(document, limits):
    output = document.get('context', {}).get('output')
    if not output or not (Path(output) / 'manifest.json').is_file():
        return
    output = Path(output)
    name = 'ai/deadlines.json'
    payload = (json.dumps(dict(schema_version=1,
                               enforced=True,
                               limits_seconds=limits,
                               supervisor_worker_launches=1,
                               application_runtime_limit=None,
                               mechanism='separate_worker_phase_watchdog'),
                          indent=2) + '\n').encode()
    (output / name).write_bytes(payload)
    manifest_path = output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files'][name] = dict(bytes=len(payload),
                                   sha256=hashlib.sha256(payload).hexdigest())
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


def worker_command(module, arguments):
    # CPython's own subprocess flag propagation preserves -I/-E/-s/-O/-X,
    # rather than silently changing import isolation or __debug__ in the app.
    return [
        sys.executable, *subprocess._args_from_interpreter_flags(), '-m',
        module, *arguments
    ]


class _Cancelled(BaseException):

    def __init__(self, signum):
        self.signum = signum


def _cancel(signum, frame):
    raise _Cancelled(signum)


def supervise(command,
              *,
              compile_seconds=120,
              export_seconds=60,
              require_capture=False):
    if type(compile_seconds) is not int or not 1 <= compile_seconds <= 300:
        raise ValueError(
            'compile deadline must be an integer in [1,300] seconds')
    if type(export_seconds) is not int or not 1 <= export_seconds <= 60:
        raise ValueError(
            'export deadline must be an integer in [1,60] seconds')
    directory = Path(tempfile.mkdtemp(prefix='flagprism-deadline-'))
    control = directory / 'phase.json'
    env = dict(os.environ, **{CONTROL: str(control), WORKER: '1'})
    env.pop(OWNER, None)
    started = time.monotonic()
    process = subprocess.Popen(command, env=env, start_new_session=True)
    limits = {
        'startup': 120,
        'compile': compile_seconds,
        'export': export_seconds
    }
    document = dict(phase='startup',
                    pid=process.pid,
                    started=started,
                    context={})
    previous_handlers = {}
    try:
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, _cancel)
        while process.poll() is None:
            try:
                candidate = json.loads(control.read_text())
                owner = candidate.get('pid')
                if owner == process.pid:
                    document = candidate
                elif type(owner) is int:
                    table = _processes()
                    seen = set()
                    while owner in table and owner not in seen:
                        seen.add(owner)
                        owner = table[owner][0]
                        if owner == process.pid:
                            document = candidate
                            break
            except (OSError, ValueError):
                pass
            limit = limits.get(document.get('phase'))
            elapsed = time.monotonic() - document['started']
            if document.get('phase') == 'export':
                elapsed += document.get('export_elapsed', 0.0)
            if limit is not None and elapsed > limit:
                _stop_worker(process)
                document.update(timeout_seconds=limit,
                                worker_returncode=process.returncode,
                                state='timed_out',
                                control_directory=str(directory))
                (directory / 'timeout.json').write_text(
                    json.dumps(document, indent=2))
                print(
                    f"FlagPrism {document['phase']} exceeded {limit}s; owned worker stopped. "
                    f"Evidence retained at {directory}; capture paths: {document.get('context')}",
                    file=sys.stderr)
                return 124
            time.sleep(.05)
        code = process.returncode
        if code == 0:
            # Read the last context even when the final phase was very short.
            if control.is_file():
                document = json.loads(control.read_text())
            output = document.get('context', {}).get('output')
            if require_capture and (
                    not output
                    or not (Path(output) / 'manifest.json').is_file()):
                document.update(
                    state='incomplete',
                    reason='worker_exited_without_completed_capture',
                    worker_returncode=0)
                (directory / 'incomplete.json').write_text(
                    json.dumps(document, indent=2))
                raise RuntimeError(
                    'Automatic profiling worker exited without a completed '
                    f'capture; evidence retained at {directory}')
            _retain_success(document, limits)
            import shutil
            shutil.rmtree(directory)
        return code if code >= 0 else 128 - code
    except BaseException as error:
        # A second cancellation must not interrupt cleanup and orphan a job.
        for signum in previous_handlers:
            signal.signal(signum, signal.SIG_IGN)
        if process.poll() is None:
            _stop_worker(process)
        if isinstance(error, _Cancelled):
            (directory / 'cancelled.json').write_text(
                json.dumps(
                    {
                        'state': 'cancelled',
                        'signal': error.signum,
                        'worker_pid': process.pid,
                        'phase': document,
                    },
                    indent=2))
            print(
                f'FlagPrism worker cancelled; evidence retained at {directory}',
                file=sys.stderr)
            return 128 + error.signum
        raise
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
