"""Semantic and rejection tests for the finite LLVM State address checker."""
import importlib.util
from pathlib import Path
import sys
import pytest

spec = importlib.util.spec_from_file_location(
    'ascend_state_check',
    Path(__file__).with_name('ascend_state_writer_partition.py'))
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


def sample(*,
           predicate='true',
           offset='%id',
           size='1',
           stride='1',
           suffix='',
           body=''):
    return '''define dso_local void @independent(ptr addrspace(1) %state, i32 %gx, i32 %gy, i32 %gz) {
  %id = call i64 @llvm.hivm.GET.BLOCK.IDX()
  %sub = call i64 @llvm.hivm.GET.SUBBLOCKID()
  %only = icmp eq i64 %sub, 0
''' + body + '''
  br i1 ''' + predicate + ''', label %write, label %done
write:
  call void @store_ubuf_to_gm_1d_int32_t(ptr addrspace(6) null, ptr addrspace(6) null, i64 0, i64 ''' + size + ''', i64 1, ptr addrspace(1) %state, ptr addrspace(1) %state, i64 ''' + offset + ''', i64 ''' + size + ''', i64 ''' + stride + ''', i32 0)
''' + suffix + '''
  br label %done
done:
  ret void
}'''


def run(text, *, actors=1, grid=(3, ), elements=3):
    return checker.analyze(text,
                           state_parameter='%state',
                           grid_parameters=('%gx', '%gy', '%gz'),
                           grid=grid,
                           subblocks=actors,
                           elements=elements)


def test_scalar_partition():
    assert run(sample())['element_writers'] == {0: 1, 1: 1, 2: 1}


def test_readonly_counter_preserves_state_partition():
    answer = run(
        sample(body='  %tick = call i64 asm sideeffect '
               '"MOV $0, SYS_CNT", "=l"()'))
    if answer['element_writers'] != {0: 1, 1: 1, 2: 1}:
        raise AssertionError(answer)


@pytest.mark.parametrize('assembly', [
    '"MOV $0, SYS_CNT", "=l,~{memory}"()',
    '"MOV $0, SYS_CNT; ST x0, [x1]", "=l"()',
    '"MOV $0, SYS_CNT", "=l,l"(i64 0)',
])
def test_counter_does_not_admit_other_assembly(assembly):
    with pytest.raises(ValueError, match='Unsupported indirect call'):
        run(sample(body='  %tick = call i64 asm sideeffect ' + assembly))


def test_clock_does_not_become_a_known_state_offset():
    with pytest.raises(ValueError, match='Unmodeled scalar call result'):
        run(
            sample(body='  %tick = call i64 asm sideeffect '
                   '"MOV $0, SYS_CNT", "=l"()',
                   offset='%tick'))


def test_assembly_comment_cannot_impersonate_a_direct_call():
    with pytest.raises(ValueError, match='Unsupported indirect call'):
        run(
            sample(body='  call void asm sideeffect "/* @fake() */", '
                   '"l"(ptr addrspace(1) %state)'))


def test_exact_empty_source_marker_preserves_partition():
    text = ('  call void asm sideeffect '
            '"/* flagprism.source_census_site.v3:7:2:8 */", '
            '"l,l,l,l,l,l"(i64 0, i64 0, i64 0, i64 0, i64 0, i64 0)')
    answer = run(sample(body=text))
    if answer['element_writers'] != {0: 1, 1: 1, 2: 1}:
        raise AssertionError(answer)
    for changed in [
            text.replace(' */', ' */ MOV x0, x1'),
            text.replace('"l,l,l,l,l,l"', '"l,l,l,l,l,l,~{memory}"'),
    ]:
        with pytest.raises(ValueError, match='Unsupported indirect call'):
            run(sample(body=changed))
    with pytest.raises(ValueError, match='Source marker operand ABI'):
        run(sample(body=text.replace('i64 0, i64 0)', 'i64 0)')))


def test_selected_actor():
    assert run(sample(predicate='%only'), actors=2)['element_writers'] == {
        0: 1,
        1: 1,
        2: 1
    }


def test_two_actor_disjoint_offsets():
    text = sample(
        offset='%offset',
        body='  %start = mul i64 %id, 2\n  %offset = add i64 %start, %sub')
    assert run(text, actors=2, elements=6)['element_writers'] == {
        n: 1
        for n in range(6)
    }


def test_integer_signed_widths():
    text = sample(
        offset='%offset',
        body=
        '  %negative = sext i8 -1 to i64\n  %one = sub i64 0, %negative\n  %offset = mul i64 %id, %one'
    )
    assert run(text)['element_writers'] == {0: 1, 1: 1, 2: 1}


def test_unrelated_loop_does_not_repeat_state():
    text = sample().replace(
        '  br i1 true, label %write, label %done', '''  br label %loop
loop:
  %n = phi i32 [ 0, %0 ], [ %next, %loop ]
  %next = add i32 %n, 1
  %again = icmp slt i32 %next, 7
  br i1 %again, label %loop, label %write''')
    assert run(text)['element_writers'] == {0: 1, 1: 1, 2: 1}


