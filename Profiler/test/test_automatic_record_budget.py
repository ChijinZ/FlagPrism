"""The default policy follows backend record granularity, not workload IDs."""
import importlib

import pytest


@pytest.mark.parametrize('backend', [
    'instrumentation', 'cupti', 'cuda', 'nvidia', 'enflame', 'gcu', 'tops',
    'cann', 'ascend', 'npu'
])
def test_census_default_covers_all_admitted_programs_with_two_allocation_budgets(
        backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    request = profile._automatic_observation_request(backend)
    assert request.semantics == ('counter', )
    assert request.programs is None and request.program_policy == 'all_grid_census'
    assert request.max_census_cells == 1048576
    assert request.max_census_bytes == 8388608
    assert request.automatic and request.sample_every == 1


@pytest.mark.parametrize('backend', ['cann', 'ascend', 'npu'])
def test_census_default_does_not_request_vendor_activity_or_fallback(backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    mode = profile._automatic_mode(backend).split(':')
    assert mode[0] == 'runtime_base'
    options = dict(token.split('=', 1) for token in mode[1:])
    assert options == {
        'aclprof_runtime_enabled': 'false',
        'aclprof_auto_export': 'false',
        'mstx_enabled': 'false',
        'aclprof_msproftx_enabled': 'false',
        'runtime_host_timing_fallback': 'false',
    }


@pytest.mark.parametrize('backend', ['instrumentation', 'enflame'])
def test_other_census_backends_keep_their_native_mode_defaults(backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    assert profile._automatic_mode(backend) is None


@pytest.mark.parametrize('backend', ['cann', 'ascend', 'npu'])
def test_census_mode_preserves_the_actual_runtime_device(backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    assert profile._automatic_mode(backend, device=4).endswith(':device_id=4')
    assert profile._automatic_mode(backend, device=0).endswith(':device_id=0')
    for invalid in (True, -1, '4'):
        with pytest.raises(ValueError, match='runtime device'):
            profile._automatic_mode(backend, device=invalid)
