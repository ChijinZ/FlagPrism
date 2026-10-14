"""Per-compilation CANN LLVM pass handoff using FlagTree compiler.driver.v1.

The caller supplies a plugin for the isolated upstream LLVM15 opt process.
The SDK compiler receives its validated output through its normal driver entry.
Capture uses new immutable directories per compiler invocation.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import uuid


def prepare(event):
    if event.backend != 'ascend':
        return
    if os.environ.get('FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX') and os.environ.get('FLAGPRISM_ASCEND_ALLOW_TEST_FORMAL_INDEX') != '1':
        raise ValueError('Direct final formal indices are only allowed by an explicit test adapter; use compiler source argument identity')
    plugin = event.metadata.get('flagprism_ascend_late_plugin') or os.environ.get('FLAGPRISM_ASCEND_LATE_PLUGIN')
    destination = event.metadata.get('flagprism_ascend_compiler_capture') or os.environ.get('FLAGPRISM_ASCEND_COMPILER_CAPTURE')
    requested = event.metadata.get('flagprism_ascend_observation_request')
    if requested:
        fields = (('flagprism_ascend_trace_capacity', 1, 1_000_000),
                  ('flagprism_ascend_trace_program', 0, None),
                  ('flagprism_ascend_trace_source_argument_index', 0, None))
        for field, minimum, maximum in fields:
            value = event.metadata.get(field)
            if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
                raise ValueError(f'Ascend observation compiler metadata requires valid {field}')
    if not plugin and not destination:
        if requested:
            raise RuntimeError('Ascend detailed observations require a built late LLVM pass and compiler capture directory')
        return
    if not plugin or not destination:
        raise ValueError('Ascend late compiler capture requires plugin and capture directory')
    plugin = Path(plugin).resolve()
    if not plugin.is_file():
        raise FileNotFoundError(plugin)
    if requested:
        event.environment['FLAGPRISM_ASCEND_TRACE_CAPACITY'] = str(event.metadata['flagprism_ascend_trace_capacity'])
        event.environment['FLAGPRISM_ASCEND_TRACE_PROGRAM'] = str(event.metadata['flagprism_ascend_trace_program'])
        event.environment['FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'] = str(event.metadata['flagprism_ascend_trace_source_argument_index'])
    compile_id = str(uuid.uuid4())
    output = Path(destination).resolve() / compile_id
    output.mkdir(parents=True, exist_ok=False)
    real_bisheng = shutil.which('bisheng', path=event.environment.get('PATH'))
    opt = event.metadata.get('flagprism_ascend_opt') or os.environ.get('FLAGPRISM_ASCEND_OPT') or shutil.which('opt-15')
    if not real_bisheng or not opt:
        raise RuntimeError('Ascend late capture requires actual bisheng and LLVM15 opt')
    wrapper_directory = output / 'bin'
    wrapper_directory.mkdir()
    wrapper = wrapper_directory / 'bisheng'
    driver = Path(__file__).with_name('ascend_driver.py')
    wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(driver)) + ' "$@"\n')
    wrapper.chmod(0o755)
    event.environment['FLAGPRISM_ASCEND_REAL_BISHENG'] = real_bisheng
    event.environment['FLAGPRISM_ASCEND_OPT'] = str(opt)
    event.environment['FLAGPRISM_ASCEND_LATE_PLUGIN'] = str(plugin)
    event.environment['PATH'] = str(wrapper_directory) + os.pathsep + event.environment.get('PATH', '')
    source_inputs = [Path(value) for value in event.command if not value.startswith('-') and Path(value).suffix in {'.mlir', '.ttadapter', '.bcmlir'} and Path(value).is_file()]
    source_inputs = list(dict.fromkeys(source_inputs))
    if len(source_inputs) > 1:
        raise RuntimeError('CANN compiler driver source module identity is ambiguous')
    if requested and not source_inputs:
        raise RuntimeError('Ascend detailed observations require the actual compiler source module')
    trace_source_argument = event.metadata.get('flagprism_ascend_trace_source_argument_index')
    if trace_source_argument is None and os.environ.get('FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT') is not None:
        trace_source_argument = int(os.environ['FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'])
    if source_inputs:
        from .ascend_abi import source_abi
        try:
            source = source_inputs[0].read_text()
        except UnicodeDecodeError as error:
            raise RuntimeError('Ascend source ABI handoff requires a textual compiler source module; MLIR bytecode export is currently unsupported') from error
        (output / 'source.mlir').write_text(source)
        abi = source_abi(source, trace_source_argument=trace_source_argument)
        from triton.backends.ascend import utils as ascend_utils
        runtime_arch = ascend_utils.get_ascend_arch_from_env()
        abi['ffts_control_present'] = bool(ascend_utils.is_ffts_supported(runtime_arch) and not ascend_utils.force_disable_ffts())
        abi['ffts_basis'] = 'actual_FlagTree_launch_struct_configuration'
        abi['runtime_arch'] = runtime_arch
        driver_source = Path(ascend_utils.__file__).with_name('driver.py')
        abi['runtime_driver_sha256'] = hashlib.sha256(driver_source.read_bytes()).hexdigest()
        abi_path = output / 'source-abi.json'
        abi_path.write_text(json.dumps(abi, indent=2))
        event.environment['FLAGPRISM_ASCEND_SOURCE_ABI'] = str(abi_path)
    event.environment['FLAGPRISM_ASCEND_COMPILER_OUTPUT'] = str(output)
    event.environment['FLAGPRISM_ASCEND_COMPILE_ID'] = compile_id
    provenance = {'compile_id': compile_id, 'phase': 'prepared', 'plugin_sha256': hashlib.sha256(plugin.read_bytes()).hexdigest(), 'command': event.command, 'output': str(output), 'source_association': 'surviving_explicit_metadata_only'}
    if source_inputs:
        tracked = event.metadata.get('debug_tracked_table')
        if isinstance(tracked, str):
            tracked = json.loads(tracked)
        provenance['source_snapshot'] = {'ir_sha256': abi['source_sha256'], 'tracked_ops_sha256': hashlib.sha256(json.dumps(tracked, sort_keys=True, separators=(',', ':')).encode()).hexdigest() if isinstance(tracked, list) else None, 'phase': 'pre_backend_driver'}
    (output / 'driver.json').write_text(json.dumps(provenance, indent=2))
    event.metadata['flagprism_ascend_handoff'] = provenance


def finish(event, *, returncode):
    provenance = event.metadata.get('flagprism_ascend_handoff')
    if not provenance:
        if event.backend == 'ascend' and event.metadata.get('flagprism_ascend_observation_request'):
            raise RuntimeError('Ascend observation request did not prepare a late compiler handoff')
        return
    output = Path(provenance['output'])
    provenance['returncode'] = returncode
    provenance['phase'] = 'failed' if returncode else 'finished'
    artifacts = []
    for path in sorted(output.rglob('*.ll')):
        manifest = path.with_suffix('.json')
        if not manifest.is_file():
            continue
        metadata = json.loads(manifest.read_text())
        artifact = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'llir': path.read_text(), 'manifest_path': str(manifest), 'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(), 'metadata': metadata, 'representation': 'original_pre_instrumentation_canonical_llvm', 'actor_kinds': [actor.get('actor_kind') for actor in metadata.get('actors', [])], 'argument_roles': [actor.get('argument_roles', []) for actor in metadata.get('actors', [])]}
        receipt_path = path.parent / 'receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            artifact['driver_job'] = receipt
            for item in receipt.get('inputs', []):
                if item.get('path') == metadata.get('module_identifier'):
                    artifact['original_input_sha256'] = item['sha256']
                    adapted_path = Path(item['adapted_path']) if item.get('adapted_path') else None
                    if adapted_path and adapted_path.exists():
                        artifact['adapted'] = {'path': str(adapted_path), 'sha256': hashlib.sha256(adapted_path.read_bytes()).hexdigest(), 'llir': adapted_path.read_text(), 'representation': 'instrumented_llvm_compiled_by_sdk'}
        artifacts.append(artifact)
    provenance['artifacts'] = artifacts
    (output / 'driver.json').write_text(json.dumps(provenance, indent=2))
    if not returncode and not artifacts:
        raise RuntimeError('CANN driver produced no final actor LLVM capture; verify the selected SDK plugin extension point')
    if not returncode and event.metadata.get('flagprism_ascend_observation_request'):
        if not all(item['metadata'].get('actors') and all(
                actor.get('dynamic_observation_prepared') for actor in item['metadata']['actors'])
                for item in artifacts):
            raise RuntimeError('Ascend observation request did not prepare every final actor dynamic ABI')


def cache_key():
    plugin = os.environ.get('FLAGPRISM_ASCEND_LATE_PLUGIN')
    if not plugin:
        return ''
    return hashlib.sha256(json.dumps({
        'plugin': hashlib.sha256(Path(plugin).read_bytes()).hexdigest(),
        'trace_argument': os.environ.get('FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX'),
        'trace_source_argument': os.environ.get('FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'),
        'capacity': os.environ.get('FLAGPRISM_ASCEND_TRACE_CAPACITY'),
        'program': os.environ.get('FLAGPRISM_ASCEND_TRACE_PROGRAM'),
        'line_info': os.environ.get('TRITON_DISABLE_LINE_INFO'),
    }, sort_keys=True).encode()).hexdigest()
