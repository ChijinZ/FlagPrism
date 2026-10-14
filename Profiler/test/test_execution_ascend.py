"""General LLVM mapping cases, independent of Study kernel names/SSA slots."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('execution_ascend_test', Path(__file__).parents[1]/'python/flagtree_profiler/execution_ascend.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

LLVM = '''define dso_local void @totally_new_symbol(ptr addrspace(1) %workspace, i64 %limit) {
entry:
  %bid = call i64 @llvm.hivm.GET.BLOCK.IDX()
  br label %loop
loop:
  %iteration = phi i64 [ 0, %entry ], [ %next, %loop ]
  %buffer = urem i64 %iteration, 2
  %offset = mul i64 %bid, 256
  call void @llvm.hivm.SET.CROSS.CORE(i64 10, i64 %buffer), !flagprism.source_op_id !4
  %next = add i64 %iteration, 1
  %more = icmp ult i64 %next, %limit
  br i1 %more, label %loop, label %exit
exit:
  ret void
}
!4 = !{!"source-operation-7"}
!hivm.annotations = !{!1}
!1 = !{ptr @totally_new_symbol, !"kernel", i32 1}
'''


def test_actual_ssa_cfg_and_native_event_evidence():
    result = module.build_execution_mapping({'final_cube': LLVM}, {'artifact_actor_kinds': {'final_cube': 'AIC'}, 'argument_roles': {'final_cube': {'0': 'workspace'}}}, binary_id='binary-sha', source_operations=['source-operation-7'])
    assert result['status'] == 'partial'
    assert result['actors'][0]['kind'] == 'AIC'
    assert result['workspace'][0]['ssa'] == '%workspace'
    assert result['loops'][0]['blocks'] == ['loop']
    assert result['loops'][0]['dynamic_iteration_count'] is None
    assert result['sites'][0]['operand_expressions'] == ['10', '(%iteration % 2)']
    assert result['source_associations'][0]['source_op_id'] == 'source-operation-7'
    assert result['dependencies'][0]['peer_site_id'] is None


def test_kernel_name_is_never_actor_or_source_evidence():
    result = module.build_execution_mapping({'llir': LLVM.replace('totally_new_symbol', 'matmul_mix_aic').replace(', !flagprism.source_op_id !4', '')}, {})
    assert result['actors'][0]['kind'] is None
    assert not result['workspace'] and not result['source_associations']
    assert result['global_arguments'][0]['role'] is None


def test_pre_actor_expansion_cannot_claim_final_mapping():
    result = module.build_execution_mapping({'ttadapter': 'module { func.func @matmul() { return } }'}, {'mix_mode': 'mix'})
    assert result['status'] == 'unsupported'
    assert result['actors'] == []


def test_debug_origin_requires_complete_snapshot_and_unique_candidate():
    import hashlib,json
    entries={'41':{'opId':41,'sourceLoc':'loc("/source/a.py":7:3)'}}
    table_hash=hashlib.sha256(json.dumps(list(entries.values()),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    sites=[{'id':i,'callee':'llvm.hivm.WAIT.FLAG.IMM','operands':['1','2','3'],'debug_directory':'/source','debug_file':'a.py','debug_line':7,'debug_column':3,'inline_chain':[]} for i in range(2)]
    manifest={'module_sha256':'actual-compiler-sha','actors':[{'function':'any_symbol','actor_kind':'AIV','arguments':[],'sites':sites,'loops':[]}]}
    metadata={'flagprism_ascend_handoff':{'source_snapshot':{'ir_sha256':'actual-source-ir-sha','tracked_ops_sha256':table_hash},'artifacts':[{'metadata':manifest}]}}
    result=module.build_execution_mapping({},metadata,source_operations=entries)
    assert len(result['source_associations'])==2
    assert all(a['status']=='verified_origin' and a['cost_ownership']=='not_established' for a in result['source_associations'])
    ambiguous=dict(entries);ambiguous['42']={'opId':42,'sourceLoc':entries['41']['sourceLoc']}
    metadata['flagprism_ascend_handoff']['source_snapshot']['tracked_ops_sha256']=hashlib.sha256(json.dumps(list(ambiguous.values()),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    result=module.build_execution_mapping({},metadata,source_operations=ambiguous)
    assert not result['source_associations'] and all(s['debug_origin_status']=='ambiguous' for s in result['sites'])
    metadata['flagprism_ascend_handoff']['source_snapshot']['tracked_ops_sha256']='wrong-snapshot'
    assert not module.build_execution_mapping({},metadata,source_operations=entries)['source_associations']


def test_dynamic_loop_checkpoint_retains_actual_origin_without_iteration_claim():
    import hashlib,json
    entries={'71':{'opId':71,'sourceLoc':'loc("/source/control.py":9:4)'}}
    table_hash=hashlib.sha256(json.dumps(list(entries.values()),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    site={'site_id':0,'semantics':'loop_header_occurrence','debug_directory':'/source','debug_file':'control.py','debug_line':9,'debug_column':4,'inline_chain':[],'iteration_identity':None}
    manifest={'module_sha256':'actual-module','actors':[{'function':'fresh_actor','actor_kind':'AIC','arguments':[],'sites':[],'loops':[]}],'dynamic_sites':[site]}
    metadata={'flagprism_ascend_handoff':{'source_snapshot':{'ir_sha256':'source-snapshot','tracked_ops_sha256':table_hash},'artifacts':[{'metadata':manifest}]}}
    result=module.build_execution_mapping({},metadata,source_operations=entries)
    mapped=result['sites'][0]
    assert mapped['dynamic_observation'] and mapped['semantics']=='control_checkpoint'
    assert mapped['debug_origin_status']=='verified_origin'
    assert result['source_associations'][0]['cost_ownership']=='not_established'
    assert mapped['compiler_evidence']['iteration_identity'] is None
