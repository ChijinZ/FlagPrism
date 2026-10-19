"""Default full-CTA physical accounting must compose across invocations."""
import pytest

from flagtree.profiler.timeline_nvidia_late_compile import _automatic_pair_budget


@pytest.mark.parametrize('actors,capacity,physical_ceiling', [
    (32, 1022, 2 * 1024 * 1024),
    (64, 510, 2 * 1024 * 1024),
    (128, 510, 4 * 1024 * 1024),
    (256, 510, 8 * 1024 * 1024),
])
def test_header_and_guards_stay_inside_full_cta_physical_allowance(
        actors, capacity, physical_ceiling):
    budget = _automatic_pair_budget(actors, True)
    assert budget + 128 == physical_ceiling
    assert min(4096, (budget // (2 * actors * 8) - 6) // 4) == capacity
    actual = 2 * actors * (6 + 4 * capacity) * 8 + 128
    assert actual <= physical_ceiling
    if actors == 128:
        # The actual two-call failure had 512 records: header spill alone
        # consumed the unchanged session limit before the second launch.
        assert 2 * actual <= 8 * 1024 * 1024
        assert 2 * (2 * actors * (6 + 4 * 512) * 8 + 128) > 8 * 1024 * 1024


@pytest.mark.parametrize('actors', [1, 2, 4])
def test_sampled_capacity_and_explicit_budget_scope_are_unchanged(actors):
    budget = _automatic_pair_budget(actors, False)
    assert budget == 2 * actors * (6 + 4 * 4096) * 8
    assert (budget // (2 * actors * 8) - 6) // 4 == 4096
