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


def reader_fixture():
    ops = [
        ('l.ld.w', 'r7, [r16]'),
        ('c.li', 'r5, 0x4'),
        ('l.adda.u', 'r5, r16, r5'),
        ('l.ld.w', 'r9, [r5]'),
        ('l.ld.w', 'r13, [r16]'),
        ('l.bge.u', 'r13, r7, 0x3 <0x80>'),
        ('l.ld.w', 'r9, [r5]'),
        ('l.ld.w', 'r13, [r16]'),
        ('l.movs', 'r5, sipinfo'),
    ]
    return [
        dict(pc=16 * i + 10, opcode=op, operands=args)
        for i, (op, args) in enumerate(ops)
    ]


def test_inline_counter_registers_are_inferred():
    row = module.inspect_inline_reader(reader_fixture(), marker_packet=0)
    assert (row['low_register'], row['high_register'],
            row['identity_register']) == ('r13', 'r9', 'r5')
    assert row['sample_pcs'] == [10, 58, 74, 106, 122]
    assert row['mmio_base_qualified'] is False
    assert row['external_entries_qualified'] is False
    assert row['reader_valueflow_qualified'] is False
    changed = reader_fixture()
    for r in changed:
        r['operands'] = r['operands'].replace('r13', 'r23').replace(
            'r9', 'r19').replace('r5', 'r25')
    answer = module.inspect_inline_reader(changed, marker_packet=0)
    assert answer['low_register'] == 'r23' and answer['high_register'] == 'r19'


@pytest.mark.parametrize('fault', [
    'high_offset',
    'wrong_comparison',
    'wrong_branch_direction',
    'wrong_reread_address',
    'wrong_reread_dest',
    'missing_load',
    'bad_target',
    'identity_clobbers_low',
    'unknown_instruction',
    'same_packet_raw',
    'post_reread_overwrite',
    'fast_high_overwrite',
])
def test_incomplete_or_corrupt_inline_reader_is_rejected(fault):
    rows = reader_fixture()
    if fault == 'high_offset': rows[1]['operands'] = 'r5, 0x8'
    elif fault == 'wrong_comparison':
        rows[5]['operands'] = 'r7, r13, 0x3 <0x80>'
    elif fault == 'wrong_branch_direction':
        rows[5]['opcode'] = 'l.blt.u'
    elif fault == 'wrong_reread_address':
        rows[6]['operands'] = 'r9, [r16]'
    elif fault == 'wrong_reread_dest':
        rows[6]['operands'] = 'r10, [r5]'
    elif fault == 'missing_load':
        rows.pop(6)
    elif fault == 'bad_target':
        rows[5]['operands'] = 'r13, r7, 0x2 <0x70>'
    elif fault == 'identity_clobbers_low':
        rows[8]['operands'] = 'r13, sipinfo'
    elif fault == 'unknown_instruction':
        rows[2]['opcode'] = 'l.jal'
    elif fault == 'same_packet_raw':
        rows[2]['pc'] = rows[1]['pc'] + 4
    elif fault == 'post_reread_overwrite':
        rows.insert(8, dict(pc=128, opcode='c.li', operands='r13, 0x0'))
        rows[-1]['pc'] += 16
        rows[5]['operands'] = 'r13, r7, 0x4 <0x90>'
    elif fault == 'fast_high_overwrite':
        rows.insert(4, dict(pc=64, opcode='c.li', operands='r9, 0x0'))
    with pytest.raises(ValueError):
        module.inspect_inline_reader(rows, marker_packet=0)


def combined_fixture():
    rows = reader_fixture()
    tail = fixture()
    for row in tail:
        row['pc'] += 256
    return rows + tail


def test_inferred_reader_values_reach_record_fields():
    row = module.inspect_inline_record_fields(combined_fixture(),
                                              marker_packet=0,
                                              tail_start_pc=256,
                                              tail_end_pc=432)
    assert row['reader_outputs_inferred'] is True
    assert row['reader_bridge_registers_preserved'] is True
    assert row['reader_to_relative_fields_checked'] is True
    assert row['record_path_selection_qualified'] is False
    assert row['tail_boundaries_automatically_selected'] is False


