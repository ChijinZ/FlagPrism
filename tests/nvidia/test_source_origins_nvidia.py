import base64
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[2] / 'Profiler/python/flagtree_profiler/source_origins_nvidia.py'
spec = importlib.util.spec_from_file_location('source_origins_nvidia', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestScopeOrigins(unittest.TestCase):
    def test_emitted_boundaries_keep_binary_and_exact_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'example.py'
            data = b"begin\r\nwork\r\nend\r\n"
            source.write_bytes(data)
            file = {'kind': 'file_line_column', 'file': str(source), 'line': 1, 'column': 2}
            origins = {'0': {'semantic': 'source_region_origin', 'entry': [file], 'exit': [{**file, 'line': 3}]}}
            first, sources = module.capture_scope_origins(origins, binary_id='binary-A')
            second, _ = module.capture_scope_origins(origins, binary_id='binary-B')
            self.assertEqual(first['0']['status'], 'source_region_origin')
            self.assertEqual(first['0']['binary_id'], 'binary-A')
            self.assertEqual(second['0']['binary_id'], 'binary-B')
            self.assertEqual(base64.b64decode(sources[0]['content']), data)
            self.assertEqual(first['0']['source_capture'][0]['source_sha256'], hashlib.sha256(data).hexdigest())

    def test_parser_ir_location_is_not_original_source(self):
        location = {'kind': 'file_line_column', 'file': '/cache/generated.ttgir', 'line': 3, 'column': 0}
        result, _ = module.capture_scope_origins({'0': {'entry': [location], 'exit': [location]}},
                                                binary_id='B', compiler_ir_path='/cache/generated.ttgir')
        self.assertEqual(result['0']['status'], 'unknown')
        self.assertEqual(result['0']['entry'], [location])
        self.assertTrue(result['0']['capture_notes'])

    def test_callsite_does_not_replace_unknown_callee_with_caller(self):
        location = {'kind': 'callsite', 'callee': {'kind': 'unknown'},
                    'caller': {'kind': 'file_line_column', 'file': '/missing.py', 'line': 3, 'column': 4}}
        result, sources = module.capture_scope_origins({'7': {'entry': [location], 'exit': [location]}}, binary_id='B')
        self.assertEqual(result['7']['status'], 'unknown')
        self.assertEqual(result['7']['entry'][0], location)
        self.assertEqual(sources[0]['status'], 'unavailable')

    def test_fused_candidates_and_named_unknown_are_preserved(self):
        a = {'kind': 'file_line_column', 'file': '/a.py', 'line': 1, 'column': 0}
        b = {**a, 'file': '/b.py'}
        fused = {'kind': 'fused', 'candidates': [a, b], 'metadata': 'origin-set'}
        unknown = {'kind': 'named', 'descriptive_name': 'same_scope', 'child': {'kind': 'unknown'}}
        result, _ = module.capture_scope_origins({'0': {'entry': [fused], 'exit': [fused]},
                                                  '1': {'entry': [unknown], 'exit': [unknown]}}, binary_id='B')
        self.assertEqual(result['0']['status'], 'multiple_candidates')
        self.assertEqual(result['0']['entry'][0]['candidates'], [a, b])
        self.assertEqual(result['1']['status'], 'unknown')
