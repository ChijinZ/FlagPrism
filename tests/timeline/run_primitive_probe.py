"""Bound one explicitly requested primitive probe in an existing server Docker.

Uses the already installed, qualified descendant cleanup helper. This controller
is development infrastructure, not the final independent qualification harness.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


class Cancelled(BaseException):
    pass


def identity(pid):
    text = Path(f'/proc/{pid}/stat').read_text()
    fields = text.rsplit(')', 1)[1].split()
    return {'pid': pid, 'ppid': int(fields[1]), 'pgid': int(fields[2]),
            'startticks': int(fields[19])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', required=True)
    parser.add_argument('--deadline-module', required=True, type=Path)
    parser.add_argument('--script', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    if args.timeout < 1 or args.timeout > 300:
        raise ValueError('Probe deadline must be in [1, 300] seconds')
    args.root.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('probe_cleanup',
                                                 args.deadline_module)
    cleanup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleanup)
    command = [args.python, '-I', str(args.script), '--output',
               str(args.root / 'output')]
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.update(TRITON_CACHE_DIR=str(args.root / 'cache'),
               TMPDIR=str(args.root / 'tmp'))
    (args.root / 'tmp').mkdir()
    started = time.monotonic_ns()
    with (args.root / 'stdout.log').open('xb') as out, (
            args.root / 'stderr.log').open('xb') as err:
        process = subprocess.Popen(command, env=env, stdout=out, stderr=err,
                                   start_new_session=True)
        receipt = {
            'controller': identity(os.getpid()),
            'worker': identity(process.pid), 'argv': command,
            'argv_sha256': hashlib.sha256(json.dumps(command).encode()).hexdigest(),
            'script_sha256': hashlib.sha256(args.script.read_bytes()).hexdigest(),
            'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'cleanup_sha256': hashlib.sha256(args.deadline_module.read_bytes()).hexdigest(),
            'timeout_seconds': args.timeout, 'state': 'running',
        }
        (args.root / 'launch.json').write_text(json.dumps(receipt, indent=2))
        previous = {}

        def cancel(signum, frame):
            raise Cancelled(signum)

        try:
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                previous[sig] = signal.signal(sig, cancel)
            try:
                code = process.wait(timeout=args.timeout)
                receipt.update(state='terminal', returncode=code)
            except (subprocess.TimeoutExpired, Cancelled) as error:
                for sig in previous:
                    signal.signal(sig, signal.SIG_IGN)
                cleanup._stop_worker(process)
                receipt.update(state='timeout' if isinstance(
                    error, subprocess.TimeoutExpired) else 'cancelled',
                    returncode=process.returncode)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            receipt['wall_ns'] = time.monotonic_ns() - started
            (args.root / 'terminal.json').write_text(json.dumps(receipt, indent=2))
    return 0 if receipt['state'] == 'terminal' and receipt['returncode'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
