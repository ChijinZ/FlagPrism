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
    assert plan['proton.automatic_candidates'] == 3
    assert plan['proton.automatic_selected'] == 2
    assert plan['schema_version'] == binding.AUTOMATIC_INVENTORY_VERSION == 2
    inventory = plan['inventory']
    assert [row['candidate_ordinal'] for row in inventory] == [0, 1, 2]
    assert [row['operation'] for row in inventory
            ] == ['arith.mulf', 'arith.addf', 'arith.subf']
    assert [row['location']['line'] for row in inventory] == [8, 9, 10]
    assert [row['selected'] for row in inventory] == [True, False, True]
    assert inventory[1]['selection_reason'] == 'site_budget_excluded'
    assert inventory[1]['scope_id'] is None and inventory[1][
        'selected_scope_name'] is None
    assert inventory[2][
        'scope_id'] == 1  # candidate ordinal 2 is not scope ID 2.
    assert all(names[row['scope_id']] == row['selected_scope_name']
               for row in inventory if row['selected'])
    roundtrip = parse(module.str())
    assert binding.get_automatic_proton_plan(roundtrip) == plan
    instrument(module, 8)
    assert binding.get_scope_id_names(module) == list(names.items())
    assert binding.get_automatic_proton_plan(module) == plan


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
    for budget in (0, 129, 256):
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
    row = compiler_binding().get_automatic_proton_plan(module)['inventory'][1]
    assert row['selected'] and row[
        'selection_reason'] == 'source_statement_priority'
    assert row['candidate_class'] == 'source_statement'


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


def test_explicit_single_site_budget_is_supported():
    from flagtree.profiler.observations import ObservationRequest
    from flagtree.profiler.observations_nvidia import lower_request
    plan = lower_request(ObservationRequest(automatic=True, max_sites=1))
    assert plan['max_sites'] == 1
    module = instrument(parse(PROGRAM), 1)
    inventory = compiler_binding().get_automatic_proton_plan(
        module)['inventory']
    assert [row['selected'] for row in inventory] == [True, False, False]
    assert inventory[0]['candidate_ordinal'] == 0 and inventory[0][
        'scope_id'] == 0
    assert len(compiler_binding().get_scope_id_names(module)) == 1


def test_scope_mapping_survives_real_control_flow_lowering():
    module = parse('''module {
      tt.func public @control(%input: tensor<32xf32>, %trip: index, %pred: i1) -> tensor<32xf32> {
        %zero = arith.constant 0 : index
        %one = arith.constant 1 : index
        %result = scf.for %i = %zero to %trip step %one iter_args(%v = %input) -> (tensor<32xf32>) {
          %next = scf.if %pred -> (tensor<32xf32>) {
            %a = arith.mulf %v, %input : tensor<32xf32> loc("control.py":8:4)
            scf.yield %a : tensor<32xf32>
          } else {
            %b = arith.addf %v, %input : tensor<32xf32> loc("control.py":11:4)
            scf.yield %b : tensor<32xf32>
          }
          scf.yield %next : tensor<32xf32>
        }
        %d = arith.subf %result, %input : tensor<32xf32> loc("control.py":15:4)
        tt.return %d : tensor<32xf32>
      }
    }''')
    instrument(module)
    before = compiler_binding().get_automatic_proton_plan(module)
    pm = core.ir.pass_manager(module.context)
    core.passes.convert.add_scf_to_cf(pm)
    pm.run(module, 'automatic-scope-cfg-test')
    assert compiler_binding().get_automatic_proton_plan(module) == before


def statement_chain(count, initial, prefix, line):
    lines = []
    value = initial
    for index in range(count):
        following = f'%{prefix}{index}'
        lines.append(f'{following} = arith.addf {value}, %input '
                     f'{{flagtree.debug.statement_id = {line + index} : i32, '
                     f'flagtree.debug.triton_statement = "{prefix}{index}"}} '
                     f': tensor<32xf32> loc("regions.py":{line + index}:4)')
        value = following
    return '\n'.join(lines), value


def test_real_ir_single_loop_body_survives_long_statement_prefix_and_suffix():
    prefix, before = statement_chain(8, '%input', 'prefix', 10)
    suffix, after = statement_chain(8, '%loop', 'suffix', 40)
    text = f'''module {{
      tt.func public @spread(%input: tensor<32xf32>, %trip: index) -> tensor<32xf32> {{
        %zero = arith.constant 0 : index
        %one = arith.constant 1 : index
        {prefix}
        %loop = scf.for %i = %zero to %trip step %one iter_args(%v = {before}) -> (tensor<32xf32>) {{
          %body = arith.mulf %v, %input {{flagtree.debug.statement_id = 30 : i32, flagtree.debug.triton_statement = "body"}} : tensor<32xf32> loc("regions.py":30:4)
          scf.yield %body : tensor<32xf32>
        }} loc("regions.py":29:4)
        {suffix}
        tt.return {after} : tensor<32xf32>
      }}
    }}'''
    for budget in (1, 8):
        plan = compiler_binding().get_automatic_proton_plan(
            instrument(parse(text), budget))
        body = next(row for row in plan['inventory']
                    if row.get('source_statement') == 'body')
        assert body['selected']
        assert body['selection_reason'] == 'control_flow_region_representative'
        assert plan['proton.automatic_selected'] == budget
        region, = plan['control_regions']
        assert region['repeated'] and region[
            'coverage_status'] == 'direct_representative'
        assert region['selected_candidates'] == [body['candidate_ordinal']]


