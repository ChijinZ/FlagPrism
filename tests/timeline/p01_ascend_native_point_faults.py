"""Real final-image native-point faults, with internally consistent ELF seals.

CPU only in the matching server Docker. Never modifies the original recordings.
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import struct

from flagtree.profiler import timeline_ascend_machine as machine
from flagtree.profiler import timeline_ascend_native as native


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    directory = args.timeline
    before = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob('*') if p.is_file()
    }
    row = json.loads((directory / 'index.json').read_text())['captures'][0]
    from flagtree.profiler.timeline_capture_store import load_capture_file
    capture = load_capture_file(directory / row['capture_file'])
    metadata = capture['metadata']['compiler_metadata']
    binary = machine.retained_binary(metadata)
    dwarf = (directory /
             ('machine/' + metadata['hash'] + '/dwarf.stdout')).read_bytes()
    positive = native.native_control_map(binary=binary,
                                         dwarf_lines=dwarf,
                                         metadata=metadata)
    need(positive['complete'], 'Actual native point baseline is incomplete')
    target = positive['native_pcs'][0]
    offset = struct.unpack_from('<Q', binary, 40)[0]
    count = struct.unpack_from('<H', binary, 60)[0]
    headers = [
        struct.unpack_from('<IIQQQQIIQQ', binary, offset + 64 * i)
        for i in range(count)
    ]
    section = next(h for h in headers
                   if h[2] & 4 and h[3] <= target['pc'] < h[3] + h[5])
    word_offset = section[4] + target['pc'] - section[3]
    rejected = []
    for name, replacement in [('different_native_operation',
                               target['instruction_word'] ^ 0x00600000),
                              ('different_native_event',
                               target['instruction_word'] ^ 1)]:
        altered = bytearray(binary)
        struct.pack_into('<I', altered, word_offset, replacement)
        altered = bytes(altered)
        meta = copy.deepcopy(metadata)
        meta['flagprism_ascend_handoff']['final_outputs']['binary'].update(
            encoding='base64',
            data=base64.b64encode(altered).decode(),
            bytes=len(altered),
            sha256=hashlib.sha256(altered).hexdigest())
        try:
            native.native_control_map(binary=altered,
                                      dwarf_lines=dwarf,
                                      metadata=meta)
        except ValueError:
            rejected.append(name)
        else:
            raise RuntimeError(
                'Consistently resealed wrong native word accepted: ' + name)
    pattern = re.compile(r'^0x0*' + format(target['pc'], 'x') + r'\s+', re.I)
    damaged = ('\n'.join(line for line in dwarf.decode().splitlines()
                         if not pattern.match(line)) + '\n').encode()
    incomplete = native.native_control_map(binary=binary,
                                           dwarf_lines=damaged,
                                           metadata=metadata)
    need(not incomplete['complete'] and incomplete['unbound_image_flag_words'],
         'Missing native point was hidden by a different instruction clone')
    rejected.append('missing_native_clone_is_incomplete')
    # An uncatalogued event-extension word outside all marked points must
    # invalidate mechanism coverage too, rather than disappearing from the scan.
    counter = machine.counter_map(binary=binary,
                                  dwarf_lines=dwarf,
                                  metadata=metadata)
    marked = {row['pc'] for row in positive['native_pcs']}
    marked.update(row['pc'] for row in counter['counter_pcs'])
    candidate = next((h[4] + i for h in headers if h[2] & 4
                      for i in range(0, h[5], 4) if h[3] + i not in marked),
                     None)
    need(candidate is not None, 'No unmarked instruction for the CPU fixture')
    altered = bytearray(binary)
    unknown = 0x40a40603  # Not in the finite reference catalogue.
    need(unknown not in native.WORDS, 'Unknown fixture became catalogued')
    struct.pack_into('<I', altered, candidate, unknown)
    altered = bytes(altered)
    meta = copy.deepcopy(metadata)
    meta['flagprism_ascend_handoff']['final_outputs']['binary'].update(
        encoding='base64',
        data=base64.b64encode(altered).decode(),
        bytes=len(altered),
        sha256=hashlib.sha256(altered).hexdigest())
    incomplete = native.native_control_map(binary=altered,
                                           dwarf_lines=dwarf,
                                           metadata=meta)
    need(
        not incomplete['complete']
        and any(row['instruction_word'] == unknown
                for row in incomplete['uncatalogued_family_candidates']),
        'Unmarked extended-event flag was not reported as incomplete')
    rejected.append('unmarked_extended_event_is_incomplete')
    need(
        before == {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()
        }, 'Original image/recording changed')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'real_native_point_corruption_contract_passed_not_full_qualification',
            binary_sha256=hashlib.sha256(binary).hexdigest(),
            target=target,
            rejected=rejected),
                   indent=2))


if __name__ == '__main__':
    main()
