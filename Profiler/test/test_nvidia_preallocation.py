"""CPU checks of the real CUDA launcher and allocator admission ordering.

A source-stage driver may be selected explicitly while developing a compiler
patch. The tests never initialize CUDA, allocate device memory or launch work.
"""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def components(monkeypatch):
    import triton.backends.nvidia.driver as installed_driver
    driver_path = os.environ.get('FLAGPRISM_TEST_NVIDIA_DRIVER',
                                 installed_driver.__file__)
    driver = load_module('triton.backends.nvidia._admission_test_driver',
                         driver_path)
    source = Path(__file__).parents[
        1] / 'python/flagtree_profiler/hooks/instrumentation.py'
    hooks = load_module('flagtree.profiler.hooks._admission_test_hook', source)
    return driver, hooks


def launcher_fixture(components,
                     monkeypatch,
                     *,
                     cells=24,
                     byte_budget=1536,
                     scratch_size=128,
                     census=True):
    driver, hooks = components
    metadata = dict(compiler_metadata=dict(num_ctas=1,
                                           profile_scratch_size=128),
                    scope_id_names=[(0, 'context'), (1, 'body')],
                    scope_id_origins={
                        '0': dict(automatic=True, census_role='context'),
                        '1': dict(automatic=True, census_role='primary')
                    })
    hook = SimpleNamespace(census=census,
                           observation_metadata={37: metadata},
                           profile_buffer_alignment=128,
                           profile_buffer_size=0,
                           observation_plan={
                               'output_selection': {
                                   'max_census_cells': cells,
                                   'max_census_bytes': byte_budget
                               }
                           })
    allocator = hooks.CudaAllocator(hook)
    calls = []

    class TrackingAllocator:
        validate_launch = allocator.validate_launch

        def __call__(self, *args):
            calls.append('profile_allocation')
            return None

    def global_allocator(*args):
        calls.append('global_allocation')
        return None

    monkeypatch.setattr(driver._allocation, '_allocator',
                        SimpleNamespace(get=lambda: global_allocator))
    monkeypatch.setattr(driver._allocation, '_profile_allocator',
                        SimpleNamespace(get=lambda: TrackingAllocator()))
    launcher = driver.CudaLauncher.__new__(driver.CudaLauncher)
    launcher.global_scratch_size = 64
    launcher.global_scratch_align = 128
    launcher.profile_scratch_size = scratch_size
    launcher.profile_scratch_align = 128
    launcher.num_ctas = 1
    launcher.metadata = SimpleNamespace(debug_enabled=False)
    launcher.launch_cooperative_grid = False
    launcher.launch_pdl = False
    launcher.launch = lambda *args: calls.append('launch')
    return launcher, hook, calls


@pytest.mark.parametrize('kwargs, reason', [
    ({
        'cells': 23
    }, 'cell budget'),
    ({
        'byte_budget': 1535
    }, 'byte budget'),
    ({
        'scratch_size': 256
    }, 'scratch ABI'),
])
def test_budget_or_abi_failure_precedes_both_allocators(
        components, monkeypatch, kwargs, reason):
    launcher, hook, calls = launcher_fixture(components, monkeypatch, **kwargs)
    with pytest.raises(RuntimeError, match=reason):
        launcher(4, 3, 1, 0, 37)
    assert calls == []


def test_valid_launch_keeps_normal_allocation_and_launch_order(
        components, monkeypatch):
    launcher, hook, calls = launcher_fixture(components, monkeypatch)
    launcher(4, 3, 1, 0, 37)
    assert calls == ['global_allocation', 'profile_allocation', 'launch']


def test_missing_function_identity_cannot_allocate(components, monkeypatch):
    launcher, hook, calls = launcher_fixture(components, monkeypatch)
    with pytest.raises(RuntimeError, match='actual function metadata'):
        launcher(4, 3, 1, 0, 38)
    assert calls == []


def test_non_census_allocator_retains_legacy_behavior(components, monkeypatch):
    launcher, hook, calls = launcher_fixture(components,
                                             monkeypatch,
                                             census=False)
    launcher(4, 3, 1, 0, 38)
    assert calls == ['global_allocation', 'profile_allocation', 'launch']


@pytest.mark.parametrize('size, alignment', [(1536, 128), (512, 128)])
def test_old_launcher_cannot_bypass_admission(components, size, alignment):
    _, hooks = components
    allocator = hooks.CudaAllocator(SimpleNamespace(census=True))
    # Rejection happens before importing Torch or consulting a CUDA stream.
    with pytest.raises(RuntimeError,
                       match='requires compiler/launch preflight'):
        allocator(size, alignment, None)


@pytest.mark.parametrize('wrong_size', [None, 512])
def test_admission_is_exact_and_single_use(components, monkeypatch,
                                           wrong_size):
    import contextlib
    import sys
    _, hooks = components
    hook = SimpleNamespace(census=True,
                           profile_buffer_alignment=128,
                           profile_buffer_size=0,
                           observation_metadata={
                               37:
                               dict(compiler_metadata=dict(
                                   num_ctas=1, profile_scratch_size=128),
                                    scope_id_names=[(0, 'body')],
                                    scope_id_origins={
                                        '0':
                                        dict(automatic=True,
                                             census_role='primary')
                                    })
                           },
                           observation_plan={
                               'output_selection': {
                                   'max_census_cells': 1,
                                   'max_census_bytes': 128
                               }
                           })
    allocator = hooks.CudaAllocator(hook)
    calls = []
    buffer = SimpleNamespace(zero_=lambda: calls.append('zero'))

    def empty(*args, **kwargs):
        calls.append('allocate')
        return buffer

    # Explicit CPU Torch boundary: verify the admission lifecycle without CUDA.
    torch = SimpleNamespace(
        empty=empty,
        uint8='fixture-uint8',
        cuda=SimpleNamespace(ExternalStream=lambda stream: stream,
                             stream=lambda stream: contextlib.nullcontext()))
    monkeypatch.setitem(sys.modules, 'torch', torch)
    allocator.validate_launch(function=37,
                              grid=(1, 1, 1),
                              scratch_size=128,
                              alignment=128,
                              num_ctas=1)
    if wrong_size is not None:
        with pytest.raises(RuntimeError,
                           match='requires compiler/launch preflight'):
            allocator(wrong_size, 128, 0)
        assert calls == []
        allocator.validate_launch(function=37,
                                  grid=(1, 1, 1),
                                  scratch_size=128,
                                  alignment=128,
                                  num_ctas=1)
    assert allocator(128, 128, 0) is buffer
    assert calls == ['allocate', 'zero']
    with pytest.raises(RuntimeError,
                       match='requires compiler/launch preflight'):
        allocator(128, 128, 0)
    assert calls == ['allocate', 'zero']
