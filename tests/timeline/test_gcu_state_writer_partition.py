"""Finite GCU State address/CFG checks, including semantic rejection cases."""
import importlib.util
from pathlib import Path
import sys
import pytest

spec = importlib.util.spec_from_file_location(
    'gcu_state_check',
    Path(__file__).with_name('gcu_state_writer_partition.py'))
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


def sample(*,
           predicate='%only',
           offset='%offset',
           length='4',
           body='',
           extra='',
           primitive=None):
    call = primitive or f'call void @tops_memcpy_async(ptr %tag, ptr %dest, ptr %local, i32 {length})'
    return '''define void @anonymous(ptr %state, ptr %tag) {
  %block = call i32 @tops_get_block_id(i32 0)
  %thread = call i32 @tops_get_thread_id(i32 0)
  %only = icmp eq i32 %thread, 0
  %local = call ptr @tops_get_local_memory()
  %wide = sext i32 %block to i64
  %offset = mul i64 %wide, 4
  %base = ptrtoint ptr %state to i64
  %address = add i64 %base, ''' + offset + '''
  %dest = inttoptr i64 %address to ptr
''' + body + '''
  br i1 ''' + predicate + ''', label %write, label %done
write:
  ''' + call + '''
''' + extra + '''
  br label %done
done:
  ret void
}'''


def run(text, **kwargs):
    return checker.analyze(text,
                           state_parameter='%state',
                           grid=kwargs.get('grid', (3, )),
                           threads=kwargs.get('threads', 4),
                           elements=kwargs.get('elements', 3))


def test_scalar_physical_thread_zero():
    assert run(sample())['element_writers'] == {0: 1, 1: 1, 2: 1}


def test_two_dimensional_physical_grid():
    text = sample(
        body=
        '  %by = call i32 @tops_get_block_id(i32 1)\n  %row = mul i32 %by, 3\n  %linear = add i32 %row, %block\n  %linear64 = sext i32 %linear to i64\n  %off = mul i64 %linear64, 4'
    ).replace('  %address = add i64 %base, %offset\n', '').replace(
        '  %dest = inttoptr i64 %address to ptr\n', ''
    ).replace(
        '  br i1 %only,',
        '  %address = add i64 %base, %off\n  %dest = inttoptr i64 %address to ptr\n  br i1 %only,'
    )
    assert run(text, grid=(3, 2), elements=6)['element_writers'] == {
        i: 1
        for i in range(6)
    }


@pytest.mark.parametrize('text,reason', [
    (sample(predicate='true'), 'Overlapping'),
    (sample(offset='0'), 'Overlapping'),
    (sample(offset='12'), 'exceeds'),
    (sample(length='3'), 'extent'),
    (sample(length='-4'), 'extent'),
    (sample(predicate='%unknown',
            body='  %unknown = load i1, ptr %state'), 'bypassed'),
    (sample(body='  %old = atomicrmw add ptr %state, i32 1 monotonic'),
     'Unmodeled State'),
    (sample(body='  call void @unknown(ptr %state)'),
     'Unmodeled State callee'),
    (sample(body='  store ptr %state, ptr %tag'), 'escapes'),
    (sample().replace('  br label %done\ndone:',
                      '  br label %write\ndone:'), 'No reachable'),
    (sample(
        body='  %small = add nsw i8 127, 1\n  %bad = icmp eq i8 %small, 0'
    ).replace(
        '  br i1 %only, label %write, label %done',
        '  br i1 %bad, label %left, label %right\nleft:\n  br label %write\nright:\n  br label %write'
    ), 'Poison'),
])
def test_reject(text, reason):
    with pytest.raises(ValueError, match=reason):
        run(text)


def test_deslice_one_dimension_clips_tail():
    text = sample(
        offset='0',
        body='  %chunk = mul i32 %thread, 2',
        predicate='true',
        primitive=
        'call void @tops_deslice_async_1_si32(ptr %tag, ptr %dest, i32 7, ptr %local, i32 2, i32 %chunk)'
    )
    assert run(text, grid=(1, ), elements=7)['element_writers'] == {
        i: 1
        for i in range(7)
    }


def test_slice_deslice_destination_clipping_with_valid_source():
    text = sample(
        offset='0',
        primitive=
        'call void @tops_slice_deslice_async_1_si32(ptr %tag, ptr %dest, i32 3, ptr %local, i32 5, i32 1, i32 5, i32 0)'
    )
    assert run(text, grid=(1, ), elements=3)['element_writers'] == {
        0: 1,
        1: 1,
        2: 1
    }


