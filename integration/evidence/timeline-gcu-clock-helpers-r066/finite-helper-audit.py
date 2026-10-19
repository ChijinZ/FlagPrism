"""Finite original-ELF helper audit, without inline-reader/raw or region rights."""
import hashlib
import json
from pathlib import Path
import re
import struct

elf = Path('/tmp/chijin-timeline-r061-gcu/runs/final-inspect-v1/output/32-8/1.elf')
disassembly = Path('/tmp/chijin-timeline-r065-gcu/runs/llvm11-native-v6/output/llvm11-disassembly.stdout')
expected_elf = 'ac6748ff87599aa31b21356701527be356ceb9908637df9b67006fa072701cba'
expected_disassembly = '61fa447ccd36509ba2a97e48d794d35716f6870fb51cea9b2521e754f4b1067c'


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def symbols(binary):
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', binary)
    need(header[0][:6] == b'\x7fELF\x02\x01', 'Expected ELF64 little endian')
    sections = [struct.unpack_from('<IIQQQQIIQQ',binary,header[6]+i*header[11]) for i in range(header[12])]
    found = {}
    for section in sections:
        if section[1] != 2:
            continue
        strings_section = sections[section[6]]
        strings = binary[strings_section[4]:strings_section[4]+strings_section[5]]
        for offset in range(section[4],section[4]+section[5],section[9]):
            sn,info,other,index,value,size = struct.unpack_from('<IBBHQQ',binary,offset)
            name = strings[sn:].split(b'\0',1)[0].decode()
            if name not in ('_ZN4tops12global_timerEv', 'flagprism_gcu_clock_identity_v1'):
                continue
            need(name not in found and 0 < index < len(sections), 'Ambiguous helper symbol')
            target = sections[index]
            need(size > 0 and target[3] <= value and value+size <= target[3]+target[5], 'Helper outside section')
            found[name] = dict(address=value, bytes=size, section_address=target[3], section_file_offset=target[4])
    need(len(found) == 2, 'Missing actual helper symbols')
    return found


def instructions(binary, text, symbol):
    rows = []
    for line in text.splitlines():
        m = re.match(r'^\s*([0-9a-f]+):\s+([^\t]+)\t(.+)$',line)
        if not m:
            continue
        pc = int(m[1],16)
        if not symbol['address'] <= pc < symbol['address']+symbol['bytes']:
            continue
        fields = m[2].split()
        need(fields and all(re.fullmatch(r'[0-9a-f]{2}',x) for x in fields), 'Unknown displayed instruction bytes')
        raw = bytes(int(x,16) for x in fields)
        offset = symbol['section_file_offset']+pc-symbol['section_address']
        need(binary[offset:offset+len(raw)] == raw, 'Displayed native bytes differ from original ELF')
        assembly = m[3].strip().split(None,1)
        opcode = assembly[0]
        operands = re.sub(r'\s+','',assembly[1]) if len(assembly)>1 else ''
        if opcode in ('c.nop','s.nop16','v.nop') or (opcode == 'c.addi4spn' and operands == 'r8,0x0'):
            continue
        rows.append(dict(pc=pc, opcode=opcode, operands=operands, actual_bytes=raw.hex()))
    need(rows, 'Helper has no decoded actual instructions')
    return rows


def clock_semantics(rows):
    pairs = [(r['opcode'],r['operands']) for r in rows]
    required = [('l.ldi16.s','r5,0x10'),('l.ldi_hi','r5,0x4243'),('l.ld.w','r7,[r5]'),('l.ld.w','r6,[r5,0x4]'),('l.ld.w','r4,[r5]')]
    need(pairs[:5] == required, 'Unexpected finite counter-read prefix')
    need(len(pairs) == 13, 'Unexpected helper shape')
    need(pairs[5][0] == 'l.bge.u' and pairs[5][1].startswith('r4,r7,'), 'Missing low-word rollover comparison')
    target = re.search(r'<0x([0-9a-f]+)>',pairs[5][1])
    need(target is not None and int(target[1],16) == (rows[10]['pc'] & ~0xf), 'Unexpected rollover branch landing packet')
    need(pairs[6:10] == [('c.li','r4,0x4'),('l.adda.u','r4,r5,r4'),('l.ld.w','r6,[r4]'),('l.ld.w','r4,[r5]')], 'Unexpected rollover reread path')
    need(pairs[10:] == [('l.ldi16.s','r5,0x3fff'),('l.anda','r5,r6,r5'),('l.jalr','r0,lr,0x0')], 'Unexpected upper-word mask or return')
    return dict(returned_low_word_bits=32, returned_upper_word_mask=0x3fff, maximum_returned_value_bits=46, low_word_rollover_reread_present=True)


binary, native = elf.read_bytes(), disassembly.read_bytes()
need(sha(binary) == expected_elf and sha(native) == expected_disassembly, 'Actual evidence identity changed')
found = symbols(binary)
clock = instructions(binary,native.decode(),found['_ZN4tops12global_timerEv'])
identity = instructions(binary,native.decode(),found['flagprism_gcu_clock_identity_v1'])
facts = clock_semantics(clock)
need([(r['opcode'],r['operands']) for r in identity] == [('l.movs','r4,sipinfo'),('l.jalr','r0,lr,0x0')], 'Unexpected physical-counter identity helper')
negative = []
for name, changed in [('wrong_upper_mask',[dict(r,operands='r5,0x7fff') if i==10 else r for i,r in enumerate(clock)]),('missing_rollover_comparison',[dict(r,opcode='l.adda.u') if i==5 else r for i,r in enumerate(clock)])]:
    try:
        clock_semantics(changed)
    except ValueError as error:
        negative.append(dict(name=name,rejected=True,reason=str(error)))
    else:
        raise RuntimeError('Invalid helper accepted: '+name)
print(json.dumps(dict(status='finite_original_helper_clock_shape_audited', actual_ELF_sha256=expected_elf, native_disassembly_sha256=expected_disassembly, symbols=found, native_clock_instructions=clock, native_identity_instructions=identity, **facts, physical_counter_identity_read='unmasked sipinfo in helper', negative_fixtures=negative, actual_inline_reader_to_raw_binding=False, source_region_qualified=False, shared_epoch_qualified=False, absolute_frequency_qualified=False, hardware_busy_qualified=False, application_replayed=False, SDK_or_product_changed=False),indent=2))
