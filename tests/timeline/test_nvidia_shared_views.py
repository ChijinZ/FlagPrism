"""CPU protocol/association negatives; these are not device qualification."""
import copy
import struct
import unittest

from flagtree.profiler.timeline_nvidia import decode_timeline_ring
from flagtree.profiler.timeline_nvidia_async import derive_cp_async_facts


def fixture(operations, *, warp_count=1, capacity=64):
    metadata = 16 + warp_count * 4
    segment = capacity * 32
    scratch = metadata + segment * warp_count
    payload = bytearray(scratch)
    struct.pack_into('<4I', payload, 0, 0x46505433, 7, 2, segment * warp_count)
    for warp in range(warp_count):
        struct.pack_into('<I', payload, 16 + warp * 4, len(operations) * 16)
        for i, (site, address) in enumerate(operations):
            for phase in range(2):
                seq = i * 2 + phase
                tick = (1 << 63) + seq * 17
                offset = metadata + warp * segment + (seq % capacity) * 32
                struct.pack_into('<8I', payload, offset, site | (phase << 31),
                                 tick & 0xffffffff, tick >> 32, seq,
                                 int(address is not None), address or 0, 0, 0)
    options = dict(scratch_size=scratch,
                   total_warps=warp_count,
                   selected_warps=tuple(range(warp_count)),
                   slots=((0, 7), ),
                   scope_ids=frozenset(range(5)),
                   record_version=3)
    return payload, options


def plan():
    return dict(timeline_plan_version=1,
                timeline_record_version=3,
                schema_version=2,
                binary_id='binary',
                timeline_async_boundary_count=4,
                inventory=[
                    dict(selected=True,
                         scope_id=0,
                         operation='ttg.async_copy_global_to_local',
                         timeline_mechanism='nvidia.cp_async.submit'),
                    dict(selected=True,
                         scope_id=1,
                         operation='ttg.async_commit_group',
                         timeline_mechanism='nvidia.cp_async.commit'),
                    dict(selected=True,
                         scope_id=2,
                         operation='ttg.async_wait',
                         timeline_mechanism='nvidia.cp_async.wait',
                         timeline_wait_pending=0),
                    dict(selected=True, scope_id=3,
                         operation='ttg.local_load'),
                    dict(selected=True,
                         scope_id=4,
                         operation='ttg.async_wait',
                         timeline_mechanism='nvidia.cp_async.wait',
                         timeline_wait_pending=1)
                ])


def decode(operations, **options):
    payload, kwargs = fixture(operations, **options)
    return decode_timeline_ring(bytes(payload), **kwargs)


def facts(decoded, selected_plan=None, invocation='invocation'):
    return derive_cp_async_facts(
        decoded,
        plan() if selected_plan is None else selected_plan,
        capture_id='capture',
        invocation_id=invocation,
        binary_id='binary')


