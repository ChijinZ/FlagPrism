"""Real saved-image checks and explicit faults; no NPU execution/qualification."""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline',
                        action='append',
                        type=Path,
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.source_root:
        import flagtree.profiler
        flagtree.profiler.__path__.insert(
            0, str(args.source_root / 'Profiler/python/flagtree_profiler'))
    from flagtree.profiler import timeline_ascend_machine as machine
    captures = [
        json.loads(path.read_text()) for directory in args.timeline
        for path in sorted((directory / 'captures').glob('*.input.json'))
    ]
    if len(captures) < 3:
        raise RuntimeError(
            'Three actual captures are required; no skip permitted')
    receipts = []
    for capture in captures:
        status = machine.inspect_capture_binary(args.output / 'portable',
                                                metadata=capture['metadata'])
        if status['status'] != 'counter_mapping_complete_region_unverified':
            raise RuntimeError('Real inspection failed: ' + str(status))
        mapped = machine.load_counter_machine_map(args.output / 'portable',
                                                  capture)
        receipts.append(
            dict(capture=capture['owner']['invocation_id'],
                 binary_id=mapped['binary_id'],
                 clocks=len(mapped['counter_pcs'])))
    capture = captures[0]
    first_timeline = args.timeline[0]
    batch = json.loads(
        (first_timeline / ('captures/' + capture['owner']['invocation_id'] +
                           '.events.json')).read_text())
    raw_path = args.output / 'portable' / capture['raw_file']
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes((first_timeline / capture['raw_file']).read_bytes())
    metadata = capture['metadata']['compiler_metadata']
    binary = machine.retained_binary(metadata)
    prefix = args.output / 'portable/machine' / metadata['hash']
    dwarf = (prefix / 'dwarf.stdout').read_bytes()
    actual = machine.counter_map(binary=binary,
                                 dwarf_lines=dwarf,
                                 metadata=metadata)

    def sealed(raw):
        meta = copy.deepcopy(metadata)
        meta['flagprism_ascend_handoff']['final_outputs']['binary'].update(
            data=base64.b64encode(raw).decode(),
            sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw))
        return meta

    class Checks(unittest.TestCase):

        def test_actual_locations(self):
            self.assertTrue(actual['counter_pcs'])
            self.assertFalse(actual['region_boundaries_verified'])
            self.assertFalse(actual['clock_unit_verified'])
            self.assertFalse(actual['record_value_provenance_verified'])

        def test_wrong_instruction_with_consistent_binary_seal(self):
            row = actual['counter_pcs'][0]
            sections, _ = machine._elf(binary)
            section = next(s for s in sections.values()
                           if s['name'] == row['section'])
            # Locate the actual code bytes using the executable's section header.
            import struct
            start = struct.unpack_from('<Q', binary, 40)[0]
            count = struct.unpack_from('<H', binary, 60)[0]
            headers = [
                struct.unpack_from('<IIQQQQIIQQ', binary, start + 64 * i)
                for i in range(count)
            ]
            h = next(h for h in headers
                     if h[2] & 4 and h[3] == section['address'])
            raw = bytearray(binary)
            offset = h[4] + row['pc'] - h[3]
            struct.pack_into('<I', raw, offset, 0x07000000)
            with self.assertRaisesRegex(ValueError, 'reference SYS_CNT'):
                machine.counter_map(binary=bytes(raw),
                                    dwarf_lines=dwarf,
                                    metadata=sealed(bytes(raw)))

        def test_loaded_image_identity(self):
            c = copy.deepcopy(capture)
            c['metadata']['compiled_snapshot']['executable'][
                'binary_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'loaded executable'):
                machine._bound_binary(c['metadata'])

        def test_non_c220_architecture(self):
            meta = copy.deepcopy(metadata)
            meta['arch'] = 'Ascend950'
            with self.assertRaisesRegex(ValueError, 'architecture'):
                machine.counter_map(binary=binary,
                                    dwarf_lines=dwarf,
                                    metadata=meta)

        def test_other_sdk_target(self):
            meta = copy.deepcopy(metadata)
            meta['flagprism_ascend_handoff']['artifacts'][0]['driver_job'][
                'target_arch'] = 'dav-c310-vec'
            with self.assertRaisesRegex(ValueError, 'actor compiler job'):
                machine.counter_map(binary=binary,
                                    dwarf_lines=dwarf,
                                    metadata=meta)

        def test_missing_clock_file(self):
            with self.assertRaisesRegex(ValueError, 'phases are missing'):
                machine.counter_map(binary=binary,
                                    dwarf_lines=dwarf.replace(
                                        machine.CLOCK_FILE.encode(),
                                        b'other_clock_file'),
                                    metadata=metadata)

        def test_missing_endpoint(self):
            rows = dwarf.decode().splitlines()
            marker_rows = machine._dwarf_rows(dwarf)
            row = marker_rows[0]
            expression = r'^0x0*' + format(row['pc'], 'x') + r'\s+' + str(
                row['line']) + r'\s+0\s+'
            changed = '\n'.join(s for s in rows
                                if not re.match(expression, s)).encode()
            with self.assertRaisesRegex(ValueError, 'phases are missing'):
                machine.counter_map(binary=binary,
                                    dwarf_lines=changed,
                                    metadata=metadata)

        def test_one_pc_cannot_alias_two_phases(self):
            rows = dwarf.decode().splitlines()
            marked = machine._dwarf_rows(dwarf)[0]
            expression = r'^0x0*' + format(marked['pc'], 'x') + r'\s+' + str(
                marked['line']) + r'\s+0\s+'
            for index, line in enumerate(rows):
                if re.match(expression, line):
                    other = marked['line'] + 1 if marked[
                        'line'] % 2 else marked['line'] - 1
                    tokens = line.split()
                    tokens[1] = str(other)
                    rows.insert(index + 1, ' '.join(tokens))
                    break
            with self.assertRaisesRegex(ValueError, 'aliases'):
                machine.counter_map(binary=binary,
                                    dwarf_lines='\n'.join(rows).encode(),
                                    metadata=metadata)

        def test_line_zero_is_not_a_marker(self):
            zero = dwarf.decode().splitlines()
            marked = machine._dwarf_rows(dwarf)[0]
            for index, line in enumerate(zero):
                if (line.startswith('0x')
                        and int(line.split()[0], 16) == marked['pc']
                        and int(line.split()[1]) == marked['line']
                        and int(line.split()[3]) == marked['file_index']):
                    tokens = line.split()
                    tokens[1] = '0'
                    zero.insert(index + 1, ' '.join(tokens))
                    break
            mapped = machine.counter_map(binary=binary,
                                         dwarf_lines='\n'.join(zero).encode(),
                                         metadata=metadata)
            self.assertEqual(
                mapped, actual | {
                    'dwarf_sha256':
                    hashlib.sha256('\n'.join(zero).encode()).hexdigest()
                })

        def test_wrong_column(self):
            rows = dwarf.decode().splitlines()
            marked = machine._dwarf_rows(dwarf)[0]
            for index, line in enumerate(rows):
                if line.startswith('0x') and int(
                        line.split()[0], 16) == marked['pc'] and int(
                            line.split()[1]) == marked['line']:
                    tokens = line.split()
                    tokens[2] = '7'
                    rows[index] = ' '.join(tokens)
                    break
            with self.assertRaisesRegex(ValueError,
                                        'Invalid clock marker row'):
                machine.counter_map(binary=binary,
                                    dwarf_lines='\n'.join(rows).encode(),
                                    metadata=metadata)

        def test_truncated_elf(self):
            with self.assertRaises(ValueError):
                machine.counter_map(binary=b'bad',
                                    dwarf_lines=dwarf,
                                    metadata=sealed(b'bad'))

        def test_changed_retained_binary(self):
            with self.assertRaisesRegex(ValueError, 'retained final compiler'):
                machine.counter_map(binary=binary + b'changed',
                                    dwarf_lines=dwarf,
                                    metadata=metadata)

        def test_cached_status_cannot_grant_machine_proof(self):
            path = args.output / 'fake/machine' / metadata['hash']
            path.mkdir(parents=True)
            (path / 'status.json').write_text(
                json.dumps(
                    dict(status='counter_mapping_complete_region_unverified')))
            with self.assertRaises(ValueError):
                machine.load_counter_machine_map(args.output / 'fake', capture)

        def test_optional_missing_tool_preserves_raw(self):
            from unittest.mock import patch
            with patch.dict(os.environ,
                            FLAGPRISM_ASCEND_DWARFDUMP='/missing/clock-tool'):
                status = machine.inspect_capture_binary(
                    args.output / 'missing-tool', metadata=capture['metadata'])
            self.assertEqual(status['status'], 'counter_mapping_unavailable')
            self.assertFalse(status['region_boundaries_verified'])

        def test_cached_corrupt_status_is_not_a_profile_failure(self):
            path = args.output / 'corrupt/machine' / metadata['hash']
            path.mkdir(parents=True)
            (path / 'status.json').write_bytes(b'{bad')
            status = machine.inspect_capture_binary(
                args.output / 'corrupt', metadata=capture['metadata'])
            self.assertEqual(status['status'], 'counter_mapping_unavailable')
            self.assertEqual((path / 'status.json').read_bytes(), b'{bad')

        def test_offline_requires_no_tool(self):
            from unittest.mock import patch
            with patch.object(
                    machine.subprocess,
                    'Popen',
                    side_effect=RuntimeError('offline tool execution')):
                self.assertEqual(
                    machine.load_counter_machine_map(args.output / 'portable',
                                                     capture), actual)

        def test_unit_runtime_fixture(self):
            # The old real image has no runtime-name snapshot. This injection
            # tests provider logic only; it is not a real unit qualification.
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['metadata']['runtime_device'] = dict(name=metadata['arch'],
                                                   device=c['owner']['device'])
            proofs = load_counter_unit_proofs(args.output / 'portable', c,
                                              batch)
            self.assertTrue(proofs)
            self.assertTrue(
                all(p.period_numerator_ns == 20 and p.period_denominator == 1
                    for p in proofs))

        def test_old_capture_without_runtime_binding_stays_raw(self):
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['metadata'].pop('runtime_device', None)
            with self.assertRaisesRegex(ValueError, 'runtime target'):
                load_counter_unit_proofs(args.output / 'portable', c, batch)

        def test_wrong_runtime_model(self):
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['metadata']['runtime_device'] = dict(name='Ascend950',
                                                   device=c['owner']['device'])
            with self.assertRaisesRegex(ValueError, 'runtime target'):
                load_counter_unit_proofs(args.output / 'portable', c, batch)

        def test_cross_invocation_unit_proof(self):
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['owner']['invocation_id'] = 'foreign-invocation'
            with self.assertRaisesRegex(ValueError, 'different captures'):
                load_counter_unit_proofs(args.output / 'portable', c, batch)

        def test_conservative_wrap_window(self):
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['metadata']['runtime_device'] = dict(name=metadata['arch'],
                                                   device=c['owner']['device'])
            c['owner']['host_completion_observed_ns'] = c['owner'][
                'host_admission_ns'] + 20 * (1 << 32)
            with self.assertRaisesRegex(ValueError, 'wrap bound'):
                load_counter_unit_proofs(args.output / 'portable', c, batch)

        def test_narrow_counter_floor(self):
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['metadata']['runtime_device'] = dict(name=metadata['arch'],
                                                   device=c['owner']['device'])
            b = copy.deepcopy(batch)
            for row in b['records']:
                row['tick'] = 0
            for event in b['events']:
                event['start_tick'] = 0
                event['end_tick'] = 0
            with self.assertRaisesRegex(ValueError, 'width floor'):
                load_counter_unit_proofs(args.output / 'portable', c, b)

        def test_canonical_tick_forgery(self):
            from flagtree.profiler.timeline_unit_ascend import load_counter_unit_proofs
            c = copy.deepcopy(capture)
            c['metadata']['runtime_device'] = dict(name=metadata['arch'],
                                                   device=c['owner']['device'])
            b = copy.deepcopy(batch)
            for row in b['records']:
                row['tick'] += 1
            for event in b['events']:
                event['start_tick'] += 1
                event['end_tick'] += 1
            with self.assertRaisesRegex(ValueError, 'actual raw bytes'):
                load_counter_unit_proofs(args.output / 'portable', c, b)

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    report = dict(
        status='real_machine_positive_and_fault_checks_passed'
        if result.wasSuccessful() else 'failed',
        tests=result.testsRun,
        skips=len(result.skipped),
        receipts=receipts,
        unit_runtime_binding_positive=
        'synthetic fixture only; actual runtime capture still required',
        module_sha256=hashlib.sha256(Path(
            machine.__file__).read_bytes()).hexdigest())
    (args.output / 'result.json').write_text(json.dumps(report, indent=2))
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
