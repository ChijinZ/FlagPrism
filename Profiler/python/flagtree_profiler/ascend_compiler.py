"""Per-compilation CANN LLVM pass handoff using FlagTree compiler.driver.v1.

The caller supplies a plugin for the isolated upstream LLVM15 opt process.
The SDK compiler receives its validated output through its normal driver entry.
Capture uses new immutable directories per compiler invocation.
"""
from __future__ import annotations
import hashlib
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import uuid


def prepare(event):
    if event.backend != 'ascend':
        return
    if os.environ.get(
            'FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX') and os.environ.get(
                'FLAGPRISM_ASCEND_ALLOW_TEST_FORMAL_INDEX') != '1':
        raise ValueError(
            'Direct final formal indices are only allowed by an explicit test adapter; use compiler source argument identity'
        )
    plugin = event.metadata.get(
        'flagprism_ascend_late_plugin') or os.environ.get(
            'FLAGPRISM_ASCEND_LATE_PLUGIN')
    destination = event.metadata.get(
        'flagprism_ascend_compiler_capture') or os.environ.get(
            'FLAGPRISM_ASCEND_COMPILER_CAPTURE')
    requested = event.metadata.get('flagprism_ascend_observation_request')
    if requested and not plugin:
        packaged_plugin = Path(__file__).with_name(
            'lib') / 'FlagPrismAscendLateObserver.so'
        if packaged_plugin.is_file():
            plugin = str(packaged_plugin)
    if requested and plugin and not destination:
        # Compiler artifacts are immutable and retained on failure. Their exact
        # bytes/hashes are embedded in the ordinary portable bundle on success.
        destination = tempfile.mkdtemp(prefix='flagprism-ascend-compiler-')
    census = bool(requested
                  and requested.get('program_policy') == 'all_grid_census')
    if requested:
        fields = (('flagprism_ascend_trace_capacity', 1,
                   1_000_000), ('flagprism_ascend_trace_program', 0, None),
                  ('flagprism_ascend_trace_source_argument_index', 0, None))
        if census:
            fields = (('flagprism_ascend_trace_source_argument_index', 0,
                       None), )
        for field, minimum, maximum in fields:
            value = event.metadata.get(field)
            if type(value) is not int or value < minimum or (
                    maximum is not None and value > maximum):
                raise ValueError(
                    f'Ascend observation compiler metadata requires valid {field}'
                )
    if not plugin and not destination:
        if requested:
            raise RuntimeError(
                'Ascend detailed observations require a built late LLVM pass and compiler capture directory'
            )
        return
    if not plugin or not destination:
        raise ValueError(
            'Ascend late compiler capture requires plugin and capture directory'
        )
    plugin = Path(plugin).resolve()
    if not plugin.is_file():
        raise FileNotFoundError(plugin)
    if requested:
        semantics = requested.get('semantics')
        allowed = {'counter'} if census else {
            'issue', 'wait_bracket', 'control_checkpoint',
            'operation_checkpoint'
        }
        if (not isinstance(semantics, (list, tuple)) or not semantics
                or any(value not in allowed for value in semantics)
                or len(set(semantics)) != len(semantics)):
            raise ValueError(
                'Ascend observation semantics must be unique supported names')
        event.environment['FLAGPRISM_ASCEND_TRACE_SEMANTICS'] = ','.join(
            semantics)
        event.metadata[
            'flagprism_ascend_semantic_selection_stage'] = 'compile_time_before_timestamp_and_record'
        max_sites = event.metadata.get('flagprism_ascend_trace_max_sites', 32)
        if type(max_sites) is not int or not 1 <= max_sites <= 256:
            raise ValueError('Ascend operation site budget must be 1..256')
        event.environment['FLAGPRISM_ASCEND_TRACE_MAX_SITES'] = str(max_sites)
        if census:
            version = event.metadata.get(
                'flagprism_ascend_source_census_version')
            if type(version) is not int or version not in (1, 2, 3):
                raise ValueError(
                    'Ascend census requires an actual prepared frontend ABI')
            if version >= 2:
                abi = event.metadata.get('debug_ascend_census_abi') or {}
                columns = event.metadata.get('debug_census_columns')
                if (type(columns) is not int or not 1 <= columns <= 128
                        or abi.get('site_count') != columns
                        or abi.get('version') != version
                        or abi.get('records_per_instance') != 3 * columns):
                    raise ValueError(
                        'Ascend census requires actual native frontend columns'
                    )
                event.environment['FLAGPRISM_ASCEND_CENSUS_COLUMNS'] = str(
                    columns)
            event.environment[
                'FLAGPRISM_ASCEND_TRACE_MODE'] = f'source_census_v{version}'
            event.environment['FLAGPRISM_ASCEND_TRACE_CAPACITY'] = '1'
        else:
            event.environment['FLAGPRISM_ASCEND_TRACE_CAPACITY'] = str(
                event.metadata['flagprism_ascend_trace_capacity'])
            event.environment['FLAGPRISM_ASCEND_TRACE_PROGRAM'] = str(
                event.metadata['flagprism_ascend_trace_program'])
        event.environment['FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'] = str(
            event.metadata['flagprism_ascend_trace_source_argument_index'])
    compile_id = str(uuid.uuid4())
    output = Path(destination).resolve() / compile_id
    output.mkdir(parents=True, exist_ok=False)
    real_bisheng = shutil.which('bisheng', path=event.environment.get('PATH'))
    opt = event.metadata.get('flagprism_ascend_opt') or os.environ.get(
        'FLAGPRISM_ASCEND_OPT') or shutil.which('opt-15')
    if not real_bisheng or not opt:
        raise RuntimeError(
            'Ascend late capture requires actual bisheng and LLVM15 opt')
    wrapper_directory = output / 'bin'
    wrapper_directory.mkdir()
    wrapper = wrapper_directory / 'bisheng'
    driver = Path(__file__).with_name('ascend_driver.py')
    wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                       shlex.quote(str(driver)) + ' "$@"\n')
    wrapper.chmod(0o755)
    event.environment['FLAGPRISM_ASCEND_REAL_BISHENG'] = real_bisheng
    event.environment['FLAGPRISM_ASCEND_OPT'] = str(opt)
    event.environment['FLAGPRISM_ASCEND_LATE_PLUGIN'] = str(plugin)
    event.environment['PATH'] = str(
        wrapper_directory) + os.pathsep + event.environment.get('PATH', '')
    source_inputs = [
        Path(value) for value in event.command
        if not value.startswith('-') and Path(value).suffix in
        {'.mlir', '.ttadapter', '.bcmlir'} and Path(value).is_file()
    ]
    source_inputs = list(dict.fromkeys(source_inputs))
    if len(source_inputs) > 1:
        raise RuntimeError(
            'CANN compiler driver source module identity is ambiguous')
    if requested and not source_inputs:
        raise RuntimeError(
            'Ascend detailed observations require the actual compiler source module'
        )
    trace_source_argument = event.metadata.get(
        'flagprism_ascend_trace_source_argument_index')
    if trace_source_argument is None and os.environ.get(
            'FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT') is not None:
        trace_source_argument = int(
            os.environ['FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'])
    if source_inputs:
        from .ascend_abi import source_abi
        try:
            source_bytes = source_inputs[0].read_bytes()
            source = source_bytes.decode('utf-8')
        except UnicodeDecodeError as error:
            raise RuntimeError(
                'Ascend source ABI handoff requires a textual compiler source module; MLIR bytecode export is currently unsupported'
            ) from error
        (output / 'source.mlir').write_bytes(source_bytes)
        abi = source_abi(source, trace_source_argument=trace_source_argument)
        from triton.backends.ascend import utils as ascend_utils
        runtime_arch = ascend_utils.get_ascend_arch_from_env()
        abi['ffts_control_present'] = bool(
            ascend_utils.is_ffts_supported(runtime_arch)
            and not ascend_utils.force_disable_ffts())
        abi['ffts_basis'] = 'actual_FlagTree_launch_struct_configuration'
        abi['runtime_arch'] = runtime_arch
        driver_source = Path(ascend_utils.__file__).with_name('driver.py')
        abi['runtime_driver_sha256'] = hashlib.sha256(
            driver_source.read_bytes()).hexdigest()
        abi_path = output / 'source-abi.json'
        abi_path.write_text(json.dumps(abi, indent=2))
        event.environment['FLAGPRISM_ASCEND_SOURCE_ABI'] = str(abi_path)
    event.environment['FLAGPRISM_ASCEND_FINAL_OUTPUTS'] = json.dumps(
        getattr(event, 'output_files', None) or {}, sort_keys=True)
    event.environment['FLAGPRISM_ASCEND_COMPILER_OUTPUT'] = str(output)
    event.environment['FLAGPRISM_ASCEND_COMPILE_ID'] = compile_id
    from .ascend_hivm import PRINT_FLAG
    if PRINT_FLAG not in event.command:
        event.command.append(PRINT_FLAG)
    sdk_driver = Path(__file__).with_name('ascend_sdk_driver.py')
    sdk_command = list(event.command)
    event.command[:] = [sys.executable, str(sdk_driver), *sdk_command]
    provenance = {
        'compile_id':
        compile_id,
        'phase':
        'prepared',
        'plugin_sha256':
        hashlib.sha256(plugin.read_bytes()).hexdigest(),
        'command':
        sdk_command,
        'sdk_capture_wrapper_sha256':
        hashlib.sha256(sdk_driver.read_bytes()).hexdigest(),
        'output':
        str(output),
        'source_association':
        'surviving_source_metadata_and_full_debug_locations'
    }
    if source_inputs:
        tracked = event.metadata.get('debug_tracked_table')
        if isinstance(tracked, str):
            tracked = json.loads(tracked)
        provenance['source_snapshot'] = {
            'ir_sha256':
            abi['source_sha256'],
            'tracked_ops_sha256':
            hashlib.sha256(
                json.dumps(tracked, sort_keys=True,
                           separators=(',', ':')).encode()).hexdigest()
            if isinstance(tracked, list) else None,
            'phase':
            'pre_backend_driver',
            'encoding':
            'utf-8',
            'ir':
            source
        }
    (output / 'driver.json').write_text(json.dumps(provenance, indent=2))
    event.metadata['flagprism_ascend_handoff'] = provenance


