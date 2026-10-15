"""Acceptance coverage contracts; CPU validation runs only in a backend Docker."""
import importlib.util
from pathlib import Path

import pytest


def runner():
    path = Path(__file__).resolve().parents[2] / 'tests/ascend/acceptance.py'
    spec = importlib.util.spec_from_file_location('ascend_acceptance_plans',
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def coverage(plans):
    return {(tuple(p['shape']), p['variant'], p['mode']) for p in plans}


def test_heldout_requires_all_shapes_configs_and_modes():
    module = runner()
    plans = module.build_plans('heldout', 4)
    assert len(plans) == 18
    assert {p['operator'] for p in plans} == {'rmsnorm'}
    assert coverage(plans) == {(shape, variant, mode)
                               for shape in [(32, 256), (256, 1024), (127,
                                                                      769)]
                               for variant in (0, 1)
                               for mode in ('off', 'native', 'detailed')}
    assert all(p['samples'] == p['warmup'] == 3 and p['batch'] == 0
               for p in plans)


def test_fixed_t5_does_not_masquerade_as_heldout_generalization():
    plans = runner().build_plans('t5', 4)
    assert len(plans) == 9
    assert {tuple(p['shape']) for p in plans} == {(127, 769)}
    assert {p['variant'] for p in plans} == {0}
    assert {p['batch'] for p in plans} == {0, 1, 2}
    assert all(p['samples'] == 30 for p in plans)


def test_original_six_operator_contract_remains_108_requests():
    plans = runner().build_plans('operators', 4)
    assert len(plans) == 108
    operators = {p['operator'] for p in plans}
    assert operators == {
        'gemm', 'gemm_bias_gelu', 'softmax', 'layernorm', 'reduce_sum',
        'transpose'
    }
    assert all(
        sum(p['operator'] == op for p in plans) == 18 for op in operators)
    assert len({(p['operator'], *tuple(p['shape']), p['variant'], p['mode'])
                for p in plans}) == 108


def test_longk_uses_explicit_original_kernel_config_without_changing_defaults(
):
    module = runner()
    default = module.resolve_matmul_config({'variant': 0})
    requested = {
        'BM': 64,
        'BN': 64,
        'BK': 256,
        'num_stages': 4,
        'num_warps': 4
    }
    assert module.resolve_matmul_config({
        'variant': 0,
        'config': requested
    }) == requested
    assert requested == {
        'BM': 64,
        'BN': 64,
        'BK': 256,
        'num_stages': 4,
        'num_warps': 4
    }
    assert default == {
        'BM': 16,
        'BN': 16,
        'BK': 16,
        'num_stages': 1,
        'num_warps': 4
    }
    assert module.resolve_matmul_config({'variant': 1}) == {
        'BM': 32,
        'BN': 16,
        'BK': 16,
        'num_stages': 2,
        'num_warps': 4
    }


@pytest.mark.parametrize(
    'config', [None, {
        'unknown': 32
    }, {
        'BK': 0
    }, {
        'BM': True
    }, {
        'BN': 48
    }])
def test_invalid_config_cannot_silently_change_the_requested_case(config):
    with pytest.raises(ValueError, match='matmul'):
        runner().resolve_matmul_config({'variant': 0, 'config': config})
