"""Run the real LLVM15 pass: selection occurs before timestamp instrumentation."""
import json
import os
import subprocess
import pytest

IR = '''define dso_local void @fresh_actor(ptr addrspace(1) %log) {
entry:
 call void @llvm.hivm.SET.FLAG.IMM(i64 3, i64 4, i64 7)
 call void @llvm.hivm.WAIT.FLAG.IMM(i64 3, i64 4, i64 7)
 ret void
}
declare void @llvm.hivm.SET.FLAG.IMM(i64,i64,i64)
declare void @llvm.hivm.WAIT.FLAG.IMM(i64,i64,i64)
!hivm.annotations = !{!0}
!0 = !{ptr @fresh_actor, !"kernel", i32 1}
'''


def execute(tmp_path, semantics, ir=IR, actor_kind="AIC"):
    plugin = os.environ.get('FLAGPRISM_ASCEND_LATE_PLUGIN')
    if not plugin:
        pytest.skip('requires the actual built upstream LLVM15 plugin')
    tmp_path.mkdir(exist_ok=True)
    source = tmp_path / 'input.ll'
    source.write_text(ir)
    env = dict(os.environ,
               FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(tmp_path),
               FLAGPRISM_ASCEND_ACTOR_KIND=actor_kind,
               FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX='0',
               FLAGPRISM_ASCEND_TRACE_CAPACITY='16',
               FLAGPRISM_ASCEND_TRACE_PROGRAM='0',
               FLAGPRISM_ASCEND_ALLOW_TEST_FORMAL_INDEX='1')
    env.pop('FLAGPRISM_ASCEND_TRACE_SOURCE_ARGUMENT', None)
    env.pop('FLAGPRISM_ASCEND_SOURCE_ABI', None)
    if semantics is None: env.pop('FLAGPRISM_ASCEND_TRACE_SEMANTICS', None)
    else: env['FLAGPRISM_ASCEND_TRACE_SEMANTICS'] = semantics
    result = subprocess.run([
        os.environ.get('FLAGPRISM_ASCEND_OPT',
                       '/usr/bin/opt-15'), '-load-pass-plugin=' + plugin,
        '-passes=flagprism-ascend-late-observer', '-S', '-o',
        str(tmp_path / 'adapted.ll'),
        str(source)
    ],
                            env=env,
                            capture_output=True)
    return result, tmp_path


@pytest.mark.parametrize('semantics,expected_sites,timestamps',
                         [(None, [0, 1], 4), ('issue', [0], 2),
                          ('wait_bracket', [1], 2),
                          ('control_checkpoint', [], 0)])
def test_actual_pass_preserves_site_ids_and_omits_unselected_timestamp(
        tmp_path, semantics, expected_sites, timestamps):
    result, path = execute(tmp_path, semantics)
    assert result.returncode == 0, result.stderr.decode()
    text = (path / 'adapted.ll').read_text()
    assert text.count('MOV $0, SYS_CNT') == timestamps
    assert text.count('call void @llvm.hivm.SET.FLAG.IMM') == 1
    assert text.count('call void @llvm.hivm.WAIT.FLAG.IMM') == 1
    manifests = [json.loads(p.read_text()) for p in path.glob('*.json')]
    manifest, = manifests
    assert [site['site_id']
            for site in manifest['dynamic_sites']] == expected_sites
    assert manifest[
        'semantic_selection_stage'] == 'compile_time_before_timestamp_and_record'
    if not timestamps: assert 'store volatile' not in text


@pytest.mark.parametrize('semantics',
                         ['busy', 'issue,issue', 'wait_bracket,busy'])
def test_actual_pass_rejects_unknown_or_duplicate_semantics(
        tmp_path, semantics):
    result, _ = execute(tmp_path, semantics)
    assert result.returncode != 0 and b'semantics must be unique supported names' in result.stderr


