"""Build and install an independent Enflame wheel from pinned public sources.

Dependencies are installed SDK/LLVM distributions, not another FlagPrism build.
The supplied FlagTree checkout is read only; its pinned commit is cloned into
--workdir before the maintained integration patch is applied.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

FLAGTREE_COMMIT = 'add842f2c495a3974944733ea6b07ff6b5bfcee8'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', type=Path, required=True)
    parser.add_argument('--flagtree', type=Path, required=True)
    parser.add_argument('--llvm-prefix', type=Path, required=True)
    parser.add_argument('--tops-prefix', type=Path, required=True)
    parser.add_argument('--json-include', type=Path, required=True)
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume the immutable source snapshot in an existing workdir')
    parser.add_argument('--vendor-site-packages', type=Path)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    for name in ('component', 'flagtree'):
        source = getattr(args, name)
        if args.workdir == source or args.workdir.is_relative_to(source):
            parser.error(f'--workdir must be outside the {name} source')
    if not 1 <= args.jobs <= 64:
        parser.error('--jobs must be in [1,64]')
    for path in (args.llvm_prefix / 'lib/cmake/llvm/LLVMConfig.cmake',
                 args.llvm_prefix / 'lib/cmake/mlir/MLIRConfig.cmake',
                 args.tops_prefix / 'include/tops/tops_runtime.h',
                 args.tops_prefix / 'extras/TOPSPTI/lib64/libtopspti.so',
                 args.json_include / 'nlohmann/json.hpp'):
        if not path.is_file():
            parser.error(f'missing required installed dependency: {path}')
    if args.vendor_site_packages is None:
        spec = importlib.util.find_spec('torch')
        if spec is None or not spec.origin:
            parser.error(
                'install matching Torch/GCU dependencies or pass --vendor-site-packages'
            )
        args.vendor_site_packages = Path(spec.origin).resolve().parent.parent
    args.workdir.mkdir(parents=True, exist_ok=args.resume)
    history = args.workdir / 'commands.json'
    commands = json.loads(history.read_text()) if args.resume else []
    env = dict(os.environ,
               FLAGTREE_BACKEND='enflame',
               TOPS_HOME=str(args.tops_prefix),
               LLVM_SYSPATH=str(args.llvm_prefix),
               KURAMA_LLVM_DIR=str(args.llvm_prefix))
    env.pop('PYTHONPATH', None)

    def run(command, name, **kwargs):
        original = name
        attempt = 0
        while (args.workdir / (name + '.log')).exists():
            attempt += 1
            name = original + '-resume' + str(attempt)
        command = [str(word) for word in command]
        commands.append({'name': name, 'argv': command})
        (args.workdir /
         'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        with (args.workdir / (name + '.log')).open('wb') as log:
            result = subprocess.run(command,
                                    env=env,
                                    stdout=log,
                                    stderr=subprocess.STDOUT,
                                    **kwargs)
        (args.workdir /
         (name + '.exit')).write_text(str(result.returncode) + '\n')
        if result.returncode:
            raise RuntimeError(
                f'{name} failed with exit {result.returncode}; see {args.workdir / (name + ".log")}'
            )

    host = args.workdir / 'FlagTree'
    component = args.workdir / 'FlagPrism'
    if args.resume:
        captured = json.loads(
            (args.workdir / 'source-sha256.json').read_text())
        for name, digest in captured.items():
            if hashlib.sha256(
                (component / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError(
                    f'original source snapshot was modified: {name}')
    else:
        run([
            'git', 'clone', '--no-hardlinks', '--no-checkout', args.flagtree,
            host
        ], 'clone')
        run(['git', '-C', host, 'checkout', '--detach', FLAGTREE_COMMIT],
            'checkout')
        shutil.copytree(args.component,
                        component,
                        symlinks=True,
                        ignore=shutil.ignore_patterns(
                            '.git', '__pycache__', '*.pyc',
                            'usability_qualification'))
        source_files = {
            str(path.relative_to(component)):
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in component.rglob('*') if path.is_file()
        }
        (args.workdir / 'source-sha256.json'
         ).write_text(json.dumps(source_files, indent=2) + '\n')
        run([
            'git', '-C', host, 'apply',
            component / 'integration/patches/enflame/flagtree-source.patch'
        ], 'patch')
        (host / 'third_party/FlagPrism').symlink_to(component,
                                                    target_is_directory=True)
    build = args.workdir / 'build'
    native = args.workdir / 'native'
    run([
        'cmake', '-S', host, '-B', build, '-G', 'Ninja',
        '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
        '-DTRITON_BUILD_PYTHON_MODULE=ON', '-DTRITON_BUILD_UT=ON',
        '-DTRITON_BUILD_FLAGPRISM=ON', '-DTRITON_BUILD_PROTON=OFF',
        '-DTRITON_CODEGEN_BACKENDS=nvidia;amd;enflame',
        '-DFLAGTREE_BACKEND=enflame', '-DFLAGPRISM_BACKEND=enflame',
        f'-DFLAGPRISM_SOURCE_DIR={component}',
        f'-DFLAGPRISM_PYTHON_DIR={native}',
        f'-DTRITON_WHEEL_DIR={host / "python/triton"}',
        f'-DLLVM_DIR={args.llvm_prefix / "lib/cmake/llvm"}',
        f'-DMLIR_DIR={args.llvm_prefix / "lib/cmake/mlir"}',
        f'-DLLVM_SYSPATH={args.llvm_prefix}',
        f'-DLLVM_INCLUDE_DIRS={args.llvm_prefix / "include"}',
        f'-DLLVM_LIBRARY_DIR={args.llvm_prefix / "lib"}',
        f'-DJSON_INCLUDE_DIR={args.json_include}',
        f'-DPython3_EXECUTABLE={sys.executable}',
        f'-DTOPS_INCLUDE_DIR={args.tops_prefix / "include"}',
        f'-DTOPS_LIBRARY={args.tops_prefix / "lib/libtopsrt.so"}',
        f'-DTOPSPTI_INCLUDE_DIR={args.tops_prefix / "extras/TOPSPTI/include"}',
        f'-DTOPSPTI_ACTIVITY_LIBRARY={args.tops_prefix / "extras/TOPSPTI/lib64/libtopspti.so"}'
    ], 'configure')
    targets = [
        'triton', 'flagtree_debugger_native', 'flagtree_profiler_native',
        'triton-gcu300-opt', 'triton-gcu400-opt',
        f'_triton_gcu300_py{sys.version_info.major}{sys.version_info.minor}',
        f'_triton_gcu400_py{sys.version_info.major}{sys.version_info.minor}',
        'FlagTreeDebuggerMetadataTest', 'flagprism-gcu-timeline'
    ]
    run([
        'cmake', '--build', build, '--target', *targets, '--parallel',
        args.jobs
    ], 'build')
    # Execute the actual compiled unit binary, never count an empty ctest regex.
    executables = [
        path for path in build.rglob('FlagTreeDebuggerMetadataTest')
        if path.is_file() and os.access(path, os.X_OK)
    ]
    if len(executables) != 1:
        raise RuntimeError(
            f'expected one metadata unit executable, found {executables}')
    unit_xml = args.workdir / ('metadata-unit-resume.xml'
                               if args.resume else 'metadata-unit.xml')
    run([executables[0], '--gtest_output=xml:' + str(unit_xml)],
        'metadata-unit')
    wheel = args.workdir / 'wheel'
    wheel_attempt = 0
    while wheel.exists():
        wheel_attempt += 1
        wheel = args.workdir / ('wheel-resume' + str(wheel_attempt))
    run([
        sys.executable,
        component / 'integration/patches/enflame/build_automatic_wheel.py',
        '--flagtree', host, '--component', component, '--native-python',
        native, '--core-library', build / 'libtriton.so', '--backend-build',
        build, '--output', wheel
    ], 'wheel')
    venv = args.workdir / 'venv'
    venv_attempt = 0
    while venv.exists():
        venv_attempt += 1
        venv = args.workdir / ('venv-resume' + str(venv_attempt))
    run([sys.executable, '-m', 'venv', '--without-pip', venv], 'venv')
    wheels = list((wheel / 'dist').glob('*.whl'))
    if len(wheels) != 1:
        raise RuntimeError(f'expected one wheel, found {wheels}')
    run([
        sys.executable, '-m', 'pip', '--python', venv / 'bin/python',
        'install', '--no-deps', wheels[0]
    ], 'install')
    site = next((venv / 'lib').glob('python*/site-packages'))
    (site / 'vendor-dependencies.pth'
     ).write_text(str(args.vendor_site_packages) + '\n')
    run([
        venv / 'bin/python',
        component / 'tests/enflame/installed_environment.py',
        '--wheel-manifest', wheel / 'result.json'
    ],
        'installed-audit',
        cwd='/tmp')
    result = {
        'status': 'source_build_and_independent_install_passed',
        'flagtree_commit': FLAGTREE_COMMIT,
        'component_snapshot': str(component),
        'build': str(build),
        'native': str(native),
        'wheel': json.loads((wheel / 'result.json').read_text()),
        'venv': str(venv),
        'llvm_prefix': str(args.llvm_prefix),
        'tops_prefix': str(args.tops_prefix),
        'vendor_site_packages': str(args.vendor_site_packages),
        'targets': targets
    }
    (args.workdir /
     'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
