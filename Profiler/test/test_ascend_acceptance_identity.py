"""The acceptance runner cannot promote scope-only or duplicate task views."""
import importlib.util
from pathlib import Path

import pytest


def matcher():
    path = Path(__file__).resolve().parents[2] / 'tests/ascend/acceptance.py'
    spec = importlib.util.spec_from_file_location('ascend_acceptance_identity',
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.matched_native_tasks


def example():
    identity = {
        'invocation_id': 'launch-0',
        'binary_id': 'actual-binary',
        'scope_id': 0
    }
    native = dict(
        identity,
        status='verified_task_identity',
        evidence_kind='retained_worker_token_and_sdk_connection_tables')
    event = {
        'kind': 'kernel',
        'source': 'cann_sdk_task',
        'scope_id': 0,
        'invocation_identity': native
    }
    return event, [{'invocation_identity': identity}]


def test_zero_scope_exact_invocation_is_matched():
    event, samples = example()
    assert matcher()([event], samples, 'actual-binary') == [event]


@pytest.mark.parametrize('field,value',
                         [('binary_id', 'other-binary'),
                          ('invocation_id', 'other-call'),
                          ('status', 'unassociated'), ('scope_id', 9),
                          ('evidence_kind', 'name-or-time-guess')])
def test_identity_mismatch_cannot_reuse_scope(field, value):
    event, samples = example()
    event['invocation_identity'][field] = value
    assert matcher()([event], samples, 'actual-binary') == []


def test_duplicate_native_views_are_not_multiple_measurements():
    event, samples = example()
    assert matcher()([event, event], samples, 'actual-binary') == []


def test_legacy_scope_view_is_not_direct_proof():
    event, samples = example()
    event['source'] = 'aclprof_op_summary'
    assert matcher()([event], samples, 'actual-binary') == []
