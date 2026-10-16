"""Build an isolated Ascend compiler, runtime, observer, wheel and installation.

No existing FlagPrism compiler build or native binary is an input. Source mirrors
and LLVM/SDK dependency prefixes may be reused; every command has a receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import sysconfig
import time

PINS = {
    'flagtree': '0364ed4bc39d1dfae483741ec272298297fa5bda',
    'ascend_ir': '4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9',
    'flir': 'ff91e64b6042a27e0db053f28ea3741be65d24d0',
}
PATCHES = {
    'flagtree': ('flagtree-source-census-v2.patch', ),
    'flir': ('flir-source-census-v2.patch', ),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest(root):
    result = {}
    for folder in ('Debugger', 'Profiler', 'cmake', 'python',
                   'integration/patches/ascend'):
        for path in (root / folder).rglob('*'):
            if path.is_file() and not any(part in path.parts for part in (
                    '__pycache__', '.pytest_cache',
                    '.ruff_cache')) and path.suffix not in ('.so', '.pyc'):
                result[str(path.relative_to(root))] = digest(path)
    return result


class Recipe:

    def __init__(self, args):
        self.args = args
        self.root = args.work_dir
        self.receipt = self.root / 'recipe.json'
        self.document = json.loads(
            self.receipt.read_text()) if self.receipt.exists() else {}
        self.records = self.document.get('commands', [])
        self.env = dict(os.environ)
        for name in ('PYTHONPATH', 'FLAGPRISM_ASCEND_LATE_PLUGIN',
                     'FLAGPRISM_ASCEND_COMPILER_CAPTURE', 'FLAGTREE_PLUGIN'):
            self.env.pop(name, None)
        self.env.update(FLAGTREE_BACKEND='ascend',
                        TORCH_DEVICE_BACKEND_AUTOLOAD='0',
                        LLVM_SYSPATH=str(args.llvm22_prefix),
                        ASCEND_HOME_PATH=str(args.cann_root))
        self.env['PATH'] = ':'.join([
            str(args.llvm22_prefix / 'bin'),
            str(args.llvm15_prefix / 'bin'),
            str(args.cann_root / 'bin'), self.env['PATH']
        ])
        self.env['LD_LIBRARY_PATH'] = ':'.join([
            str(args.cann_root / 'lib64'),
            self.env.get('LD_LIBRARY_PATH', '')
        ])
        self.document.setdefault('invocations', []).append({
            'pid':
            os.getpid(),
            'started':
            time.time(),
            'entrypoint_sha256':
            digest(Path(__file__)),
            'previous_state':
            self.document.get('state'),
            'previous_error':
            self.document.get('error'),
            'arguments': {
                k: str(v) if isinstance(v, Path) else v
                for k, v in vars(args).items()
            }
        })
        self.document.pop('error', None)
        self.save(state='preparing')

    def save(self, **extra):
        if 'schema_version' not in self.document:
            self.document.update(schema_version=1,
                                 pins=PINS,
                                 python=sys.executable,
                                 owner_pid=os.getpid(),
                                 commands=self.records,
                                 arguments={
                                     k: str(v) if isinstance(v, Path) else v
                                     for k, v in vars(self.args).items()
                                 })
        self.document.update(extra)
        self.receipt.write_text(json.dumps(self.document, indent=2) + '\n')

    def run(self, label, argv, cwd=None, env=None):
        log = self.root / f'{len(self.records):03d}-{label}.log'
        record = dict(label=label,
                      command=[str(x) for x in argv],
                      cwd=str(cwd or self.root),
                      log=str(log),
                      started=time.time())
        self.records.append(record)
        with log.open('w') as output:
            process = subprocess.Popen(record['command'],
                                       cwd=cwd or self.root,
                                       env=env or self.env,
                                       stdout=output,
                                       stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record['pid'] = process.pid
            self.save()
            try:
                record['returncode'] = process.wait(
                    timeout=self.args.command_timeout)
            except BaseException as error:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
                record.update(state='interrupted',
                              error=repr(error),
                              returncode=process.returncode,
                              ended=time.time())
                self.save(state='failed')
                raise
        record['ended'] = time.time()
        self.save()
        if record['returncode']:
            raise RuntimeError(
                f'{label} exited {record["returncode"]}; retained log: {log}')
        return log.read_text()

    def checkout(self, name, repository, target):
        if not target.exists():
            self.run(name + '-clone',
                     ['git', 'clone', '--no-checkout', repository, target])
            self.run(name + '-checkout',
                     ['git', '-C', target, 'checkout', '--detach', PINS[name]])
        commit = self.run(name + '-pin',
                          ['git', '-C', target, 'rev-parse', 'HEAD']).strip()
        if name not in PATCHES:
            status = self.run(name + '-clean', [
                'git', '-C', target, 'status', '--porcelain',
                '--untracked-files=no'
            ]).strip()
            if status:
                raise ValueError(
                    f'{name} source has tracked modifications: {status}')
        if commit != PINS[name]:
            raise ValueError(
                f'{name} pin mismatch: {commit}; expected {PINS[name]}')

    def apply_patches(self, name, target, patch_files):
        """Resume only our recorded tracked diff, including staged changes."""
        receipt = self.root / f'{name}-patches-applied.json'
        hashes = {n: digest(patch_files / n) for n in PATCHES[name]}
        previous = json.loads(
            receipt.read_text()) if receipt.exists() else None
        if previous is not None:
            if previous['patches'] != hashes:
                raise ValueError(
                    'Patch bytes changed; use a new work directory')
        else:
            status = self.run(name + '-before-patches', [
                'git', '-C', target, 'status', '--porcelain',
                '--untracked-files=no'
            ]).strip()
            if status:
                raise ValueError(
                    f'{name} has unrecorded tracked changes; use a fresh work directory'
                )
            for index, filename in enumerate(PATCHES[name]):
                patch = patch_files / filename
                self.run(f'{name}-patch-{index}-check',
                         ['git', '-C', target, 'apply', '--check', patch])
                self.run(f'{name}-patch-{index}-apply',
                         ['git', '-C', target, 'apply', patch])
        diff = self.run(name + '-diff',
                        ['git', '-C', target, 'diff', '--binary', 'HEAD'])
        diff_sha = hashlib.sha256(diff.encode()).hexdigest()
        if previous is not None and previous['diff_sha256'] != diff_sha:
            raise ValueError(
                f'{name} patched source changed unexpectedly; use a fresh work directory'
            )
        result = dict(patches=hashes, diff_sha256=diff_sha)
        if previous is None:
            receipt.write_text(json.dumps(result, indent=2) + '\n')
        return result

    def dependencies(self):
        evidence = {}
        for name, prefix, major in [('llvm22', self.args.llvm22_prefix, '22'),
                                    ('llvm15', self.args.llvm15_prefix, '15')]:
            config = prefix / 'bin/llvm-config'
            version = self.run(name + '-version',
                               [config, '--version']).strip()
            if version.split('.')[0] != major:
                raise ValueError(
                    f'{prefix}: expected LLVM {major}, found {version}')
            required = [
                config, prefix / 'lib/cmake/llvm/LLVMConfig.cmake',
                prefix / 'include/llvm/Config/llvm-config.h'
            ]
            if major == '22':
                required += [
                    prefix / 'lib/cmake/mlir/MLIRConfig.cmake',
                    prefix / 'bin/clang++'
                ]
            else:
                required += [prefix / 'bin/opt']
            evidence[name] = dict(
                prefix=str(prefix),
                version=version,
                files={str(p): digest(p)
                       for p in required},
                libraries={
                    str(p): digest(p)
                    for p in sorted((prefix / 'lib').glob('*'))
                    if p.is_file() and (p.suffix == '.a' or '.so' in p.name)
                })
        sdk = self.args.cann_root
        required = [
            sdk / 'include/acl/acl.h', sdk / 'lib64/libascendcl.so',
            sdk / 'bin/bisheng'
        ]
        evidence['cann'] = dict(root=str(sdk),
                                files={str(p): digest(p)
                                       for p in required},
                                compiler_version=self.run(
                                    'bisheng-version',
                                    [sdk / 'bin/bisheng', '--version']))
        evidence['json_header'] = dict(
            path=str(self.args.json_include / 'nlohmann/json.hpp'),
            sha256=digest(self.args.json_include / 'nlohmann/json.hpp'))
        previous = self.document.get('dependencies')
        if previous is not None and previous != evidence:
            raise ValueError(
                'Dependency prefix identity changed; use a fresh work directory'
            )
        self.save(dependencies=evidence)

    def prepare(self):
        a = self.args
        component = self.root / 'component'
        if not component.exists() or a.refresh_component:
            if component.exists():
                shutil.rmtree(component)
            component.mkdir()
            for folder in ('Debugger', 'Profiler', 'cmake', 'python',
                           'integration/patches/ascend'):
                shutil.copytree(a.component / folder,
                                component / folder,
                                dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(
                                    '__pycache__', '*.so', '.pytest_cache'))
        manifest = source_manifest(component)
        if manifest != source_manifest(a.component):
            raise ValueError(
                'Component snapshot differs; use --refresh-component deliberately before rebuilding'
            )
        self.save(component_files=manifest,
                  component_snapshot_sha256=hashlib.sha256(
                      json.dumps(manifest,
                                 sort_keys=True).encode()).hexdigest())
        tree = self.root / 'FlagTree'
        self.checkout('flagtree', a.flagtree_repository, tree)
        patch_files = component / 'integration/patches/ascend'
        patches = {
            'flagtree': self.apply_patches('flagtree', tree, patch_files)
        }
        self.checkout('ascend_ir', a.ascend_ir_repository,
                      tree / 'third_party/ascend/AscendNPU-IR')
        flir = tree / 'third_party/flir'
        self.checkout('flir', a.flir_repository, flir)
        patches['flir'] = self.apply_patches('flir', flir, patch_files)
        link = tree / 'third_party/FlagPrism'
        if not link.exists():
            link.symlink_to(component, target_is_directory=True)
        if link.resolve() != component:
            raise ValueError(
                'FlagPrism integration link must resolve to this isolated component snapshot'
            )
        self.save(state='prepared', patches=patches)

    def configure(self):
        a = self.args
        tree = self.root / 'FlagTree'
        llvm = a.llvm22_prefix
        self.run('configure-core', [
            'cmake', '-G', 'Ninja', '-S', tree, '-B', self.root / 'core-build',
            '-DCMAKE_BUILD_TYPE=Release', '-DTRITON_BUILD_PYTHON_MODULE=ON',
            '-DTRITON_WHEEL_DIR=' + str(self.root / 'parent-wheel'),
            '-DTRITON_BUILD_FLAGPRISM=ON', '-DTRITON_BUILD_PROTON=OFF',
            '-DTRITON_BUILD_UT=OFF',
            '-DTRITON_CODEGEN_BACKENDS=ascend;nvidia;amd',
            '-DFLAGPRISM_BACKEND=ascend', '-DFLAGPRISM_SOURCE_DIR=' +
            str(self.root / 'component'), '-DFLAGPRISM_PYTHON_DIR=' +
            str(self.root / 'native-python'), '-DPYTHON_EXTENSION_SUFFIX=' +
            sysconfig.get_config_var('EXT_SUFFIX'),
            '-DLLVM_DIR=' + str(llvm / 'lib/cmake/llvm'), '-DMLIR_DIR=' +
            str(llvm / 'lib/cmake/mlir'), '-DLLVM_INCLUDE_DIRS=' +
            str(llvm / 'include'), '-DLLVM_LIBRARY_DIR=' + str(llvm / 'lib'),
            '-DLLVM_SYSPATH=' + str(llvm), '-DJSON_INCLUDE_DIR=' +
            str(a.json_include), '-DFLAGTREE_DEBUGGER_CANN_ROOT=' +
            str(a.cann_root), '-DTRITON_PARALLEL_LINK_JOBS=1'
        ])
        self.run('configure-observer', [
            'cmake', '-G', 'Ninja', '-S', self.root /
            'component/Profiler/llvm', '-B', self.root / 'observer-build',
            '-DLLVM_DIR=' + str(a.llvm15_prefix / 'lib/cmake/llvm'),
            '-DCMAKE_BUILD_TYPE=Release'
        ])
        cache = (self.root / 'core-build/CMakeCache.txt').read_text()
        required = {
            'CMAKE_HOME_DIRECTORY:INTERNAL': str(tree),
            'LLVM_DIR:UNINITIALIZED': str(llvm / 'lib/cmake/llvm'),
            'FLAGPRISM_SOURCE_DIR:UNINITIALIZED': str(self.root / 'component')
        }
        for key, value in required.items():
            if key + '=' + value not in cache:
                raise ValueError(
                    f'Configured CMake input does not match {key}={value}')
        self.save(
            state='configured',
            cmake_cache_sha256=digest(self.root / 'core-build/CMakeCache.txt'),
            build_graph_sha256=digest(self.root / 'core-build/build.ninja'))

    def build_native(self):
        a = self.args
        self.run('build-core', [
            'cmake', '--build', self.root / 'core-build', '--target', 'triton',
            'triton-mlir-opt', 'flagtree_profiler_native',
            'flagtree_debugger_native', '-j',
            str(a.jobs)
        ])
        self.run('build-observer', [
            'cmake', '--build', self.root / 'observer-build', '-j',
            str(a.jobs)
        ])
        if source_manifest(self.root /
                           'component') != self.document['component_files']:
            raise ValueError(
                'Source changed during build; artifacts cannot be certified')
        artifacts = [
            self.root / 'core-build/libtriton.so',
            self.root / 'core-build/third_party/ascend/bin/triton-mlir-opt',
            self.root / 'observer-build/FlagPrismAscendLateObserver.so', *list(
                (self.root / 'native-python/flagtree').rglob('*.so')),
            self.root /
            'native-python/flagtree/profiler/_cann_launch_receipt.h'
        ]
        self.save(state='native_built',
                  native_artifacts={str(p): digest(p)
                                    for p in artifacts})

    def build_install(self):
        self.build_native()
        # Treat wheel assembly and installation as one immutable attempt. A
        # failed assembler may leave a partial wheel directory; never reuse it.
        attempt = 0
        while True:
            suffix = '' if attempt == 0 else '-resume' + str(attempt)
            wheel = self.root / ('wheel' + suffix)
            venv = self.root / ('venv' + suffix)
            probe = self.root / ('check-install' + suffix + '.py')
            check = self.root / ('install-check' + suffix + '.json')
            if not any(path.exists() or path.is_symlink()
                       for path in (wheel, venv, probe, check)):
                break
            attempt += 1
        self.save(install_attempt=dict(wheel=str(wheel),
                                       venv=str(venv),
                                       probe=str(probe),
                                       check=str(check)))
        self.run('assemble-wheel', [
            sys.executable, self.root /
            'component/integration/patches/ascend/build_automatic_wheel.py',
            '--flagtree', self.root / 'FlagTree', '--component',
            self.root / 'component', '--native-python',
            self.root / 'native-python', '--core-library',
            self.root / 'core-build/libtriton.so', '--plugin', self.root /
            'observer-build/FlagPrismAscendLateObserver.so', '--output', wheel
        ])
        self.run(
            'create-venv',
            [sys.executable, '-m', 'venv', '--system-site-packages', venv])
        python = venv / 'bin/python'
        wheels = list((wheel / 'dist').glob('*.whl'))
        if len(wheels) != 1:
            raise ValueError('Expected exactly one wheel')
        self.run('install-wheel',
                 [python, '-m', 'pip', 'install', '--no-deps', wheels[0]])
        expected = {
            'compiler':
            digest(self.root / 'core-build/libtriton.so'),
            'profiler':
            digest(
                next((self.root /
                      'native-python/flagtree/profiler').glob('*.so'))),
            'debugger':
            digest(
                next((self.root /
                      'native-python/flagtree/debugger').glob('*.so'))),
            'helper':
            digest(self.root /
                   'core-build/third_party/ascend/bin/triton-mlir-opt'),
            'plugin':
            digest(self.root /
                   'observer-build/FlagPrismAscendLateObserver.so'),
            'header':
            digest(
                self.root /
                'component/Profiler/csrc/include/Profiler/Vendor/CannLaunchReceipt.h'
            )
        }
        probe.write_text(
            'import pathlib,sys,json,hashlib,torch,torch_npu\n'
            'import triton,flagtree.profiler,flagtree.debugger\n'
            'from flagtree.profiler.native import runtime_binding as pb\n'
            'from flagtree.debugger.native import runtime_binding as db\n'
            'import triton._C.libtriton as c\n'
            'files={}\n'
            'for n,m in [("compiler",c),("profiler",pb()),("debugger",db())]:\n'
            ' p=pathlib.Path(m.__file__);assert p.is_relative_to(sys.prefix);files[n]={"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}\n'
            'root=pathlib.Path(flagtree.profiler.__file__).parent\n'
            'for n,p in [("header",root/"_cann_launch_receipt.h"),("plugin",root/"lib/FlagPrismAscendLateObserver.so"),("helper",pathlib.Path(c.__file__).parent/"triton-mlir-opt")]:files[n]={"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}\n'
            'expected=' + repr(expected) + '\n'
            'assert all(files[n]["sha256"]==sha for n,sha in expected.items())\n'
            'python_files={}\n'
            'for component in ["Profiler","Debugger"]:\n'
            ' source=pathlib.Path(sys.argv[1])/component/"python"/("flagtree_"+component.lower());target=root.parent/component.lower();assert target.is_relative_to(sys.prefix)\n'
            ' for p in source.rglob("*.py"):\n'
            '  if "__pycache__" in p.parts:continue\n'
            '  installed=target/p.relative_to(source);sha=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(installed.read_bytes()).hexdigest()==sha;python_files[str(installed)]=sha\n'
            'assert not torch.npu.is_initialized()\n'
            'pathlib.Path(sys.argv[2]).write_text(json.dumps({"python":sys.executable,"files":files,"python_files":python_files,"npu_initialized":False},indent=2)+"\\n")\n'
            'print(json.dumps({"python":sys.executable,"files":files,"npu_initialized":False},indent=2))\n'
        )
        self.run('check-install',
                 [python, '-I', probe, self.root / 'component', check])
        artifacts = [
            self.root / 'core-build/libtriton.so',
            self.root / 'core-build/third_party/ascend/bin/triton-mlir-opt',
            self.root / 'observer-build/FlagPrismAscendLateObserver.so', *list(
                (self.root / 'native-python/flagtree').rglob('*.so')),
            self.root /
            'native-python/flagtree/profiler/_cann_launch_receipt.h'
        ]
        self.save(state='installed',
                  installed_prefix=str(venv),
                  installed_wheel=str(wheels[0]),
                  install_check=str(check),
                  wheel_sha256=digest(wheels[0]),
                  native_artifacts={str(p): digest(p)
                                    for p in artifacts})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('component', 'work-dir', 'llvm22-prefix', 'llvm15-prefix',
                 'cann-root', 'json-include'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--flagtree-repository',
                   default='https://github.com/flagos-ai/FlagTree.git')
    p.add_argument('--ascend-ir-repository',
                   default='https://gitcode.com/Ascend/AscendNPU-IR.git')
    p.add_argument('--flir-repository',
                   default='https://github.com/flagos-ai/flir.git')
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--command-timeout', type=int, default=7200)
    p.add_argument('--stop-after',
                   choices=('prepare', 'configure', 'native', 'install'),
                   default='install')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--refresh-component', action='store_true')
    a = p.parse_args()
    for name, value in vars(a).items():
        if isinstance(value, Path):
            setattr(a, name, value.resolve())
    if a.jobs < 1 or a.command_timeout < 1:
        p.error('--jobs and --command-timeout must be positive')
    if a.work_dir == a.component or a.work_dir.is_relative_to(a.component):
        p.error('--work-dir must be outside the component source')
    if a.work_dir.exists() and not a.resume:
        p.error(
            '--work-dir exists; use --resume deliberately or select a fresh directory'
        )
    a.work_dir.mkdir(parents=True, exist_ok=True)
    recipe = Recipe(a)
    try:
        recipe.dependencies()
        recipe.prepare()
        if a.stop_after != 'prepare':
            recipe.configure()
        if a.stop_after == 'native':
            recipe.build_native()
        elif a.stop_after == 'install':
            recipe.build_install()
    except BaseException as error:
        recipe.save(state='failed', error=repr(error))
        raise
    print(f'Receipt and command logs: {recipe.receipt}')


if __name__ == '__main__':
    main()