def test_loop_checkpoint_ids_remain_stable_after_call_selection(tmp_path):
    loop = IR.replace(
        ' ret void\n}',
        ' br label %loop\nloop:\n %i = phi i64 [0,%entry], [%next,%loop]\n %next = add i64 %i,1\n %more = icmp ult i64 %next,4\n br i1 %more,label %loop,label %exit\nexit:\n ret void\n}'
    )
    for semantics, expected, ticks in [('wait_bracket', [1], 2),
                                       ('control_checkpoint', [2], 1)]:
        result, path = execute(tmp_path / semantics, semantics, loop)
        assert result.returncode == 0, result.stderr.decode()
        manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
        assert [site['site_id']
                for site in manifest['dynamic_sites']] == expected
        assert (path /
                'adapted.ll').read_text().count('MOV $0, SYS_CNT') == ticks


OPERATIONS_IR = '''source_filename = "user_module"
define dso_local void @fresh_actor(ptr addrspace(1) %log, ptr addrspace(1) %x) !dbg !4 {
entry:
 %a = load float, ptr addrspace(1) %x, !dbg !8
 %b = fadd float %a, 2.0, !dbg !9
 %c = fmul float %b, 3.0, !dbg !9
 store float %c, ptr addrspace(1) %x, !dbg !10
 ret void, !dbg !10
}
!hivm.annotations = !{!0}
!0 = !{ptr @fresh_actor, !"kernel", i32 1}
!llvm.dbg.cu = !{!1}
!llvm.module.flags = !{!2, !3}
!1 = distinct !DICompileUnit(language: DW_LANG_Python, file: !5, producer: "compiler", isOptimized: true, runtimeVersion: 0, emissionKind: LineTablesOnly)
!2 = !{i32 2, !"Dwarf Version", i32 4}
!3 = !{i32 2, !"Debug Info Version", i32 3}
!4 = distinct !DISubprogram(name: "fresh_actor", scope: !5, file: !5, line: 1, type: !6, scopeLine: 1, spFlags: DISPFlagDefinition, unit: !1)
!5 = !DIFile(filename: "user_kernel.py", directory: "/user")
!6 = !DISubroutineType(types: !7)
!7 = !{}
!8 = !DILocation(line: 11, column: 2, scope: !4)
!9 = !DILocation(line: 12, column: 2, scope: !4)
!10 = !DILocation(line: 13, column: 2, scope: !4)
'''


def test_generic_operations_have_source_positions_and_are_coalesced(tmp_path):
    result, path = execute(tmp_path, 'operation_checkpoint', OPERATIONS_IR)
    assert result.returncode == 0, result.stderr.decode()
    manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
    sites = manifest['dynamic_sites']
    assert [s['operation_class']
            for s in sites] == ['load', 'compute', 'store']
    assert [s['line'] for s in sites] == [11, 12, 13]
    assert all(s['source_file'] == '/user/user_kernel.py' for s in sites)
    assert all(s['candidate_count'] == s['selected_count'] == 3 for s in sites)
    text = (path / 'adapted.ll').read_text()
    assert text.count('MOV $0, SYS_CNT') == 3
    assert 'WAIT.FLAG' not in text and 'PIPE.BARRIER' not in text


def test_operation_site_budget_reduces_device_work_and_preserves_identity(
        tmp_path, monkeypatch):
    monkeypatch.setenv('FLAGPRISM_ASCEND_TRACE_MAX_SITES', '2')
    result, path = execute(tmp_path, 'operation_checkpoint', OPERATIONS_IR)
    assert result.returncode == 0, result.stderr.decode()
    manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
    assert [s['operation_class']
            for s in manifest['dynamic_sites']] == ['load', 'store']
    assert [s['site_id'] for s in manifest['dynamic_sites']] == [0, 2]
    assert [s['selected'] for s in manifest['operation_plan']['inventory']
            ] == [True, False, True]
    assert manifest['operation_plan']['inventory'][1][
        'selection_reason'] == 'static_site_budget'
    assert manifest['operation_plan']['inventory'][1]['line'] == 12
    assert all(s['candidate_count'] == 3 and s['selected_count'] == 2
               for s in manifest['dynamic_sites'])
    assert (path / 'adapted.ll').read_text().count('MOV $0, SYS_CNT') == 2


