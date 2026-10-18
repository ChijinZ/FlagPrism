"""Build the experimental late LLVM recorder with an explicit matching SDK.

This does not install or enable the default profiler. The caller runs this in
its server Docker and owns the subprocess deadline/cleanup. Receipts identify
the actual source, SDK config, compiler argv and new executable bytes.
"""
import argparse
import hashlib
import importlib.util
import signal
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llvm-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source', type=Path)
    p.add_argument('--compiler', default='g++')
    p.add_argument('--deadline-module', type=Path)
    a = p.parse_args()
    source = a.source or (
        Path(__file__).resolve().parents[3] /
        'Profiler/Dialect/tools/late-timeline/late-timeline.cpp')
    cleanup_path = a.deadline_module or (
        Path(__file__).resolve().parents[3] /
        'Profiler/python/flagtree_profiler/_deadline.py')
    spec = importlib.util.spec_from_file_location('late_build_cleanup',
                                                  cleanup_path)
    cleanup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleanup)
    config = a.llvm_root / 'bin/llvm-config'
    compiler = shutil.which(a.compiler)
    if not compiler or not config.is_file() or not source.is_file():
        raise RuntimeError('Missing explicit SDK/config/compiler/source')
    if a.output.exists():
        raise RuntimeError('Build output must be a fresh directory')
    a.output.mkdir(parents=True)
    flags_command = [
        str(config), '--cxxflags', '--ldflags', '--system-libs', '--libs',
        'irreader', 'core', 'transformutils', 'analysis', 'support'
    ]
    flags = subprocess.run(flags_command,
                           capture_output=True,
                           timeout=10,
                           check=True)
    (a.output / 'llvm-config.stdout').write_bytes(flags.stdout)
    (a.output / 'llvm-config.stderr').write_bytes(flags.stderr)
    executable = a.output / 'late-timeline'
    command = [
        compiler, '-O1', '-g0',
        str(source), '-o',
        str(executable), *shlex.split(flags.stdout.decode())
    ]
    receipt = dict(
        source=str(source),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        llvm_config=str(config),
        llvm_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        argv=command,
        cleanup_sha256=hashlib.sha256(cleanup_path.read_bytes()).hexdigest(),
        state='building')
    receipt_path = a.output / 'build-receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    with (a.output / 'build.stdout').open('xb') as out, (
            a.output / 'build.stderr').open('xb') as err:
        child = subprocess.Popen(command,
                                 stdout=out,
                                 stderr=err,
                                 start_new_session=True)
        fields = Path('/proc/' + str(child.pid) + '/stat').read_text().rsplit(
            ')', 1)[1].split()
        receipt.update(pid=child.pid,
                       startticks=int(fields[19]),
                       pgid=int(fields[2]))
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
        started = time.monotonic_ns()

        class Cancelled(BaseException):
            pass

        def cancel(signum, frame):
            raise Cancelled(signum)

        signals = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        previous = {s: signal.signal(s, cancel) for s in signals}
        try:
            code = child.wait(timeout=120)
        except BaseException:
            for signum in signals:
                signal.signal(signum, signal.SIG_IGN)
            if child.poll() is None:
                cleanup._stop_worker(child)
            raise
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
            receipt.update(state='terminal',
                           returncode=child.returncode,
                           wall_ns=time.monotonic_ns() - started)
            receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    if code:
        raise RuntimeError(
            'Actual matching-SDK native tool compilation failed')
    receipt.update(executable=str(executable),
                   executable_sha256=hashlib.sha256(
                       executable.read_bytes()).hexdigest())
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
