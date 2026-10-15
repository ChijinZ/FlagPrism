"""Actual compiler region ownership and versioned automatic cache identity."""
import json
from pathlib import Path
import tempfile

import pytest
from triton._C.libtriton import ir
from flagtree.debugger.native import compiler_binding
from flagtree.debugger import compiler

WHILE = '''module {
 tt.func public @region_test(%x: tensor<32xf32>, %steps: i32) -> tensor<32xf32> {
  %zero = arith.constant 0 : i32
  %one = arith.constant 1 : i32
  %out:2 = scf.while (%i = %zero, %v = %x) : (i32, tensor<32xf32>) -> (i32, tensor<32xf32>) {
   %pred = arith.cmpi slt, %i, %steps : i32
   scf.condition(%pred) %i, %v : i32, tensor<32xf32>
  } do {
  ^bb0(%i: i32, %v: tensor<32xf32>):
   %next = arith.addf %v, %x : tensor<32xf32>
   %j = arith.addi %i, %one : i32
   scf.yield %j, %next : i32, tensor<32xf32>
  }
  tt.return %out#1 : tensor<32xf32>
 }
}'''

NESTED = '''module {
 tt.func public @nested_test(%x: tensor<32xf32>, %steps: index, %pred: i1) -> tensor<32xf32> {
  %zero = arith.constant 0 : index
  %one = arith.constant 1 : index
  %out = scf.for %i = %zero to %steps step %one iter_args(%v = %x) -> (tensor<32xf32>) {
   %next = scf.if %pred -> (tensor<32xf32>) {
    %a = arith.addf %v, %x : tensor<32xf32> loc(unknown)
    scf.yield %a : tensor<32xf32>
   } else {
    %b = arith.subf %v, %x : tensor<32xf32> loc(unknown)
    scf.yield %b : tensor<32xf32>
   }
   scf.yield %next : tensor<32xf32>
  }
  tt.return %out : tensor<32xf32>
 }
}'''


def tracked(text):
    fd = compiler_binding()
    assert fd.CONTROL_FLOW_METADATA_VERSION == 1
    context = ir.context()
    ir.load_dialects(context)
    fd.load_dialects(context)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'input.mlir'
        path.write_text(text)
        module = ir.parse_mlir_module(str(path), context)
    assert fd.insert_default_debug_collect_markers(module, 1, 0)
    assert fd.assign_debug_collect_scope_ids_without_erase(module)
    assert fd.assign_debug_op_ids_and_metadata_without_pass_manager(module)
    return json.loads(fd.get_debug_tracked_op_table_json(module))


def test_real_while_header_and_body_have_distinct_actual_region_indices():
    rows = tracked(WHILE)
    header = next(row for row in rows if row['mlirOpName'] == 'arith.cmpi')
    body = next(row for row in rows if row['mlirOpName'] == 'arith.addf')
    owner = next(row for row in rows if row['mlirOpName'] == 'scf.while')
    h, b = header['controlFlowAncestors'][0], body['controlFlowAncestors'][0]
    assert h['controlId'] == b[
        'controlId'] and h['parentOpId'] == b['parentOpId'] == owner['opId']
    assert (h['regionIndex'], b['regionIndex']) == (0, 1)
    assert h['repeated'] and b['repeated']
    assert h['operation'] == b['operation'] == 'scf.while'
    assert all(row['controlFlowSchemaVersion'] == 1 for row in rows)


def test_real_nested_for_and_branch_arm_ancestry_uses_ir_not_source_text():
    rows = tracked(NESTED)
    for operation, arm in [('arith.addf', 0), ('arith.subf', 1)]:
        row = next(item for item in rows if item['mlirOpName'] == operation)
        owners = row['controlFlowAncestors']
        assert [owner['operation']
                for owner in owners] == ['scf.for', 'scf.if']
        assert [owner['regionIndex'] for owner in owners] == [0, arm]
        assert [owner['repeated'] for owner in owners] == [True, False]
        assert row['sourceLoc'] == 'loc(unknown)'


def test_automatic_policy_version_is_in_frozen_compiler_cache_options(
        monkeypatch):
    import flagtree.debugger.api as api
    request = {
        'automatic': True,
        'semantics': ['source_control_interval'],
        'max_sites': 8
    }
    config = {'debug_observation_request': request}
    monkeypatch.setattr(api, 'current_compile_config', lambda: config)
    original = compiler.get_instrumentation_mode()
    compiler.set_instrumentation_mode('debugger_auto')
    try:
        options = {}
        compiler.apply_compile_options(options)
    finally:
        compiler.set_instrumentation_mode(original)
    frozen = json.loads(options['instrumentation_mode'].split('|config=',
                                                              1)[1])
    assert frozen['debug_automatic_plan_version'] == 3
    assert frozen['debug_control_flow_metadata_version'] == 1
    legacy = dict(frozen)
    del legacy['debug_automatic_plan_version']
    del legacy['debug_control_flow_metadata_version']
    assert json.dumps(legacy,
                      sort_keys=True) not in options['instrumentation_mode']


def test_old_compiler_without_structural_metadata_cannot_silently_profile(
        monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(
        compiler, '_get_debug_passes',
        lambda: SimpleNamespace(has_debug_collect_markers=lambda mod: False))
    monkeypatch.setattr(compiler, '_instrumentation_kind',
                        lambda: 'debugger_auto')
    with pytest.raises(RuntimeError,
                       match='matching compiler control-flow metadata'):
        compiler.run_ttir_debug_passes_if_needed(
            None, {'target': {
                'backend': 'gcu'
            }})


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("publisher", ["scalar16", "vector16_per_work_item"])
def test_dynamic_lowering_revision_invalidates_every_dynamic_cache(
        monkeypatch, automatic, publisher):
    import flagtree.debugger.api as api
    monkeypatch.setenv("FLAGPRISM_GCU_DYNAMIC_PUBLISHER", publisher)
    config = {
        "debug_observation_request": {
            "automatic": automatic,
            "semantics": ["source_control_interval"],
            "sample_every": 3
        }
    }
    monkeypatch.setattr(api, "current_compile_config", lambda: config)
    options = {
        "instrumentation_mode": "debugger_auto" if automatic else "debugger"
    }
    compiler.apply_compile_options(options)
    first = options["instrumentation_mode"]
    frozen = json.loads(first.split("|config=", 1)[1])
    assert frozen[
        "debug_dynamic_lowering_revision"] == compiler.GCU_DYNAMIC_LOWERING_REVISION
    assert frozen["debug_dynamic_publication_mode"] == publisher
    assert ("debug_automatic_plan_version" in frozen) is automatic
    monkeypatch.setattr(compiler, "GCU_DYNAMIC_LOWERING_REVISION",
                        compiler.GCU_DYNAMIC_LOWERING_REVISION + 1)
    compiler.apply_compile_options(options)
    assert options["instrumentation_mode"] != first
    assert config == {
        "debug_observation_request": {
            "automatic": automatic,
            "semantics": ["source_control_interval"],
            "sample_every": 3
        }
    }
