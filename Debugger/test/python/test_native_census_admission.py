"""Exercise the installed C++ admission path with the CPU HOST adapter.

No kernel is dispatched. The compiled census layout must control admission even
when a caller supplies a conflicting runtime layout directly to the binding.
"""
import struct

import pytest

from flagtree.debugger import native


def metadata():
    return dict(debug_backend_name='host',
                debug_record_level=1,
                debug_record_capacity=64,
                debug_record_size=64,
                debug_record_layout='gcu_site_census_v1',
                debug_census_version=1,
                debug_records_per_instance=8,
                debug_census_sites=[{} for _ in range(8)],
                debug_max_census_cells=104,
                debug_max_census_bytes=6688)


@pytest.mark.parametrize('layout',
                         ['', 'unknown', 'selected_dynamic_timeline_v1'])
def test_native_compiled_census_cannot_be_downgraded(layout):
    binding = native.runtime_binding()
    assert binding is not None, 'installed native runtime is required'
    runtime = dict(grid=[13, 1, 1],
                   records_per_instance=8,
                   record_layout=layout)
    with pytest.raises(ValueError, match='matching compiler layout'):
        binding.prepare_launch(metadata(), 0, runtime)


def test_native_runtime_census_cannot_upgrade_a_different_compiled_layout():
    binding = native.runtime_binding()
    assert binding is not None
    compiled = metadata()
    compiled['debug_record_layout'] = 'selected_dynamic_timeline_v1'
    with pytest.raises(ValueError, match='matching compiler layout'):
        binding.prepare_launch(
            compiled, 0,
            dict(grid=[13, 1, 1],
                 records_per_instance=8,
                 record_layout='gcu_site_census_v1'))


def test_native_census_matching_layout_uses_actual_grid_capacity():
    binding = native.runtime_binding()
    assert binding is not None
    handle = binding.prepare_launch(
        metadata(), 0,
        dict(grid=[13, 1, 1],
             records_per_instance=8,
             record_layout='gcu_site_census_v1'))
    try:
        result = handle.finish()
        raw = result['raw_buffer']
        assert len(raw) == 32 + 13 * 8 * 64
        assert struct.unpack_from('<I', raw, 4)[0] == 104
    finally:
        handle.release()
