"""The default policy follows backend record granularity, not workload IDs."""
import importlib

import pytest


@pytest.mark.parametrize('backend', ['cann', 'ascend', 'npu'])
def test_late_checkpoint_budget_is_bounded_and_keeps_every_occurrence(backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    request = profile._automatic_observation_request(backend)
    assert request.semantics == ('operation_checkpoint', 'control_checkpoint')
    assert request.max_events_per_instance == 4096
    assert request.programs == (0, ) and request.sites is None
    assert request.automatic and request.sample_every == 1
    assert 3 * (32 + request.max_events_per_instance * 64) < 2 * 1024**2


@pytest.mark.parametrize(
    'backend',
    ['instrumentation', 'cupti', 'cuda', 'nvidia', 'enflame', 'gcu', 'tops'])
def test_census_default_covers_all_admitted_programs_with_two_allocation_budgets(
        backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    request = profile._automatic_observation_request(backend)
    assert request.semantics == ('counter', )
    assert request.programs is None and request.program_policy == 'all_grid_census'
    assert request.max_census_cells == 1048576
    assert request.max_census_bytes == 8388608
    assert request.automatic and request.sample_every == 1
