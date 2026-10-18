"""Synthetic finite-path negatives; real compiled objects are checked separately."""
import copy
import hashlib
import json
import unittest

from flagtree.profiler.timeline_nvidia_control import (
    derive_wait_control_brackets, inspect_wait_control_brackets)


def fixture(change=None):

    def op(opcode, operands='', **extra):
        return dict(opcode=opcode, operands=operands, **extra)

    root = [
        op('BRA', '0x30', predicate='@!P0'),
        op('MOV', 'R16,0x30'),
        op('CALL.REL.NOINC', '$clock_begin'),
        op('DEPBAR.LE', 'SB0,0x2'),
        op('BAR.SYNC.DEFER_BLOCKING', '0x0'),
        op('BRA', '0x80', predicate='@!P0'),
        op('MOV', 'R16,0x80'),
        op('CALL.REL.NOINC', '$clock_end'),
        op('EXIT')
    ]
    functions = [
        dict(**{'function-name': 'kernel'},
             start=0,
             length=144,
             **{'sass-instructions': root})
    ]
    for label, start in [('begin', 144), ('end', 192)]:
        functions.append(
            dict(**{'function-name': '$clock_' + label},
                 start=start,
                 length=48,
                 **{
                     'sass-instructions': [
                         op('CS2R', 'R2,SR_GLOBALTIMERLO'),
                         op('MOV', 'R17,0x0'),
                         op('RET.REL.NODEC', 'R16,kernel')
                     ]
                 }))
    if change:
        change(functions)
    text = ['.section .text.kernel,"ax",@progbits']
    for function in functions:
        text.append(function['function-name'] + ':')
        for i, row in enumerate(function['sass-instructions']):
            operands = row.get('operands', '')
            if row['opcode'].startswith('CALL'):
                operands = '`(' + operands + ')'
            elif row['opcode'].startswith('RET'):
                register, callee = operands.split(',')
                operands = register + ' `(' + callee + ')'
            text.append(
                '/*%04x*/ %s%s %s;' %
                (function['start'] + i * 16, row.get('predicate', '') +
                 ' ' if row.get('predicate') else '', row['opcode'], operands))
    lines = ('\n'.join(text) + '\n').encode()
    payload = json.dumps([{}, functions]).encode()
    machine_map = dict(
        status='counter_mapping_complete_region_unverified',
        expected_sm=[12, 0],
        binary_id='a' * 64,
        artifacts=dict(sass_lines_sha256=hashlib.sha256(lines).hexdigest(),
                       sass_json_sha256=hashlib.sha256(payload).hexdigest()),
        function_ranges=[
            dict(function=f['function-name'],
                 start=f['start'],
                 instruction_bytes=len(f['sass-instructions']) * 16,
                 section='.text.kernel') for f in functions
        ],
        counter_call_sites=[
            dict(function='$clock_' + label,
                 pc=start,
                 site_id=0,
                 phase=phase,
                 direct_call_sites=[dict(function='kernel', pc=pc)])
            for label, phase, start, pc in [('begin', 'entry', 144,
                                             32), ('end', 'exit', 192, 112)]
        ])
    plan = dict(binary_id='a' * 64,
                inventory=[
                    dict(selected=True,
                         scope_id=0,
                         timeline_mechanism='nvidia.cp_async.wait',
                         timeline_wait_pending=2)
                ])
    return dict(machine_map=machine_map,
                sass_lines=lines,
                sass_json=payload,
                plan=plan)


