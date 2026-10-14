"""Actual native pre-allocation validation for the bounded GCU dynamic ABI.

Run in the formal Enflame Docker. Rejected launches never create a large buffer
or open a device. Valid launches are exercised by the dynamic hardware suite.
"""
import os
import pytest

pytestmark = pytest.mark.skipif(os.environ.get('FLAGPRISM_TEST_ENFLAME') != '1',
                                reason='requires formal Enflame native extension')


@pytest.mark.parametrize('change,runtime_change,message', [
    ({'debug_dynamic_selected_program': None}, {}, 'selected program'),
    ({}, {'grid': None}, 'actual launch grid'),
    ({}, {'grid': ()}, 'one to three'),
    ({}, {'grid': (1, 1, 1, 1)}, 'one to three'),
    ({}, {'grid': (0, 1, 1)}, 'launch grid dimension must be positive and fit uint32_t'),
    ({}, {'grid': (1 << 31, 1, 1)}, 'dimension exceeds INT32_MAX'),
    ({}, {'grid': (65536, 65536, 1)}, 'product exceeds UINT32_MAX'),
    ({'debug_record_capacity': 33554432}, {}, 'buffer exceeds INT32_MAX'),
    ({'debug_dynamic_selected_program': 1 << 31}, {}, 'program exceeds INT32_MAX'),
    ({'debug_record_size': 32}, {}, '64-byte'),
    ({'debug_clock_carrier': 'unknown'}, {}, 'llvm_i64_words'),
])
def test_real_native_rejects_unbounded_dynamic_launch(change, runtime_change, message):
    from flagtree.debugger.native import runtime_binding
    binding = runtime_binding()
    assert binding is not None, 'formal native runtime is required'
    metadata = {
        'name': 'bounded_preallocation_validation',
        'debug_enabled': True, 'debug_backend_name': 'enflame',
        'debug_record_level': 1, 'debug_record_capacity': 1,
        'debug_record_size': 64, 'debug_dynamic_index_bits': 32,
        'debug_clock_carrier': 'llvm_i64_words',
        'debug_dynamic_selected_program': 0,
    }
    runtime = {'record_layout': 'selected_dynamic_timeline_v1', 'grid': (1, 1, 1)}
    metadata.update(change);runtime.update(runtime_change)
    if metadata.get('debug_dynamic_selected_program') is None:
        metadata.pop('debug_dynamic_selected_program', None)
    if runtime.get('grid') is None:
        runtime.pop('grid', None)
    with pytest.raises((ValueError, OverflowError), match=message):
        binding.prepare_launch(metadata, 0, runtime)
