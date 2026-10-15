"""General LLVM mapping cases, independent of Study kernel names/SSA slots."""
import importlib.util
import sys
import types
import copy
import hashlib
import json
import pytest
from pathlib import Path

namespace = types.ModuleType('_ascend_test_package')
namespace.__path__ = [
    str(Path(__file__).parents[1] / 'python/flagtree_profiler')
]
sys.modules['_ascend_test_package'] = namespace
spec = importlib.util.spec_from_file_location(
    '_ascend_test_package.execution_ascend',
    Path(__file__).parents[1] / 'python/flagtree_profiler/execution_ascend.py')
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


def provenance_metadata(manifest, entries):
    source = 'module { /* exact retained compiler input */ }\r\n'
    llir = 'define void @retained_actor() { ret void }\n'
    compile_id = 'enclosing-actual-test-compile'
    manifest = copy.deepcopy(manifest)
    manifest.update(module_sha256=hashlib.sha256(llir.encode()).hexdigest(),
                    compile_id=compile_id)
    text = json.dumps(manifest, sort_keys=True, indent=2) + '\n'
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    table_hash = hashlib.sha256(
        json.dumps(list(entries.values()),
                   sort_keys=True,
                   separators=(',', ':')).encode()).hexdigest()
    return {
        'flagprism_ascend_handoff': {
            'compile_id':
            compile_id,
            'phase':
            'finished',
            'returncode':
            0,
            'source_snapshot': {
                'phase': 'pre_backend_driver',
                'encoding': 'utf-8',
                'ir': source,
                'ir_sha256': source_hash,
                'tracked_ops_sha256': table_hash
            },
            'sdk_ir_capture': {
                'receipt': {
                    'compile_id': compile_id,
                    'source_ir_sha256': source_hash,
                    'state': 'finished',
                    'returncode': 0
                }
            },
            'artifacts': [{
                'metadata':
                manifest,
                'manifest_text':
                text,
                'manifest_sha256':
                hashlib.sha256(text.encode()).hexdigest(),
                'llir':
                llir,
                'sha256':
                hashlib.sha256(llir.encode()).hexdigest(),
                'driver_job': {
                    'state': 'finished',
                    'exit_code': 0,
                    'compile_id': compile_id
                }
            }]
        }
    }


def test_actual_ssa_cfg_and_native_event_evidence():
    result = module.build_execution_mapping({'final_cube': LLVM}, {'artifact_actor_kinds': {'final_cube': 'AIC'}, 'argument_roles': {'final_cube': {'0': 'workspace'}}}, binary_id='binary-sha', source_operations=['source-operation-7'])
    assert result['status'] == 'partial'
    assert result['actors'][0]['kind'] == 'AIC'
    assert result['workspace'][0]['ssa'] == '%workspace'
    assert result['loops'][0]['blocks'] == ['loop']
    assert result['loops'][0]['dynamic_iteration_count'] is None
    assert result['sites'][0]['operand_expressions'] == ['10', '(%iteration % 2)']
    assert not result['source_associations']
    assert result['sites'][0]['source_op_id'] == 'source-operation-7'
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
    sites=[{'id':i,'callee':'llvm.hivm.WAIT.FLAG.IMM','operands':['1','2','3'],'debug_directory':'/source','debug_file':'a.py','debug_line':7,'debug_column':3,'inline_chain':[]} for i in range(2)]
    manifest={'module_sha256':'actual-compiler-sha','actors':[{'function':'any_symbol','actor_kind':'AIV','arguments':[],'sites':sites,'loops':[]}]}
    metadata = provenance_metadata(manifest, entries)
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
    site={'site_id':0,'semantics':'loop_header_occurrence','debug_directory':'/source','debug_file':'control.py','debug_line':9,'debug_column':4,'inline_chain':[],'iteration_identity':None}
    manifest={'module_sha256':'actual-module','actors':[{'function':'fresh_actor','actor_kind':'AIC','arguments':[],'sites':[],'loops':[]}],'dynamic_sites':[site]}
    metadata = provenance_metadata(manifest, entries)
    result=module.build_execution_mapping({},metadata,source_operations=entries)
    mapped=result['sites'][0]
    assert mapped['dynamic_observation'] and mapped['semantics']=='control_checkpoint'
    assert mapped['debug_origin_status']=='verified_origin'
    assert result['static_readiness']['state'] == 'unavailable'
    assert result['compiler_provenance']['state'] == 'verified_source_binding'
    assert result['source_associations'][0]['cost_ownership']=='not_established'
    assert mapped['compiler_evidence']['iteration_identity'] is None


