"""CPU ABI resource contracts; execute in the backend Docker environment."""
import importlib.util
from pathlib import Path

import pytest


def module_at(path):
    spec = importlib.util.spec_from_file_location('ascend_launch_resource',
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_header_is_authoritative():
    root = Path(__file__).resolve().parents[1]
    module = module_at(root / 'python/flagtree_profiler/ascend_launch.py')
    header = root / 'csrc/include/Profiler/Vendor/CannLaunchReceipt.h'
    assert module.get_launch_receipt_abi() == header.read_text()


def test_installed_resource_is_used_without_source(tmp_path):
    original = Path(__file__).resolve(
    ).parents[1] / 'python/flagtree_profiler/ascend_launch.py'
    package = tmp_path / 'flagtree/profiler'
    package.mkdir(parents=True)
    script = package / 'ascend_launch.py'
    script.write_text(original.read_text())
    expected = 'struct CannLaunchWorkerRecordV1 {};\nstruct CannLaunchReceiptSinkV1 {};\n'
    (package / '_cann_launch_receipt.h').write_text(expected)
    assert module_at(script).get_launch_receipt_abi() == expected


def test_missing_installed_resource_fails_explicitly(tmp_path):
    original = Path(__file__).resolve(
    ).parents[1] / 'python/flagtree_profiler/ascend_launch.py'
    script = tmp_path / 'site-packages/flagtree/profiler/ascend_launch.py'
    script.parent.mkdir(parents=True)
    script.write_text(original.read_text())
    with pytest.raises(RuntimeError, match='header missing'):
        module_at(script).get_launch_receipt_abi()
