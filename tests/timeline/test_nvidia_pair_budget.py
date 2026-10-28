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


@pytest.mark.parametrize('actors,capacity', [(128, 2046), (128, 4096), (1024, 4096)])
def test_explicit_capacity_admits_exact_bounded_geometry(actors, capacity):
    from flagtree.profiler.timeline_nvidia_late_raw import late_raw_byte_budget
    plan = {'capacity_policy': 'explicit-record-count', 'actors': actors,
            'capacity_per_program': capacity}
    assert late_raw_byte_budget(plan) == 2 * actors * (6 + 4 * capacity) * 8


@pytest.mark.parametrize('actors,capacity', [(0, 1022), (1025, 1022), (128, 4097), (True, 1022)])
def test_explicit_raw_geometry_rejects_invalid_manifest(actors, capacity):
    from flagtree.profiler.timeline_nvidia_late_raw import late_raw_byte_budget
    with pytest.raises(ValueError):
        late_raw_byte_budget({'capacity_policy': 'explicit-record-count',
                             'actors': actors, 'capacity_per_program': capacity})


@pytest.mark.parametrize('value', ['16', '32', '64'])
def test_explicit_canonical_document_budget(monkeypatch, value):
    from flagtree.profiler.timeline_events import canonical_document_byte_budget
    monkeypatch.setenv('FLAGTREE_PROFILER_TIMELINE_DOCUMENT_MB', value)
    assert canonical_document_byte_budget() == int(value) * 1024 * 1024


@pytest.mark.parametrize('value', ['0', '65', '-1', 'unbounded'])
def test_canonical_document_budget_stays_bounded(monkeypatch, value):
    from flagtree.profiler.timeline_events import canonical_document_byte_budget
    monkeypatch.setenv('FLAGTREE_PROFILER_TIMELINE_DOCUMENT_MB', value)
    with pytest.raises(ValueError):
        canonical_document_byte_budget()


def test_explicit_capacity_reaches_handle_admission():
    from flagtree.profiler.timeline_nvidia_late_storage import plan_late_storage
    actors, capacity = 128, 4096
    stride = actors * (6 + 4 * capacity) * 8
    plan = dict(schema_version=1, profile_argument_abi=1, record_layout_version=1,
                word_layout='program/logical_word/actor', compact_programs=True,
                actors=actors, capacity_per_program=capacity, header_words=6,
                block_dimensions=[128, 1, 1], dependency_footprint_complete=True,
                segment_words=stride // 8, capacity_policy='explicit-record-count')
    layout = plan_late_storage(plan, grid=(100, 1, 1), scratch_size=stride,
                               alignment=8, num_ctas=1)
    assert layout['raw_bytes'] == 2 * stride
    with pytest.raises(ValueError):
        plan_late_storage(plan, grid=(100, 1, 1), scratch_size=stride,
                          alignment=8, num_ctas=1, max_raw_bytes=8 * 1024 * 1024)
