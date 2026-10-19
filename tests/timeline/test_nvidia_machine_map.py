"""CPU counter-map contracts; synthetic ELF/tool fixtures are not device evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from flagtree.profiler import timeline_nvidia_machine as machine

PTX = '''.version 8.8
.target sm_120a
.address_size 64
.visible .entry kernel() {
// flagprism_timeline_v1_site_0_entry;
mov.u64 %rd1, %globaltimer;
// flagprism_timeline_v1_site_0_exit;
mov.u64 %rd2, %globaltimer;
}
'''
DEBUG = '''.version 8.8
.target sm_120a
.address_size 64
.visible .entry kernel() {

mov.u64 %rd1, %globaltimer;

mov.u64 %rd2, %globaltimer;
}
'''
SASS = '''.section .text.kernel,"ax",@progbits
//## File ".nv_debug_ptx_txt", line 6
/*0000*/ CS2R R2, SR_GLOBALTIMERLO;
//## File ".nv_debug_ptx_txt", line 8
/*0010*/ CS2R R4, SR_GLOBALTIMERLO;
'''
DOC = [{
    'SchemaVersion': {
        'major': 13,
        'minor': 2,
        'revision': 0
    },
    'SM': {
        'version': {
            'major': 12,
            'minor': 0
        }
    }
},
       [{
           'function-name':
           'kernel',
           'start':
           0,
           'length':
           32,
           'sass-instructions': [{
               'opcode': 'CS2R',
               'operands': 'R2,SR_GLOBALTIMERLO'
           }, {
               'opcode': 'CS2R',
               'operands': 'R4,SR_GLOBALTIMERLO'
           }]
       }]]


def elf(debug=DEBUG, text_bytes=32):
    strings = b'\0.shstrtab\0.nv_debug_ptx_txt\0.text.kernel\0'
    data = b'\0'.join(v.encode() for v in debug.splitlines()) + b'\0'
    header = struct.pack('<16sHHIQQQIHHHHHH',
                         b'\x7fELF\x02\x01\x01' + b'\0' * 9, 2, 190, 1, 0, 0,
                         64, 0, 64, 0, 0, 64, 4, 1)
    tables = [
        bytes(64),
        struct.pack('<IIQQQQIIQQ', 1, 3, 0, 0, 320, len(strings), 0, 0, 1, 0),
        struct.pack('<IIQQQQIIQQ', strings.index(b'.nv_debug'), 1, 0, 0,
                    320 + len(strings), len(data), 0, 0, 1, 0),
        struct.pack('<IIQQQQIIQQ', strings.index(b'.text.kernel'), 1, 6, 0,
                    320 + len(strings) + len(data), text_bytes, 0, 0, 16, 0)
    ]
    return header + b''.join(tables) + strings + data + bytes(text_bytes)


def args():
    return dict(cubin=elf(),
                ptx=PTX.encode(),
                sass_lines=SASS.encode(),
                sass_json=json.dumps(DOC).encode(),
                binary_id='a' * 64,
                scope_ids=(0, ),
                expected_sm=(12, 0))


class CounterMapTests(unittest.TestCase):

    def test_late_inventory_can_include_wholly_unemitted_static_site(self):
        a = args()
        a.update(marker_flavor='late-v1',
                 scope_ids=(0, 1),
                 expected_phases=((0, 'entry'), (0, 'exit'), (1, 'entry'),
                                  (1, 'exit')))
        a['ptx'] = PTX.replace('flagprism_timeline_v1_',
                               'flagprism_late_probe_').encode()
        result = machine.counter_map(**a)
        self.assertEqual(result['not_emitted_static_sites'], [1])
        self.assertEqual({row['site_id']
                          for row in result['counter_pcs']}, {0})
        self.assertEqual(len(result['expected_phases']), 4)
        # An emitted half-bracket is a defect, rather than an absent site.
        a['ptx'] = a['ptx'].replace(b'site_0_exit', b'site_1_exit')
        with self.assertRaisesRegex(ValueError, 'Missing scope phase'):
            machine.counter_map(**a)

    def test_legacy_missing_static_site_remains_rejected(self):
        a = args()
        a['scope_ids'] = (0, 1)
        with self.assertRaisesRegex(ValueError, 'Missing scope phase'):
            machine.counter_map(**a)

    def test_uniform_counter_binding_keeps_exact_line_and_register_bank(self):
        a = args()
        doc = copy.deepcopy(DOC)
        doc[1][0]['sass-instructions'][0] = dict(
            opcode='CS2UR', operands='UR2,SR_GLOBALTIMERLO')
        a['sass_lines'] = SASS.replace('CS2R R2', 'CS2UR UR2').encode()
        a['sass_json'] = json.dumps(doc).encode()
        result = machine.counter_map(**a)
        self.assertEqual(result['counter_pcs'][0]['opcode'], 'CS2UR')
        self.assertFalse(result['region_boundaries_verified'])
        for opcode, operands in [('CS2UR', 'R2,SR_GLOBALTIMERLO'),
                                 ('CS2R', 'UR2,SR_GLOBALTIMERLO'),
                                 ('CS2UR.32', 'UR2,SR_GLOBALTIMERLO'),
                                 ('CS2UR', 'UR2,SR_GLOBALTIMERHI')]:
            broken = copy.deepcopy(doc)
            broken[1][0]['sass-instructions'][0] = dict(opcode=opcode,
                                                        operands=operands)
            a['sass_json'] = json.dumps(broken).encode()
            a['sass_lines'] = SASS.replace('CS2R R2, SR_GLOBALTIMERLO',
                                           opcode + ' ' + operands).encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**a)

    def test_failed_map_can_be_revalidated_from_original_inputs(self):
        from flagtree.profiler.timeline_unit_nvidia import load_counter_machine_map
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = args()
            binary = data['binary_id']
            prefix = 'machine/' + binary
            (root / prefix).mkdir(parents=True)
            artifacts = []
            for suffix in ['cubin', 'ptx']:
                name = 'kernel.' + suffix
                raw = data[suffix]
                (root / name).write_bytes(raw)
                artifacts.append(
                    dict(retained_file=name,
                         sha256=hashlib.sha256(raw).hexdigest()))
            (root / prefix / 'lines.stdout').write_bytes(data['sass_lines'])
            (root / prefix / 'json.stdout').write_bytes(data['sass_json'])
            capture = dict(machine_counter_mapping=dict(
                status='counter_mapping_unavailable', binary_id=binary),
                           metadata=dict(
                               binary_id=binary,
                               timeline_artifacts=artifacts,
                               compiler_metadata=dict(
                                   target=dict(backend='cuda', arch=120)),
                               scope_id_names=[['0', 'region']]),
                           owner=dict(plan=dict(timeline_marker_version=1)))
            original = copy.deepcopy(capture)
            actual = load_counter_machine_map(root, capture)
            self.assertEqual(actual, machine.counter_map(**data))
            self.assertEqual(capture, original)
            self.assertFalse((root / prefix / 'counter-map.json').exists())
            for change in [
                    dict(binary_id='b' * 64),
                    dict(status='unavailable_tool_missing'),
                    dict(counter_map_file=prefix + '/counter-map.json')
            ]:
                broken = copy.deepcopy(capture)
                broken['machine_counter_mapping'].update(change)
                with self.assertRaises(ValueError):
                    load_counter_machine_map(root, broken)
            (root / prefix / 'json.stdout').unlink()
            with self.assertRaises(ValueError):
                load_counter_machine_map(root, capture)

    def test_complete_mapping_is_not_a_certificate(self):
        value = machine.counter_map(**args())
        self.assertEqual([(p['site_id'], p['phase'], p['pc'])
                          for p in value['counter_pcs']], [(0, 'entry', 0),
                                                           (0, 'exit', 16)])
        self.assertFalse(value['region_boundaries_verified'])
        self.assertFalse(value['clock_qualified'])
        self.assertNotIn('time_ns', value)

    def test_actual_marker_spacing_and_debug_metadata_erasure(self):
        a = args()
        text = PTX.replace('entry;', 'entry ;').replace('exit;', 'exit ;')
        text = text.replace('.address_size 64', '.loc 1 3 0')
        text += '.file 1 "kernel.py"\n.section .debug_info\n{\n.b32 .debug_line\n.b8 3\n}\n'
        debug = DEBUG.replace('.address_size 64', '')
        debug += '\n.section .debug_info\n{\n\n\n}\n'
        a['ptx'], a['cubin'] = text.encode(), elf(debug)
        result = machine.counter_map(**a)
        self.assertEqual(len(result['counter_pcs']), 2)
        self.assertEqual([x['kind'] for x in result['ptx_debug_omissions']], [
            'location_directive', 'file_directive', 'dwarf_data', 'dwarf_data'
        ])
        self.assertFalse(result['region_boundaries_verified'])

    def test_metadata_erasure_cannot_hide_code_or_change_line_positions(self):
        for token in [
                'mov.u64 %rd9, %globaltimer;', '.b32 3',
                '.loc 1 3 0; add.u32 %r1, %r2, 1;'
        ]:
            a = args()
            a['ptx'] = PTX.replace('.address_size 64', token).encode()
            a['cubin'] = elf(DEBUG.replace('.address_size 64', ''))
            with self.assertRaises(ValueError):
                machine.counter_map(**a)
        a = args()
        a['ptx'] += b'.section .debug_info\n{\nadd.u32 %r1, %r2, 1;\n}\n'
        a['cubin'] = elf(DEBUG + '.section .debug_info\n{\n\n}\n')
        with self.assertRaises(ValueError):
            machine.counter_map(**a)
        for text in [
                PTX.replace('.address_size 64', '.loc 1 3 0'),
                PTX.replace('.address_size 64', '.file 1 "x.py"')
        ]:
            a = args()
            a['ptx'] = text.encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**a)

    def test_dwarf_code_label_address_erasure_preserves_executable_lines(self):
        source = [
            '.visible.entrykernel(){', '$L__func_begin18:',
            'mov.u64%rd1,%globaltimer;', '$L__tmp1:', '}',
            '.section.debug_info', '{', '.b64$L__func_begin18', '.b64$L__tmp1',
            '}'
        ]
        debug = list(source)
        debug[7:9] = ['', '']
        self.assertEqual(machine._bind_debug_lines(source, debug), [
            dict(line=8, kind='dwarf_address'),
            dict(line=9, kind='dwarf_address')
        ])
        changed = list(debug)
        changed[2] = 'mov.u64%rd1,0;'
        with self.assertRaisesRegex(ValueError, 'executable tokens'):
            machine._bind_debug_lines(source, changed)

    def test_dwarf_address_erasure_cannot_hide_unknown_symbols_or_code(self):
        for token in ('.b64$L__missing', '.b64$L__tmp1+8',
                      '.b64$L__tmp1;mov.u64%rd1,%globaltimer;',
                      'mov.u64%rd1,%globaltimer;'):
            source = ['$L__tmp1:', '.section.debug_info', '{', token, '}']
            debug = list(source)
            debug[3] = ''
            with self.assertRaisesRegex(ValueError, 'executable tokens'):
                machine._bind_debug_lines(source, debug)
        source = ['$L__tmp1:', '.b64$L__tmp1']
        with self.assertRaisesRegex(ValueError, 'executable tokens'):
            machine._bind_debug_lines(source, ['$L__tmp1:', ''])

    def test_actual_P2R_JSON_PR_is_an_operand_not_a_guard(self):
        data = args()
        doc = copy.deepcopy(DOC)
        doc[1][0]['length'] = 48
        doc[1][0]['sass-instructions'].insert(
            1, dict(opcode='P2R', predicate='PR', operands='R3,RZ,0x1'))
        text = SASS.replace('/*0010*/', '/*0020*/').replace(
            '//## File ".nv_debug_ptx_txt", line 8',
            '/*0010*/ P2R R3, PR, RZ, 0x1;\n//## File ".nv_debug_ptx_txt", line 8'
        )
        data.update(cubin=elf(text_bytes=48),
                    sass_lines=text.encode(),
                    sass_json=json.dumps(doc).encode())
        result = machine.counter_map(**data)
        self.assertEqual([r['pc'] for r in result['counter_pcs']], [0, 32])
        self.assertFalse(result['region_boundaries_verified'])
        for changed in ('P2R R3, PR, R1, 0x1', 'P2R R4, PR, RZ, 0x1',
                        'P2R R3, PR, RZ, 0x2', '@P0 P2R R3, PR, RZ, 0x1'):
            broken = dict(data,
                          sass_lines=text.replace('P2R R3, PR, RZ, 0x1',
                                                  changed).encode())
            with self.assertRaises(ValueError):
                machine.counter_map(**broken)
        for operands in ('R3,RZ,0x1;BRA', 'R3,PR,RZ,0x1', None):
            with self.assertRaisesRegex(ValueError, 'P2R register operands'):
                machine.normalized_json_instruction(
                    dict(opcode='P2R', predicate='PR', operands=operands))

    def test_missing_marker_does_not_guess_nearest_clock(self):
        a = args()
        a['ptx'] = PTX.replace('// flagprism_timeline_v1_site_0_entry;',
                               '').encode()
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_changed_source_tokens_or_line_numbers_rejected(self):
        for text in [PTX.replace('%rd1', '%rd3'), '\n' + PTX]:
            a = args()
            a['ptx'] = text.encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**a)

    def test_source_binding_does_not_confer_64bit_getter(self):
        a = args()
        a['ptx'] = PTX.replace('mov.u64', 'mov.u32').encode()
        a['cubin'] = elf(DEBUG.replace('mov.u64', 'mov.u32'))
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_wrong_ptx_line_is_not_nearest_clock(self):
        a = args()
        a['sass_lines'] = SASS.replace('line 6', 'line 5').encode()
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_actual_json_predicate_and_pc_must_match_text(self):
        for key, value in [('predicate', '@P1'), ('opcode', 'S2R'),
                           ('operands', 'R8,SR_GLOBALTIMERLO')]:
            a = args()
            doc = copy.deepcopy(DOC)
            doc[1][0]['sass-instructions'][0][key] = value
            a['sass_json'] = json.dumps(doc).encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**a)

    def test_complete_instruction_coverage_required(self):
        a = args()
        a['sass_lines'] = SASS.replace('/*0010*/ CS2R R4, SR_GLOBALTIMERLO;',
                                       '').encode()
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_foreign_scope_and_wrong_phase_rejected(self):
        for text in [
                PTX.replace('site_0_entry', 'site_1_entry'),
                PTX.replace('site_0_exit', 'site_0_entry')
        ]:
            a = args()
            a['ptx'] = text.encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**a)

    def test_duplicated_machine_pc_candidates_stay_static(self):
        a = args()
        doc = copy.deepcopy(DOC)
        f = doc[1][0]
        f['length'] = 48
        a['cubin'] = elf(text_bytes=48)
        f['sass-instructions'].insert(1, {
            'opcode': 'CS2R',
            'operands': 'R2,SR_GLOBALTIMERLO'
        })
        a['sass_json'] = json.dumps(doc).encode()
        a['sass_lines'] = SASS.replace(
            '//## File ".nv_debug_ptx_txt", line 8',
            '/*0010*/ CS2R R2, SR_GLOBALTIMERLO;\n//## File ".nv_debug_ptx_txt", line 8'
        ).replace('/*0010*/ CS2R R4', '/*0020*/ CS2R R4').encode()
        value = machine.counter_map(**a)
        self.assertEqual(len(value['counter_pcs']), 3)
        self.assertFalse(value['region_boundaries_verified'])

    def _nested(self):
        a = args()
        doc = copy.deepcopy(DOC)
        child = dict(
            doc[1][0], **{
                'function-name': '$kernel$clock',
                'start': 16,
                'length': 16,
                'sass-instructions': [doc[1][0]['sass-instructions'][1]]
            })
        doc[1][0]['sass-instructions'] = doc[1][0]['sass-instructions'][:1]
        doc[1].append(child)
        a['sass_json'] = json.dumps(doc).encode()
        a['sass_lines'] = SASS.replace(
            '//## File ".nv_debug_ptx_txt", line 8',
            '.type $kernel$clock,@function\n$kernel$clock:\n//## File ".nv_debug_ptx_txt", line 8'
        ).encode()
        return a, doc

    def test_explicit_nonzero_helper_in_parent_section(self):
        a, _ = self._nested()
        result = machine.counter_map(**a)
        child = result['counter_pcs'][1]
        self.assertEqual((child['function'], child['section'], child['pc'],
                          child['function_start'], child['relative_pc']),
                         ('$kernel$clock', '.text.kernel', 16, 16, 0))
        self.assertFalse(result['region_boundaries_verified'])
        self.assertEqual(len(result['function_ranges']), 2)

    def test_helper_cannot_be_inferred_from_pc_or_name(self):
        a, _ = self._nested()
        a['sass_lines'] = a['sass_lines'].replace(b'$kernel$clock:\n',
                                                  b'nearby_clock:\n')
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_function_body_and_elf_extents_are_checked(self):
        for field, value in [('start', True), ('start', 1), ('start', 0),
                             ('length', True), ('length', 0), ('length', 32)]:
            a, doc = self._nested()
            doc[1][1][field] = value
            a['sass_json'] = json.dumps(doc).encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**a)
        a = args()
        a['cubin'] = elf(text_bytes=16)
        with self.assertRaises(ValueError):
            machine.counter_map(**a)
        a = args()
        a['cubin'] = elf().replace(b'.text.kernel', b'.text.absent')
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def _called_helper(self):
        a = args()
        doc = copy.deepcopy(DOC)
        helper = dict(doc[1][0], **{
            'function-name': '$kernel$clock',
            'start': 16
        })
        doc[1][0]['length'] = 48
        doc[1][0]['sass-instructions'] = [
            dict(opcode='CALL.REL.NOINC', operands='$kernel$clock')
        ]
        doc[1].append(helper)
        a['cubin'] = elf(text_bytes=48)
        a['sass_json'] = json.dumps(doc).encode()
        a['sass_lines'] = (
            '.section .text.kernel,"ax",@progbits\n'
            '/*0000*/ CALL.REL.NOINC `($kernel$clock);\n'
            '$kernel$clock:\n' +
            SASS.split('\n', 1)[1].replace('/*0010*/', '/*0020*/').replace(
                '/*0000*/', '/*0010*/')).encode()
        return a, doc

    def test_actual_direct_calls_bind_all_helper_reads(self):
        a, _ = self._called_helper()
        value = machine.counter_map(**a)
        self.assertEqual(value['static_model_version'], 1)
        self.assertEqual(len(value['call_sites']), 1)
        self.assertEqual(value['call_sites'][0]['callee'], '$kernel$clock')
        self.assertEqual(
            [len(x['direct_call_sites']) for x in value['counter_call_sites']],
            [1, 1])
        self.assertFalse(value['region_boundaries_verified'])
        self.assertFalse(value['clock_qualified'])

    def test_call_target_cannot_be_changed_in_either_tool_output(self):
        a, doc = self._called_helper()
        for side in ['text', 'json']:
            b = copy.deepcopy(a)
            if side == 'text':
                b['sass_lines'] = b['sass_lines'].replace(
                    b'`($kernel$clock)', b'`(other)')
            else:
                doc[1][0]['sass-instructions'][0]['operands'] = 'other'
                b['sass_json'] = json.dumps(doc).encode()
            with self.assertRaises(ValueError):
                machine.counter_map(**b)

    def test_unresolved_call_is_explicit_not_assigned_to_nearby_helper(self):
        a, doc = self._called_helper()
        doc[1][0]['sass-instructions'][0]['operands'] = 'external_clock'
        a['sass_json'] = json.dumps(doc).encode()
        a['sass_lines'] = a['sass_lines'].replace(b'`($kernel$clock)',
                                                  b'`(external_clock)')
        value = machine.counter_map(**a)
        self.assertEqual(value['call_sites'][0]['target_status'], 'unresolved')
        self.assertTrue(
            all(not x['direct_call_sites']
                for x in value['counter_call_sites']))

    def test_synchronization_operands_are_bound_without_claiming_dynamic_counts(
            self):
        a = args()
        doc = copy.deepcopy(DOC)
        doc[1][0]['length'] = 48
        doc[1][0]['sass-instructions'].insert(
            1, dict(opcode='DEPBAR.LE', operands='SB0,0x2'))
        a['cubin'] = elf(text_bytes=48)
        a['sass_json'] = json.dumps(doc).encode()
        a['sass_lines'] = SASS.replace(
            '//## File ".nv_debug_ptx_txt", line 8',
            '/*0010*/ DEPBAR.LE SB0, 0x2;\n//## File ".nv_debug_ptx_txt", line 8'
        ).replace('/*0010*/ CS2R R4', '/*0020*/ CS2R R4').encode()
        value = machine.counter_map(**a)
        self.assertEqual(value['synchronization_sites'][0]['operands'],
                         'SB0,0x2')
        self.assertNotIn('dynamic_count', value['synchronization_sites'][0])
        a['sass_lines'] = a['sass_lines'].replace(b'SB0, 0x2', b'SB0, 0x0')
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_call_reference_expansion_has_a_bounded_output(self):
        a, _ = self._called_helper()
        with patch.object(machine, 'MAX_CALL_REFERENCES', 1):
            with self.assertRaisesRegex(ValueError, 'reference budget'):
                machine.counter_map(**a)

    def test_malformed_elf_and_missing_debug_section(self):
        for blob in [
                b'\x7fELF',
                elf()[:250],
                elf().replace(b'.nv_debug_ptx_txt', b'.nv_debug_ptx_bad')
        ]:
            with self.assertRaises(ValueError):
                machine.embedded_ptx(blob)

    def test_boolean_versions_scopes_and_targets_rejected(self):
        for key, value in [('marker_version', True), ('scope_ids', (True, )),
                           ('expected_sm', (12, False))]:
            a = args()
            a[key] = value
            with self.assertRaises(ValueError):
                machine.counter_map(**a)
        a = args()
        doc = copy.deepcopy(DOC)
        doc[0]['SchemaVersion']['revision'] = False
        a['sass_json'] = json.dumps(doc).encode()
        with self.assertRaises(ValueError):
            machine.counter_map(**a)

    def test_quoted_comment_characters_are_preserved(self):
        a = args()
        old = '.address_size 64'
        new = '.file 1 "https://x/a // not a comment"'
        a['ptx'] = PTX.replace(old, new).encode()
        a['cubin'] = elf(DEBUG.replace(old, new))
        self.assertEqual(len(machine.counter_map(**a)['counter_pcs']), 2)

    def _inputs(self, root):
        rows = []
        for name, raw in [('x.cubin', elf()), ('x.ptx', PTX.encode())]:
            (root / name).write_bytes(raw)
            rows.append(
                dict(retained_file=name,
                     sha256=hashlib.sha256(raw).hexdigest()))
        return dict(
            binary_id='a' * 64,
            scope_id_names=[(0, 'one')],
            timeline_artifacts=rows,
            compiler_metadata={'target': {
                'backend': 'cuda',
                'arch': 120
            }})

    def _tool(self, root, body):
        path = root / 'tool'
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o700)
        return str(path)

    def test_tool_failure_is_durable_and_never_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._inputs(root)
            tool = self._tool(root, 'raise SystemExit(7)\n')
            with patch.dict(os.environ, FLAGTREE_NVDISASM=tool):
                first = machine.inspect_capture_binary(
                    root, metadata=meta, plan={'timeline_marker_version': 1})
                second = machine.inspect_capture_binary(
                    root, metadata=meta, plan={'timeline_marker_version': 1})
            self.assertEqual(first, second)
            self.assertEqual(first['status'], 'counter_mapping_unavailable')
            receipt = json.loads((root / 'machine' / ('a' * 64) /
                                  'commands.json').read_text())[0]
            self.assertEqual(receipt['returncode'], 7)
            self.assertEqual(receipt['state'], 'failed')

    def test_tool_timeout_is_owned_stopped_and_reaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._inputs(root)
            tool = self._tool(root, 'import time\ntime.sleep(30)\n')
            with patch.dict(os.environ, FLAGTREE_NVDISASM=tool):
                value = machine.inspect_capture_binary(
                    root,
                    metadata=meta,
                    plan={'timeline_marker_version': 1},
                    deadline=time.monotonic() + 0.1)
            self.assertEqual(value['status'], 'counter_mapping_unavailable')
            receipt = json.loads((root / 'machine' / ('a' * 64) /
                                  'commands.json').read_text())[0]
            self.assertEqual(receipt['state'], 'stopped')
            self.assertIsNotNone(receipt['returncode'])

    def test_tool_output_budget_is_not_a_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._inputs(root)
            tool = self._tool(root, 'print("x"*32768)\n')
            with patch.dict(os.environ, FLAGTREE_NVDISASM=tool), patch.object(
                    machine, 'LIMIT', 8192):
                value = machine.inspect_capture_binary(
                    root, metadata=meta, plan={'timeline_marker_version': 1})
            self.assertEqual(value['status'], 'counter_mapping_unavailable')
            self.assertIn('output budget', value['reason'])


if __name__ == '__main__': unittest.main()