def test_empty_selected_branch_has_real_scalar_control_candidates():
    text = '''module {
      tt.func public @inactive(%input: tensor<32xf32>) -> tensor<32xf32> {
        %zero = arith.constant 0 : i32
        %pid = tt.get_program_id x : i32 loc("inactive.py":5:10)
        %pred = arith.cmpi sgt, %pid, %zero : i32 loc("inactive.py":6:7)
        %result = scf.if %pred -> (tensor<32xf32>) {
          %a = arith.mulf %input, %input : tensor<32xf32> loc("inactive.py":7:8)
          scf.yield %a : tensor<32xf32>
        } else {
          scf.yield %input : tensor<32xf32>
        } loc("inactive.py":6:4)
        tt.return %result : tensor<32xf32>
      }
    }'''
    module = instrument(parse(text))
    plan = compiler_binding().get_automatic_proton_plan(module)
    selected = {
        row['operation']: row
        for row in plan['inventory'] if row['selected']
    }
    assert selected['tt.get_program_id'][
        'candidate_class'] == 'control_computation'
    assert selected['arith.cmpi']['candidate_class'] == 'control_computation'
    assert selected['scf.if']['candidate_class'] == 'control_region'
    assert {row['location']['line'] for row in selected.values()} == {5, 6, 7}
    assert [r['coverage_status'] for r in plan['control_regions']
            ] == ['direct_representative', 'no_eligible_operation']
    pm = core.ir.pass_manager(module.context)
    core.passes.convert.add_scf_to_cf(pm)
    pm.run(module, 'automatic-empty-branch-cfg-test')
    assert compiler_binding().get_automatic_proton_plan(module) == plan


def test_nested_regions_and_insufficient_budget_have_explicit_coverage():
    text = '''module {
      tt.func public @nested(%input: tensor<32xf32>, %trip: index, %pred: i1) -> tensor<32xf32> {
        %zero = arith.constant 0 : index
        %one = arith.constant 1 : index
        %r = scf.for %i = %zero to %trip step %one iter_args(%v = %input) -> (tensor<32xf32>) {
          %next = scf.if %pred -> (tensor<32xf32>) {
            %a = arith.mulf %v, %input : tensor<32xf32> loc("nested.py":8:4)
            scf.yield %a : tensor<32xf32>
          } else {
            %b = arith.addf %v, %input : tensor<32xf32> loc("nested.py":11:4)
            scf.yield %b : tensor<32xf32>
          } loc("nested.py":7:4)
          scf.yield %next : tensor<32xf32>
        } loc("nested.py":6:4)
        tt.return %r : tensor<32xf32>
      }
    }'''
    full = compiler_binding().get_automatic_proton_plan(
        instrument(parse(text), 8))
    assert len(full['control_regions']) == 3
    assert all(row['coverage_status'] == 'direct_representative'
               for row in full['control_regions'])
    narrow = compiler_binding().get_automatic_proton_plan(
        instrument(parse(text), 1))
    assert narrow['proton.automatic_selected'] == 1
    assert narrow['control_regions'][0][
        'coverage_status'] == 'direct_representative'
    assert [row['coverage_status'] for row in narrow['control_regions'][1:]
            ] == ['budget_excluded', 'budget_excluded']
    assert all(row['selection_reason'] == 'site_budget_excluded'
               for row in narrow['inventory'] if not row['selected'])


def test_control_selection_policy_binding_matches_compiled_plan():
    binding = compiler_binding()
    plan = binding.get_automatic_proton_plan(instrument(parse(PROGRAM)))
    assert binding.AUTOMATIC_SELECTION_POLICY_VERSION == 1
    assert plan[
        'selection_policy_version'] == binding.AUTOMATIC_SELECTION_POLICY_VERSION
    assert plan[
        'selection_policy'] == 'bounded_control_regions_then_source_statements'


def test_while_condition_and_body_are_separate_repeating_regions():
    text = '''module {
      tt.func public @conditioned(%input: tensor<32xf32>, %trip: index) -> tensor<32xf32> {
        %zero = arith.constant 0 : index
        %one = arith.constant 1 : index
        %result:2 = scf.while (%v = %input, %i = %zero) : (tensor<32xf32>, index) -> (tensor<32xf32>, index) {
          %pred = arith.cmpi slt, %i, %trip : index loc("while.py":5:4)
          scf.condition(%pred) %v, %i : tensor<32xf32>, index
        } do {
        ^bb0(%v: tensor<32xf32>, %i: index):
          %next = arith.mulf %v, %input : tensor<32xf32> loc("while.py":6:8)
          %j = arith.addi %i, %one : index
          scf.yield %next, %j : tensor<32xf32>, index
        } loc("while.py":5:4)
        tt.return %result#0 : tensor<32xf32>
      }
    }'''
    module = instrument(parse(text), 2)
    plan = compiler_binding().get_automatic_proton_plan(module)
    assert [(r['region_index'], r['repeated'], r['coverage_status'])
            for r in plan['control_regions']
            ] == [(0, True, 'direct_representative'),
                  (1, True, 'direct_representative')]
    assert {row['operation']
            for row in plan['inventory']
            if row['selected']} == {'arith.cmpi', 'arith.mulf'}
    pm = core.ir.pass_manager(module.context)
    core.passes.convert.add_scf_to_cf(pm)
    pm.run(module, 'automatic-while-cfg-test')
    assert compiler_binding().get_automatic_proton_plan(module) == plan