@pytest.mark.parametrize('mutation', [
    'missing_source', 'source_bytes', 'source_hash', 'sdk_source',
    'sdk_failed', 'enclosing_compile', 'manifest_missing', 'manifest_bytes',
    'manifest_hash', 'metadata_numeric_bool', 'llvm_bytes', 'module_hash',
    'job_failed', 'job_compile', 'manifest_compile', 'coherent_stale_artifact',
    'table_hash', 'missing_llvm', 'missing_job', 'non_dict_job',
    'missing_enclosing', 'missing_table', 'missing_sdk_receipt',
    'null_sdk_receipt'
])
def test_native_origin_and_explicit_association_reject_invalid_provenance(
        mutation):
    entries = {'41': {'opId': 41, 'sourceLoc': 'loc("/source/a.py":7:3)'}}
    site = {
        'id': 0,
        'callee': 'llvm.hivm.WAIT.FLAG.IMM',
        'operands': ['1', '2', '3'],
        'source_op_id': '41',
        'debug_directory': '/source',
        'debug_file': 'a.py',
        'debug_line': 7,
        'debug_column': 3,
        'inline_chain': []
    }
    manifest = {
        'schema_version':
        1,
        'actors': [{
            'function': 'only_aic',
            'actor_kind': 'AIC',
            'arguments': [],
            'sites': [site],
            'loops': []
        }]
    }
    metadata = provenance_metadata(manifest, entries)
    h = metadata['flagprism_ascend_handoff']
    a = h['artifacts'][0]
    if mutation == 'missing_source': h['source_snapshot'].pop('ir')
    elif mutation == 'source_bytes': h['source_snapshot']['ir'] += 'stale'
    elif mutation == 'source_hash': h['source_snapshot']['ir_sha256'] = 'wrong'
    elif mutation == 'sdk_source':
        h['sdk_ir_capture']['receipt']['source_ir_sha256'] = 'wrong'
    elif mutation == 'sdk_failed':
        h['sdk_ir_capture']['receipt']['returncode'] = 1
    elif mutation == 'enclosing_compile':
        h['compile_id'] = 'other'
    elif mutation == 'manifest_missing':
        a.pop('manifest_text')
    elif mutation == 'manifest_bytes':
        a['manifest_text'] += ' '
    elif mutation == 'manifest_hash':
        a['manifest_sha256'] = 'wrong'
    elif mutation == 'metadata_numeric_bool':
        a['metadata']['schema_version'] = True
    elif mutation == 'llvm_bytes':
        a['llir'] += '; stale'
    elif mutation == 'module_hash':
        a['metadata']['module_sha256'] = 'wrong'
    elif mutation == 'job_failed':
        a['driver_job']['exit_code'] = 1
    elif mutation == 'job_compile':
        a['driver_job']['compile_id'] = 'other'
    elif mutation == 'manifest_compile':
        a['metadata']['compile_id'] = 'other'
    elif mutation == 'coherent_stale_artifact':
        a['driver_job']['compile_id'] = 'other'
        a['metadata']['compile_id'] = 'other'
        a['manifest_text'] = json.dumps(
            a['metadata'], sort_keys=True, indent=2) + '\n'
        a['manifest_sha256'] = hashlib.sha256(
            a['manifest_text'].encode()).hexdigest()
    elif mutation == 'table_hash':
        h['source_snapshot']['tracked_ops_sha256'] = 'wrong'
    elif mutation == 'missing_llvm':
        a.pop('llir')
    elif mutation == 'missing_job':
        a.pop('driver_job')
    elif mutation == 'non_dict_job':
        a['driver_job'] = None
    elif mutation == 'missing_enclosing':
        h.pop('compile_id')
    elif mutation == 'missing_table':
        h['source_snapshot'].pop('tracked_ops_sha256')
    elif mutation == 'missing_sdk_receipt':
        h['sdk_ir_capture'].pop('receipt')
    elif mutation == 'null_sdk_receipt':
        h['sdk_ir_capture']['receipt'] = None
    result = module.build_execution_mapping({},
                                            metadata,
                                            source_operations=entries)
    assert result['actors'] and result['sites']
    assert not result['source_associations']
    assert all(s['debug_origin_status'] == 'unassociated'
               for s in result['sites'])


def test_source_origin_does_not_require_a_cross_actor_channel_or_sdk_dump():
    entries = {'41': {'opId': 41, 'sourceLoc': 'loc("/source/a.py":7:3)'}}
    site = {
        'id': 0,
        'callee': 'llvm.hivm.WAIT.FLAG.IMM',
        'operands': ['1', '2', '3'],
        'source_op_id': '41',
        'debug_directory': '/source',
        'debug_file': 'a.py',
        'debug_line': 7,
        'debug_column': 3,
        'inline_chain': []
    }
    manifest = {
        'actors': [{
            'function': 'only_aic',
            'actor_kind': 'AIC',
            'arguments': [],
            'sites': [site],
            'loops': []
        }]
    }
    result = module.build_execution_mapping({},
                                            provenance_metadata(
                                                manifest, entries),
                                            source_operations=entries)
    assert result['actors'][0]['kind'] == 'AIC'
    assert result['static_readiness']['state'] == 'unavailable'
    assert len(result['source_associations']) == 2
    assert result['sites'][0]['debug_origin_status'] == 'verified_origin'
