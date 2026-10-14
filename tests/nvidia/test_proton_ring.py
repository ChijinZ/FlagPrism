import importlib.util
from pathlib import Path
import struct
import unittest

path = Path(__file__).resolve(
).parents[2] / 'Profiler/python/flagtree_profiler/observations_nvidia.py'
spec = importlib.util.spec_from_file_location('observations_nvidia', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def ring(events, capacity=8):
    buffer_size = capacity * 8
    scratch = 20 + buffer_size
    header = struct.pack('<11I', 1, 4, 44, 44, scratch, 1, 1, 1, scratch, 1, 0)
    payload = bytearray(
        struct.pack('<5I', 0xDEADBEEF, 3, 5, buffer_size,
                    len(events) * 2) + bytes(buffer_size))
    for index, (site, end, tick) in enumerate(events):
        tag = (site << 23) | (int(end) << 31) | ((tick >> 32) & 2047)
        struct.pack_into('<2I', payload, 20 + (index % capacity) * 8, tag,
                         tick & 0xFFFFFFFF)
    return header + payload


class TestProtonRing(unittest.TestCase):

    def test_cycles_actor_occurrence_and_explicit_identity(self):
        result = module.decode_proton_ring(
            ring([(7, False, 100), (7, True, 120), (7, False, 130),
                  (7, True, 180)]),
            capture_id='buffer-1',
            invocation_id='launch-1',
            association_evidence={'basis': 'single_selected_launch'},
            scopes={7: 'body'})
        self.assertEqual(result['dropped_records'], 0)
        self.assertEqual(
            [event['duration_ticks'] for event in result['observations']],
            [20, 50])
        self.assertEqual(
            [event['occurrence'] for event in result['observations']], [0, 1])
        self.assertTrue(
            all(event['duration_ns'] is None
                for event in result['observations']))
        self.assertEqual(result['observations'][0]['actor'], 'SM:5/warp:0')

    def test_clock32_keeps_width_and_rejects_unverified_wrap(self):
        result = module.decode_proton_ring(ring([(7, False, 100),
                                                 (7, True, 120)]),
                                           capture_id='clock32',
                                           clock_bits=32)
        self.assertEqual(result['observations'][0]['clock']['wrap_bits'], 32)
        self.assertEqual(result['observations'][0]['clock']['encoding'],
                         'clock_low32')
        wrapped = module.decode_proton_ring(ring([(7, False, (1 << 32) - 4),
                                                  (7, True, 3)]),
                                            capture_id='clock32-wrap',
                                            clock_bits=32)
        self.assertEqual(wrapped['observations'], [])
        self.assertEqual(len(wrapped['unpaired_records']), 2)

    def test_overwritten_ring_rotates_and_reports_record_loss(self):
        result = module.decode_proton_ring(ring(
            [(7, False, 100), (7, True, 120), (7, False, 130), (7, True, 150),
             (7, False, 170), (7, True, 200)],
            capacity=4),
                                           capture_id='buffer-2')
        self.assertEqual(result['dropped_records'], 2)
        self.assertEqual([record['tick'] for record in result['records']],
                         [130, 150, 170, 200])
        self.assertEqual(
            [event['record_ordinal'] for event in result['observations']],
            [2, 4])
        self.assertTrue(
            all(event['occurrence'] is None
                for event in result['observations']))

    def test_no_invented_wrap_or_iteration(self):
        result = module.decode_proton_ring(ring([(2, False, 1 << 42),
                                                 (2, True, 5)]),
                                           capture_id='buffer-3')
        self.assertEqual(result['observations'], [])
        self.assertEqual(len(result['unpaired_records']), 2)

    def test_incomplete_scope_pair_preserved(self):
        result = module.decode_proton_ring(ring([(7, True, 120)]),
                                           capture_id='buffer-4')
        self.assertEqual(result['unpaired_records'][0]['reason'],
                         'exit_without_retained_entry')

    def test_request_distinguishes_collection_from_output(self):
        plan = module.lower_request({
            'semantics': ['source_control_interval'],
            'programs': [0],
            'sites': None,
            'max_events_per_instance': 256,
            'sample_every': 1
        })
        self.assertEqual(plan['mode_options']['buffer_size'], 4096)
        self.assertEqual(plan['collection_scope']['programs'], [0])
        decoded = module.decode_proton_ring(ring([(7, False, 100),
                                                  (7, True, 120)]),
                                            capture_id='selected')
        filtered = module.select_observations(decoded, plan)
        self.assertEqual(filtered['observations'], [])  # fixture program is 3
        self.assertEqual(filtered['output_filtered_intervals'], 1)
        self.assertEqual(filtered['dropped_records'], 0)

    def test_unsupported_request_never_becomes_completion(self):
        with self.assertRaises(ValueError):
            module.lower_request({'semantics': ['completion_checkpoint']})
        with self.assertRaises(ValueError):
            module.lower_request({'sample_every': 2})

    def test_bad_payload_and_scope_alias_are_rejected(self):
        with self.assertRaises(ValueError):
            module.decode_proton_ring(ring([])[:-1], capture_id='bad')
        with self.assertRaises(ValueError):
            module.decode_proton_ring(ring([]),
                                      capture_id='bad',
                                      scopes={263: 'aliased'})


if __name__ == '__main__':
    unittest.main()
