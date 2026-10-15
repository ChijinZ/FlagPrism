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
    if semantics is None:
        env.pop('FLAGPRISM_ASCEND_TRACE_SEMANTICS', None)
    else:
        env['FLAGPRISM_ASCEND_TRACE_SEMANTICS'] = semantics
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
    if not timestamps:
        assert 'store volatile' not in text


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


def test_control_inventory_preserves_original_unnamed_blocks(tmp_path):
    ir = NESTED_CONTROL_IR
    for name, number in [('entry', 0), ('outer', 1), ('inner', 2),
                         ('latch', 3), ('exit', 4)]:
        ir = ir.replace(name + ':',
                        str(number) + ':').replace('%' + name,
                                                   '%' + str(number))
    result, path = execute(tmp_path, 'issue,wait_bracket,control_checkpoint',
                           ir)
    assert result.returncode == 0, result.stderr.decode()
    manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
    original = manifest['actors'][0]['loops']
    inventory = [
        item for item in manifest['control_plan']['inventory']
        if item['operation_class'] == 'original_loop_header'
    ]
    assert [item['block']
            for item in inventory] == [item['header'] for item in original]
    assert [item['loop_blocks']
            for item in inventory] == [item['blocks'] for item in original]
    assert all(item['block_representation'] ==
               'original_pre_instrumentation_canonical_llvm'
               for item in inventory)


@pytest.mark.parametrize('kind,slots', [('AIC', [0]), ('AIV', [1, 2])])
def test_binding_describes_actual_emitted_actor_value(tmp_path, kind, slots):
    result, path = execute(tmp_path, 'issue', actor_kind=kind)
    assert result.returncode == 0, result.stderr.decode()
    manifest, = [json.loads(p.read_text()) for p in path.glob('*.json')]
    binding = manifest['runtime_actor_binding']
    assert binding['admissible_slots'] == slots
    assert binding['function'] == 'fresh_actor'
    assert binding['module_sha256'] == manifest['module_sha256']
    assert binding['segment_words'] == 132
    text = (path / 'adapted.ll').read_text()
    if kind == 'AIV':
        import re
        call, = re.findall(
            r'(%[\w.]+) = call i64 @llvm.hivm.GET.SUBBLOCKID\(\)', text)
        actor, = re.findall(r'(%[\w.]+) = add i64 ' + re.escape(call) + r', 1',
                            text)
        assert re.search(r'mul i64 ' + re.escape(actor) + r', 132', text)
        assert re.search(r'store volatile i64 ' + re.escape(actor) + r',',
                         text)
        assert binding['expression'] == {
            'kind': 'add_i64',
            'call': 'llvm.hivm.GET.SUBBLOCKID',
            'constant': 1
        }
    else:
        assert '@llvm.hivm.GET.SUBBLOCKID' not in text
        assert 'store volatile i64 0,' in text
        assert binding['expression'] == {'kind': 'constant_i64', 'value': 0}


@pytest.mark.parametrize('kind,slot', [('AIC', 0), ('AIV', 1), ('AIV', 2)])
def test_real_pass_manifest_binds_cpu_record_fixture(tmp_path, monkeypatch,
                                                     kind, slot):
    """Real opt emission plus synthetic protocol record; no device claim."""
    import hashlib
    import importlib.util
    from pathlib import Path
    import sys
    import types
    monkeypatch.setenv('FLAGPRISM_ASCEND_COMPILE_ID', 'actual_opt_unit')
    result, path = execute(tmp_path, 'issue', actor_kind=kind)
    assert result.returncode == 0, result.stderr.decode()
    manifest_path, = list(path.glob('*.json'))
    manifest_text = manifest_path.read_text()
    manifest = json.loads(manifest_text)
    original = manifest_path.with_suffix('.ll').read_text()
    adapted = (path / 'adapted.ll').read_text()

    def digest(text):
        return hashlib.sha256(text.encode()).hexdigest()

    handoff = {
        'compile_id':
        'actual_opt_unit',
        'artifacts': [{
            'metadata': manifest,
            'manifest_text': manifest_text,
            'manifest_sha256': digest(manifest_text),
            'llir': original,
            'sha256': digest(original),
            'adapted': {
                'llir': adapted,
                'sha256': digest(adapted)
            }
        }]
    }
    package = types.ModuleType('_real_ascend_binding_test')
    package.__path__ = [
        str(Path(__file__).parents[1] / 'python/flagtree_profiler')
    ]
    sys.modules[package.__name__] = package
    modules = []
    for name in ('ascend_actor_binding', 'observations_ascend'):
        spec = importlib.util.spec_from_file_location(
            package.__name__ + '.' + name,
            Path(package.__path__[0]) / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    helper, decoder = modules
    sites = helper.bind_compiler_sites(handoff, require_binding=True)
    words = [0] * (3 * 132)
    words[slot * 132:slot * 132 + 12] = [
        1, 1, 1, 0, (1 << 32), 0, 100, 110, 0, slot, (1 << 64) - 1,
        (1 << 64) - 1
    ]
    event, = decoder.decode_dynamic64(
        words,
        capacity=16,
        capture_id='cpu_fixture',
        site_manifest=sites,
        require_actor_binding=True)['observations']
    assert event['compiler_site']['compiler_actor']['module_sha256'] == digest(
        original)
    assert event['compiler_site']['compiler_actor']['binding_proof'][
        'observed_actor_slot'] == slot
    (path / 'cpu-record-projection.json').write_text(
        json.dumps(
            {
                'evidence_kind': 'real_opt_manifest_plus_synthetic_cpu_record',
                'hardware_execution_claim': False,
                'compiler_actor': event['compiler_site']['compiler_actor'],
                'actor_slot': event['actor_slot'],
                'compiler_actor_status': event['compiler_actor_status']
            },
            indent=2))
