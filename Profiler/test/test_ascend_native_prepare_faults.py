"""Compile actual native sources with controlled SDK faults; never uses an NPU."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope='module')
def native_fault_binary(tmp_path_factory):
    include = Path(
        os.environ.get('FLAGPRISM_TEST_CANN_INCLUDE',
                       '/usr/local/Ascend/cann-9.0.0/include'))
    if not (include / 'acl/acl_rt.h').is_file():
        pytest.skip('requires SDK headers for CPU fault-injection ABI checks')
    output = tmp_path_factory.mktemp('native-cann-fault') / 'fault-test'
    command = [
        os.environ.get('CXX', 'c++'), '-std=c++17',
        '-DFLAGTREE_DEBUGGER_HAS_CANN_RUNTIME=1', '-I' + str(include),
        '-I' + str(ROOT / 'Debugger/include'),
        str(ROOT / 'Debugger/test/unittest/CannPrepareFaultTest.cpp'),
        str(ROOT / 'Debugger/lib/Frontend/Bridge.cpp'),
        str(ROOT / 'Debugger/lib/Runtime/TransferEngine.cpp'),
        str(ROOT / 'Debugger/lib/Runtime/BufferLayout.cpp'), '-ldl',
        '-pthread', '-o',
        str(output)
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    (output.parent / 'compile.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return output


@pytest.mark.parametrize('fault', [
    'active', 'invalidated', 'query', 'host', 'host-and-free', 'memset',
    'memset-and-free', 'eager'
])
def test_cann_prepare_rejects_or_rolls_back_without_aborting(
        native_fault_binary, fault):
    result = subprocess.run([str(native_fault_binary), fault],
                            capture_output=True,
                            text=True)
    (native_fault_binary.parent / (fault + '.log')).write_text(result.stdout +
                                                               result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'CPU_FAULT_PASS ' + fault in result.stdout


def test_unrelated_invalid_backend_fatal_boundary_remains_explicit(
        native_fault_binary):
    import resource
    import signal

    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    result = subprocess.run([str(native_fault_binary), 'invalid-backend'],
                            capture_output=True,
                            text=True,
                            preexec_fn=no_core)
    (native_fault_binary.parent / 'remaining-fatal-boundary.log').write_text(
        result.stderr)
    assert result.returncode == -signal.SIGABRT
    assert 'cann transfer driver requires BufferMeta.backendKind == CANN' in result.stderr


def test_sdk_disabled_native_build_rejects_before_allocation(tmp_path):
    include = Path(
        os.environ.get('FLAGPRISM_TEST_CANN_INCLUDE',
                       '/usr/local/Ascend/cann-9.0.0/include'))
    if not (include / 'acl/acl_rt.h').is_file():
        pytest.skip('requires SDK headers only for fault fixture declarations')
    output = tmp_path / 'sdk-disabled'
    command = [
        os.environ.get('CXX', 'c++'), '-std=c++17',
        '-DFLAGTREE_DEBUGGER_HAS_CANN_RUNTIME=0', '-I' + str(include),
        '-I' + str(ROOT / 'Debugger/include'),
        str(ROOT / 'Debugger/test/unittest/CannPrepareFaultTest.cpp'),
        str(ROOT / 'Debugger/lib/Frontend/Bridge.cpp'),
        str(ROOT / 'Debugger/lib/Runtime/TransferEngine.cpp'),
        str(ROOT / 'Debugger/lib/Runtime/BufferLayout.cpp'), '-ldl',
        '-pthread', '-o',
        str(output)
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    (tmp_path / 'compile.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([str(output), 'unavailable'],
                            capture_output=True,
                            text=True)
    (tmp_path / 'sdk-disabled.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    assert 'CPU_FAULT_PASS unavailable' in result.stdout
