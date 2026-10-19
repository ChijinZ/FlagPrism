"""Exercise the built GCU native scope bridge, not a mock or Python rewriter.

Run in the matching SDK Docker: python gcu_native_debug_scopes.py --tool TOOL.
Full retained-IR SDK validation and real kernels are separate integration tests.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = '''"builtin.module"() ({
  "llvm.func"() <{function_type = !llvm.func<i32 (i32)>, sym_name = "clock_marker"}> ({
  ^bb0(%x: i32):
    %c = "llvm.mlir.constant"() <{value = 3 : i32}> : () -> i32
    %r = "llvm.add"(%x, %c) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32 loc("__flagprism_gcu_clock_v1__":7:2)
    "llvm.return"(%r) : (i32) -> ()
  }) : () -> ()
}) : () -> ()
'''


class NativeScopes(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'input.mlir'
        self.source.write_text(SOURCE)
        self.output = self.root / 'output.mlir'

    def invoke(self, source=None, output=None):
        return subprocess.run([
            TOOL, '--debug-scopes',
            str(source or self.source),
            str(output or self.output)
        ],
                              capture_output=True,
                              timeout=20)

    def test_scopes_preserve_marker_and_sdk_overflow_encoding(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        text = self.output.read_text()
        self.assertIn('__flagprism_gcu_clock_v1__":7:2', text)
        self.assertIn('#llvm.di_subprogram<', text)
        self.assertIn('#llvm.di_lexical_block_file<', text)
        self.assertIn('#llvm.overflow<none>', text)
        self.assertEqual(self.source.read_text(), SOURCE)

    def test_existing_scopes_can_be_parsed_again(self):
        first = self.invoke()
        self.assertEqual(first.returncode, 0, first.stderr.decode())
        result = self.invoke(self.output, self.root / 'second.mlir')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn('__flagprism_gcu_clock_v1__":7:2',
                      (self.root / 'second.mlir').read_text())

    def test_malformed_ir_rejected_without_output(self):
        self.source.write_text('module { llvm.func @broken(')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_missing_input_rejected_without_output(self):
        result = self.invoke(self.root / 'missing.mlir')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_output_io_error_is_failure(self):
        result = self.invoke(output=self.root)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', type=Path, required=True)
    args = parser.parse_args()
    TOOL = str(args.tool.resolve(strict=True))
    unittest.main(argv=['gcu_native_debug_scopes.py'], verbosity=2)
