"""Isolated SDK codegen driver handoff; invoked only by configured FlagTree.

The SDK command is preserved exactly in observer mode. LLVM15 parsing and
passes run in their own process, avoiding the vendor compiler plugin ABI.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def file_receipt(path, *, retain=None):
    path = Path(path)
    data = path.read_bytes()
    result = {
        'path': str(path),
        'sha256': hashlib.sha256(data).hexdigest(),
        'bytes': len(data)
    }
    if retain is not None:
        Path(retain).write_bytes(data)
        result['retained_path'] = str(retain)
    return result


def command_output(argv):
    indices = [index for index, value in enumerate(argv) if value == '-o']
    if not indices:
        return None
    if len(indices) != 1 or indices[0] + 1 >= len(argv):
        raise RuntimeError('SDK output argument is ambiguous')
    return Path(argv[indices[0] + 1])


def command_inputs(argv):
    """Retain input identities from actual argv, excluding the output operand."""
    output = command_output(argv)
    files = []
    for index, value in enumerate(argv):
        if value.startswith('-') or index and argv[index - 1] == '-o':
            continue
        path = Path(value)
        if path.is_file() and path != output:
            files.append(dict(argument_index=index, **file_receipt(path)))
    return files


def main():
    argv = sys.argv[1:]
    real = os.environ['FLAGPRISM_ASCEND_REAL_BISHENG']
    output = Path(
        os.environ['FLAGPRISM_ASCEND_COMPILER_OUTPUT']) / 'jobs' / str(
            uuid.uuid4())
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env['FLAGPRISM_ASCEND_COMPILER_OUTPUT'] = str(output)
    arch = next((arg.split('=', 1)[1]
                 for arg in argv if arg.startswith('--cce-aicore-arch=')),
                None)
    actor = 'AIC' if arch and arch.endswith(
        '-cube') else 'AIV' if arch and arch.endswith('-vec') else None
    env['FLAGPRISM_ASCEND_ACTOR_KIND'] = actor or ''
    receipt = {
        'schema_version': 1,
        'compile_id': env['FLAGPRISM_ASCEND_COMPILE_ID'],
        'command': [real, *argv],
        'target_arch': arch,
        'actor_kind': actor,
        'actor_basis': 'actual_sdk_target_argument' if actor else None,
        'mode': 'observer',
        'state': 'started',
        'inputs': [],
        'driver_process_id': os.getpid(),
        'parent_process_id': os.getppid(),
        'process_group_id': os.getpgrp()
    }
    receipt_path = output / 'receipt.json'

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2))

    save()
    try:
        receipt['input_files'] = command_inputs(argv)
        if actor is None:
            receipt['executed_command'] = [real, *argv]
            code = subprocess.call([real, *argv], env=env)
            destination = command_output(argv)
            if not code and destination is not None and destination.is_file():
                receipt['object'] = file_receipt(destination,
                                                 retain=output / 'output.bin')
            receipt['exit_code'] = code
            receipt['state'] = 'finished' if not code else 'failed'
            return code
        consumes_value = {
            '-o', '-x', '-cce-link-aicore-ll-module', '-mllvm', '-I', '-L',
            '-include', '-isystem'
        }
        skip_value = False
        main_inputs = []
        for arg in argv:
            if skip_value:
                skip_value = False
                continue
            if arg in consumes_value:
                skip_value = True
                continue
            if arg.startswith('-'):
                continue
            path = Path(arg)
            if path.suffix not in {'.ll', '.bc'} or not path.is_file():
                continue
            main_inputs.append((arg, path))
        if len(main_inputs) != 1:
            raise RuntimeError(
                'SDK actor driver requires one identifiable main LLVM input; missing/multiple inputs are unsupported'
            )
        dynamic = bool(
            env.get('FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX')
            or env.get('FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'))
        if dynamic and arch not in {'dav-c220-cube', 'dav-c220-vec'}:
            raise RuntimeError(
                'The three-slot Ascend dynamic ABI currently supports the actual 910B dav-c220 cube/vector targets only'
            )
        for arg, path in main_inputs:
            original = file_receipt(
                path,
                retain=output / ('original-input-' +
                                 str(len(receipt['inputs'])) + path.suffix))
            # opt's IRReader is authoritative: no LLVM text/kernel-name parsing.
            command = [
                env['FLAGPRISM_ASCEND_OPT'],
                '-load-pass-plugin=' + env['FLAGPRISM_ASCEND_LATE_PLUGIN'],
                '-passes=flagprism-ascend-late-observer'
            ]
            adapted = output / ('adapted-' + str(len(receipt['inputs'])) +
                                '.ll')
            if dynamic:
                command += ['-S', '-o', str(adapted), str(path)]
                receipt['mode'] = 'selected_dynamic_trace'
            else:
                command += ['-disable-output', str(path)]
            result = subprocess.run(command,
                                    env=env,
                                    capture_output=True,
                                    timeout=120)
            receipt['inputs'].append(
                dict(original,
                     pass_command=command,
                     pass_returncode=result.returncode))
            (output / ('pass-' + str(len(receipt['inputs'])) + '.log')
             ).write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(
                    f'Ascend LLVM observation pass failed (exit {result.returncode}); '
                    f'evidence: {output / ("pass-" + str(len(receipt["inputs"])) + ".log")}; '
                    'original SDK invocation was not run')
            if adapted.is_file():
                receipt['inputs'][-1]['adapted_path'] = str(adapted)
                receipt['inputs'][-1]['adapted_sha256'] = hashlib.sha256(
                    adapted.read_bytes()).hexdigest()
                argv = [
                    str(adapted) if value == arg else value for value in argv
                ]
        receipt['executed_command'] = [real, *argv]
        receipt['executed_input_files'] = command_inputs(argv)
        code = subprocess.call([real, *argv], env=env)
        object_path = command_output(argv)
        if not code and object_path is not None and object_path.is_file():
            receipt['object'] = file_receipt(object_path,
                                             retain=output / 'output.bin')
        receipt['exit_code'] = code
        receipt['state'] = 'finished' if not code else 'failed'
        return code
    except BaseException as error:
        receipt['state'] = 'failed'
        receipt['error'] = str(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    raise SystemExit(main())
