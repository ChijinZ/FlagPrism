"""Static adapter contracts; run inside the backend container."""
import importlib.util
from pathlib import Path
import unittest

module_path = Path(__file__).resolve().parents[2] / 'Profiler/python/flagtree_profiler/execution_nvidia.py'
spec = importlib.util.spec_from_file_location('execution_nvidia', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BLOCKED = '''#blocked = #ttg.blocked<{sizePerThread = [1, 2], threadsPerWarp = [4, 8], warpsPerCTA = [2, 2], order = [1, 0]}>
module attributes {"ttg.num-warps" = 4 : i32, "ttg.threads-per-warp" = 32 : i32, "ttg.num-ctas" = 1 : i32} {
 %0 = tt.load %ptr {flagprism.source_op_id = "region-load"} : tensor<32x64xf32, #blocked>
 tt.store %ptr, %0 : tensor<32x64xf32, #blocked>
}'''


class TestExecutionMapping(unittest.TestCase):
    def test_blocked_coordinate_basis_and_explicit_source(self):
        result = module.build_execution_mapping({'ttgir': BLOCKED}, {'num_warps': 4}, binary_id='binary', source_operations=['region-load'])
        layout = result['layouts'][0]
        self.assertEqual(layout['warp_width'], 32)
        self.assertEqual(layout['warp_count'], 4)
        self.assertEqual(layout['nominal_tile_shape'], [8, 32])
        self.assertEqual(layout['coordinates'][0]['lane_coordinate'], '(lane // 8) % 4')
        self.assertEqual(len(result['source_associations']), 1)
        self.assertEqual(len(result['unassociated_sites']), 1)
        self.assertEqual(result['status'], 'partial')

    def test_names_and_metadata_do_not_create_source_identity(self):
        text = BLOCKED.replace(' {flagprism.source_op_id = "region-load"}', '')
        result = module.build_execution_mapping({'ttgir': text}, {'name': 'softmax', 'num_warps': 99})
        self.assertEqual(result['source_associations'], [])
        self.assertEqual(result['organization']['num-warps'], 4)

    def test_mma_keeps_cooperative_group_but_rejects_guessed_ownership(self):
        text = '#mma = #ttg.nvidia_mma<{versionMajor = 3, versionMinor = 0, warpsPerCTA = [4, 1], instrShape = [16, 64, 16]}>'
        result = module.build_execution_mapping({'ttgir': text}, {})
        self.assertEqual(result['layouts'][0]['version_major'], 3)
        self.assertEqual(result['layouts'][0]['instruction_shape'], [16, 64, 16])
        self.assertEqual(result['layouts'][0]['lane_element_ownership'], 'unsupported_by_this_adapter')

    def test_malformed_layout_stays_partial(self):
        result = module.build_execution_mapping({'ttgir': BLOCKED.replace('order = [1, 0]', 'order = [0, 0]')}, {})
        self.assertEqual(result['layouts'][0]['status'], 'partial')
        self.assertNotIn('coordinates', result['layouts'][0])

    def test_missing_ir_and_sampling_declaration(self):
        result = module.build_execution_mapping({}, {'instrumentation_mode': 'default:sampling_strategy=selective:sampling_options=0,2:granularity=warp', 'scope_id_names': [[7, 'body']]})
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(result['instrumentation_sampling']['options']['sampling_options'], '0,2')
        self.assertFalse(result['instrumentation_sampling']['observed_units'])
        self.assertEqual(result['instrumentation_scopes'], [[7, 'body']])


if __name__ == '__main__':
    unittest.main()
