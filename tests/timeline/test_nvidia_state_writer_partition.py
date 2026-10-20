"""Counterexamples for the finite physical State partition checker."""
import pytest
from nvidia_state_writer_partition import partition


def program(body, threads=4):
    return '''.visible .entry partition_test(
.param .u64 .ptr .global .align 4 partition_test_param_0
)
.reqntid %d
{
.reg .b32 %%r<12>;
.reg .b64 %%rd<5>;
.reg .pred %%p<3>;
ld.param.b64 %%rd1, [partition_test_param_0];
mov.u32 %%r1, %%tid.x;
mov.u32 %%r2, %%ctaid.x;
%s
ret;
}
''' % (threads, body)


SCALAR = '''mad.lo.u32 %r3, %r2, 4, %r1;
mul.wide.u32 %rd2, %r3, 4;
add.u64 %rd3, %rd1, %rd2;
st.global.b32 [%rd3 + 0], {%r1};'''


def check(text, elements=4, grid=(1, )):
    return partition(text,
                     state_argument=0,
                     threads=4,
                     grid=grid,
                     elements=elements)


def test_scalar_partition():
    assert check(program(SCALAR))['unique_writers'] == 4


def test_vector_store_width():
    body = SCALAR.replace('4;\nadd.u64', '16;\nadd.u64').replace(
        'st.global.b32 [%rd3 + 0], {%r1};',
        'st.global.v4.b32 [%rd3 + 0], {%r1, %r1, %r1, %r1};')
    assert check(program(body), elements=16)['unique_writers'] == 16


def test_tail_and_two_programs():
    body = SCALAR.replace('st.global.b32',
                          'setp.lt.u32 %p1, %r3, 3;\n@%p1 st.global.b32')
    assert check(program(body), elements=3, grid=(2, ))['unique_writers'] == 3


def test_reduction_one_writer_per_program():
    body = SCALAR.replace('mad.lo.u32 %r3, %r2, 4, %r1;',
                          'mov.u32 %r3, %r2;').replace(
                              'st.global.b32',
                              'setp.eq.u32 %p1, %r1, 0;\n@%p1 st.global.b32')
    assert check(program(body), elements=3, grid=(3, ))['unique_writers'] == 3


@pytest.mark.parametrize('body,elements,message', [
    (SCALAR, 3, 'guard/tail'),
    (SCALAR.replace(
        'st.global.b32',
        'mov.u32 %r4, -1;\nsetp.ne.b32 %p1, %r4, -1;\n@%p1 st.global.b32'), 4,
     'missing'),
    (SCALAR.replace('mul.wide.u32 %rd2, %r3, 4;',
                    'mov.u64 %rd2, 0;'), 4, 'duplicate'),
    (SCALAR.replace(
        'st.global.b32',
        'setp.eq.u32 %p1, %r1, 9;\n@%p1 st.global.b32'), 4, 'missing'),
    (SCALAR.replace('add.u64 %rd3', 'add.u32 %rd3'), 4, 'pointer arithmetic'),
    (SCALAR.replace('mul.wide.u32 %rd2, %r3, 4;',
                    'ld.global.b32 %r3, [%rd1];\nmul.wide.u32 %rd2, %r3, 4;'),
     4, 'Unsupported State cone'),
    ('setp.eq.u32 %p1, %r1, 0;\n@%p1 bra done;\n' + SCALAR + '\ndone:', 4,
     'bypassed'),
    ('again:\n' + SCALAR + '\nsetp.eq.u32 %p1, %r1, 0;\n@%p1 bra again;', 4,
     'inside a loop'),
    (SCALAR.replace(
        'mul.wide.u32',
        'setp.eq.u32 %p1, %r1, 0;\n@%p1 bra target;\nmov.u32 %r3, 0;\ntarget:\nmul.wide.u32'
    ), 4, 'definition'),
])
def test_unsafe_partition_rejected(body, elements, message):
    with pytest.raises(ValueError, match=message):
        check(program(body), elements=elements)


def test_thread_geometry_bound_to_ptx():
    with pytest.raises(ValueError, match='geometry'):
        check(program(SCALAR, threads=8))


@pytest.mark.parametrize('body,message', [
    ('mov.u32 %r3, %r1;\nbra later;\ntarget:\nmul.wide.u32 %rd2, %r3, 4;\nadd.u64 %rd3, %rd1, %rd2;\nst.global.b32 [%rd3 + 0], {%r1};\nret;\nlater:\nmov.u32 %r3, 0;\nbra target;',
     'duplicate'),
    ('setp.lt.u32 %p1, %r1, 4;\nbra later;\ntarget:\n' +
     SCALAR.replace('st.global.b32', '@%p1 st.global.b32') +
     '\nret;\nlater:\nsetp.lt.u32 %p1, %r1, 0;\nbra target;', 'missing'),
    (SCALAR.replace('mad.lo.u32 %r3, %r2, 4, %r1;',
                    'mul.hi.u32 %r3, %r1, 1;'), 'Unsupported'),
    (SCALAR.replace(
        'st.global.b32',
        'mov.pred %p2, 0;\nsetp.lt.and.u32 %p1, %r3, 4, %p2;\n@%p1 st.global.b32'
    ), 'Unsupported'),
    (SCALAR.replace(
        'st.global.b32',
        'setp.lt.u32 %p1|%p2, %r3, 4;\n@%p2 st.global.b32'), 'Unsupported'),
    (SCALAR.replace(
        'mad.lo.u32 %r3, %r2, 4, %r1;',
        'shr.u32 %r4, -1, 31;\nadd.u32 %r3, %r1, %r4;\nadd.u32 %r3, %r3, 1;'),
     'guard/tail'),
    ('mul.wide.u32 %rd2, -1, 1;\nadd.u64 %rd2, %rd2, 1;\nmul.wide.u32 %rd4, %r1, 4;\nadd.u64 %rd2, %rd2, %rd4;\nadd.u64 %rd3, %rd1, %rd2;\nst.global.b32 [%rd3 + 0], {%r1};',
     'guard/tail'),
])
def test_control_and_typed_semantic_false_passes_rejected(body, message):
    with pytest.raises(ValueError, match=message):
        check(program(body))


def test_predicated_non_state_pointer_does_not_hide_old_state_pointer():
    body = SCALAR + '''
ld.param.b64 %rd2, [partition_test_param_1];
mov.b64 %rd4, %rd1;
setp.eq.u32 %p1, %r1, 99;
@%p1 mov.b64 %rd4, %rd2;
st.global.b32 [%rd4 + 0], {%r1};
'''
    text = program(body).replace(
        'partition_test_param_0\n',
        'partition_test_param_0,\n.param .u64 .ptr .global .align 4 partition_test_param_1\n'
    )
    with pytest.raises(ValueError, match='reaching'):
        check(text)
