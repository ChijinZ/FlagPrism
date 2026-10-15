"""Cold package import order follows the actual installed compiler marker."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import pytest

SOURCE = Path(__file__).parents[1] / 'python/flagtree_profiler'


@pytest.mark.parametrize('selection', ['installed_marker', 'explicit_environment'])
def test_cold_initializer_loads_runtime_before_triton(tmp_path, selection):
    package = tmp_path / 'flagtree/profiler'
    package.mkdir(parents=True)
    (package.parent / '__init__.py').write_text('')
    (package.parent / '_flagprism.py').write_text('def register_component(*a): pass\n')
    # Execute the real initializer prefix, including its imports, in a separate
    # interpreter. Remaining API modules are irrelevant to import-order proof.
    prefix = (SOURCE / '__init__.py').read_text().split('from .scope', 1)[0]
    (package / '__init__.py').write_text(prefix)
    (package / '_bootstrap.py').write_bytes((SOURCE / '_bootstrap.py').read_bytes())
    trace = tmp_path / 'order.txt'
    append = f'open({str(trace)!r}, "a").write'
    (tmp_path / 'torch.py').write_text(append + '("torch\\n")\n')
    (tmp_path / 'torch_npu.py').write_text('import sys\nassert "torch" in sys.modules\n' + append + '("torch_npu\\n")\n')
    triton = tmp_path / 'triton'
    triton.mkdir()
    (triton / '__init__.py').write_text('import sys\nassert "torch_npu" in sys.modules\n' + append + '("triton\\n")\n__version__="test"\n')
    env = dict(os.environ)
    env.pop('FLAGTREE_BACKEND', None)
    if selection == 'installed_marker':
        (triton / 'FLAGTREE_BACKEND').write_text('ascend')
    else:
        env['FLAGTREE_BACKEND'] = 'ascend'
    process = subprocess.run([sys.executable, '-I', '-c',
                              f'import sys; sys.path.insert(0,{str(tmp_path)!r}); import flagtree.profiler'],
                             env=env, capture_output=True, text=True, timeout=20)
    assert process.returncode == 0, process.stderr
    assert trace.read_text().splitlines() == ['torch', 'torch_npu', 'triton']


def test_missing_runtime_import_is_not_silently_ignored(monkeypatch):
    spec = importlib.util.spec_from_file_location('ascend_bootstrap_actual', SOURCE / '_bootstrap.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delitem(sys.modules, 'triton', raising=False)
    monkeypatch.setenv('FLAGTREE_BACKEND', 'ascend')
    def missing(name):
        raise ImportError('runtime dependency missing: ' + name)
    monkeypatch.setattr(module.importlib, 'import_module', missing)
    with pytest.raises(ImportError, match='runtime dependency missing'):
        module.prepare_runtime_imports()


def test_actual_vendor_parent_patch_bootstraps_before_version_import(tmp_path):
    vendor = tmp_path / 'python/flagtree'
    vendor.mkdir(parents=True)
    (vendor / '__init__.py').write_text('"""FlagPrism debugger and profiler components bundled with FlagTree."""\n\nfrom triton import __version__\n\n__all__ = ["__version__"]\n')
    patch = SOURCE.parents[2] / 'integration/patches/ascend/automatic-import-order.patch'
    applied = subprocess.run(['git', 'apply', str(patch)], cwd=tmp_path,
                             capture_output=True, text=True, timeout=10)
    assert applied.returncode == 0, applied.stderr
    trace = tmp_path / 'order.txt'
    append = f'open({str(trace)!r}, "a").write'
    (tmp_path / 'python/torch.py').write_text(append + '("torch\\n")\n')
    (tmp_path / 'python/torch_npu.py').write_text('import sys\nassert "torch" in sys.modules\n' + append + '("torch_npu\\n")\n')
    triton = tmp_path / 'python/triton'
    triton.mkdir()
    (triton / 'FLAGTREE_BACKEND').write_text('ascend')
    (triton / '__init__.py').write_text('import sys\nassert "torch_npu" in sys.modules\n' + append + '("triton\\n")\n__version__="test"\n')
    env = dict(os.environ)
    env.pop('FLAGTREE_BACKEND', None)
    process = subprocess.run([sys.executable, '-I', '-c',
                              f'import sys; sys.path.insert(0,{str(tmp_path / "python")!r}); import flagtree'],
                             env=env, capture_output=True, text=True, timeout=20)
    assert process.returncode == 0, process.stderr
    assert trace.read_text().splitlines() == ['torch', 'torch_npu', 'triton']
