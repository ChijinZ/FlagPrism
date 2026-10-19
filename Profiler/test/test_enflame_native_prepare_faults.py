"""Real TOPS headers and actual native sources; CPU fault injection, no GCU."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess

import pytest

ROOT = Path(__file__).parents[2]


def no_core_dump():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def compile_fixture(output, enabled):
    include = Path(
        os.environ.get('FLAGPRISM_TEST_TOPS_INCLUDE', '/opt/tops/include'))
    if not (include / 'tops/tops_runtime.h').is_file():
        pytest.skip('requires real TOPS SDK headers for native CPU ABI tests')
    sources = [
        ROOT / name
        for name in ('Debugger/test/unittest/EnflamePrepareFaultTest.cpp',
                     'Debugger/lib/Frontend/Bridge.cpp',
                     'Debugger/lib/Runtime/TransferEngine.cpp',
                     'Debugger/lib/Runtime/BufferLayout.cpp')
    ]
    command = [
        os.environ.get('CXX', 'c++'), '-std=c++17',
        '-DFLAGTREE_DEBUGGER_HAS_ENFLAME_RUNTIME=' + str(int(enabled)),
        '-DFLAGTREE_DEBUGGER_HAS_CANN_RUNTIME=0', '-I' + str(include),
        '-I' + str(ROOT / 'Debugger/include'),
        *(str(path) for path in sources), '-ldl', '-pthread', '-o',
        str(output)
    ]
    result = subprocess.run(command,
                            capture_output=True,
                            text=True,
                            timeout=120)
    (output.parent / 'compile.log').write_text(result.stdout + result.stderr)
    (output.parent / 'compile.json').write_text(
        json.dumps(
            {
                'argv':
                command,
                'exit_code':
                result.returncode,
                'source_sha256': {
                    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sources
                },
                'sdk_header_sha256': {
                    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (include / 'tops').glob('*.h')
                },
                'link_policy':
                'CPU fixture defines SDK symbols; no real runtime library linked',
                'binary_sha256':
                hashlib.sha256(output.read_bytes()).hexdigest() if output.
                exists() else None,
            },
            indent=2) + '\n')
    assert result.returncode == 0, result.stdout + result.stderr
    return output


@pytest.fixture(scope='module')
def native_fault_binary(tmp_path_factory):
    return compile_fixture(
        tmp_path_factory.mktemp('native-enflame-fault') / 'fault-test', True)


@pytest.mark.parametrize('fault', [
    'active', 'invalidated', 'query', 'malloc', 'host', 'host-and-free',
    'memset', 'memset-and-free', 'copy', 'copy-and-free', 'eager', 'stream-v2',
    'stream-v3'
])
def test_enflame_prepare_failure_is_catchable_and_transactional(
        native_fault_binary, fault):
    result = subprocess.run([str(native_fault_binary), fault],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            preexec_fn=no_core_dump)
    (native_fault_binary.parent / (fault + '.log')).write_text(result.stdout +
                                                               result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'CPU_FAULT_PASS ' + fault in result.stdout


def test_sdk_disabled_public_gcu_and_cann_reject_without_runtime_calls(
        tmp_path):
    binary = compile_fixture(tmp_path / 'sdk-disabled', False)
    for backend in ('unavailable', 'cann-unavailable'):
        result = subprocess.run([str(binary), backend],
                                capture_output=True,
                                text=True,
                                timeout=15,
                                preexec_fn=no_core_dump)
        (tmp_path / (backend + '.log')).write_text(result.stdout +
                                                   result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'CPU_FAULT_PASS ' + backend in result.stdout