class WaitControlTests(unittest.TestCase):

    def test_guarded_wait_has_order_fact_without_other_qualifications(self):
        result = derive_wait_control_brackets(**fixture())
        row = result['sites'][0]
        self.assertEqual(row['status'], 'wait_control_order_checked')
        self.assertEqual(
            (row['begin_call_pc'], row['wait_pc'], row['end_call_pc']),
            (32, 48, 112))
        self.assertFalse(row['source_region_qualified'])
        self.assertFalse(row['record_value_provenance_verified'])
        self.assertFalse(row['participation_verified'])
        self.assertFalse(result['hardware_overlap_verified'])

    def reject(self, change, reason):
        result = derive_wait_control_brackets(**fixture(change))
        self.assertEqual(result['sites'][0]['status'], 'unverified')
        self.assertIn(reason, result['sites'][0]['reason'])

    def test_wait_operand_is_not_guessed_from_an_adjacent_instruction(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][3].update(
                operands='SB0,0x0'), 'Missing or ambiguous native wait')

    def test_predicate_change_invalidates_the_entry_guard_fact(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][4].update(
                opcode='ISETP.EQ.AND', operands='P0,PT,R1,R2,PT'),
            'Path escapes')

    def test_uniform_branch_operand_is_conditional_even_without_predicate_field(
            self):

        def change(fs):
            fs[0]['sass-instructions'][3] = dict(opcode='BRA.U',
                                                 operands='UP0,0x70')
            fs[0]['sass-instructions'][4] = dict(opcode='DEPBAR.LE',
                                                 operands='SB0,0x2')

        self.reject(change, 'can be bypassed')

    def test_entry_guard_cannot_be_bypassed_by_another_edge(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][8].update(opcode='BRA',
                                                            operands='0x10'),
            'guard can be bypassed')

    def test_backward_path_is_not_unrolled_or_assumed_to_terminate(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][4].update(opcode='BRA',
                                                            operands='0x30'),
            'Backward branch')

    def test_new_call_inside_wait_region_is_not_transparent(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][4].update(
                opcode='CALL.REL.NOINC', operands='$clock_begin'),
            'Unrecognized control')

    def test_predicated_wait_is_not_assumed_to_execute(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][3].update(predicate='@P2'),
            'Conditional native wait')

    def test_unknown_helper_side_effect_and_wrong_return_are_not_accepted(
            self):
        self.reject(
            lambda fs: fs[1]['sass-instructions'][1].update(
                opcode='LDG.E', operands='R17,[R2]'), 'timer leaf instruction')
        self.reject(
            lambda fs: fs[1]['sass-instructions'][2].update(
                operands='R16,another'), 'actual caller')
        self.reject(
            lambda fs: fs[1]['sass-instructions'][0].update(predicate='@P2'),
            'Conditional or oversized')

    def test_ambiguous_callers_are_not_paired_by_closest_pc(self):
        args = fixture()
        args['machine_map']['counter_call_sites'][0][
            'direct_call_sites'].append(dict(function='kernel', pc=16))
        result = derive_wait_control_brackets(**args)
        self.assertIn('ambiguous static callers', result['sites'][0]['reason'])

    def test_binary_or_artifact_mismatch_is_rejected(self):
        for field in ['sass_lines', 'sass_json']:
            args = fixture()
            args[field] += b' '
            with self.assertRaisesRegex(ValueError, 'Control inputs differ'):
                derive_wait_control_brackets(**args)
        args = fixture()
        args['plan']['binary_id'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'matching plan'):
            derive_wait_control_brackets(**args)

    def test_json_operands_are_bound_to_text_not_just_getter_names(self):
        args = fixture()
        doc = json.loads(args['sass_json'])
        doc[1][0]['sass-instructions'][4]['operands'] = '0x1'
        args['sass_json'] = json.dumps(doc).encode()
        args['machine_map']['artifacts']['sass_json_sha256'] = hashlib.sha256(
            args['sass_json']).hexdigest()
        with self.assertRaisesRegex(ValueError, 'operands differ'):
            derive_wait_control_brackets(**args)

    def test_report_does_not_mutate_the_plan_or_machine_map(self):
        args = fixture()
        original = copy.deepcopy(args)
        derive_wait_control_brackets(**args)
        self.assertEqual(args, original)

    def test_unrecognized_analysis_preserves_a_diagnostic_without_granting_a_fact(
            self):
        args = fixture()
        args['sass_lines'] += b' '
        result = inspect_wait_control_brackets(**args)
        self.assertEqual(result['status'],
                         'unverified_control_inputs_or_pattern')
        self.assertEqual(result['sites'], [])
        self.assertFalse(result['source_region_qualified'])
        self.assertFalse(result['clock_qualified'])

    def test_unknown_indirect_entry_cannot_validate_the_guard(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][8].update(opcode='BRX',
                                                            operands='R1'),
            'Unknown caller control')

    def test_wrong_rpc_and_helper_clobber_do_not_imply_fallthrough(self):
        self.reject(
            lambda fs: fs[0]['sass-instructions'][1].update(
                operands='R16,0x40'), 'checked caller return address')
        self.reject(
            lambda fs: fs[1]['sass-instructions'][1].update(
                operands='R16,0x0'), 'checked caller return address')
        self.reject(
            lambda fs: fs[1]['sass-instructions'][1].update(
                opcode='MOV.64', operands='R15,UR8'),
            'checked caller return address')


if __name__ == '__main__':
    unittest.main()
