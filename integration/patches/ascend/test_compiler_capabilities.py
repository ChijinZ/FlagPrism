"""CPU external-driver boundaries: compiler capability follows bytes, not basename."""
from collections import defaultdict
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

MODERN = [
    '--enable-hfusion-compile', '--enable-triton-kernel-compile',
    '--limit-auto-multi-buffer-buffer', '--reg-based', '--save-linked-ir'
]


def tool(path, modern=True, help_exit=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!' + sys.executable + '''
import json,pathlib,sys
modern = MODERN
help_exit = HELP_EXIT
flags = FLAGS
with pathlib.Path(__file__).with_name('calls.jsonl').open('a') as log:
 log.write(json.dumps(sys.argv[1:])+'\\n')
if '--help' in sys.argv:
 print(' '.join(flags) if modern else 'legacy compiler options')
 if help_exit:print('explicit capability fixture failure',file=sys.stderr)
 sys.exit(help_exit)
args=sys.argv[1:]
required=['--enable-hfusion-compile=true','--enable-triton-kernel-compile=true']
assert all(flag in args for flag in required) if modern else all(flag not in args for flag in required), 'compiler-family flags mismatch'
output=pathlib.Path(args[args.index('-o')+1]+('.o' if modern else '_reloc.o'))
output.write_bytes(b'cpu-modern' if modern else b'cpu-legacy')
'''.replace('MODERN', repr(modern)).replace('HELP_EXIT',
                                            str(help_exit)).replace(
                                                'FLAGS', repr(MODERN)))
    path.chmod(0o755)
    return path


@pytest.fixture
def backend(monkeypatch):
    import torch  # noqa: F401
    import torch_npu
    from triton.backends.ascend import compiler, utils
    monkeypatch.setattr(compiler, '_parse_linalg_metadata',
                        lambda source, metadata: (source, metadata))
    monkeypatch.setattr(compiler, 'NPUUtils',
                        lambda: SimpleNamespace(get_arch=lambda: 'Ascend910B'))
    monkeypatch.setattr(compiler, 'get_libdevice',
                        lambda: '/cpu-fixture/libdevice.bc')
    assert not torch_npu.npu.is_initialized()
    yield compiler, utils
    assert not torch_npu.npu.is_initialized()


def compile_fixture(compiler, stage):
    metadata = defaultdict(lambda: None)
    metadata['target'] = SimpleNamespace(arch='Ascend910B')
    options = compiler.NPUOptions(use_bytecode=False)
    return getattr(compiler, stage)('module {}', metadata, options), metadata


@pytest.mark.parametrize('stage', [
    'linalg_to_bin_enable_npu_compile_910_95',
    'linalg_to_bin_enable_npu_compile_A2_A3'
])
@pytest.mark.parametrize(
    'selection',
    ['override-link', 'override-direct', 'packaged-link', 'path-link'])
def test_versioned_target_reaches_actual_linalg_driver(backend, monkeypatch,
                                                       tmp_path, stage,
                                                       selection):
    compiler, utils = backend
    executable = tool(tmp_path / 'toolchain' / 'compiler-custom-version')
    link = tmp_path / 'bin' / 'bishengir-compile'
    link.parent.mkdir()
    link.symlink_to(executable)
    monkeypatch.delenv('TRITON_ASCEND_COMPILER', raising=False)
    if selection.startswith('override'):
        monkeypatch.setenv(
            'TRITON_ASCEND_COMPILER',
            str(link if selection.endswith('link') else executable))
    else:
        monkeypatch.setattr(utils, '__file__', str(tmp_path / 'utils.py'))
        if selection == 'packaged-link':
            packaged = tmp_path / 'bishengir/bin/bishengir-compile'
            packaged.parent.mkdir(parents=True)
            packaged.symlink_to(executable)
        else:
            monkeypatch.setattr(utils.shutil, 'which', lambda name: str(link))
    result, metadata = compile_fixture(compiler, stage)
    assert utils._check_bishengir_api_change()
    assert utils._check_bishengir_is_regbased()
    assert utils._check_bishengir_able_save_ir()
    assert result == b'cpu-modern'
    assert metadata['ascend_compiler_identity']['path'] == str(executable)
    calls = [
        json.loads(line) for line in executable.with_name(
            'calls.jsonl').read_text().splitlines()
    ]
    assert sum(call == ['--help'] for call in calls) == 1
    compile_call = next(call for call in calls if call != ['--help'])
    assert '--enable-hfusion-compile=true' in compile_call
    assert '--enable-triton-kernel-compile=true' in compile_call


@pytest.mark.parametrize('stage', [
    'linalg_to_bin_enable_npu_compile_910_95',
    'linalg_to_bin_enable_npu_compile_A2_A3'
])
def test_same_path_capability_refresh_preserves_legacy(backend, monkeypatch,
                                                       tmp_path, stage):
    compiler, utils = backend
    executable = tool(tmp_path / 'arbitrary-name')
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(executable))
    assert compile_fixture(compiler, stage)[0] == b'cpu-modern'
    old = executable.stat()
    tool(executable, modern=False)
    os.utime(executable, ns=(old.st_atime_ns, old.st_mtime_ns))
    assert not utils._check_bishengir_api_change()
    assert not utils._check_bishengir_is_regbased()
    assert not utils._check_bishengir_able_save_ir()
    assert compile_fixture(compiler, stage)[0] == b'cpu-legacy'
    calls = [
        json.loads(line) for line in executable.with_name(
            'calls.jsonl').read_text().splitlines()
    ]
    assert sum(call == ['--help'] for call in calls) == 2


def test_probe_failure_does_not_silently_choose_legacy(backend, monkeypatch,
                                                       tmp_path):
    _, utils = backend
    executable = tool(tmp_path / 'compiler', help_exit=2)
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(executable))
    for _ in range(2):
        with pytest.raises(
                RuntimeError,
                match=
                'capability probe failed.*explicit capability fixture failure'
        ):
            utils._check_bishengir_api_change()
    calls = [
        json.loads(line) for line in executable.with_name(
            'calls.jsonl').read_text().splitlines()
    ]
    assert calls == [['--help'], ['--help']]


def test_probe_timeout_is_bounded_and_explicit(backend, monkeypatch, tmp_path):
    _, utils = backend
    executable = tool(tmp_path / 'compiler')
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(executable))

    def timeout(command, **kwargs):
        assert kwargs['timeout'] == 30
        raise subprocess.TimeoutExpired(command, 30)

    monkeypatch.setattr(utils.subprocess, 'run', timeout)
    with pytest.raises(RuntimeError, match='capability probe failed'):
        utils._check_bishengir_api_change()


@pytest.mark.parametrize('name', ['PATH', 'LD_LIBRARY_PATH'])
def test_help_cache_uses_loader_search_environment(backend, monkeypatch,
                                                   tmp_path, name):
    _, utils = backend
    executable = tool(tmp_path / 'compiler')
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(executable))
    assert utils._check_bishengir_api_change()
    monkeypatch.setenv(
        name,
        os.environ.get(name, '') + ':/cpu-fixture/alternate-search')
    assert utils._check_bishengir_api_change()
    calls = [
        json.loads(line) for line in executable.with_name(
            'calls.jsonl').read_text().splitlines()
    ]
    assert calls == [['--help'], ['--help']]
