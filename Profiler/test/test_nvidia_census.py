"""CPU layout/budget checks for the NVIDIA compiler census adapter."""
import pytest
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "nvidia_census_test_adapter",
    Path(__file__).parents[1] / "python/flagtree_profiler/nvidia_census.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
census_descriptor = adapter.census_descriptor


def fixture():
    metadata = dict(binary_id='actual-binary',
                    compiler_ir_sha256='actual-ir',
                    compiler_metadata=dict(num_ctas=1,
                                           profile_scratch_size=128),
                    scope_id_names=[(0, 'entry'), (1, 'load')],
                    scope_id_origins={
                        '0': dict(automatic=True, census_role='context'),
                        '1': dict(automatic=True, census_role='primary')
                    })
    return metadata, dict(grid=[4, 3, 1], invocation_id='actual-launch'), dict(
        max_census_cells=1048576, max_census_bytes=8388608)


def test_layout_preserves_grid_roles_and_padding():
    m, launch, selection = fixture()
    d = census_descriptor(m, launch, 12 * 128, selection)
    assert d['program_count'] == 12
    assert d['program_stride'] == 128 and d['site_stride'] == 8
    assert [s['role'] for s in d['sites']] == ['context', 'primary']
    assert d['binary_id'] == m['binary_id']
    assert d['invocation_id'] == launch['invocation_id']
    assert d['actors'][0]['mask_activity'] == 'unobserved'


@pytest.mark.parametrize('change,error', [('cells', 'cell budget'),
                                          ('bytes', 'byte budget'),
                                          ('allocation', 'actual allocation'),
                                          ('scratch', 'scratch layout'),
                                          ('role', 'role/source'),
                                          ('cluster', 'num_ctas'),
                                          ('grid', 'launch geometry')])
def test_rejects_unrepresentable_or_unbounded_capture(change, error):
    m, launch, selection = fixture()
    allocation = 12 * 128
    if change == 'cells':
        selection['max_census_cells'] = 23
    if change == 'bytes':
        selection['max_census_bytes'] = allocation - 1
    if change == 'allocation':
        allocation += 128
    if change == 'scratch':
        m['compiler_metadata']['profile_scratch_size'] = 256
    if change == 'role':
        del m['scope_id_origins']['1']['census_role']
    if change == 'cluster':
        m['compiler_metadata']['num_ctas'] = 2
    if change == 'grid':
        launch['grid'] = None
    with pytest.raises(RuntimeError, match=error):
        census_descriptor(m, launch, allocation, selection)


def test_all_grid_plan_retains_explicit_budgets_and_rejects_fixed_programs():
    spec = importlib.util.spec_from_file_location(
        'nvidia_census_request_test',
        Path(__file__).parents[1] /
        'python/flagtree_profiler/observations_nvidia.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    request = dict(program_policy='all_grid_census',
                   programs=None,
                   semantics=['counter'],
                   automatic=True,
                   max_sites=8,
                   sample_every=1,
                   sites=None,
                   max_census_cells=112,
                   max_census_bytes=4096)
    lowered = module.lower_request(request)
    assert lowered['census']
    assert lowered['collection_scope']['programs'] == 'all_launched_CTAs'
    assert lowered['output_selection']['max_census_cells'] == 112
    assert lowered['output_selection']['max_census_bytes'] == 4096
    for value in ([0], [7]):
        with pytest.raises(ValueError, match='programs=None'):
            module.lower_request(dict(request, programs=value))
    with pytest.raises(ValueError, match='automatic sites'):
        module.lower_request(dict(request, automatic=1))


def test_partition_observer_is_typed_and_included_in_cell_budget():
    m, launch, selection = fixture()
    m['scope_id_origins']['1'].update(census_actor=1,
                                      census_observer_threads=64,
                                      census_partition_region=0)
    descriptor = census_descriptor(m, launch, 12 * 128, selection)
    assert descriptor['actors'][0]['kind'] == 'logical_warp'
    worker = descriptor['actors'][1]
    assert worker['kind'] == 'logical_program_observer'
    assert worker['id'] == 1 and worker['partition_threads'] == 64
    assert worker['writer'] == 'physical_thread_id_mod_partition_threads_zero'
    assert descriptor['actor_stride'] == 16
    with pytest.raises(RuntimeError, match='cell budget'):
        census_descriptor(m, launch, 12 * 128,
                          dict(selection, max_census_cells=47))


def test_partition_requires_actual_geometry_and_dense_identity():
    m, launch, selection = fixture()
    origin = m['scope_id_origins']['1']
    origin.update(census_actor=1, census_observer_threads=0)
    with pytest.raises(RuntimeError,
                       match='partition observer lacks compiler geometry'):
        census_descriptor(m, launch, 12 * 128, selection)
    origin.update(census_actor=3,
                  census_observer_threads=32,
                  census_partition_region=0)
    with pytest.raises(RuntimeError, match='not dense'):
        census_descriptor(m, launch, 12 * 128, selection)
