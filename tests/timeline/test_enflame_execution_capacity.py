"""Bounded v3 capacity and loss accounting; fixtures are not hardware evidence."""
import struct
import unittest
from unittest.mock import patch

from flagtree.profiler.timeline_enflame import plan_enflame_storage
from flagtree.profiler.timeline_events_enflame_native import decode_execution_capture


def fixture(capacity, attempted=1):
    stride = 32 + 128 * capacity
    retained = min(attempted, capacity)
    raw = bytearray(stride)
    struct.pack_into('<8I', raw, 0, retained, capacity, attempted-retained,
                     0x20, 128, stride, attempted, 0)
    for index in range(retained):
        words = [0] * 32
        words[0:4] = [0x46504733, 1, index, 3]
        words[4], words[6] = index * 2, index * 2 + 1
        words[26], words[30], words[31] = 3, 0x55543033, 0x46504743
        struct.pack_into('<32I', raw, 32 + index*128, *words)
    metadata = dict(debug_record_layout='gcu_execution_timeline_v3',
                    debug_record_capacity=capacity, debug_record_size=128,
                    debug_dynamic_slot_bytes=stride,
                    debug_dynamic_storage_version=3,
                    debug_dynamic_publisher_version=3,
                    debug_dynamic_index_bits=32,
                    debug_dynamic_program_policy='runtime_first_last',
                    debug_execution_manifest=dict(
                        schema_version=1, record_layout='gcu_execution_timeline_v3',
                        capacity=capacity, record_size=128, slot_bytes=stride,
                        publication='first_last_at_return',
                        sites=[dict(id=1, kind=3, operation='gcu.matmul',
                                    location='loc("kernel.py":9:1)')]))
    return bytes(raw), metadata


def decode(capacity, attempted=1):
    raw, metadata = fixture(capacity, attempted)
    return decode_execution_capture(
        raw, compiler_metadata=metadata,
        identity=dict(capture_id='capture',invocation_id='invocation',binary_id='binary'),
        association=dict(evidence='direct_owned_compiled_kernel_launch',binary_id='binary'),
        grid=[1,1,1])['canonical']


class ExecutionCapacity(unittest.TestCase):
    def test_larger_capacity_retains_the_previously_lost_suffix(self):
        # A real Journey program attempted 8875 pairs. Keep the same fixture
        # stream while changing allocation; do not infer missing endpoints.
        with patch.dict('os.environ', {'FLAGTREE_PROFILER_TIMELINE_DOCUMENT_MB':'64'}):
            small = decode(4096, 8875)
            large = decode(16384, 8875)
        self.assertFalse(small['complete'])
        self.assertTrue(large['complete'])
        self.assertEqual(small['observers'][0]['dropped_records'], 2*(8875-4096))
        self.assertEqual(large['observers'][0]['dropped_records'], 0)
        self.assertEqual(len(large['events']), 8875)
        self.assertEqual(large['records'][:8192], small['records'])
        self.assertEqual(large['events'][-1]['end_tick'], 17749)

    def test_capacity_still_has_an_exact_upper_bound(self):
        self.assertTrue(decode(16384)['complete'])
        with self.assertRaisesRegex(ValueError, 'execution capacity'):
            decode(16385)

    def test_two_selected_programs_have_exact_bounded_allocation(self):
        _, metadata = fixture(16384)
        stride = 32 + 128*16384
        plan = dict(compiler_metadata=metadata)
        args = dict(grid=(2,1,1), scratch_size=stride,alignment=8,num_ctas=None,
                    max_raw_bytes=2*stride)
        actual = plan_enflame_storage(plan, **args)
        self.assertEqual(actual['raw_bytes'], 4194368)
        with self.assertRaisesRegex(ValueError, 'admission budget'):
            plan_enflame_storage(plan, **dict(args,max_raw_bytes=2*stride-1))
        metadata['debug_execution_manifest']['capacity'] = 4096
        with self.assertRaisesRegex(ValueError, 'geometry'):
            plan_enflame_storage(plan, **args)


if __name__ == '__main__':
    unittest.main()
