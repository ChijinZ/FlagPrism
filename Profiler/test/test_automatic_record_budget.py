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


@pytest.mark.parametrize('backend', ['instrumentation', 'enflame'])
def test_interval_backends_keep_their_smaller_budget(backend):
    profile = importlib.import_module('flagtree.profiler.profile')
    request = profile._automatic_observation_request(backend)
    assert request.semantics == ('source_control_interval', )
    assert request.max_events_per_instance == 256
    assert request.automatic and request.sample_every == 1
