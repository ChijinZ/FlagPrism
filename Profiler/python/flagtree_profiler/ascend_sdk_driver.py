"""Run the original SDK compiler argv and retain bounded diagnostic streams."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

STREAM_LIMIT = 32 * 1024 * 1024


def main():
    command = sys.argv[1:]
    if not command:
        raise ValueError('SDK compiler argv is empty')
    output = Path(os.environ['FLAGPRISM_ASCEND_COMPILER_OUTPUT'])
    receipt = {
        'schema_version':
        1,
        'command':
        command,
        'state':
        'started',
        'streams': {},
        'compile_id':
        os.environ.get('FLAGPRISM_ASCEND_COMPILE_ID'),
        'sdk_tool_sha256':
        hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()
    }
    source_files = [
        Path(value) for value in command[1:]
        if not value.startswith('-') and Path(value).suffix in
        {'.mlir', '.ttadapter', '.bcmlir'} and Path(value).is_file()
    ]
    if len(source_files) == 1:
        receipt['source_ir_sha256'] = hashlib.sha256(
            source_files[0].read_bytes()).hexdigest()
    receipt_path = output / 'sdk-compiler.json'
    receipt_path.write_text(json.dumps(receipt, indent=2))
    errors = []

    def drain(stream, name, destination):
        digest = hashlib.sha256()
        count = retained = 0
        forwarding = True
        capture = None
        try:
            capture = (output / ('sdk-' + name + '.txt')).open('wb')
        except (OSError, ValueError) as error:
            errors.append(repr(error))
        while True:
            data = stream.read(65536)
            if not data:
                break
            count += len(data)
            keep = data[:max(0, STREAM_LIMIT - retained)]
            if capture is not None:
                try:
                    capture.write(keep)
                    digest.update(keep)
                    retained += len(keep)
                except (OSError, ValueError) as error:
                    errors.append(repr(error))
                    try:
                        capture.close()
                    except (OSError, ValueError) as close_error:
                        errors.append(repr(close_error))
                    capture = None
            if forwarding:
                try:
                    destination.write(data)
                    destination.flush()
                except (OSError, ValueError) as error:
                    errors.append(repr(error))
                    forwarding = False
        if capture is not None:
            try:
                capture.close()
            except (OSError, ValueError) as error:
                errors.append(repr(error))
        receipt['streams'][name] = {
            'bytes': count,
            'retained_bytes': retained,
            'truncated': count != retained,
            'sha256': digest.hexdigest()
        }

    try:
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        threads = [
            threading.Thread(target=drain,
                             args=(process.stdout, 'stdout',
                                   sys.stdout.buffer)),
            threading.Thread(target=drain,
                             args=(process.stderr, 'stderr',
                                   sys.stderr.buffer))
        ]
        for thread in threads:
            thread.start()
        code = process.wait()
        for thread in threads:
            thread.join()
        receipt.update(returncode=code,
                       state='finished' if code == 0 else 'failed')
        if errors:
            receipt['capture_errors'] = errors
            if code == 0:
                raise RuntimeError('SDK compiler output retention failed: ' +
                                   '; '.join(errors))
        return code if code >= 0 else 128 - code
    except BaseException as error:
        receipt.update(state='failed', error=repr(error))
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
