"""Static adapter contracts; hardware compilation is tested separately."""
from flagtree.profiler.execution_enflame import build_execution_mapping


def test_preserves_work_item_ownership_and_unknown_source():
    ir = '''"builtin.module"() ({
%0 = "arith.constant"() <{value = 7 : index}> : () -> index
%1 = "arith.constant"() <{value = 3 : index}> : () -> index
%2 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
%3 = "arith.remsi"(%2, %1) : (index, index) -> index
%4 = "arith.muli"(%3, %0) : (index, index) -> index
"vector.store"(%v, %storage, %4) : (vector<7xf32>, memref<21xf32>, index) -> ()
"gpu.barrier"() : () -> ()
%5 = "memref.load"(%storage, %2) : (memref<3xf32, 2>, index) -> f32
}) {"ttg.num-warps" = 3 : i32, "ttg.threads-per-warp" = 1 : i32, "ttg.num-ctas" = 1 : i32} : () -> ()'''
    mapping = build_execution_mapping({"gcuir": ir}, {"name": "arbitrary"})
    assert mapping["execution_model"] == "vector_work_items"
    assert mapping["work_item_count"] == 3
    assert mapping["sites"][0]["operand_expressions"][-1] == "((work_item.x % 3) * 7)"
    assert mapping["sites"][1]["kind"] == "barrier"
    assert mapping["sites"][2]["kind"] == "partial_exchange_storage"
    assert mapping["status"] == "partial"
    assert not mapping["source_associations"]
    assert len(mapping["unassociated_sites"]) == 3


def test_name_and_border_are_not_source_identity():
    ir = '''"gcu.border"() {enter = "tt.reduce"} : () -> ()
"gpu.barrier"() : () -> ()'''
    one = build_execution_mapping({"gcuir": ir}, {"name": "softmax"})
    two = build_execution_mapping({"gcuir": ir}, {"name": "unrelated"})
    assert one["sites"] == two["sites"]
    assert not one["source_associations"]
    assert one["lowered_regions"][0]["source_association"] == "unknown"


def test_explicit_source_identity_survives_split():
    ir = '''"gpu.barrier"() {flagprism.source_op_id = "op:a"} : () -> ()
"gpu.barrier"() {flagprism.source_op_id = "op:a"} : () -> ()
"gpu.barrier"() {flagprism.source_op_id = "not-in-source"} : () -> ()'''
    mapping = build_execution_mapping({"gcuir": ir}, {}, source_operations={"op:a": {}})
    assert len(mapping["source_associations"]) == 2
    assert len({row["lowered_site_id"] for row in mapping["source_associations"]}) == 2
    assert len(mapping["unassociated_sites"]) == 1


def test_missing_artifact_and_llvm_sites_are_not_measurements():
    mapping = build_execution_mapping({"llir": '"llvm.call"() <{callee = @tops_clock_begin}> : () -> i64'}, {})
    assert mapping["status"] == "unsupported"
    assert mapping["work_item_count"] is None
    assert not mapping["llvm_primitive_sites"][0]["dynamic_observation"]


def test_ssa_ownership_does_not_leak_between_functions():
    ir = '''"func.func"() ({
%0 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
"memref.load"(%a, %0) : (memref<4xf32>, index) -> f32
})
"func.func"() ({
%0 = "unknown.index"() : () -> index
"memref.load"(%a, %0) : (memref<4xf32>, index) -> f32
})'''
    mapping = build_execution_mapping({"gcuir": ir}, {})
    assert mapping["sites"][0]["ownership_status"] == "symbolic"
    assert mapping["sites"][1]["ownership_status"] == "unknown"


