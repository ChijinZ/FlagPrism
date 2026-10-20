"""Real native GCU rewrite and exact-reproduction checks; run inside the SDK Docker."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = '''module {
  func.func private @observer_escape(memref<40xi32>)
  func.func @anonymous(%state: !gcu.ptr<i32>, %trace: !gcu.ptr<i32>) {
    %zero = arith.constant 0 : index
    %one = arith.constant 1 : i32
    %state_view = "gcu.ptr2memref"(%state) : (!gcu.ptr<i32>) -> memref<1xi32>
    %old = memref.load %state_view[%zero] : memref<1xi32>
    %next = arith.addi %old, %one : i32
    memref.store %next, %state_view[%zero] : memref<1xi32>
    %temporary = memref.alloc() : memref<1xi32>
    %tag = memref.alloc() {gcu_private_tag} : memref<1xi32>
    %count = arith.constant 1 : index
    "memref.dma_start"(%temporary, %zero, %state_view, %zero, %count, %tag, %zero) : (memref<1xi32>, index, memref<1xi32>, index, index, memref<1xi32>, index) -> ()
    "memref.dma_wait"(%tag, %zero, %count) : (memref<1xi32>, index, index) -> ()
    memref.dealloc %tag : memref<1xi32>
    memref.dealloc %temporary : memref<1xi32>
    gpu.barrier
    return
  }
}
'''


class Preservation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.before = self.root / 'before.mlir'
        self.after = self.root / 'after.mlir'
        self.plan = self.root / 'plan.json'
        self.before.write_text(SOURCE)
        result = self.run_tool(self.before, self.after, self.plan, '1', '1')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.text = self.after.read_text()
        self.ring = re.search(
            r'(%[\w]+) = "memref.alloc"\([^\n]*memref<40xi32>', self.text)[1]
        self.state = re.search(
            r'(%[\w]+) = "gcu.ptr2memref"\((%[\w]+)\)[^\n]*memref<1xi32>',
            self.text)

    def run_tool(self, *args):
        return subprocess.run([TOOL, *(str(arg) for arg in args)],
                              capture_output=True,
                              timeout=20)

    def check(self, text):
        self.after.write_text(text)
        return self.run_tool('--check-preservation', self.before, self.after,
                             self.root / 'certificate.json', '1', '1', '8')

    def add_observation(self, extra=''):
        # Insert inside the lifetime of the fresh ring, before any original
        # program operation. Explicit SSA names remain unique in this fixture.
        line = next(line for line in self.text.splitlines()
                    if f'{self.ring} = "memref.alloc"' in line)
        code = f'''
    %obs_index = "arith.constant"() <{{value = 0 : index}}> : () -> index
    %obs_address = "gcu.ptr2int"({self.state[2]}) : (!gcu.ptr<i32>) -> i64
    %obs_low = "llvm.trunc"(%obs_address) : (i64) -> i32
    "memref.store"(%obs_low, {self.ring}, %obs_index) : (i32, memref<40xi32>, index) -> ()
{extra}'''
        return self.text.replace(line, line + code, 1)

    def rejected(self, text, reason):
        result = self.check(text)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(reason, result.stderr.decode())
        self.assertFalse((self.root / 'certificate.json').exists())

    def test_real_rewrite_carries_certificate(self):
        proof = json.loads(self.plan.read_text())['user_program_preservation']
        self.assertTrue(proof['original_program_preserved'])
        self.assertTrue(proof['observer_memory_isolated'])
        self.assertFalse(proof['native_timing_boundary_qualified'])
        self.assertEqual(self.check(self.text).returncode, 0)

    def test_actual_producer_records_addresses_as_data(self):
        self.assertIn('gcu.ptr2int', self.text)
        self.assertIn('llvm.trunc', self.text)
        result = self.check(self.text)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_saved_bits_cannot_change_original_program(self):
        text = self.add_observation()
        pattern = r'"memref.store"\((%[\w]+), ' + re.escape(self.state[1])
        match = re.search(pattern, text)
        self.assertIsNotNone(match)
        text = text[:match.start(1)] + '%obs_low' + text[match.end(1):]
        self.rejected(text, 'Actual GCU output differs from checked producer')

    def test_saved_bits_cannot_escape_to_unknown_helper(self):
        extra = f'    "func.call"({self.ring}) <{{callee = @observer_escape}}> : (memref<40xi32>) -> ()\n'
        self.rejected(self.add_observation(extra),
                      'Actual GCU output differs from checked producer')

    def test_saved_bits_cannot_index_original_memory(self):
        # This catches laundering via an ordinary integer offset, without any
        # inttoptr operation. The new write targets original program memory.
        # Put it after the original view definition so SSA is valid.
        text = self.add_observation()
        line = next(line for line in text.splitlines()
                    if f'{self.state[1]} = "gcu.ptr2memref"' in line)
        extra = f'''
    %obs_loaded = "memref.load"({self.ring}, %obs_index) : (memref<40xi32>, index) -> i32
    %obs_offset = "arith.index_cast"(%obs_loaded) : (i32) -> index
    "memref.store"(%obs_low, {self.state[1]}, %obs_offset) : (i32, memref<1xi32>, index) -> ()
'''
        self.rejected(text.replace(line, line + extra, 1),
                      'Actual GCU output differs from checked producer')

    def test_added_read_of_original_memory_rejected(self):
        line = next(line for line in self.text.splitlines()
                    if f'{self.state[1]} = "gcu.ptr2memref"' in line)
        extra = f'''
    %extra_zero = "arith.constant"() <{{value = 0 : index}}> : () -> index
    %extra_read = "memref.load"({self.state[1]}, %extra_zero) : (memref<1xi32>, index) -> i32
'''
        self.rejected(self.text.replace(line, line + extra, 1),
                      'Actual GCU output differs from checked producer')

    def test_navigation_location_change_is_not_a_program_change(self):
        text = self.text.replace('__flagprism_gcu_clock_v1__',
                                 'navigation_only.py')
        self.assertNotEqual(text, self.text)
        result = self.check(text)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        proof = json.loads((self.root / 'certificate.json').read_text())
        self.assertFalse(proof['actual_output_bytes_identical'])
        self.assertTrue(proof['actual_output_program_core_identical'])
        self.assertFalse(proof['native_timing_boundary_qualified'])

    def test_reserved_clock_cannot_resolve_to_local_side_effects(self):
        local_getter = '''
  llvm.mlir.global internal @counter(0 : i32) : i32
  llvm.func @flagprism_gcu_clock_identity_v1() -> i32 {
    %ptr = llvm.mlir.addressof @counter : !llvm.ptr
    %old = llvm.load %ptr : !llvm.ptr -> i32
    %one = llvm.mlir.constant(1 : i32) : i32
    %next = llvm.add %old, %one : i32
    llvm.store %next, %ptr : i32, !llvm.ptr
    llvm.return %old : i32
  }
'''
        self.before.write_text(
            SOURCE.replace('module {', 'module {' + local_getter, 1))
        result = self.run_tool(self.before, self.root / 'shadow.mlir',
                               self.root / 'shadow.json', '1', '1')
        self.assertGreater(result.returncode, 0)
        self.assertIn('reserved clock declaration', result.stderr.decode())
        self.assertFalse((self.root / 'shadow.mlir').exists())

    def test_reserved_clock_signature_must_be_exact(self):
        for signature in ('(...) -> i32', '() -> i64'):
            with self.subTest(signature=signature):
                self.before.write_text(
                    SOURCE.replace(
                        'module {',
                        'module {\n  llvm.func @flagprism_gcu_clock_identity_v1'
                        + signature + '\n', 1))
                result = self.run_tool(self.before,
                                       self.root / 'signature.mlir',
                                       self.root / 'signature.json', '1', '1')
                self.assertGreater(result.returncode, 0)
                self.assertIn('reserved clock declaration',
                              result.stderr.decode())

    def test_hidden_argument_wraparound_rejected(self):
        zero_args = self.root / 'zero-args.mlir'
        zero_args.write_text(
            'module { func.func @empty() { gpu.barrier return } }')
        result = self.run_tool(zero_args, self.root / 'invalid.mlir',
                               self.root / 'invalid.json', '4294967295', '1')
        self.assertGreater(result.returncode, 0)
        self.assertIn('hidden argument', result.stderr.decode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', type=Path, required=True)
    args = parser.parse_args()
    TOOL = str(args.tool.resolve(strict=True))
    unittest.main(argv=['gcu_execution_preservation.py'], verbosity=2)
