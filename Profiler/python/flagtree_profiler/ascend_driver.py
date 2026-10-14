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


def main():
    argv = sys.argv[1:]
    real = os.environ['FLAGPRISM_ASCEND_REAL_BISHENG']
    output = Path(os.environ['FLAGPRISM_ASCEND_COMPILER_OUTPUT']) / 'jobs' / str(uuid.uuid4())
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env['FLAGPRISM_ASCEND_COMPILER_OUTPUT'] = str(output)
    arch = next((arg.split('=', 1)[1] for arg in argv if arg.startswith('--cce-aicore-arch=')), None)
    actor = 'AIC' if arch and arch.endswith('-cube') else 'AIV' if arch and arch.endswith('-vec') else None
    env['FLAGPRISM_ASCEND_ACTOR_KIND'] = actor or ''
    receipt = {'schema_version': 1, 'compile_id': env['FLAGPRISM_ASCEND_COMPILE_ID'], 'command': [real, *argv], 'target_arch': arch, 'actor_kind': actor, 'actor_basis': 'actual_sdk_target_argument' if actor else None, 'mode': 'observer', 'state': 'started', 'inputs': []}
    receipt_path = output / 'receipt.json'
    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2))
    save()
    try:
        if actor is None:
            code = subprocess.call([real, *argv], env=env)
            receipt['exit_code'] = code
            receipt['state'] = 'finished' if not code else 'failed'
            return code
        consumes_value = {'-o', '-x', '-cce-link-aicore-ll-module', '-mllvm', '-I', '-L', '-include', '-isystem'}
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
            raise RuntimeError('SDK actor driver requires one identifiable main LLVM input; missing/multiple inputs are unsupported')
        dynamic = bool(env.get('FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX') or env.get('FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'))
        if dynamic and arch not in {'dav-c220-cube', 'dav-c220-vec'}:
            raise RuntimeError('The three-slot Ascend dynamic ABI currently supports the actual 910B dav-c220 cube/vector targets only')
        for arg, path in main_inputs:
            (output / ('original-input-' + str(len(receipt['inputs'])) + path.suffix)).write_bytes(path.read_bytes())
            # opt's IRReader is authoritative: no LLVM text/kernel-name parsing.
            command = [env['FLAGPRISM_ASCEND_OPT'], '-load-pass-plugin=' + env['FLAGPRISM_ASCEND_LATE_PLUGIN'], '-passes=flagprism-ascend-late-observer']
            adapted = output / ('adapted-' + str(len(receipt['inputs'])) + '.ll')
            if dynamic:
                command += ['-S', '-o', str(adapted), str(path)]
                receipt['mode'] = 'selected_dynamic_trace'
            else:
                command += ['-disable-output', str(path)]
            result = subprocess.run(command, env=env, capture_output=True, timeout=120)
            receipt['inputs'].append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'pass_command': command, 'pass_returncode': result.returncode})
            (output / ('pass-' + str(len(receipt['inputs'])) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError('LLVM pass failed; original SDK invocation was not run')
            if adapted.is_file():
                receipt['inputs'][-1]['adapted_path'] = str(adapted)
                receipt['inputs'][-1]['adapted_sha256'] = hashlib.sha256(adapted.read_bytes()).hexdigest()
                argv = [str(adapted) if value == arg else value for value in argv]
        code = subprocess.call([real, *argv], env=env)
        if not code and '-o' in argv:
            object_path = Path(argv[argv.index('-o') + 1])
            if object_path.is_file():
                receipt['object'] = {'path': str(object_path), 'sha256': hashlib.sha256(object_path.read_bytes()).hexdigest(), 'bytes': object_path.stat().st_size}
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