def test_real_location_aliases_preserve_ambiguous_origin_not_exclusive_cost():
    ir = '''"vector.store"(%v, %p, %i) : (vector<4xf32>, memref<4xf32>, index) -> () loc(#loc4)
"gpu.barrier"() : () -> () loc(#loc3)
#loc1 = loc("/source a.py":10:7)
#loc2 = loc("/library.py":20:5)
#loc3 = loc(callsite(#loc2 at #loc1))
#loc4 = loc(fused[#loc1, #loc2])'''
    sources = {'11': {'sourceLoc': 'loc("/source a.py":10:7)'},
               '12': {'sourceLoc': 'loc("/library.py":20:5)'}}
    mapping = build_execution_mapping({'gcuir': ir}, {}, source_operations=sources)
    assert len(mapping['source_origin_associations']) == 2
    assert all(row['status'] == 'ambiguous' for row in mapping['source_origin_associations'])
    assert all(set(row['candidate_source_ids']) == {'11', '12'} for row in mapping['source_origin_associations'])
    assert all(row['exclusive_cost'] is False for row in mapping['source_origin_associations'])
    assert not mapping['source_associations']
    assert mapping['status'] == 'partial'


def test_unique_location_origin_and_unresolved_alias_remain_distinct():
    ir = '''"memref.load"(%a, %i) : (memref<4xf32>, index) -> f32 loc(#loc1)
"memref.load"(%a, %i) : (memref<4xf32>, index) -> f32 loc(fused[#loc1, #missing])
"memref.load"(%a, %i) : (memref<4xf32>, index) -> f32 loc(#missing)
#loc1 = loc("/source.py":3:9)'''
    mapping = build_execution_mapping({'gcuir': ir}, {'debug_tracked_table': [
        {'opId': 7, 'sourceLoc': 'loc("/source.py":3:9)', 'mlirOpName': 'tt.load'}]})
    assert [site['source_origin_status'] for site in mapping['sites']] == ['unique_origin', 'ambiguous', 'missing']
    assert mapping['source_origin_associations'][0]['candidate_source_ids'] == ['7']
    assert mapping['source_origin_associations'][1]['unresolved_location_aliases'] == ['#missing']


def test_ttir_origins_are_ir_scoped_and_location_aliases_do_not_leak_ssa():
    ttir = '''module {
 tt.func public @first() {
  %0 = tt.load %p : !tt.ptr<f32> loc(#loc1)
 }
 tt.func public @second() {
  %0 = tt.load %p : !tt.ptr<f32> loc(#loc2)
 }
}
#loc1 = loc("/first.py":1:2)
#loc2 = loc("/second.py":1:2)'''
    gcu = '''"func.func"() ({
%0 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index loc(#loc1)
"memref.load"(%a, %0) : (memref<4xf32>, index) -> f32 loc(#loc1)
})
"func.func"() ({
%0 = "unknown.index"() : () -> index loc(#loc2)
"memref.load"(%a, %0) : (memref<4xf32>, index) -> f32 loc(#loc2)
})
#loc1 = loc("/first.py":1:2)
#loc2 = loc("/second.py":1:2)'''
    mapping = build_execution_mapping({'ttir': ttir, 'gcuir': gcu}, {})
    assert [site['ownership_status'] for site in mapping['sites']] == ['symbolic', 'unknown']
    origins = mapping['origin_source_operations']
    assert all(row['identity_kind'] == 'ttir_operation_with_debug_origin' for row in origins)
    assert origins[0]['id'] != origins[1]['id']
    assert ':function-1:' in origins[0]['id'] and ':function-2:' in origins[1]['id']
    assert [site['source_origin_status'] for site in mapping['sites']] == ['unique_origin', 'unique_origin']


def test_location_cycle_and_quoted_alias_are_not_guessed():
    ir = '''"gpu.barrier"() : () -> () loc(#loc1)
"gpu.barrier"() : () -> () loc("/literal#loc1.py":2:8)
#loc1 = loc(#loc2)
#loc2 = loc(#loc1)'''
    mapping = build_execution_mapping({'gcuir': ir}, {}, source_operations={
        'literal': {'sourceLoc': 'loc("/literal#loc1.py":2:8)'}})
    assert mapping['sites'][0]['source_origin_status'] == 'missing'
    assert mapping['sites'][0]['location']['unresolved_aliases']
    assert mapping['sites'][1]['source_origin_status'] == 'unique_origin'
    assert not mapping['sites'][1]['location']['unresolved_aliases']
