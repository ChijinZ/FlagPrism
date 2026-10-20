"""ELF/disassembly corruption fixtures; these are not device/ISA evidence."""
import importlib.util
from pathlib import Path
import struct

import pytest

spec = importlib.util.spec_from_file_location(
    'gcu_native_image',
    Path(__file__).parents[1] / 'python/flagtree_debugger/gcu_native_image.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    text = bytearray(64)
    text[32:36] = b'abcd'
    strings = b'\0kernel\0'
    symbols = struct.pack('<IBBHQQ', 1, 0x12, 0, 1, 0, 64)
    header = struct.pack('<16sHHIQQQIHHHHHH',
                         b'\x7fELF\x02\x01\x01' + b'\0' * 9, 2, 0, 1, 0, 0, 64,
                         0, 64, 0, 0, 64, 4, 0)
    sections = [
        bytes(64),
        struct.pack('<IIQQQQIIQQ', 0, 1, 4, 0, 320, 64, 0, 0, 16, 0),
        struct.pack('<IIQQQQIIQQ', 0, 2, 0, 0, 384, 24, 3, 0, 8, 24),
        struct.pack('<IIQQQQIIQQ', 0, 3, 0, 0, 408, len(strings), 0, 0, 1, 0)
    ]
    binary = header + b''.join(sections) + text + symbols + strings
    native = (b'0000000000000000 kernel:\n\t.dtu_kernel_code_t\n'
              b'\tkernel_code_entry_byte_offset 32\n\tkernel_code_size 32\n'
              b'\t.end_dtu_kernel_code_t\n'
              b' 20: 61 62 63 64\tl.ld.w r7, [r16]\n')
    return binary, native


def test_byte_binding_and_descriptor_extent():
    answer = module.bind_instructions(*fixture())
    assert answer['start_packet'] == 32
    assert answer['end_packet'] == 64
    assert answer['instructions'] == [
        dict(pc=32, opcode='l.ld.w', operands='r7, [r16]')
    ]
    assert answer['source_region_qualified'] is False
    assert answer['reader_valueflow_qualified'] is False


def test_linked_sdk_code_is_bound_without_becoming_kernel_body():
    binary, native = fixture()
    binary = bytearray(binary)
    binary[320:324] = b'wxyz'
    struct.pack_into('<QQ', binary, 384 + 8, 16, 48)
    native = native.replace(b'0000000000000000 kernel:',
                            b'0000000000000010 kernel:')
    native = native.replace(b'entry_byte_offset 32', b'entry_byte_offset 16')
    native = native.replace(b' 20:',
                            b' 0: 77 78 79 7a\tl.ld.w r9, [r16]\n 20:')
    answer = module.bind_instructions(bytes(binary), native)
    assert answer['other_decoded_instruction_count'] == 1
    assert [r['pc'] for r in answer['instructions']] == [32]


def test_long_symbol_suffixes_have_a_cumulative_scan_budget():
    binary, native = fixture()
    names = b'\0kernel\0' + b'x' * 2048 + b'\0'
    symbols = struct.pack('<IBBHQQ', 1, 0x12, 0, 1, 0, 64)
    symbols += b''.join(
        struct.pack('<IBBHQQ', 8 + i, 0x12, 0, 1, 0, 0) for i in range(128))
    binary = bytearray(binary[:384])
    struct.pack_into('<Q', binary, 192 + 32, len(symbols))
    struct.pack_into('<QQ', binary, 256 + 24, 384 + len(symbols), len(names))
    binary.extend(symbols)
    binary.extend(names)
    with pytest.raises(ValueError,
                       match='symbol-name scan exceeds byte budget'):
        module.bind_instructions(bytes(binary), native)


@pytest.mark.parametrize('fault', [
    'wrong_bytes', 'missing_bytes', 'duplicate_pc', 'overlap', 'wrong_entry',
    'wrong_symbol', 'outside_code', 'truncated_section', 'bad_symbol_offset',
    'bad_section_table', 'duplicate_descriptor', 'symbol_budget'
])
def test_corrupt_native_image_is_rejected(fault):
    binary, native = fixture()
    if fault == 'wrong_bytes':
        native = native.replace(b'61 62 63 64', b'61 62 63 65')
    elif fault == 'missing_bytes':
        native = native.replace(b' 20: 61 62 63 64\tl.ld.w r7, [r16]\n', b'')
    elif fault == 'duplicate_pc':
        native += b' 20: 61 62 63 64\tl.ld.w r7, [r16]\n'
    elif fault == 'overlap':
        native += b' 22: 63 64\tc.nop\n'
    elif fault == 'wrong_entry':
        native = native.replace(b'entry_byte_offset 32',
                                b'entry_byte_offset 16')
    elif fault == 'wrong_symbol':
        native = native.replace(b'kernel:', b'other:')
    elif fault == 'outside_code':
        native += b' 40: 00 00\tc.nop\n'
    elif fault == 'truncated_section':
        binary = bytearray(binary)
        struct.pack_into('<Q', binary, 128 + 32, 4096)
        binary = bytes(binary)
    elif fault == 'bad_symbol_offset':
        binary = bytearray(binary)
        struct.pack_into('<I', binary, 384, 1000)
        binary = bytes(binary)
    elif fault == 'bad_section_table':
        binary = bytearray(binary)
        struct.pack_into('<Q', binary, 40, 4096)
        binary = bytes(binary)
    elif fault == 'symbol_budget':
        binary = bytearray(binary)
        struct.pack_into('<Q', binary, 192 + 32, len(binary) * 2)
        binary = bytes(binary)
    else:
        native += native[:native.index(b' 20:')]
    with pytest.raises(ValueError):
        module.bind_instructions(binary, native)