def _portable_file(info):
    """Seal exact retained producer bytes, without canonical text conversion."""
    retained = Path(info.get('retained_path') or info['path'])
    data = retained.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != info['sha256'] or len(data) != info.get('bytes', len(data)):
        raise RuntimeError('Retained compiler artifact changed: ' +
                           str(retained))
    return dict(info,
                bytes=len(data),
                encoding='base64',
                data=base64.b64encode(data).decode('ascii'))


def finish(event, *, returncode):
    provenance = event.metadata.get('flagprism_ascend_handoff')
    if not provenance:
        if event.backend == 'ascend' and event.metadata.get(
                'flagprism_ascend_observation_request'):
            raise RuntimeError(
                'Ascend observation request did not prepare a late compiler handoff'
            )
        return
    output = Path(provenance['output'])
    provenance['returncode'] = returncode
    provenance['phase'] = 'failed' if returncode else 'finished'
    artifacts = []
    for path in sorted(output.rglob('*.ll')):
        manifest = path.with_suffix('.json')
        if not manifest.is_file():
            continue
        manifest_text = manifest.read_bytes().decode('utf-8')
        metadata = json.loads(manifest_text)
        artifact = {
            'path':
            str(path),
            'sha256':
            hashlib.sha256(path.read_bytes()).hexdigest(),
            'llir':
            path.read_text(),
            'manifest_path':
            str(manifest),
            'manifest_sha256':
            hashlib.sha256(manifest_text.encode('utf-8')).hexdigest(),
            'manifest_text':
            manifest_text,
            'metadata':
            metadata,
            'representation':
            'original_pre_instrumentation_canonical_llvm',
            'actor_kinds':
            [actor.get('actor_kind') for actor in metadata.get('actors', [])],
            'argument_roles': [
                actor.get('argument_roles', [])
                for actor in metadata.get('actors', [])
            ]
        }
        receipt_path = path.parent / 'receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            artifact['driver_job'] = receipt
            for item in receipt.get('inputs', []):
                if item.get('path') == metadata.get('module_identifier'):
                    artifact['original_input_sha256'] = item['sha256']
                    if item.get('retained_path'):
                        artifact['original_input'] = _portable_file(item)
                        if metadata.get(
                                'module_input_sha256') != item['sha256']:
                            raise RuntimeError(
                                'LLVM producer raw input differs from retained SDK input'
                            )
                    adapted_path = Path(item['adapted_path']) if item.get(
                        'adapted_path') else None
                    if adapted_path and adapted_path.exists():
                        artifact['adapted'] = {
                            'path':
                            str(adapted_path),
                            'sha256':
                            hashlib.sha256(
                                adapted_path.read_bytes()).hexdigest(),
                            'llir':
                            adapted_path.read_text(),
                            'representation':
                            'instrumented_llvm_compiled_by_sdk'
                        }
        artifacts.append(artifact)
    provenance['artifacts'] = artifacts
    # Include every actual compiler subprocess, including linker invocations;
    # actor LLVM files alone do not prove the final SDK output identity.
    provenance['codegen_jobs'] = [
        json.loads(path.read_text())
        for path in sorted((output / 'jobs').glob('*/receipt.json'))
    ]
    final_outputs = {}
    if not returncode:
        for name, path in (getattr(event, 'output_files', None) or {}).items():
            data = Path(path).read_bytes()
            retained = output / ('final-output-' + str(len(final_outputs)) +
                                 '.bin')
            retained.write_bytes(data)
            final_outputs[name] = _portable_file({
                'path':
                str(path),
                'retained_path':
                str(retained),
                'sha256':
                hashlib.sha256(data).hexdigest(),
                'bytes':
                len(data)
            })
    provenance['final_outputs'] = final_outputs
    sdk_receipt = output / 'sdk-compiler.json'
    if sdk_receipt.is_file():
        provenance['sdk_ir_capture'] = {
            'receipt': json.loads(sdk_receipt.read_text()),
            'stderr': (output / 'sdk-stderr.txt').read_text(errors='replace')
        }
    if not returncode and event.metadata.get(
            'flagprism_ascend_observation_request'):
        sdk = (provenance.get('sdk_ir_capture') or {}).get('receipt') or {}
        binary = final_outputs.get('binary') or {}
        sdk_binary = (sdk.get('outputs') or {}).get('binary') or {}
        group = sdk.get('process_group_id')
        jobs = provenance['codegen_jobs']
        if (sdk.get('state') != 'finished' or sdk.get('returncode') != 0
                or sdk.get('compile_id') != provenance['compile_id']
                or type(group) is not int or group <= 0 or not binary
                or not sdk_binary or any(
                    binary.get(key) != sdk_binary.get(key)
                    for key in ('path', 'sha256', 'bytes')) or not jobs or any(
                        job.get('compile_id') != provenance['compile_id']
                        or job.get('process_group_id') != group or job.get(
                            'state') != 'finished' or job.get('exit_code') != 0
                        for job in jobs)):
            raise RuntimeError(
                'Ascend compiler output lacks an exact successful enclosing SDK producer association'
            )
        provenance['producer_association'] = dict(
            basis=
            'same_enclosing_sdk_process_group_and_exact_final_output_bytes',
            compile_id=provenance['compile_id'],
            sdk_process_group_id=group,
            final_binary_sha256=binary['sha256'],
            codegen_job_count=len(jobs))
    from .ascend_hivm import build_static_readiness
    provenance['static_readiness'] = build_static_readiness(
        provenance.get('sdk_ir_capture'),
        artifacts,
        source_snapshot=provenance.get('source_snapshot'),
        compile_id=provenance.get('compile_id'),
        phase=provenance.get('phase'),
        returncode=provenance.get('returncode'))
    (output / 'driver.json').write_text(json.dumps(provenance, indent=2))
    if not returncode and not artifacts:
        raise RuntimeError(
            'CANN driver produced no final actor LLVM capture; verify the selected SDK plugin extension point'
        )
    if not returncode and event.metadata.get(
            'flagprism_ascend_observation_request'):
        if 'binary' not in final_outputs:
            raise RuntimeError(
                'Ascend observation requires the actual SDK final binary output; rebuild the compiler driver integration'
            )
        if any('original_input' not in artifact for artifact in artifacts):
            raise RuntimeError(
                'Ascend observation requires exact raw SDK inputs as well as canonical LLVM'
            )
        if not all(item['metadata'].get('actors') and all(
                actor.get('dynamic_observation_prepared')
                for actor in item['metadata']['actors'])
                   for item in artifacts):
            raise RuntimeError(
                'Ascend observation request did not prepare every final actor dynamic ABI'
            )


