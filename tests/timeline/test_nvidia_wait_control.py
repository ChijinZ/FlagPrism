"""Synthetic finite-path negatives; real compiled objects are checked separately."""
import copy
import hashlib
import json
import unittest

from flagtree.profiler.timeline_nvidia_control import (
    derive_wait_control_brackets, inspect_wait_control_brackets)


def fixture(change=None, *, stores=False):

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
    if stores:
        root = [
            op('BRA', '0x70', predicate='@!P0'),
            op('MOV', 'R16,0x30'),
            op('CALL.REL.NOINC', '$clock_begin'),
            op('MOV', 'R21,R2'),
            op('MOV', 'R22,R3'),
            op('MOV', 'R20,0x0', predicate='@P2'),
            op('STS.128', '[R8+0x2000],R20', predicate='@P2'),
            op('DEPBAR.LE', 'SB0,0x2'),
            op('BAR.SYNC.DEFER_BLOCKING', '0x0'),
            op('BRA', '0x100', predicate='@!P0'),
            op('MOV', 'R16,0xc0'),
            op('CALL.REL.NOINC', '$clock_end'),
            op('MOV', 'R25,R2'),
            op('MOV', 'R26,R3'),
            op('MOV', 'R24,0x80000000', predicate='@P2'),
            op('STS.128', '[R8+0x2000],R24', predicate='@P2'),
            op('EXIT')
        ]
    root_length = len(root) * 16
    begin_helper, end_helper = root_length, root_length + 48
    end_call = 176 if stores else 112
    functions = [
        dict(**{'function-name': 'kernel'},
             start=0,
             length=root_length,
             **{'sass-instructions': root})
    ]
    for label, start in [('begin', begin_helper), ('end', end_helper)]:
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
            for label, phase, start, pc in [(
                'begin', 'entry', begin_helper,
                32), ('end', 'exit', end_helper, end_call)]
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


class StoreValueFlowTests(unittest.TestCase):

    def report(self, change=None):
        row = derive_wait_control_brackets(
            **fixture(change, stores=True))['sites'][0]
        self.assertEqual(row['status'], 'wait_control_order_checked')
        return row['endpoint_store_value_flows']

    def test_clock_words_and_both_phase_tags_reach_vector_store(self):
        flows = self.report()
        self.assertEqual([r['status'] for r in flows],
                         ['counter_to_shared_store_values_checked'] * 2)
        self.assertEqual([r['tag_word'] for r in flows], [0, 1 << 31])
        self.assertEqual(flows[0]['word_registers'],
                         ['R20', 'R21', 'R22', 'R23'])
        self.assertFalse(flows[0]['record_storage_binding_verified'])
        self.assertFalse(flows[0]['call_dominates_store_verified'])
        self.assertFalse(flows[0]['record_value_provenance_verified'])

    def test_reversed_timer_words_do_not_acquire_provenance(self):

        def change(fs):
            fs[0]['sass-instructions'][3]['operands'] = 'R21,R3'
            fs[0]['sass-instructions'][4]['operands'] = 'R22,R2'

        self.assertEqual(self.report(change)[0]['status'], 'unverified')

    def test_overwritten_high_word_and_wrong_tag_are_rejected(self):
        for index, operands in [(4, 'R22,0x0'), (5, 'R20,0x100')]:
            with self.subTest(index=index):
                flows = self.report(lambda fs: fs[0]['sass-instructions'][
                    index].update(operands=operands))
                self.assertEqual(flows[0]['status'], 'unverified')

    def test_same_predicate_name_after_a_write_is_a_different_guard(self):

        def change(fs):
            rows = fs[0]['sass-instructions']
            rows[3] = dict(opcode='MOV', operands='R20,0x0', predicate='@P2')
            rows[4] = dict(opcode='MOV.64', operands='R21,R2')
            rows[5] = dict(opcode='ISETP.EQ.AND', operands='P2,PT,R1,R2,PT')

        self.assertEqual(self.report(change)[0]['status'], 'unverified')

    def test_tag_guard_must_cover_the_actual_store(self):
        flows = self.report(
            lambda fs: fs[0]['sass-instructions'][6].update(predicate='@P3'))
        self.assertEqual(flows[0]['status'], 'unverified')

    def test_second_word_of_helper_wide_move_cannot_silently_clobber_clock(
            self):
        flows = self.report(lambda fs: fs[1]['sass-instructions'][1].update(
            opcode='MOV.64', operands='R1,RZ'))
        self.assertEqual(flows[0]['status'], 'unverified')

    def test_unknown_write_after_exit_call_keeps_order_but_loses_value_fact(
            self):
        flows = self.report(lambda fs: fs[0]['sass-instructions'][13].update(
            opcode='UNKNOWN', operands='R26,R3'))
        self.assertEqual(flows[1]['status'], 'unverified')

    def test_value_flow_does_not_claim_an_address_or_raw_record_proof(self):
        flows = self.report(lambda fs: fs[0]['sass-instructions'][6].update(
            operands='[R9+0x1000],R20'))
        self.assertEqual(flows[0]['status'],
                         'counter_to_shared_store_values_checked')
        self.assertFalse(flows[0]['record_storage_binding_verified'])

    def test_unknown_move_family_is_not_assumed_to_be_a_scalar_move(self):

        def change(fs):
            rows = fs[0]['sass-instructions']
            rows[12] = dict(opcode='MOV.64', operands='R25,R2')
            rows[13] = dict(opcode='MOVM.16.MT88', operands='R22,R1')

        self.assertEqual(self.report(change)[1]['status'], 'unverified')

    def test_unknown_opcode_invalidates_entry_predicate_fact(self):
        result = derive_wait_control_brackets(
            **fixture(lambda fs: fs[0]['sass-instructions'][4].update(
                opcode='UNKNOWN', operands='R1,R2')))
        self.assertEqual(result['sites'][0]['status'], 'unverified')


if __name__ == '__main__':
    unittest.main()
