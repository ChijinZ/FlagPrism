"""Exercise real JIT cache lookup with CPU compiler/driver boundaries.

These checks do not compile or launch a device kernel. They complement the
same-process, shared-disk-cache hardware regression.
"""
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


def load(name, path, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def cache_placeholder(x):
    return x


@pytest.fixture
def jit_cache(monkeypatch):
    import torch  # noqa: F401
    import torch_npu
    import triton.runtime.jit
    import triton.backends.ascend.compiler
    parent = os.environ.get('FLAGPRISM_TEST_ASCEND_PARENT')
    if parent:
        parent = Path(parent)
        jit_path = parent / 'python/triton/runtime/jit.py'
        backend_path = parent / 'third_party/ascend/backend/compiler.py'
    else:
        jit_path = Path(triton.runtime.jit.__file__)
        backend_path = Path(triton.backends.ascend.compiler.__file__)
    jit = load('triton.runtime._cache_normalization_test', jit_path,
               monkeypatch)
    module = load('triton.backends.ascend._cache_normalization_test',
                  backend_path, monkeypatch)
    backend = module.AscendBackend(module.GPUTarget('npu', 'Ascend910B', 0))
    monkeypatch.setattr(
        jit, 'driver',
        SimpleNamespace(
            active=SimpleNamespace(get_current_device=lambda: 0,
                                   get_current_stream=lambda device: 0)))
    fn = jit.JITFunction(cache_placeholder)
    fn.used_global_vals = {}
    cache, keys, compilations = {}, {}, []

    def binder(*args, **kwargs):
        return {'x': args[0]}, [('i32', None)], dict(kwargs)

    fn.device_caches[0] = (cache, keys, backend.target, backend, binder)

    def compile_fixture(key, signature, device, constexprs, options, attrs,
                        warmup):
        assert warmup is True
        compiled = SimpleNamespace(metadata=options, hash=options.hash())
        cache[key] = compiled
        compilations.append(compiled)
        return compiled

    monkeypatch.setattr(fn, '_do_compile', compile_fixture)
    assert not torch_npu.npu.is_initialized()
    return fn, compilations, torch_npu


def test_effective_option_precedes_in_memory_cache_lookup(
        jit_cache, monkeypatch):
    fn, compilations, torch_npu = jit_cache
    results = []
    for value in ('false', 'true', 'false'):
        monkeypatch.setenv('TRITON_ALL_BLOCKS_PARALLEL', value)
        results.append(fn.run(7, grid=(1, ), warmup=True))
    assert [k.metadata.enable_auto_blockify
            for k in results] == [False, True, False]
    assert len(compilations) == 2
    assert results[0] is results[2] and results[0].hash != results[1].hash
    assert not torch_npu.npu.is_initialized()


@pytest.mark.parametrize('explicit', [False, True])
def test_explicit_option_is_stable_across_environment_changes(
        jit_cache, monkeypatch, explicit):
    fn, compilations, torch_npu = jit_cache
    results = []
    for value in ('false', 'true', 'false'):
        monkeypatch.setenv('TRITON_ALL_BLOCKS_PARALLEL', value)
        results.append(
            fn.run(7, grid=(1, ), warmup=True, enable_auto_blockify=explicit))
    assert len(compilations) == 1 and all(k is results[0] for k in results)
    assert results[0].metadata.enable_auto_blockify is explicit
    assert not torch_npu.npu.is_initialized()
