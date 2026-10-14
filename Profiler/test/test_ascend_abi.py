import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('ascend_abi_test',Path(__file__).parents[1]/'python/flagtree_profiler/ascend_abi.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SOURCE='''func.func @any_symbol(%a: memref<?xi8>, %b: memref<?xi8>, %x: memref<?xf32> {tt.tensor_kind = 0 : i32} loc("X"), %trace: memref<?xi64> loc("Trace"), %n: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, global_kernel = "local"} {
 return
}'''


def test_roles_are_compiler_emitted_and_source_pointer_is_explicit():
    result=m.source_abi(SOURCE,trace_source_argument=1)
    assert [item['role'] for item in result['formals']]==['synchronization_lock','workspace',None,'dynamic_trace',None]
    assert result['formals'][3]['source_argument_index']==1
    assert result['formals'][3]['source_formal_index']==3
    assert len(result['source_sha256'])==64


def test_unsupported_or_multiple_entries_do_not_guess():
    with pytest.raises(ValueError,match='one compiler global entry'):m.source_abi(SOURCE+SOURCE.replace('any_symbol','another'))
    with pytest.raises(ValueError,match='global pointer'):m.source_abi(SOURCE,trace_source_argument=2)


def test_missing_or_overlapping_compiler_roles_cannot_shift_hidden_pointer():
    for changed in [SOURCE.replace('WorkspaceArgIdx = 1 : i64, ',''),SOURCE.replace('WorkspaceArgIdx = 1','WorkspaceArgIdx = 0'),SOURCE.replace('WorkspaceArgIdx = 1','WorkspaceArgIdx = 999')]:
        with pytest.raises(ValueError):m.source_abi(changed,trace_source_argument=1)
