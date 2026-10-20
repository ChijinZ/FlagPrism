"""Real native typed-CFG admission, including forwarded SSA and clock markers."""
import argparse
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = '''module {
  llvm.func @timer() -> i64
  llvm.func @anonymous(%selected: i1, %limit: i32) {
    %zero = llvm.mlir.constant(0 : i32) : i32
    llvm.cond_br %selected, ^body(%zero : i32), ^exit
  ^body(%iteration: i32):
    %begin = llvm.call @timer() : () -> i64 loc("__flagprism_gcu_clock_v1__":7:1)
    %one = llvm.mlir.constant(1 : i32) : i32
    %next = llvm.add %iteration, %one : i32
    %ptr = llvm.mlir.undef : !llvm.ptr
    %word = llvm.getelementptr %ptr[6] : (!llvm.ptr) -> !llvm.ptr, i32
    %end = llvm.call @timer() : () -> i64 loc("__flagprism_gcu_clock_v1__":7:2)
    %again = llvm.icmp "slt" %next, %limit : i32
    llvm.cond_br %again, ^body(%next : i32), ^exit
  ^exit:
    llvm.return
  }
}
'''


class StructureTests(unittest.TestCase):
    tool = None
    output = None

    def inspect(self, source, name):
        path = self.output / (name + '.mlir')
        result = self.output / (name + '.json')
        path.write_text(source)
        child = subprocess.run(
            [str(self.tool), '--execution-structure',
             str(path),
             str(result)],
            capture_output=True,
            timeout=20)
        (self.output / (name + '.stderr')).write_bytes(child.stderr)
        return child, json.loads(
            result.read_text()) if result.exists() else None

    def test_forwarded_values_clock_markers_and_loop_edges(self):
        child, report = self.inspect(SOURCE, 'loop')
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        self.assertFalse(report['source_region_qualified'])
        self.assertFalse(report['native_schedule_qualified'])
        self.assertEqual(report['function'], 'anonymous')
        entry, body, exit_block = report['blocks']
        initial = entry['operations'][0]['results'][0]
        self.assertEqual(entry['operations'][-1]['successors'][0],
                         dict(block=body['id'], arguments=[initial]))
        addition = next(op for op in body['operations']
                        if op['operation'] == 'llvm.add')
        self.assertEqual(addition['operands'][0], body['arguments'][0])
        self.assertEqual(body['operations'][-1]['successors'][0],
                         dict(block=body['id'], arguments=addition['results']))
        compare = next(op for op in body['operations']
                       if op['operation'] == 'llvm.icmp')
        self.assertEqual(compare['predicate'], 'slt')
        address = next(op for op in body['operations']
                       if op['operation'] == 'llvm.getelementptr')
        self.assertEqual(address['constant_indices'], [6])
        self.assertEqual(address['element_type'], 'i32')
        self.assertEqual(address['result_types'], ['!llvm.ptr'])
        markers = [op for op in body['operations'] if 'clock_marker' in op]
        self.assertEqual([op['clock_marker'] for op in markers],
                         [dict(site=7, column=1),
                          dict(site=7, column=2)])
        self.assertTrue(all(op['callee'] == 'timer' for op in markers))
        self.assertEqual(exit_block['operations'][0]['operation'],
                         'llvm.return')

    def test_declarations_do_not_count_as_defined_functions(self):
        child, report = self.inspect('module { llvm.func @external() }',
                                     'declaration')
        self.assertNotEqual(child.returncode, 0)
        self.assertIsNone(report)

    def test_unique_marked_body_is_selected_through_a_defined_wrapper(self):
        text = SOURCE.replace(
            '\n}\n',
            '\n  llvm.func @wrapper(%selected: i1, %limit: i32) { llvm.call @anonymous(%selected, %limit) : (i1, i32) -> () llvm.return }\n}\n'
        )
        child, report = self.inspect(text, 'wrapper')
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        self.assertEqual(report['function'], 'anonymous')
        self.assertEqual(report['defined_callers'], ['wrapper'])

    def test_multiple_bodies_are_rejected(self):
        text = 'module { llvm.func @a() { llvm.return } llvm.func @b() { llvm.return } }'
        child, report = self.inspect(text, 'multiple')
        self.assertNotEqual(child.returncode, 0)
        self.assertIsNone(report)

    def test_unknown_nested_regions_are_not_flattened(self):
        text = 'module { llvm.func @a() { "unknown.region"() ({ "unknown.end"() : () -> () }) : () -> () llvm.return } }'
        child, report = self.inspect(text, 'nested')
        self.assertNotEqual(child.returncode, 0)
        self.assertIsNone(report)

    def test_input_byte_budget(self):
        child, report = self.inspect(' ' * (16 * 1024 * 1024 + 1), 'oversized')
        self.assertNotEqual(child.returncode, 0)
        self.assertIn(b'byte budget', child.stderr)
        self.assertIsNone(report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tool', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args, rest = parser.parse_known_args()
    StructureTests.tool = args.tool
    StructureTests.output = args.output
    args.output.mkdir(parents=True)
    unittest.main(argv=[__file__, *rest])