class SharedViewTests(unittest.TestCase):

    def test_actual_fields_and_zero_shared_address_are_preserved(self):
        decoded = decode([(0, 0), (1, None), (2, None), (3, 0)])
        first = decoded['records'][0]
        self.assertEqual(first['tick'], 1 << 63)
        self.assertEqual(first['raw_byte_length'], 32)
        self.assertEqual(first['association']['byte_address'], 0)
        self.assertEqual(first['association']['raw_byte_offset'],
                         first['raw_byte_offset'] + 16)
        self.assertEqual(len(facts(decoded)['shared_view_loads']), 1)
        self.assertEqual(
            facts(decoded)['model'], 'nvidia.cp_async.shared_views.v2')

    def test_reuse_follows_address_not_site_or_occurrence(self):
        sequence = [(0, 2048), (1, None), (2, None), (3, 2048), (0, 4096),
                    (1, None), (2, None), (3, 4096), (0, 2048), (1, None),
                    (2, None), (3, 2048)]
        result = facts(decode(sequence))
        versions = result['shared_view_generations']
        self.assertEqual([(v['byte_address'], v['generation'])
                          for v in versions], [(2048, 0), (4096, 0),
                                               (2048, 1)])
        self.assertEqual(
            [v['generation_id'] for v in result['shared_view_loads']],
            [v['id'] for v in versions])
        self.assertTrue(all(v['may_be_predicated_empty'] for v in versions))
        for load in result['shared_view_loads']:
            self.assertFalse(load['time_arrow_verified'])
            self.assertTrue(
                all(r in result['records'] for r in load['record_ids']))
            self.assertGreaterEqual(len(load['record_ids']), 8)

    def test_multiple_submits_to_one_view_in_one_group_share_generation(self):
        result = facts(
            decode([(0, 64), (0, 64), (1, None), (2, None), (3, 64)]))
        self.assertEqual(len(result['shared_view_generations']), 1)
        self.assertEqual(
            len(result['shared_view_generations'][0]['submit_operation_ids']),
            2)

    def test_missing_or_partial_wait_does_not_certify_load(self):
        for tail in [[(3, 64)], [(4, None), (3, 64)]]:
            result = facts(decode([(0, 64), (1, None), *tail]))
            self.assertIsNone(result['shared_view_loads'][0]['generation_id'])

    def test_uncommitted_same_origin_is_not_hidden_by_old_wait(self):
        result = facts(
            decode([(0, 64), (1, None), (2, None), (0, 64), (3, 64)]))
        load = result['shared_view_loads'][0]
        self.assertEqual(load['status'], 'uncommitted_same_origin')
        self.assertIsNone(load['generation_id'])

    def test_capture_and_observer_address_spaces_stay_separate(self):
        decoded = decode([(0, 64), (1, None), (2, None), (3, 64)],
                         warp_count=2)
        result = facts(decoded)
        self.assertEqual(
            len({v['id']
                 for v in result['shared_view_generations']}), 2)
        self.assertTrue(
            all(v['generation'] == 0
                for v in result['shared_view_generations']))
        self.assertNotEqual(
            result['shared_view_generations'][0]['id'],
            facts(decoded,
                  invocation='other')['shared_view_generations'][0]['id'])

    def test_loss_prevents_generation_assignment(self):
        decoded = decode([(0, 64), (1, None), (2, None), (3, 64)], capacity=4)
        result = facts(decoded)
        self.assertFalse(result['record_stream_complete'])
        self.assertEqual(result['shared_view_generations'], [])
        self.assertEqual(result['shared_view_loads'], [])

    def test_reserved_fields_unknown_kind_and_partial_counter_reject(self):
        for relative, value in [(16, 2), (24, 1), (28, 1)]:
            payload, options = fixture([(0, 64)])
            struct.pack_into('<I', payload, 20 + relative, value)
            with self.assertRaises(ValueError):
                decode_timeline_ring(bytes(payload), **options)
        payload, options = fixture([(0, 64)])
        struct.pack_into('<I', payload, 16, 4)
        with self.assertRaises(ValueError):
            decode_timeline_ring(bytes(payload), **options)

    def test_payload_and_manifest_cannot_disagree(self):
        original = decode([(0, 64), (1, None), (2, None), (3, 64)])
        for mutate in [
                lambda d: d['records'][0]['association'].update(
                    byte_address=True), lambda d: d['records'][0][
                        'association'].update(raw_byte_offset=0),
                lambda d: d['records'][0].update(association=None), lambda d:
                d['records'][1]['association'].update(byte_address=128),
                lambda d: d['records'][2].update(association=copy.deepcopy(d[
                    'records'][0]['association'])),
                lambda d: d.update(record_version=2)
        ]:
            bad = copy.deepcopy(original)
            mutate(bad)
            with self.assertRaises(ValueError):
                facts(bad)
        wrong = plan()
        wrong['inventory'][0]['operation'] = 'tt.dot'
        with self.assertRaises(ValueError):
            facts(original, wrong)


if __name__ == '__main__':
    unittest.main()
