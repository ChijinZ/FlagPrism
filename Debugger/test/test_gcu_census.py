"""Unit protocol negatives; hardware tests separately establish real bytes."""
import struct
import pytest
from flagtree.debugger.gcu_census import validate_transport, compiler_sites
from flagtree.debugger.automatic_plan import plan_operations


def transport(count=0, flags=0):
    return struct.pack('<8I', 0, 1, 0, 0, 64, 96, 0, 0) + struct.pack(
        '<2I', count, flags) + bytes(56)


@pytest.mark.parametrize('count,flags', [(0, 0), (1, 1), (0xffffffff, 1),
                                         (0xffffffff, 3)])
def test_transport_valid_cells(count, flags):
    assert validate_transport(transport(count, flags), programs=1,
                              sites=1)['capacity'] == 1


@pytest.mark.parametrize('count,flags', [(0, 1), (1, 0), (1, 3), (1, 5),
                                         (0, 2)])
def test_transport_rejects_contradictions(count, flags):
    with pytest.raises(ValueError):
        validate_transport(transport(count, flags), programs=1, sites=1)


def test_transport_rejects_header_padding_and_shape():
    for raw in [
            transport()[:-1],
            bytes(4) + transport()[4:8] + struct.pack('<I', 1) +
            transport()[12:],
            transport()[:-1] + b'\1'
    ]:
        with pytest.raises(ValueError):
            validate_transport(raw, programs=1, sites=1)
    with pytest.raises(ValueError):
        validate_transport(transport(), programs=2, sites=1)


def test_census_reserves_real_body_pair_and_keeps_context_separate():
    region = {
        'controlId': 90,
        'regionIndex': 0,
        'blockIndex': 0,
        'repeated': True
    }

    def row(identity, op, line, *, body=False, condition=False):
        return {
            'opId': identity,
            'mlirOpName': op,
            'sourceLoc': f'loc("fixture.py":{line}:1)',
            'result': {
                'valueKind': 'scalar' if not body else 'tensor',
                'elementDtype': 'f32'
            },
            'controlFlowAncestors': [region] if body else [],
            'isKernelEntryContext': not body,
            'isControlConditionComputation': condition
        }

    table = [
        row(1, 'tt.get_program_id', 1),
        row(2, 'tt.load', 2, condition=True),
        row(3, 'tt.load', 3, body=True),
        row(4, 'arith.addf', 4, body=True)
    ]
    plan = plan_operations(table, 4, census=True)
    assert plan['selected_sites'][:2] == [3, 4]
    roles = {s['site']: s['role'] for s in compiler_sites(plan)}
    assert roles[3] == roles[4] == 'primary'
    assert roles[1] == roles[2] == 'context'


def test_census_cache_identity_uses_actual_vector_publisher(monkeypatch):
    from flagtree.debugger.compiler import _gcu_publication_config
    monkeypatch.setenv('FLAGPRISM_GCU_DYNAMIC_PUBLISHER', 'scalar16')
    config = _gcu_publication_config({
        'debug_observation_request': {
            'program_policy': 'all_grid_census',
            'semantics': ['counter'],
            'automatic': True
        }
    })
    assert config['debug_dynamic_publication_mode'] == 'vector16_per_work_item'
    assert config['debug_census_version'] == 1


@pytest.mark.parametrize('layout,supplied,accepted,expected', [
    ('gcu_site_census_v1', [1, 1, 1], False, None),
    ('gcu_site_census_v1', [13], True, (13, 1, 1)),
    ('gcu_site_census_v1', [13, 1, 1], True, (13, 1, 1)),
    ('selected_dynamic_timeline_v1', [1, 1, 1], True, [1, 1, 1]),
])
def test_census_grid_is_bound_to_actual_launch_only(monkeypatch, layout,
                                                    supplied, accepted,
                                                    expected):
    from types import SimpleNamespace
    from flagtree.debugger import api, graph_guard

    class Prepared(Exception):
        pass

    def prepare(metadata, stream, runtime):
        assert accepted and runtime['grid'] == expected
        raise Prepared()

    monkeypatch.setattr(graph_guard, 'require_eager',
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(api, '_build_launch_metadata_dict',
                        lambda metadata: metadata)
    monkeypatch.setattr(api, '_infer_runtime_metadata', lambda *args: {})
    monkeypatch.setattr(api, '_propagate_observation_clock',
                        lambda *args: None)
    monkeypatch.setattr(api, '_load_binding',
                        lambda: SimpleNamespace(prepare_launch=prepare))
    monkeypatch.setattr(
        api, '_active_config',
        api.DebuggerConfig(
            runtime_metadata_builder=lambda *args: {'grid': supplied}))
    metadata = {'debug_record_layout': layout, 'debug_records_per_instance': 8}
    with pytest.raises(Prepared if accepted else ValueError):
        api._default_launch_prepare_hook(metadata, 0, {'grid': [13, 1, 1]}, ())
