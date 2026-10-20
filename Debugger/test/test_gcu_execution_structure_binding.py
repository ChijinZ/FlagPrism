"""Binding of the typed LLVM index to the exact SDK input and site manifest."""
import hashlib
import json
from unittest.mock import patch

import pytest
from flagtree.debugger import gcu_timeline as bridge


def metadata(text):
    return dict(debug_execution_version=1,
                debug_execution_native_ir_sha256=hashlib.sha256(
                    text.encode()).hexdigest(),
                debug_execution_manifest={
                    'capacity':
                    512,
                    'sites': [{
                        'id': 7,
                        'kind': 5,
                        'operation': 'gcu.border',
                        'location': 'loc(unknown)'
                    }]
                })


def report():
    return dict(schema_version=1,
                status='typed_sdk_llvm_structure_indexed',
                source_region_qualified=False,
                native_schedule_qualified=False,
                entry_block=0,
                blocks=[
                    dict(id=0,
                         arguments=[],
                         argument_types=[],
                         operations=[
                             dict(operation='llvm.return',
                                  operands=[],
                                  results=[],
                                  result_types=[],
                                  successors=[])
                         ])
                ])


def test_structure_binds_exact_input_and_manifest(tmp_path):
    text = 'fixture-final-LLVM'
    state = metadata(text)
    output = json.dumps(report()).encode()
    with patch.object(bridge.tempfile, 'mkdtemp', return_value=str(tmp_path)), \
            patch.object(bridge, '_native_file_stage', return_value=(output, {'state': 'terminal'})) as stage:
        bridge.bind_execution_structure(text, state)
    stage.assert_called_once_with(text.encode(), state,
                                  '--execution-structure', tmp_path)
    bound = state['debug_execution_llvm_structure']
    assert bound['llvm_ir_sha256'] == state['debug_execution_native_ir_sha256']
    assert bound['manifest_sha256'] == hashlib.sha256(
        json.dumps(state['debug_execution_manifest'],
                   sort_keys=True).encode()).hexdigest()
    assert bound['report']['source_region_qualified'] is False
    assert bound['boundary_report']['regions'][0]['status'] == 'unverified'
    assert 'fatbin_sha256' not in bound


def test_different_final_input_rejected_before_native_call():
    state = metadata('original')
    with patch.object(bridge, '_native_file_stage') as child:
        with pytest.raises(ValueError, match='differs'):
            bridge.bind_execution_structure('different', state)
    child.assert_not_called()
    assert 'debug_execution_llvm_structure' not in state


@pytest.mark.parametrize('fault',
                         ['schema_bool', 'source_rights', 'native_rights'])
def test_index_does_not_upgrade_timing_rights(tmp_path, fault):
    row = report()
    if fault == 'schema_bool':
        row['schema_version'] = True
    elif fault == 'source_rights':
        row['source_region_qualified'] = True
    else:
        row['native_schedule_qualified'] = True
    state = metadata('fixture')
    with patch.object(bridge.tempfile, 'mkdtemp', return_value=str(tmp_path)), \
            patch.object(bridge, '_native_file_stage', return_value=(json.dumps(row).encode(), {})):
        with pytest.raises(ValueError, match='Invalid'):
            bridge.bind_execution_structure('fixture', state)
    assert 'debug_execution_llvm_structure' not in state


def test_ordinary_compilation_has_no_structure_child():
    with patch.object(bridge, '_native_file_stage') as child:
        bridge.bind_execution_structure('ordinary', {})
    child.assert_not_called()