def test_deslice_two_dimensions():
    text = sample(
        offset='0',
        primitive=
        'call void @tops_deslice_async_2_si32(ptr %tag, ptr %dest, i32 2, i32 3, ptr %local, i32 2, i32 2, i32 0, i32 1)'
    )
    assert run(text, grid=(1, ), elements=6)['element_writers'] == {
        1: 1,
        2: 1,
        4: 1,
        5: 1
    }


def test_slice_deslice_two_dimensions():
    text = sample(
        offset='0',
        primitive=
        'call void @tops_slice_deslice_async_2_si32(ptr %tag, ptr %dest, i32 2, i32 3, ptr %local, i32 2, i32 4, i32 0, i32 1, i32 2, i32 3, i32 0, i32 0)'
    )
    assert run(text, grid=(1, ), elements=6)['element_writers'] == {
        i: 1
        for i in range(6)
    }


@pytest.mark.parametrize('primitive,reason', [
    ('call void @tops_deslice_async_1_si32(ptr %tag, ptr %dest, i32 3, ptr %local, i32 2, i32 4)',
     'window origin'),
    ('call void @tops_slice_deslice_async_1_si32(ptr %tag, ptr %dest, i32 3, ptr %local, i32 2, i32 1, i32 3, i32 0)',
     'source window'),
    ('call void @tops_deslice_async_2_si32(ptr %tag, ptr %dest, i32 2, i32 3, ptr %local, i32 2, i32 3, i32 0, i32 1)',
     'Unclipped'),
])
def test_no_invented_clip_or_negative_noop(primitive, reason):
    with pytest.raises(ValueError, match=reason):
        run(sample(offset='0', primitive=primitive), grid=(1, ), elements=6)


def test_padding_read_is_not_a_state_writer():
    text = sample(
        body=
        '  call void @tops_slice_pad_async_1_si32(ptr %tag, ptr %local, i32 1, ptr %state, i32 3, i32 0, i32 1, i32 0)'
    )
    assert run(text)['element_writers'] == {0: 1, 1: 1, 2: 1}


def test_padding_destination_not_assumed_readonly():
    text = sample(
        body=
        '  call void @tops_slice_pad_async_1_si32(ptr %tag, ptr %state, i32 3, ptr %local, i32 3, i32 0, i32 3, i32 0)'
    )
    with pytest.raises(ValueError, match='destination transfer'):
        run(text)


def test_unknown_constant_pointer_cannot_hide_alias():
    text = sample(
        body='  %unknown = inttoptr i64 42 to ptr\n  store i32 1, ptr %unknown'
    )
    with pytest.raises(ValueError, match='formal origin'):
        run(text)


def test_signed_remainder_overflow_is_poison():
    text = sample(offset='%off', body='').replace(
        '  %address = add i64 %base, %off',
        '  %bad = srem i64 -9223372036854775808, -1\n  %off = add i64 %offset, %bad\n  %address = add i64 %base, %off'
    )
    with pytest.raises(ValueError, match='Poison'):
        run(text)


@pytest.mark.parametrize('body,reason', [
    ('  %hidden = call ptr @unknown()', 'pointer-returning'),
    ('  %hidden = load ptr, ptr %tag', 'external formal'),
])
def test_unknown_pointer_alias_not_ignored(body, reason):
    with pytest.raises(ValueError, match=reason):
        run(sample(body=body))


@pytest.mark.parametrize('body', [
    '  store i32 1, ptr inttoptr (i64 4096 to ptr)',
    '  call void @unknown(ptr inttoptr (i64 4096 to ptr))',
])
def test_inline_constant_pointer_cannot_hide_alias(body):
    with pytest.raises(ValueError, match='constant-expression'):
        run(sample(body=body))


@pytest.mark.parametrize('body,reason', [
    ('  %hidden = load volatile ptr, ptr %tag\n  store i32 1, ptr %hidden',
     'external formal'),
    ('  %hidden = call noundef ptr @unknown()\n  store i32 1, ptr %hidden',
     'pointer-returning'),
])
def test_pointer_modifiers_cannot_hide_alias(body, reason):
    with pytest.raises(ValueError, match=reason):
        run(sample(body=body))
