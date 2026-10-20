"""Semantic faults in the relative native record-tail value flow."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    'gcu_native_values',
    Path(__file__).parents[1] / 'python' / 'flagtree_debugger' /
    'gcu_native_values.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    ops = [
        ('l.sllia', 'r7, r14, 0x7'),
        ('l.addia.u', 'r7, r7, 0x20'),
        ('l.adda.s', 'r7, r7, r20'),
        ('l.ldi16.s', 'r8, 0x4733'),
        ('l.ldi_hi', 'r8, 0x4650'),
        ('l.st.w', 'r8, [r7]'),
        ('l.ldi16.s', 'r8, 0x3fff'),
        ('l.anda', 'r9, r9, r8'),
        ('l.st.w', 'r13, [r7, 0x18]'),
        ('l.st.w', 'r9, [r7, 0x1c]'),
        ('l.st.w', 'r5, [r7, 0x20]'),
        ('l.st.w', 'r5, [r7, 0x4c]'),
    ]
    return [
        dict(pc=16 * i, opcode=op, operands=args)
        for i, (op, args) in enumerate(ops)
    ]


def check(rows):
    return module.check_record_tail(rows,
                                    low_register='r13',
                                    high_register='r9',
                                    identity_register='r5')


def test_relative_fields_with_delayed_mask():
    answer = check(fixture())
    assert answer['reader_to_relative_fields_checked'] is True
    assert answer['field_store_pcs'] == {
        '6': 128,
        '7': 144,
        '8': 160,
        '19': 176
    }
    assert answer['reader_valueflow_qualified'] is False
    assert answer['source_region_qualified'] is False
    assert answer['incoming_begin_site_qualified'] is False


@pytest.mark.parametrize('fault', [
    'wrong_mask',
    'unrelated_low',
    'wrong_identity',
    'wrong_offset',
    'late_overwrite',
    'alias',
    'unknown_instruction',
    'repeated_pc',
    'reordered_pc',
    'large_shift',
    'missing_magic',
    'missing_field',
    'unaligned_overlap',
    'magic_overwrite',
    'signed_immediate',
    'same_packet_raw',
])
def test_semantically_wrong_native_fields_are_rejected(fault):
    rows = fixture()
    if fault == 'wrong_mask': rows[6]['operands'] = 'r8, 0x7fff'
    elif fault == 'unrelated_low': rows[8]['operands'] = 'r12, [r7, 0x18]'
    elif fault == 'wrong_identity': rows[11]['operands'] = 'r6, [r7, 0x4c]'
    elif fault == 'wrong_offset': rows[9]['operands'] = 'r9, [r7, 0x2c]'
    elif fault == 'late_overwrite':
        rows.append(dict(pc=192, opcode='l.st.w', operands='r0, [r7, 0x18]'))
    elif fault == 'alias':
        rows.append(dict(pc=192, opcode='l.st.w', operands='r0, [r21]'))
    elif fault == 'unknown_instruction':
        rows[7]['opcode'] = 'l.jal'
    elif fault == 'repeated_pc':
        rows[7]['pc'] = rows[6]['pc']
    elif fault == 'reordered_pc':
        rows[7]['pc'] = 1
    elif fault == 'large_shift':
        rows[0]['operands'] = 'r7, r14, 0x20'
    elif fault == 'missing_magic':
        rows[4]['operands'] = 'r8, 0x4651'
    elif fault == 'missing_field':
        rows.pop()
    elif fault == 'unaligned_overlap':
        rows.append(dict(pc=192, opcode='l.st.w', operands='r0, [r7, 0x19]'))
    elif fault == 'magic_overwrite':
        rows.append(dict(pc=192, opcode='l.st.w', operands='r0, [r7]'))
    elif fault == 'signed_immediate':
        rows[6]['operands'] = 'r8, 0xffff'
    elif fault == 'same_packet_raw':
        rows[7]['pc'] = rows[6]['pc'] + 4
    match = 'Native immediate range' if fault == 'signed_immediate' else None
    with pytest.raises(ValueError, match=match):
        check(rows)


def test_mask_after_identity_store_and_register_renaming():
    rows = fixture()
    rows[6:11] = [rows[10], rows[6], rows[7], rows[8], rows[9]]
    for i, row in enumerate(rows):
        row['pc'] = i * 16
        row['operands'] = row['operands'].replace('r13', 'r23').replace(
            'r9', 'r19').replace('r5', 'r25')
    answer = module.check_record_tail(rows,
                                      low_register='r23',
                                      high_register='r19',
                                      identity_register='r25')
    assert answer['reader_to_relative_fields_checked'] is True