@pytest.mark.parametrize('fault',
                         ['overwrite', 'call', 'backedge', 'tail_entry'])
def test_reader_to_record_bridge_cannot_change_outputs(fault):
    rows = combined_fixture()
    if fault == 'overwrite':
        extra = dict(pc=160, opcode='c.li', operands='r13, 0x0')
    elif fault == 'call':
        extra = dict(pc=160, opcode='l.jal', operands='lr, 0x0 <0x200>')
    elif fault == 'backedge':
        extra = dict(pc=160, opcode='l.beq', operands='r7, r0, 0x0 <0x80>')
    else:
        extra = dict(pc=160, opcode='l.beq', operands='r7, r0, 0x0 <0x120>')
    rows.insert(9, extra)
    with pytest.raises(ValueError):
        module.inspect_inline_record_fields(rows,
                                            marker_packet=0,
                                            tail_start_pc=256,
                                            tail_end_pc=432)


def test_fast_path_cannot_inherit_fallback_only_zero():
    rows = reader_fixture()
    rows[5]['operands'] = 'r13, r7, 0x5 <0xa0>'
    rows[8:] = [
        dict(pc=138, opcode='c.li', operands='r8, 0x0'),
        dict(pc=170, opcode='l.adda.u', operands='r13, r13, r8'),
        dict(pc=186, opcode='l.movs', operands='r5, sipinfo')
    ]
    with pytest.raises(ValueError, match='Reader output register'):
        module.inspect_inline_reader(rows, marker_packet=0)


def test_record_block_is_selected_without_tail_addresses():
    answer = module.inspect_inline_record_fields_auto(combined_fixture(),
                                                      marker_packet=0)
    assert answer['tail_start_pc'] == 256
    assert answer['tail_end_pc'] == 432
    assert answer['tail_boundaries_automatically_selected'] is True
    assert answer['reader_to_relative_fields_checked'] is True
    assert answer['source_region_qualified'] is False
    assert answer['record_path_selection_qualified'] is False


def test_forward_guard_does_not_require_manual_tail_selection():
    rows = combined_fixture()
    rows.insert(9, dict(pc=160, opcode='l.beq',
                        operands='r7, r0, 0x0 <0x300>'))
    answer = module.inspect_inline_record_fields_auto(rows, marker_packet=0)
    assert answer['reader_to_relative_fields_checked'] is True
    assert answer['tail_start_pc'] == 256


@pytest.mark.parametrize('fault', [
    'late_overwrite', 'alias', 'unknown', 'tail_entry', 'call', 'hoisted_mask',
    'control_packet_store'
])
def test_automatic_tail_never_searches_for_a_passing_prefix(fault):
    rows = combined_fixture()
    if fault == 'late_overwrite':
        rows.append(dict(pc=448, opcode='l.st.w', operands='r0, [r7, 0x18]'))
    elif fault == 'alias':
        rows.append(dict(pc=448, opcode='l.st.w', operands='r0, [r21]'))
    elif fault == 'unknown':
        rows.append(dict(pc=448, opcode='l.future_op', operands='r4'))
    elif fault == 'tail_entry':
        rows.insert(
            9, dict(pc=160, opcode='l.beq', operands='r7, r0, 0x0 <0x120>'))
    elif fault == 'call':
        rows.insert(9, dict(pc=160, opcode='l.jal',
                            operands='lr, 0x0 <0x300>'))
    elif fault == 'hoisted_mask':
        rows.insert(9, dict(pc=160, opcode='l.anda',
                            operands='r9, r9, 0x3fff'))
    else:
        rows.extend([
            dict(pc=448, opcode='l.st.w', operands='r0, [r7, 0x18]'),
            dict(pc=458, opcode='l.beq', operands='r4, r0, 0x0 <0x300>')
        ])
    with pytest.raises(ValueError):
        module.inspect_inline_record_fields_auto(rows, marker_packet=0)
