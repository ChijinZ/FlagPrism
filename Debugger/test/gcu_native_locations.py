"""Standard DWARF mapper fixtures, not hardware-timing evidence.

Run in the SDK Docker: python gcu_native_locations.py --tool TOOL.
The host assembler creates tiny ELF fixtures; real GCU objects are checked by
p01_enflame_native_locations.py and its retained-object companion.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeLocations(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def assemble(self, body):
        source = self.root / 'fixture.s'
        source.write_text(body)
        output = self.root / 'fixture.o'
        result = subprocess.run(
            [ASSEMBLER, '--gdwarf-4', '-o',
             str(output),
             str(source)],
            capture_output=True,
            timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return output

    def invoke(self, source, output=None):
        return subprocess.run([
            TOOL, '--native-locations',
            str(source),
            str(output or self.root / 'map.json')
        ],
                              capture_output=True,
                              timeout=20)

    def test_exact_site_and_phase_rows(self):
        source = self.assemble('''.text
.file 1 "__flagprism_gcu_clock_v1__"
.globl fixture
.type fixture,@function
fixture:
.loc 1 7 1
nop
.loc 1 7 2
ret
''')
        before = source.read_bytes()
        result = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        report = json.loads((self.root / 'map.json').read_text())
        points = {(r['site_id'], r['column'], r['section_offset'], r['phase'])
                  for r in report['locations']}
        self.assertEqual(points, {(7, 1, 0, 'begin_counter'),
                                  (7, 2, 1, 'end_counter')})
        self.assertFalse(report['source_region_qualified'])
        self.assertFalse(report['reader_valueflow_qualified'])
        self.assertEqual(source.read_bytes(), before)

    def test_unknown_columns_are_not_endpoint_proofs(self):
        source = self.assemble('''.text
.file 1 "__flagprism_gcu_clock_v1__"
.loc 1 7 9
nop
ret
''')
        result = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        report = json.loads((self.root / 'map.json').read_text())
        self.assertEqual(report['locations'], [])
        self.assertGreater(report['unsupported_column_rows'], 0)
        self.assertEqual(report['status'], 'unavailable')

    def test_other_source_files_are_not_clock_markers(self):
        source = self.assemble('''.text
.file 1 "ordinary.c"
.loc 1 7 1
nop
ret
''')
        result = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        report = json.loads((self.root / 'map.json').read_text())
        self.assertEqual(report['locations'], [])
        self.assertEqual(report['status'], 'unavailable')

    def test_invalid_elf_is_rejected_without_output(self):
        source = self.root / 'invalid.elf'
        source.write_bytes(b'\x7fELF\x02\x01')
        result = self.invoke(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'map.json').exists())

    def test_output_io_error_is_failure(self):
        source = self.assemble('''.text
.file 1 "__flagprism_gcu_clock_v1__"
.loc 1 7 1
nop
ret
''')
        self.assertNotEqual(self.invoke(source, self.root).returncode, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', type=Path, required=True)
    args = parser.parse_args()
    TOOL = str(args.tool.resolve(strict=True))
    ASSEMBLER = shutil.which('as')
    if ASSEMBLER is None:
        parser.error('The host GNU assembler is required for DWARF fixtures')
    unittest.main(argv=['gcu_native_locations.py'], verbosity=2)
