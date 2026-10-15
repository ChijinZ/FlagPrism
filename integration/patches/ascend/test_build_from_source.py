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
