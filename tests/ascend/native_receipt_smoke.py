"""Actual CANN public capture identity smoke, run only in the Ascend Docker.

Uses the optional generated-launcher receipt bridge; never passes a receipt,
extra kernel argument, SDK task ID or guessed timestamp from application code.
Requires METHOD_SOURCE, METHOD_COMPILER_SOURCE and METHOD_COMPONENT_PYTHON.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', type=int, default=4)
    parser.add_argument('--relative-sdk-output-with-chdir',
                        action='store_true')
    args = parser.parse_args()
    original_working_directory = Path.cwd()
    args.output = args.output.resolve()
    sdk_output = args.output / 'aclprof'
    configured_sdk_output = (
        './' + os.path.relpath(sdk_output, original_working_directory)
        if args.relative_sdk_output_with_chdir else str(sdk_output))
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
    os.environ['FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY'] = '1'
    source = Path(os.environ['METHOD_SOURCE'])
    compiler = Path(os.environ['METHOD_COMPILER_SOURCE'])
    sys.path.insert(0, str(compiler / 'python'))
    import torch
    import torch_npu  # noqa: F401
    import triton
    import triton.language as tl
    import triton._C.libtriton as libtriton
    import flagtree
    for component, directory in (('debugger',
                                  'Debugger/python/flagtree_debugger'),
                                 ('profiler',
                                  'Profiler/python/flagtree_profiler')):
        name = 'flagtree.' + component
        package = source / directory
        built = Path(
            os.environ['METHOD_COMPONENT_PYTHON']) / 'flagtree' / component
        spec = importlib.util.spec_from_file_location(
            name,
            package / '__init__.py',
            submodule_search_locations=[str(built), str(package)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        setattr(flagtree, component, module)
    from flagtree import profiler
    from flagtree.profiler.native import runtime_binding

    @triton.jit
    def add_one(x, y, n: tl.constexpr, block: tl.constexpr):
        index = tl.program_id(0) * block + tl.arange(0, block)
        tl.store(y + index, tl.load(x + index, index < n, 0) + 1, index < n)

    torch.npu.set_device(args.device)
    streams = [torch.npu.Stream(device=args.device) for _ in range(2)]
    inputs, outputs, binaries = {}, {}, {}
    for n in (513, 769):
        inputs[n] = torch.arange(n,
                                 dtype=torch.float32).to(f'npu:{args.device}')
        for stream_index in range(2):
            outputs[n, stream_index] = torch.full((n + 32, ),
                                                  -12345.,
                                                  device=f'npu:{args.device}')
            kernel = add_one[(triton.cdiv(n, 256), )](
                inputs[n], outputs[n, stream_index][16:-16], n, 256)
            binaries[n] = kernel.hash
    torch.npu.synchronize()
    native = runtime_binding()
    native_path = Path(native.__file__)
    provenance = {
        'schema_version':
        1,
        'status':
        'running',
        'device_id':
        args.device,
        'process_id':
        os.getpid(),
        'native': {
            'path': str(native_path),
            'sha256': hashlib.sha256(native_path.read_bytes()).hexdigest()
        },
        'compiler': {
            'path':
            libtriton.__file__,
            'sha256':
            hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest()
        },
        'source_runner_sha256':
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'binaries':
        binaries,
        'expected_launches':
        4,
        'relative_sdk_with_application_chdir':
        args.relative_sdk_output_with_chdir,
        'configured_sdk_output':
        configured_sdk_output,
        'expected_sdk_output':
        str(sdk_output),
        'original_working_directory':
        str(original_working_directory),
        'boundary':
        'Native task identity only; SYS/actor alignment is not certified.'
    }
    (args.output /
     'result.json').write_text(json.dumps(provenance, indent=2) + '\n')
    session = profiler.start(
        str(args.output / 'capture'),
        backend='cann',
        hook='triton',
        mode=
        f'runtime_base:device_id={args.device}:aclprof_runtime_enabled=true:'
        'msproftx_enabled=false:runtime_host_timing_fallback=false:'
        'aclprof_data_type_flags=ACL_PROF_ACL_API,ACL_PROF_TASK_TIME,'
        'ACL_PROF_RUNTIME_API,ACL_PROF_MSPROFTX:aclprof_auto_export=true:'
        f'aclprof_output_path={configured_sdk_output}')
    try:
        if args.relative_sdk_output_with_chdir:
            os.chdir(args.output)
        provenance['working_directory_during_capture'] = str(Path.cwd())
        for stream_index, n in ((0, 513), (1, 769), (0, 769), (1, 513)):
            with torch.npu.stream(streams[stream_index]):
                add_one[(triton.cdiv(n, 256), )](inputs[n],
                                                 outputs[n,
                                                         stream_index][16:-16],
                                                 n, 256)
        torch.npu.synchronize()
    finally:
        try:
            profiler.finalize(session)
        finally:
            os.chdir(original_working_directory)
    raw_native = args.output / 'capture/raw/native'
    receipts = json.loads(
        (raw_native / 'capture.cann-launch-receipts.json').read_text())
    proofs = json.loads(
        (raw_native / 'capture.cann-task-identities.json').read_text())
    rows = proofs['task_identity_proofs']
    assert all(
        Path(row['collector_output_path']) == sdk_output /
        ('flagtree_profiler_session_' + str(row['session_id']))
        and Path(row['sdk_capture_path']).parent == Path(
            row['collector_output_path'])
        for row in receipts['receipts']), receipts
    provenance['sdk_output_original_root_verified'] = True
    assert len(rows) == 4, rows
    assert all(row['status'] == 'verified_task_identity' for row in rows), rows
    assert len({row['invocation_id'] for row in rows}) == 4, rows
    assert len({row['binary_id'] for row in rows}) == 2, rows
    assert len({row['worker']['stream_id'] for row in rows}) == 2, rows
    assert all(row['clock_alignment'] == 'unverified' for row in rows), rows
    for (n, stream_index), storage in outputs.items():
        actual = storage.cpu()
        torch.testing.assert_close(actual[16:-16],
                                   torch.arange(n, dtype=torch.float32) + 1)
        assert torch.all(actual[:16] == -12345.) and torch.all(
            actual[-16:] == -12345.)
        torch.testing.assert_close(inputs[n].cpu(),
                                   torch.arange(n, dtype=torch.float32))
    provenance.update(status='passed',
                      receipts=receipts,
                      task_identities=proofs)
    (args.output /
     'result.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('CANN_PUBLIC_NATIVE_RECEIPT_SMOKE_PASSED', flush=True)


if __name__ == '__main__':
    main()