def test_vector_actor_coordinates_are_not_user_operation_candidates(tmp_path):
    result, path = execute(tmp_path,
                           'operation_checkpoint',
                           OPERATIONS_IR,
                           actor_kind='AIV')
    assert result.returncode == 0, result.stderr.decode()
    manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
    assert [s['operation_class'] for s in manifest['dynamic_sites']
            ] == ['load', 'compute', 'store']
    assert all(s['candidate_count'] == 3 for s in manifest['dynamic_sites'])


NESTED_CONTROL_IR = '''define dso_local void @fresh_actor(ptr addrspace(1) %log) {
entry:
 call void @llvm.hivm.SET.FLAG.IMM(i64 3, i64 4, i64 7)
 br label %outer
outer:
 %i = phi i64 [0,%entry], [%inext,%latch]
 br label %inner
inner:
 %j = phi i64 [0,%outer], [%jnext,%inner]
 call void @llvm.hivm.WAIT.FLAG.IMM(i64 3, i64 4, i64 7)
 %jnext = add i64 %j,1
 %jmore = icmp ult i64 %jnext,3
 br i1 %jmore,label %inner,label %latch
latch:
 %inext = add i64 %i,1
 %imore = icmp ult i64 %inext,2
 br i1 %imore,label %outer,label %exit
exit:
 ret void
}
declare void @llvm.hivm.SET.FLAG.IMM(i64,i64,i64)
declare void @llvm.hivm.WAIT.FLAG.IMM(i64,i64,i64)
!hivm.annotations = !{!0}
!0 = !{ptr @fresh_actor, !"kernel", i32 1}
'''


@pytest.mark.parametrize('ir,loop_depths', [(IR, []),
                                            (NESTED_CONTROL_IR, [1, 2])])
def test_control_inventory_matches_actual_encoded_record_sites(
        tmp_path, monkeypatch, ir, loop_depths):
    import re
    monkeypatch.setenv('FLAGPRISM_ASCEND_TRACE_MAX_SITES', '1')
    result, path = execute(tmp_path, 'issue,control_checkpoint', ir)
    assert result.returncode == 0, result.stderr.decode()
    manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
    plan = manifest['control_plan']
    inventory = plan['inventory']
    assert plan['plan_kind'] == 'control' and plan['max_sites'] is None
    assert not plan['operation_max_sites_applies']
    assert plan['candidate_count'] == len(inventory) == 2 + len(loop_depths)
    selected = [site for site in inventory if site['selected']]
    assert plan['selected_count'] == len(selected) == 1 + len(loop_depths)
    assert [
        site['loop_depth'] for site in inventory
        if site['operation_class'] == 'original_loop_header'
    ] == loop_depths
    unselected, = [site for site in inventory if not site['selected']]
    assert unselected['public_semantic'] == 'wait_bracket'
    assert unselected['selection_reason'] == 'semantic_not_requested'
    assert {site['site_id']
            for site in selected
            } == {site['site_id']
                  for site in manifest['dynamic_sites']}
    # Inspect actual appendRecord stores, the field decoded from raw word zero.
    # This is real pass output, not a fabricated dynamic buffer or a GPU claim.
    encoded = {
        int(value)
        for value in re.findall(r'store volatile i64 ([0-9]+),', (
            path / 'adapted.ll').read_text()) if int(value) >= 1 << 32
    }
    codes = {'issue': 1, 'wait_bracket': 2, 'control_checkpoint': 3}
    assert encoded == {
        site['site_id'] | (codes[site['public_semantic']] << 32)
        for site in selected
    }
    assert manifest['observation_plan_version'] == 2
