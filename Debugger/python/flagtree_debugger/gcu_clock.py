"""Owned GCU300 full SIPINFO getter; no masked-ID clock-domain inference.

The helper is linked by the actual SDK backend after MLIR translation. An
unwrapped llvm.dtu intrinsic in upstream MLIR is not a legal portable bridge.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

IDENTITY_SYMBOL = 'flagprism_gcu_clock_identity_v1'
IDENTITY_SOURCE = '''source_filename = "flagprism_gcu_clock_identity_v1.ll"
declare i32 @llvm.dtu.movs.sipinfo()
define i32 @flagprism_gcu_clock_identity_v1() {
 %v = call i32 @llvm.dtu.movs.sipinfo()
 ret i32 %v
}
'''


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity_library(*, tops_home='/opt/tops', cache_root=None):
    """Create/reuse sealed SDK bitcode, with bounded locking and compilation.

    Both the runtime's calibration kernel and the source observer producer link
    this same full-register getter. This function is never needed for offline
    decoding; retained bytes and their actual identities suffice there.
    """
    tool = (Path(tops_home) / 'bin/opt').resolve(strict=True)
    sdk = (Path(tops_home) /
           'llvm11/lib/krt/gcu300_api_profile.bc').resolve(strict=True)
    inputs = dict(version=1,
                  source=IDENTITY_SOURCE,
                  tool_file=str(tool),
                  tool_sha256=_sha(tool),
                  sdk_library_sha256=_sha(sdk))
    key = hashlib.sha256(json.dumps(inputs,
                                    sort_keys=True).encode()).hexdigest()
    base = Path(cache_root) if cache_root is not None else Path(
        tempfile.gettempdir()) / ('flagprism-gcu-clock-' + str(os.getuid()))
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if base.is_symlink() or base.stat().st_uid != os.getuid():
        raise ValueError('Clock helper cache must be owned by this user')
    directory = base / key
    directory.mkdir(exist_ok=True, mode=0o700)
    if directory.is_symlink():
        raise ValueError('Clock helper cache namespace cannot be a symlink')
    committed = directory / 'artifact'
    library, receipt = committed / 'identity.bc', committed / 'complete.json'
    lockfile = directory / 'lock'
    if lockfile.is_symlink():
        raise ValueError('Clock helper cache lock cannot be a symlink')
    with lockfile.open('a+b') as lock:
        deadline = time.monotonic() + 10
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        'Clock helper cache lock deadline exceeded')
                time.sleep(.02)
        if committed.exists() or committed.is_symlink():
            if committed.is_symlink() or not committed.is_dir():
                raise ValueError('Clock helper artifact cannot be redirected')
            if receipt.is_symlink() or library.is_symlink(
            ) or not receipt.is_file() or not library.is_file():
                raise ValueError('Incomplete or redirected clock helper cache')
            saved = json.loads(receipt.read_text())
            if saved.get('inputs') != inputs or saved.get('sha256') != _sha(
                    library):
                raise ValueError(
                    'Clock helper cached source/tool/binary identity changed')
            return dict(file=str(library), **saved)
        attempt = Path(tempfile.mkdtemp(prefix='build-', dir=directory))
        source, output = attempt / 'identity.ll', attempt / 'identity.bc'
        source.write_text(IDENTITY_SOURCE)
        argv = [str(tool), str(source), '-o', str(output)]
        started = time.monotonic_ns()
        process = subprocess.Popen(argv,
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        owner = dict(pid=process.pid, argv=argv)
        try:
            stat = Path('/proc') / str(process.pid) / 'stat'
            fields = stat.read_text().rsplit(')', 1)[1].split()
            owner.update(pgid=int(fields[2]), startticks=int(fields[19]))
            (attempt / 'launch.json').write_text(json.dumps(owner, indent=2))
            stdout, stderr = process.communicate(timeout=20)
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
            (attempt / 'terminal.json').write_text(
                json.dumps(
                    dict(owner,
                         returncode=process.returncode,
                         state='failed_or_timed_out')))
            raise
        (attempt / 'stdout.log').write_bytes(stdout)
        (attempt / 'stderr.log').write_bytes(stderr)
        (attempt / 'terminal.json').write_text(
            json.dumps(
                dict(owner,
                     returncode=process.returncode,
                     wall_ns=time.monotonic_ns() - started)))
        if process.returncode:
            raise RuntimeError(
                'SDK clock identity helper compilation failed: ' +
                str(attempt))
        raw = output.read_bytes()
        if not 4 <= len(raw) <= 1024 * 1024 or raw[:4] != b'BC\xc0\xde':
            raise ValueError(
                'Clock identity helper is not bounded LLVM bitcode')
        if _sha(tool) != inputs['tool_sha256'] or _sha(
                sdk) != inputs['sdk_library_sha256']:
            raise ValueError(
                'SDK tool/library changed during clock helper compilation')
        saved = dict(inputs=inputs,
                     sha256=hashlib.sha256(raw).hexdigest(),
                     bytes=len(raw))
        pending = attempt / 'complete.json'
        pending.write_text(json.dumps(saved, sort_keys=True, indent=2) + '\n')
        # One directory publication exposes both the sealed binary and its
        # receipt. An interrupted prior build remains diagnostic history and
        # cannot poison a later retry with a half-committed cache entry.
        os.replace(attempt, committed)
        return dict(file=str(library), **saved)
