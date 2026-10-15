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


def execute(tmp_path, semantics, ir=IR):
    plugin = os.environ.get('FLAGPRISM_ASCEND_LATE_PLUGIN')
    if not plugin:
        pytest.skip('requires the actual built upstream LLVM15 plugin')
    tmp_path.mkdir(exist_ok=True)
    source = tmp_path / 'input.ll'
    source.write_text(ir)
    env = dict(os.environ,
               FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(tmp_path),
               FLAGPRISM_ASCEND_ACTOR_KIND='AIC',
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
