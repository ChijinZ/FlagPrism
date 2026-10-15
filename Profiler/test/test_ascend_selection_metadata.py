"""Finalizer labels require the actual complete compiler selection evidence."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import pytest

p = Path(__file__).parents[2] / 'Debugger/python/flagtree_debugger/api.py'
spec = importlib.util.spec_from_file_location('ascend_selection_actual_api', p)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def fixture():
    original, adapted = 'actual original llvm', 'actual adapted llvm'
    digest = hashlib.sha256(original.encode()).hexdigest()
    adapted_digest = hashlib.sha256(adapted.encode()).hexdigest()
    return {
        'phase':
        'finished',
        'returncode':
        0,
        'compile_id':
        'same-compile',
        'artifacts': [{
            'llir': original,
            'sha256': digest,
            'adapted': {
                'llir': adapted,
                'sha256': adapted_digest
            },
            'metadata': {
                'compile_id':
                'same-compile',
                'module_sha256':
                digest,
                'semantic_selection_stage':
                'compile_time_before_timestamp_and_record',
                'effective_semantics': ['wait_bracket'],
                'dynamic_sites': [{
                    'semantics':
                    'existing_readiness_wait_source_control'
                }]
            },
            'driver_job': {
                'state':
                'finished',
                'exit_code':
                0,
                'compile_id':
                'same-compile',
                'mode':
                'selected_dynamic_trace',
                'inputs': [{
                    'pass_returncode': 0,
                    'adapted_sha256': adapted_digest
                }]
            }
        }]
    }


def test_complete_actual_evidence_describes_compiler_selection_and_legacy_limit(
):
    result = m._ascend_selection_metadata(fixture(), {'wait_bracket'})
    assert result[
        'semantic_selection_stage'] == 'compiler_semantic_site_selection_then_output_filter'
    assert result['effective_semantics'] == ['wait_bracket']
    assert result['selection_stage'] == 'semantic_output_filter_after_capture'
    assert result[
        'program_selection_limit'] == 'counter_reads_may_execute_for_unselected_programs'


@pytest.mark.parametrize('change', [
    'legacy', 'failed', 'wrong_effective', 'duplicate', 'unknown_class',
    'wrong_compile', 'bad_original', 'bad_adapted', 'failed_pass',
    'no_artifacts'
])
def test_incomplete_evidence_does_not_upgrade_old_or_unverified_capture(
        change):
    handoff = copy.deepcopy(fixture())
    a = handoff['artifacts'][0]
    if change == 'legacy': a['metadata'].pop('semantic_selection_stage')
    if change == 'failed': a['driver_job']['exit_code'] = 1
    if change == 'wrong_effective':
        a['metadata']['effective_semantics'] = ['issue']
    if change == 'duplicate':
        a['metadata']['effective_semantics'] = ['wait_bracket', 'wait_bracket']
    if change == 'unknown_class':
        a['metadata']['dynamic_sites'][0]['semantics'] = 'engine_busy'
    if change == 'wrong_compile': a['metadata']['compile_id'] = 'other-compile'
    if change == 'bad_original': a['llir'] += 'changed'
    if change == 'bad_adapted': a['adapted']['llir'] += 'changed'
    if change == 'failed_pass':
        a['driver_job']['inputs'][0]['pass_returncode'] = 1
    if change == 'no_artifacts': handoff['artifacts'] = []
    result = m._ascend_selection_metadata(handoff, {'wait_bracket'})
    assert result[
        'semantic_selection_stage'] == 'semantic_output_filter_after_capture'
    assert 'effective_semantics' not in result


def test_zero_selected_sites_still_has_verified_compiler_selection():
    handoff = fixture()
    handoff['artifacts'][0]['metadata']['dynamic_sites'] = []
    assert m._ascend_selection_metadata(
        handoff, {'wait_bracket'})['effective_semantics'] == ['wait_bracket']
