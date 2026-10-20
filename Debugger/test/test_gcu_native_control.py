"""Direct packet edges, including shared native record bodies."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    'gcu_native_control',
    Path(__file__).parents[1] /
    'python/flagtree_debugger/gcu_native_control.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(pc, opcode, operands=''):
    return dict(pc=pc, opcode=opcode, operands=operands)


def test_shared_reader_and_shared_record_body_are_distinct_joins():
    body = [
        row(10, 'l.beq', 'r4, r0, 0x0 <0x40>'),
        row(26, 'l.jal', 'r0, 0x0 <0x60>'),
        row(42, 'l.jal', 'r0, 0x0 <0x60>'),
        row(90, 'l.beq', 'r4, r0, 0x0 <0x80>'),
        row(138, 'l.jalr', 'r0, lr, 0x0')
    ]
    graph = module.index_direct_control(body, start_packet=0, end_packet=144)
    assert {e['source'] for e in graph['predecessors'][96]} == {16, 32, 80}
    assert {e['source'] for e in graph['predecessors'][128]} == {80, 112}
    assert graph['direct_control_complete'] is True
    assert graph['external_entries_qualified'] is False


@pytest.mark.parametrize('opcode,operands', [
    ('l.loop0', '0x0 <0x40>, 0x1'),
    ('c.jal', '0x2'),
    ('l.jalr', 'lr, r5, 0x0'),
    ('l.jal', 'lr, 0x0 <0x40>'),
    ('l.future_control', 'r4'),
])
def test_unmodeled_control_cannot_gain_complete_cfg(opcode, operands):
    graph = module.index_direct_control([row(10, opcode, operands)],
                                        start_packet=0,
                                        end_packet=64)
    assert graph['direct_control_complete'] is False
    assert len(graph['unknown_controls']) == 1
    assert graph['source_region_qualified'] is False


@pytest.mark.parametrize('fault', [
    'target_alignment', 'missing_target', 'two_controls', 'outside',
    'duplicate', 'bad_extent'
])
def test_malformed_direct_control_is_rejected(fault):
    body = [row(10, 'l.beq', 'r5, r0, 0x0 <0x20>')]
    start, end = 0, 64
    if fault == 'target_alignment': body[0]['operands'] = 'r5, r0, 0x0 <0x21>'
    elif fault == 'missing_target': body[0]['operands'] = 'r5, r0, 0x2'
    elif fault == 'two_controls':
        body.append(row(14, 'l.jal', 'r0, 0x0 <0x20>'))
    elif fault == 'outside':
        body[0]['pc'] = 74
    elif fault == 'duplicate':
        body.append(dict(body[0]))
    else:
        end = 63
    with pytest.raises(ValueError):
        module.index_direct_control(body, start_packet=start, end_packet=end)
