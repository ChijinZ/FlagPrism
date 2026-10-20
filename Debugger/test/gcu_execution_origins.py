"""Read-only original-member extraction and normal producer agreement."""
import argparse
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = '''module {
  func.func @anonymous(%trip: index, %x: f32, %trace: !gcu.ptr<i32>) {
    %zero = arith.constant 0 : index
    %one = arith.constant 1 : index
    scf.for %i = %zero to %trip step %one {
      "gcu.border"() {enter = "triton_gcu.elementwise_fusion_region"} : () -> () loc(unknown)
      %sum = arith.addf %x, %x {flagtree.debug.op_id = 14 : i32, flagtree.debug.scope_id = 1 : i32} : f32 loc("fixture.py":13:4)
      "test.consume"(%sum) : (f32) -> ()
      "gcu.border"() {leave = "triton_gcu.elementwise_fusion_region"} : () -> () loc(unknown)
    }
    gpu.barrier
    return
  }
}
'''


class Origins(unittest.TestCase):
    tool = None
    output = None

    def inspect(self, text, name, maximum=8):
        source = self.output / (name + '.mlir')
        target = self.output / (name + '.json')
        source.write_text(text)
        before = source.read_bytes()
        child = subprocess.run([
            str(self.tool), '--execution-origins',
            str(source),
            str(target),
            str(maximum)
        ],
                               capture_output=True,
                               timeout=20)
        self.assertEqual(source.read_bytes(), before)
        (self.output / (name + '.stderr')).write_bytes(child.stderr)
        return child, json.loads(
            target.read_text()) if target.exists() else None

    def test_unknown_border_keeps_actual_body_members_and_loop(self):
        child, report = self.inspect(SOURCE, 'members')
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        self.assertEqual(report['status'], 'original_execution_sites_indexed')
        self.assertFalse(report['native_schedule_qualified'])
        self.assertFalse(report['source_exclusive_cost_qualified'])
        self.assertEqual([s['operation'] for s in report['sites']],
                         ['gpu.barrier', 'gcu.border'])
        site = report['sites'][1]
        self.assertEqual(site['location'], 'loc(unknown)')
        membership = site['source_membership']
        self.assertEqual(membership['status'],
                         'original_execution_members_indexed')
        source = next(m for m in membership['members']
                      if m['source_op_id'] == 14)
        self.assertEqual((source['scope_id'], source['file'], source['line']),
                         (1, 'fixture.py', 13))
        self.assertEqual(membership['enclosing_controls'][0]['operation'],
                         'scf.for')

    def test_normal_rewrite_has_the_same_original_membership(self):
        child, report = self.inspect(SOURCE, 'normal-before')
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        child = subprocess.run([
            str(self.tool),
            str(self.output / 'normal-before.mlir'),
            str(self.output / 'normal-after.mlir'),
            str(self.output / 'normal-plan.json'), '2', '8', '8'
        ],
                               capture_output=True,
                               timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        manifest = json.loads((self.output / 'normal-plan.json').read_text())
        self.assertEqual([s['source_membership'] for s in manifest['sites']],
                         [s['source_membership'] for s in report['sites']])
        self.assertTrue(manifest['user_program_preservation']
                        ['original_program_preserved'])
        child, _ = self.inspect(
            (self.output / 'normal-after.mlir').read_text(),
            'already-instrumented')
        self.assertNotEqual(child.returncode, 0)
        self.assertIn('uninstrumented', child.stderr.decode())

    def test_zero_budget_does_not_assign_a_fusion_site(self):
        child, report = self.inspect(SOURCE, 'zero', 0)
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        self.assertEqual([s['operation'] for s in report['sites']],
                         ['gpu.barrier'])

    def test_unpaired_border_does_not_claim_unrelated_members(self):
        text = SOURCE.replace(
            '"gcu.border"() {leave = "triton_gcu.elementwise_fusion_region"} : () -> () loc(unknown)',
            '')
        child, report = self.inspect(text, 'unpaired')
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        self.assertEqual([s['operation'] for s in report['sites']],
                         ['gpu.barrier'])
        self.assertTrue(
            all(m['source_op_id'] != 14 for s in report['sites']
                for m in s['source_membership']['members']))

    def test_shared_long_location_has_a_pre_copy_text_budget(self):
        original = next(line for line in SOURCE.splitlines()
                        if '%sum = arith.addf' in line)
        members = [
            '      %v' + str(i) + ' = arith.addf %x, %x : f32 loc(#shared)'
            for i in range(1023)
        ]
        members.append('      %sum = arith.addf %x, %x : f32 loc(#shared)')
        text = SOURCE.replace(original, '\n'.join(members))
        text += '#shared = loc("' + 'x' * 4096 + '":13:4)\n'
        child, report = self.inspect(text, 'shared-location-budget')
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        membership = report['sites'][1]['source_membership']
        self.assertEqual(membership['status'], 'unverified')
        self.assertEqual(membership['reason'],
                         'source_member_text_budget_exceeded')
        self.assertFalse(membership['source_exclusive_cost_qualified'])
        self.assertLess(len(membership['members']), 1024)

    def test_multiple_bodies_and_out_of_range_budget_are_rejected(self):
        child, _ = self.inspect(
            SOURCE.replace('\n}\n', '\n func.func @other() { return }\n}\n'),
            'multiple')
        self.assertNotEqual(child.returncode, 0)
        self.assertIn('one inlined', child.stderr.decode())
        child, _ = self.inspect(SOURCE, 'excessive', 129)
        self.assertNotEqual(child.returncode, 0)
        self.assertIn('budget', child.stderr.decode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tool', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args, rest = parser.parse_known_args()
    args.output.mkdir(parents=True)
    Origins.tool, Origins.output = args.tool, args.output
    unittest.main(argv=[__file__, *rest])
