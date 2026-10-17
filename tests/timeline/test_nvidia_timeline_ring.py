"""Server-Docker CPU contract negatives; fixtures are not device qualification."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--module', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    spec = importlib.util.spec_from_file_location('timeline_ring_under_test', args.module)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    passed = []

    def check(name, condition):
        if not condition:
            raise RuntimeError(name)
        passed.append(name)

    def fixture(*, count=4, saturated=False):
        # One physical block, two actual warps but only warp 1 collected.
        # Four records capacity. Large ticks prove preservation above bit 43.
        payload = bytearray(88)
        struct.pack_into('<4I', payload, 0, mod.PREAMBLE, 7, 2, 64)
        struct.pack_into('<I', payload, 20,
                         mod.SATURATED if saturated else count * 4)
        written = (mod.SATURATED - 3) // 4 if saturated else count
        for seq in range(max(0, written - 4), written):
            tick = (1 << 63) + seq * 9
            tag = 300 | (0x80000000 if seq % 2 else 0)
            struct.pack_into('<4I', payload, 24 + (seq % 4) * 16,
                             tag, tick & 0xFFFFFFFF, tick >> 32, seq)
        return bytes(payload)

    opts = dict(scratch_size=88, total_warps=2, selected_warps=(1,),
                slots=((0, 7),), scope_ids=frozenset({300}))

    def decode(raw=None, **delta):
        return mod.decode_timeline_ring(fixture() if raw is None else raw,
                                        **dict(opts, **delta))

    def rejects(name, raw=None, **delta):
        try:
            decode(raw, **delta)
        except ValueError:
            passed.append(name)
        else:
            raise RuntimeError('Accepted invalid fixture: ' + name)

    result = decode()
    check('complete-full64', result['complete'] and
          result['records'][0]['tick'] == 1 << 63 and
          result['records'][1]['tick'] - result['records'][0]['tick'] == 9)
    check('site-above-legacy8bit', all(r['site'] == 300 for r in result['records']))
    check('all-raw-provenance', [r['raw_byte_offset'] for r in result['records']] ==
          [24, 40, 56, 72] and all(r['raw_byte_length'] == 16 and
          r['counter_byte_offset'] == 20 for r in result['records']))
    wrapped = decode(fixture(count=7))
    check('ring-overwrite-sequences', not wrapped['complete'] and
          [r['sequence'] for r in wrapped['records']] == [3, 4, 5, 6] and
          wrapped['observers'][0]['overwritten_records'] == 3)
    sat = decode(fixture(saturated=True))
    check('counter-saturation-not-complete', not sat['complete'] and
          sat['observers'][0]['saturated'] and
          sat['observers'][0]['unrecorded_after_saturation'] is None)
    empty = decode(fixture(count=0))
    check('zero-records-stay-empty', empty['records'] == [])
    for name, offset, value in [
            ('old-magic', 0, 0xDEADBEEF), ('wrong-program', 4, 8),
            ('oversized-ring', 12, 128), ('partial-counter', 20, 3),
            ('bad-sequence', 36, 99), ('unknown-site', 24, 301),
            ('regressed-timer', 48, 0)]:
        data = bytearray(fixture())
        struct.pack_into('<I', data, offset, value)
        rejects(name, bytes(data))
    rejects('truncated-payload', fixture()[:-1])
    rejects('mutable-payload', bytearray(fixture()))
    rejects('duplicate-slot', slots=((0, 7), (0, 8)))
    rejects('duplicate-program', fixture() * 2, slots=((0, 7), (1, 7)))
    rejects('out-of-range-slot', slots=((1, 7),))
    rejects('bad-warp-order', selected_warps=(1, 0))
    rejects('bool-warp', selected_warps=(True,))
    rejects('unknown-record-version', record_version=1)
    rejects('boolean-record-version', record_version=True)
    rejects('unknown-site-type', scope_ids=frozenset({True}))
    rejects('scope-field-overflow', scope_ids=frozenset({1 << 31}))
    rejects('float-size', scratch_size=88.0)
    rejects('empty-slots', slots=())
    rejects('metadata-exceeds-stride', total_warps=100)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        'status': 'passed_cpu_contract_not_device_qualification',
        'passed': passed, 'count': len(passed),
        'optimized_python': bool(sys.flags.optimize),
        'module_sha256': hashlib.sha256(args.module.read_bytes()).hexdigest(),
        'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
