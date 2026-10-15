"""CPU-only failure and provenance checks for the public source-build entrypoint."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

MODULE = Path(__file__).with_name('build_from_source.py')


@pytest.fixture
def recipe_module():
    spec = importlib.util.spec_from_file_location('ascend_source_recipe',
                                                  MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments(tmp_path):
    return SimpleNamespace(work_dir=tmp_path,
                           llvm22_prefix=tmp_path / 'llvm22',
                           llvm15_prefix=tmp_path / 'llvm15',
                           cann_root=tmp_path / 'sdk',
                           command_timeout=5)


def test_failed_command_preserves_original_output_pid_and_exit(
        recipe_module, tmp_path):
    recipe = recipe_module.Recipe(arguments(tmp_path))
    with pytest.raises(RuntimeError, match='exited 7; retained log'):
        recipe.run('fail', [
            sys.executable, '-c',
            'print("original compiler failure");raise SystemExit(7)'
        ])
    record = json.loads((tmp_path / 'recipe.json').read_text())['commands'][0]
    assert record['returncode'] == 7 and record['pid'] > 0
    assert 'original compiler failure' in Path(record['log']).read_text()
    assert record['command'][0] == sys.executable


def test_resume_retains_prior_command_evidence(recipe_module, tmp_path):
    recipe_module.Recipe(arguments(tmp_path)).run(
        'probe', [sys.executable, '-c', 'print("first")'])
    recipe_module.Recipe(arguments(tmp_path)).run(
        'probe', [sys.executable, '-c', 'print("second")'])
    records = json.loads((tmp_path / 'recipe.json').read_text())['commands']
    assert len(records) == 2 and records[0]['log'] != records[1]['log']
    assert Path(records[0]['log']).read_text().strip() == 'first'
    assert Path(records[1]['log']).read_text().strip() == 'second'


def test_timeout_stops_owned_command_and_retains_receipt(
        recipe_module, tmp_path):
    args = arguments(tmp_path)
    args.command_timeout = .1
    recipe = recipe_module.Recipe(args)
    with pytest.raises(subprocess.TimeoutExpired):
        recipe.run('timeout', [
            sys.executable, '-c',
            'import time;print("partial",flush=True);time.sleep(30)'
        ])
    record = json.loads((tmp_path / 'recipe.json').read_text())['commands'][0]
    assert record['state'] == 'interrupted' and record['returncode'] < 0
    assert 'partial' in Path(record['log']).read_text()


def test_existing_workdir_is_rejected_before_mutation(tmp_path):
    result = subprocess.run([
        sys.executable,
        str(MODULE), '--component',
        str(tmp_path / 'source'), '--work-dir',
        str(tmp_path), '--llvm22-prefix', '/unused', '--llvm15-prefix',
        '/unused', '--cann-root', '/unused', '--json-include', '/unused'
    ],
                            text=True,
                            capture_output=True)
    assert result.returncode == 2 and '--work-dir exists' in result.stderr
    assert not (tmp_path / 'recipe.json').exists()


def test_source_manifest_detects_deleted_native_source(recipe_module,
                                                       tmp_path):
    source = tmp_path / 'Debugger/lib/Metadata/Metadata.cpp'
    source.parent.mkdir(parents=True)
    source.write_text('native input\n')
    before = recipe_module.source_manifest(tmp_path)
    source.unlink()
    assert before != recipe_module.source_manifest(tmp_path)


@pytest.mark.parametrize('failure', ['assemble-wheel', 'install-wheel'])
def test_build_install_resume_preserves_failed_attempt(recipe_module, tmp_path,
                                                       monkeypatch, failure):
    """Exercise real orchestration/receipts with CPU external-command fixtures.

    Compiler/SDK building, pip and the vendor import probe are fake boundaries;
    this checks recovery and evidence identity, not a real Ascend installation.
    """
    import ast
    import hashlib

    root = tmp_path / 'build'
    root.mkdir()
    args = arguments(root)
    args.resume = False
    native_files = {
        'compiler': 'core-build/libtriton.so',
        'helper': 'core-build/third_party/ascend/bin/triton-mlir-opt',
        'plugin': 'observer-build/FlagPrismAscendLateObserver.so',
        'profiler': 'native-python/flagtree/profiler/profiler.so',
        'debugger': 'native-python/flagtree/debugger/debugger.so',
        'header': 'native-python/flagtree/profiler/_cann_launch_receipt.h',
    }
    for name, relative in native_files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('fixture-' + name).encode())
    header = root / 'component/Profiler/csrc/include/Profiler/Vendor/CannLaunchReceipt.h'
    header.parent.mkdir(parents=True)
    header.write_bytes((root / native_files['header']).read_bytes())
    monkeypatch.setattr(recipe_module.Recipe, 'build_native',
                        lambda self: None)
    original_run = recipe_module.Recipe.run
    requested = []
    injected = False

    def boundary(self, label, argv, **kwargs):
        nonlocal injected
        argv = [str(x) for x in argv]
        requested.append((label, argv))
        fail = label == failure and not injected
        if fail:
            injected = True
        if label == 'assemble-wheel':
            output = Path(argv[argv.index('--output') + 1])
            # Mirrors the real assembler's exclusive output mkdir. Baseline
            # --resume fails here before the second attempt can complete.
            code = ('from pathlib import Path;import sys;'
                    'p=Path(sys.argv[1]);p.mkdir();'
                    '(p/"original-marker").write_text("retained");')
            if fail:
                code += 'print("injected assembler failure");raise SystemExit(19)'
            else:
                code += (
                    '(p/"dist").mkdir();'
                    '(p/"dist/fixture.whl").write_bytes(b"wheel-fixture")')
            return original_run(self, label,
                                [sys.executable, '-c', code, output])
        if label == 'create-venv':
            prefix = Path(argv[-1])
            code = ('from pathlib import Path;import sys;'
                    'p=Path(sys.argv[1]);(p/"bin").mkdir(parents=True);'
                    '(p/"bin/python").write_text("CPU fixture interpreter")')
            return original_run(self, label,
                                [sys.executable, '-c', code, prefix])
        if label == 'install-wheel':
            prefix = Path(argv[0]).parent.parent
            assert Path(argv[-1]).parent.parent.name.replace(
                'wheel', 'venv') == prefix.name
            code = ('from pathlib import Path;import sys;'
                    '(Path(sys.argv[1])/"pip-marker").write_text("retained");')
            code += ('print("injected pip failure");raise SystemExit(23)'
                     if fail else 'print("CPU fixture install")')
            return original_run(self, label,
                                [sys.executable, '-c', code, prefix])
        assert label == 'check-install'
        prefix = Path(argv[0]).parent.parent
        probe = Path(argv[2])
        check = Path(argv[-1])
        expected_node = next(
            n for n in ast.parse(probe.read_text()).body
            if isinstance(n, ast.Assign) and isinstance(
                n.targets[0], ast.Name) and n.targets[0].id == 'expected')
        expected = ast.literal_eval(expected_node.value)
        # Independent oracle for generated native/header hash requirements.
        assert expected == {
            n: recipe_module.digest(root / p)
            for n, p in native_files.items()
        }
        files = {}
        for name, relative in native_files.items():
            target = prefix / 'lib' / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes((root / relative).read_bytes())
            files[name] = {
                'path': str(target),
                'sha256': recipe_module.digest(target)
            }
        data = dict(python=argv[0], files=files, npu_initialized=False)
        code = 'from pathlib import Path;import sys;Path(sys.argv[1]).write_text(sys.argv[2])'
        return original_run(
            self, label, [sys.executable, '-c', code, check,
                          json.dumps(data)])

    monkeypatch.setattr(recipe_module.Recipe, 'run', boundary)
    first = recipe_module.Recipe(args)
    with pytest.raises(RuntimeError, match='exited (19|23)') as error:
        first.build_install()
    first.save(state='failed', error=repr(error.value))
    preserved = {
        p: p.read_bytes()
        for p in root.rglob('*')
        if p.is_file() and (p.name.endswith('.log') or 'wheel' in p.parts or
                            'venv' in p.parts or p.name == 'check-install.py')
    }
    assert (root / 'wheel/original-marker').read_text() == 'retained'
    args.resume = True
    resumed = recipe_module.Recipe(args)
    resumed.build_install()
    receipt = json.loads((root / 'recipe.json').read_text())
    assert receipt['state'] == 'installed'
    assert receipt['installed_prefix'] == str(root / 'venv-resume1')
    assert receipt['installed_wheel'] == str(root /
                                             'wheel-resume1/dist/fixture.whl')
    assert receipt['wheel_sha256'] == hashlib.sha256(
        b'wheel-fixture').hexdigest()
    assert receipt['install_check'] == str(root / 'install-check-resume1.json')
    assert receipt['invocations'][-1]['arguments']['resume'] is True
    assert receipt['invocations'][-1]['previous_state'] == 'failed'
    assert all(p.read_bytes() == content for p, content in preserved.items())
    check = json.loads(Path(receipt['install_check']).read_text())
    assert check['python'] == str(root / 'venv-resume1/bin/python')
    for name, item in check['files'].items():
        assert Path(item['path']).is_relative_to(root / 'venv-resume1')
        assert item['sha256'] == recipe_module.digest(root /
                                                      native_files[name])
    failures = [r for r in receipt['commands'] if r['returncode']]
    assert len(failures) == 1
    assert failures[0]['returncode'] == (19 if failure == 'assemble-wheel' else
                                         23)
    assert 'injected' in Path(failures[0]['log']).read_text()
    outputs = [
        argv[-1] for label, argv in requested if label == 'assemble-wheel'
    ]
    assert outputs == [str(root / 'wheel'), str(root / 'wheel-resume1')]
