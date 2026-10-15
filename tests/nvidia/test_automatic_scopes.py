"""Compiler tests for generic automatic scope insertion (no GPU launches)."""
import triton._C.libtriton as core
from flagtree.profiler.native import compiler_binding


def parse(text):
    context = core.ir.context()
    core.ir.load_dialects(context)
    compiler_binding().load_dialects(context)
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.mlir"
        path.write_text(text)
        module = core.ir.parse_mlir_module(str(path), context)
    module.context = context
    return module


def instrument(module, budget=8):
    pm = core.ir.pass_manager(module.context)
    compiler_binding().add_automatic_proton_scopes(pm, budget)
    pm.run(module, 'automatic-scope-test')
    return module


PROGRAM = '''module {
  tt.func public @unannotated(%input: tensor<32xf32>) -> tensor<32xf32> {
    %c = arith.constant dense<0.5> : tensor<32xf32>
    %a = arith.mulf %input, %c : tensor<32xf32> loc("development.py":8:10)
    %b = arith.addf %a, %input : tensor<32xf32> loc("development.py":9:10)
    %d = arith.subf %b, %input : tensor<32xf32> loc("development.py":10:10)
    tt.return %d : tensor<32xf32>
  }
}'''


def test_actual_operation_records_locations_budget_and_idempotence():
    module = instrument(parse(PROGRAM), 2)
    binding = compiler_binding()
    names = dict(binding.get_scope_id_names(module))
    assert len(names) == 2
    origins = binding.get_scope_id_origins(module)
    assert {origin['operation']
            for origin in origins.values()} == {'arith.mulf', 'arith.subf'}
    assert {origin['entry'][0]['line']
            for origin in origins.values()} == {8, 10}
    assert all(origin['entry'] == origin['exit'] and origin['automatic']
               for origin in origins.values())
    plan = binding.get_automatic_proton_plan(module)
    assert plan == {
        'proton.automatic_candidates': 3,
        'proton.automatic_selected': 2
    }
    instrument(module, 8)
    assert binding.get_scope_id_names(module) == list(names.items())


def test_manual_scope_compatibility():
    text = PROGRAM.replace(
        '%a = arith.mulf', 'proton.record start "manual"\n    %a = arith.mulf')
    text = text.replace('tt.return %d',
                        'proton.record end "manual"\n    tt.return %d')
    module = instrument(parse(text))
    assert dict(compiler_binding().get_scope_id_names(module)) == {0: 'manual'}
    assert not compiler_binding().get_automatic_proton_plan(module)


def test_compile_time_site_budget_rejects_abi_overflow():
    import pytest
    for budget in (0, 1, 129, 256):
        with pytest.raises((ValueError, RuntimeError)):
            instrument(parse(PROGRAM), budget)


def test_source_statement_metadata_has_budget_priority():
    text = PROGRAM.replace(
        '%b = arith.addf %a, %input : tensor',
        '%b = arith.addf %a, %input {flagtree.debug.statement_id = 8 : i32, '
        'flagtree.debug.triton_statement = "sum = a + input"} : tensor')
    module = instrument(parse(text), 2)
    origins = compiler_binding().get_scope_id_origins(module)
    statements = [
        origin for origin in origins.values()
        if origin.get('source_statement') == 'sum = a + input'
    ]
    assert len(statements) == 1
    assert statements[0]['operation'] == 'arith.addf'
    assert statements[0]['entry'][0]['line'] == 9


def test_automatic_lowering_keeps_device_budget_and_manual_contract():
    from flagtree.profiler.observations import ObservationRequest
    from flagtree.profiler.observations_nvidia import lower_request
    auto = lower_request(ObservationRequest(automatic=True, max_sites=5))
    assert auto['automatic'] and auto['max_sites'] == 5
    assert auto['output_selection']['automatic']
    assert auto['collection_scope']['max_sites'] == 5
    assert auto['collection_scope']['warps'] == [0]
    assert auto['mode_options']['buffer_size'] == 256 * 2 * 8
    manual = lower_request(ObservationRequest())
    assert 'automatic' not in manual
    assert manual['collection_scope']['sites'] == 'all_explicit_proton_scopes'