@pytest.mark.parametrize('text,actors,elements,reason', [
    (sample(), 2, 3, 'Overlapping'),
    (sample(offset='%sub'), 1, 3, 'Overlapping'),
    (sample(offset='3'), 1, 3, 'exceeds'),
    (sample(size='2'), 1, 3, 'Overlapping'),
    (sample(stride='0'), 1, 3, 'stride'),
    (sample(size='-1'), 1, 3, 'extent'),
    (sample(body='  %unknown = load i1, ptr addrspace(1) %state',
            predicate='%unknown'), 1, 3, 'bypassed'),
    (sample().replace('  br label %done\ndone:',
                      '  br label %write\ndone:'), 1, 3, 'No reachable'),
    (sample().replace('i32 0)', 'i32 1)'), 1, 3, 'mode'),
    (sample(body='  call void @unknown(ptr addrspace(1) %state)'), 1, 3,
     'Unmodeled call'),
    (sample(body='  %bad = load ptr addrspace(1), ptr addrspace(1) %state'), 1,
     3, 'pointer'),
    (sample(body='  %bad = inttoptr i64 42 to ptr addrspace(1)'), 1, 3,
     'pointer'),
    (sample(
        offset='%bad',
        body='  %small = add nsw i8 127, 1\n  %bad = sext i8 %small to i64'),
     1, 3, 'poison'),
    (sample(offset='%bad', body='  %bad = sdiv i64 1, 0'), 1, 3, 'division'),
    (sample(offset='%bad',
            body='  %bad = call i64 @unknown()'), 1, 3, 'Unmodeled integer'),
    (sample(offset='%bad',
            body='  %bad = mul i64 %undefined, 2'), 1, 3, 'Unknown'),
])
def test_reject(text, actors, elements, reason):
    with pytest.raises(ValueError, match=reason):
        run(text, actors=actors, elements=elements)


def test_two_dimensional_strides_and_actors():
    text = '''define dso_local void @matrix_range(ptr addrspace(1) %state, i32 %gx, i32 %gy, i32 %gz) {
  %sub = call i64 @llvm.hivm.GET.SUBBLOCKID()
  %offset = mul i64 %sub, 4
  call void @store_ubuf_to_gm_2d_int32_t(ptr addrspace(6) null, ptr addrspace(6) null, i64 0, i64 2, i64 2, i64 2, i64 1, ptr addrspace(1) %state, ptr addrspace(1) %state, i64 %offset, i64 2, i64 2, i64 2, i64 1, i32 0)
  ret void
}'''
    assert run(text, grid=(1, ), actors=2, elements=8)['element_writers'] == {
        n: 1
        for n in range(8)
    }


def test_nonwriting_actor():
    text = '''define dso_local void @cube(ptr addrspace(1) %state, i32 %gx, i32 %gy, i32 %gz) {
  ret void
}'''
    assert run(text)['element_writers'] == {}


def test_pointer_gep_origin():
    text = sample(
        body='  %alias = getelementptr i32, ptr addrspace(1) %state, i64 0')
    text = text.replace(
        'ptr addrspace(1) %state, ptr addrspace(1) %state, i64 %id',
        'ptr addrspace(1) %alias, ptr addrspace(1) %alias, i64 %id')
    assert run(text)['element_writers'] == {0: 1, 1: 1, 2: 1}


@pytest.mark.parametrize('operation', [
    '%old = atomicrmw add ptr addrspace(1) %state, i32 1 monotonic',
    '%pair = cmpxchg ptr addrspace(1) %state, i32 0, i32 1 monotonic monotonic',
])
def test_unmodeled_state_write_rejected(operation):
    with pytest.raises(ValueError, match='Unmodeled instruction'):
        run(sample(body='  ' + operation))


def test_known_poison_branch_is_not_unknown():
    text = sample(
        body='  %small = add nsw i8 127, 1\n  %poison = icmp eq i8 %small, 0')
    text = text.replace(
        '  br i1 true, label %write, label %done',
        '  br i1 %poison, label %left, label %right\nleft:\n  br label %write\nright:\n  br label %write'
    )
    with pytest.raises(ValueError, match='poison'):
        run(text)


@pytest.mark.parametrize('distance,valid', [(3, True), (4, False)])
def test_intermediate_inbounds_pointer(distance, valid):
    body = f'  %past = getelementptr inbounds i32, ptr addrspace(1) %state, i64 {distance}\n  %alias = getelementptr i32, ptr addrspace(1) %past, i64 -{distance}'
    text = sample(body=body).replace(
        'ptr addrspace(1) %state, ptr addrspace(1) %state, i64 %id',
        'ptr addrspace(1) %alias, ptr addrspace(1) %alias, i64 %id')
    if valid:
        assert run(text)['element_writers'] == {0: 1, 1: 1, 2: 1}
    else:
        with pytest.raises(ValueError, match='inbounds'):
            run(text)


def test_ub_constant_pointer_is_not_constructed_gm_pointer():
    text = sample().replace(
        'ptr addrspace(6) null',
        'ptr addrspace(6) inttoptr (i64 128 to ptr addrspace(6))')
    assert run(text)['element_writers'] == {0: 1, 1: 1, 2: 1}


def test_inbounds_cannot_return_from_outside_allocation():
    text = sample(
        body=
        '  %outside = getelementptr i32, ptr addrspace(1) %state, i64 4\n  %alias = getelementptr inbounds i32, ptr addrspace(1) %outside, i64 -4'
    )
    text = text.replace(
        'ptr addrspace(1) %state, ptr addrspace(1) %state, i64 %id',
        'ptr addrspace(1) %alias, ptr addrspace(1) %alias, i64 %id')
    with pytest.raises(ValueError, match='inbounds'):
        run(text)


def test_constructed_gm_constant_expression_rejected():
    text = sample(
        body=
        '  call void @unknown(ptr addrspace(1) inttoptr (i64 42 to ptr addrspace(1)))'
    )
    with pytest.raises(ValueError, match='pointer'):
        run(text)


@pytest.mark.parametrize('replacement',
                         ['i64 0, i64 2, i64 1', 'i64 0, i64 1, i64 0'])
def test_source_descriptor_contract(replacement):
    text = sample().replace('i64 0, i64 1, i64 1, ptr addrspace(1)',
                            replacement + ', ptr addrspace(1)', 1)
    with pytest.raises(ValueError, match='source transfer'):
        run(text)
