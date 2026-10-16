"""Real MLIR frontend ABI contracts; these are not NPU execution tests."""
import json
import tempfile
from pathlib import Path

import pytest
# The installed Ascend backend imports torch while discovering Triton backends.
# Initialize that public dependency first to avoid a partially initialized Triton.
import torch  # noqa: F401
import torch_npu  # noqa: F401
from triton._C.libtriton import ir
from flagtree.debugger.native import compiler_binding

SOURCE = '''module {
 tt.func public @kernel(%arg: !tt.ptr<f32>, %limit: i32) {
  %zero = arith.constant 0 : i32
  %one = arith.constant 1 : i32
  %value = arith.constant 1.0 : f32
  scf.for %i = %zero to %limit step %one : i32 {
   %old = tt.load %arg : !tt.ptr<f32>
   %new = arith.addf %old, %value : f32
   tt.store %arg, %new : !tt.ptr<f32>
  }
  tt.return
 }
}'''


def prepared_source():
    fd = compiler_binding()
    context = ir.context()
    ir.load_dialects(context)
    fd.load_dialects(context)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'input.mlir'
        path.write_text(SOURCE)
        module = ir.parse_mlir_module(str(path), context)
    assert fd.insert_default_debug_collect_markers(module, 1, 0)
    assert fd.assign_debug_collect_scope_ids_without_erase(module)
    assert fd.assign_debug_op_ids_and_metadata_without_pass_manager(module)
    rows = json.loads(fd.get_debug_tracked_op_table_json(module))
    selected = [
        row['opId'] for row in rows if row['mlirOpName'] == 'arith.addf'
    ]
    assert len(selected) == 1
    return fd, module, selected, context


def test_actual_source_site_marker_and_hidden_formal():
    fd, module, selected, context = prepared_source()
    assert fd.ASCEND_SOURCE_CENSUS_VERSION == 3
    abi = dict(fd.prepare_ascend_source_census_abi(module, selected))
    assert abi == dict(version=3,
                       hidden_argument_index=2,
                       site_count=1,
                       records_per_instance=3,
                       record_size=8,
                       record_layout='ascend_source_census_v3')
    text = str(module)
    assert f'flagprism.source_census_site.v3:{selected[0]}:0:1' in text
    assert text.count('tt.get_program_id') == 3
    assert text.count('tt.get_num_programs') == 3
    assert 'flagtree.debug.record_size = 8' in text
    assert 'flagtree.debug.records_per_instance = 3' in text
    assert 'flagtree_debug.collect' not in text
    body = text.split('tt.func public', 1)[1]
    assert body.index('scf.for') < body.index(
        'flagprism.source_census_site.v3:')
    assert body.index('flagprism.source_census_site.v3:') < body.index(
        'arith.addf')


@pytest.mark.parametrize('selection', [[], [0], [1, 1], [2147483648]])
def test_reject_invalid_selection_without_mutating(selection):
    fd, module, _, context = prepared_source()
    before = str(module)
    with pytest.raises(ValueError):
        fd.prepare_ascend_source_census_abi(module, selection)
    assert str(module) == before


def test_reject_missing_actual_source_id():
    fd, module, selected, context = prepared_source()
    before = str(module)
    with pytest.raises(ValueError, match='unique actual operations'):
        fd.prepare_ascend_source_census_abi(module, [max(selected) + 10000])
    assert str(module) == before
