"""Classify the pinned public replay's producer-only ELF difference, read-only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
REFERENCE_SHA = '05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def parse(data):
    if not data[:6] == b'\x7fELF\x02\x01':
        raise RuntimeError('requires ELF64 little-endian')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, header[6] + i * header[11]) for i in range(header[12])]
    strings = sections[header[13]]
    names = data[strings[4]:strings[4] + strings[5]]
    named = {names[s[0]:].split(b'\x00', 1)[0].decode(): (i, s) for i, s in enumerate(sections)}
    programs = [struct.unpack_from('<IIQQQQQQ', data, header[5] + i * header[9]) for i in range(header[10])]
    return (header, named, programs)

def compare(actual_path, reference_path):
    actual, reference = (actual_path.read_bytes(), reference_path.read_bytes())
    if not sha(reference) == REFERENCE_SHA:
        raise RuntimeError('unrecognized public reference')
    if not len(actual) == len(reference):
        raise RuntimeError('ELF file size differs')
    ah, asecs, ap = parse(actual)
    rh, rsecs, rp = parse(reference)
    if not ah == rh:
        raise RuntimeError('ELF header/flags/layout differ')
    if not ap == rp:
        raise RuntimeError('program headers/segment layout differ')
    if not asecs.keys() == rsecs.keys():
        raise RuntimeError('section set differs')
    ai, ac = asecs['.comment']
    ri, rc = rsecs['.comment']
    if not (ai == ri and ac[:5] == rc[:5] and (ac[6:] == rc[6:])):
        raise RuntimeError('comment layout differs')
    if not (not ac[2] & 2 and (not rc[2] & 2)):
        raise RuntimeError('comment is SHF_ALLOC')
    comment_start, comment_end = (ac[4], ac[4] + max(ac[5], rc[5]))
    if comment_end > len(actual):
        raise RuntimeError('comment extends beyond the ELF file')
    protected = [(0, ah[8]), (ah[5], ah[5] + ah[9] * ah[10]),
                 (ah[6], ah[6] + ah[11] * ah[12])]
    protected.extend((s[4], s[4] + s[5]) for name, (_, s) in asecs.items()
                     if name != '.comment' and s[1] != 8 and s[5])
    for start, end in protected:
        if start < comment_end and comment_start < end:
            raise RuntimeError('comment overlaps another section or ELF metadata table')
    for p in ap:
        if p[0] == 1:
            if not (p[2] + p[5] <= comment_start or p[2] >= comment_end):
                raise RuntimeError('comment intersects PT_LOAD')
    allowed = set(range(comment_start, comment_end))
    size_offset = ah[6] + ai * ah[11] + 32
    allowed.update(range(size_offset, size_offset + 8))
    different = [i for i, (a, b) in enumerate(zip(actual, reference)) if a != b]
    if not (different and set(different) <= allowed):
        raise RuntimeError('differences extend beyond comment and its sh_size')
    section_receipts = {}
    for name, (i, section) in asecs.items():
        other = rsecs[name][1]
        content = actual[section[4]:section[4] + section[5]]
        old = reference[other[4]:other[4] + other[5]]
        if name != '.comment':
            if not (section == other and content == old):
                raise RuntimeError(f'section differs: {name}')
        section_receipts[name] = {'header_equal': section == other, 'content_equal': content == old, 'offset': section[4], 'flags': section[2], 'type': section[1], 'actual_header': section, 'reference_header': other, 'actual_size': len(content), 'reference_size': len(old), 'actual_sha256': sha(content), 'reference_sha256': sha(old)}
    ranges = []
    for offset in different:
        if ranges and offset == ranges[-1][1]:
            ranges[-1][1] += 1
        else:
            ranges.append([offset, offset + 1])
    return {'classification': 'producer-comment-only', 'bitidentical': False, 'actual': str(actual_path.resolve()), 'actual_sha256': sha(actual), 'reference': str(reference_path.resolve()), 'reference_sha256': sha(reference), 'bytes': len(actual), 'different_byte_count': len(different), 'difference_ranges_half_open': ranges, 'elf_header_equal': True, 'program_headers_equal': True, 'program_headers': ap, 'comment_sh_size_offset': size_offset, 'comment_not_allocated': True, 'comment_outside_load_segments': True, 'all_other_sections_equal': True, 'actual_comment': actual[ac[4]:ac[4] + ac[5]].decode(), 'reference_comment': reference[rc[4]:rc[4] + rc[5]].decode(), 'sections': section_receipts}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actual', type=Path, required=True)
    parser.add_argument('--reference', type=Path, default=Path(__file__).parent / 'tests/data/ordinary_reference.npubin')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite an earlier comparison receipt')
    result = compare(args.actual, args.reference)
    result['recipe_sha256'] = sha(Path(__file__).read_bytes())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
if __name__ == '__main__':
    main()