def cache_key():
    plugin = os.environ.get('FLAGPRISM_ASCEND_LATE_PLUGIN')
    if not plugin:
        packaged_plugin = Path(__file__).with_name(
            'lib') / 'FlagPrismAscendLateObserver.so'
        if packaged_plugin.is_file():
            plugin = str(packaged_plugin)
        else:
            return ''
    return hashlib.sha256(
        json.dumps(
            {
                'plugin':
                hashlib.sha256(Path(plugin).read_bytes()).hexdigest(),
                'trace_argument':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX'),
                'trace_source_argument':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT'),
                'capacity':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_CAPACITY'),
                'program':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_PROGRAM'),
                'trace_max_sites':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_MAX_SITES'),
                'trace_mode':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_MODE'),
                'source_program_anchor_abi_version':
                2,
                'trace_semantics':
                os.environ.get('FLAGPRISM_ASCEND_TRACE_SEMANTICS'),
                'line_info':
                os.environ.get('TRITON_DISABLE_LINE_INFO'),
                'readiness_descriptor_version':
                'source_bytes_manifest_enclosing_compile_v3',
                'sdk_ir_print_flag':
                '--bishengir-print-ir-after=hivm-graph-sync-solver',
                'capture_sources': {
                    name:
                    hashlib.sha256(
                        Path(__file__).with_name(
                            name).read_bytes()).hexdigest()
                    for name in [
                        'ascend_compiler.py', 'ascend_driver.py',
                        'ascend_sdk_driver.py', 'ascend_hivm.py',
                        'ascend_abi.py', 'ascend_census.py'
                    ]
                },
            },
            sort_keys=True).encode()).hexdigest()
