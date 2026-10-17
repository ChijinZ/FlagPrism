"""Physical-protocol contract fixtures; these are not device capability evidence."""
import base64
import copy
import hashlib
import struct
import unittest

from flagtree.profiler.timeline_events import validate_raw_batch
from flagtree.profiler.timeline_events_enflame import canonicalize_enflame_capture


def fixture():
    # Inner finishes first; outer starts earlier but is appended after the inner.
    pairs = [(7, 20, 30), (8, 10, 40)]
    raw = struct.pack('<8I', 2, 2, 0, 0, 64, 160, 2, 0)
    for seq, (site, begin, end) in enumerate(pairs):
        raw += struct.pack('<HHIQQQQIIQQ', 7, 0, site, 2, begin, end, end-begin,
                           0, seq, seq, 0x465044594e563031)
    capture = dict(capture_status='decoded', record_layout='selected_dynamic_timeline_v1',
        capture_id='ir-capture-0', raw_base64=base64.b64encode(raw).decode(),
        raw_sha256=hashlib.sha256(raw).hexdigest(), runtime_metadata=dict(
            record_layout='selected_dynamic_timeline_v1', grid=[3,1,1],
            profiler_invocation_id='launch-1', profiler_association_evidence=dict(
                binary_id='a'*64, invocation_id='launch-1', scope_id=99,
                session_ids=[5], evidence='same_launch_metadata_object'),
            record_plan=[dict(op_id=i, scope_id=2, record_kind=7) for i in (7,8)]))
    metadata = dict(hash='a'*64, debug_protocol_version=2,
        debug_record_layout='selected_dynamic_timeline_v1', debug_clock_bits=46,
        debug_clock_domain='enflame.sdk.global_timer', debug_record_capacity=2,
        debug_dynamic_selected_program=2, debug_dynamic_selected_actor=0,
        debug_dynamic_sample_every=1, debug_automatic_plan=dict(selected_sites=[7,8]),
        debug_tracked_table=[dict(opId=i, scopeId=2, mlirOpName='test.op',
                                 sourceLoc=f'loc("kernel.py":{i}:1)') for i in (7,8)])
    return capture, metadata


def convert(capture=None, metadata=None, namespace='owning-session'):
    if capture is None:
        capture, metadata = fixture()
    return canonicalize_enflame_capture(capture, compiler_metadata=metadata, capture_id=namespace)


def replace_raw(capture, mutate):
    data = bytearray(base64.b64decode(capture['raw_base64']))
    mutate(data)
    capture['raw_base64'] = base64.b64encode(data).decode()
    capture['raw_sha256'] = hashlib.sha256(data).hexdigest()


class EnflameEventsTests(unittest.TestCase):
    def test_nested_pair_order_preserves_actual_reads_without_sorting(self):
        value = convert()
        self.assertEqual(value['schema_version'], 2)
        self.assertEqual([r['tick'] for r in value['records']], [20,30,10,40])
        self.assertEqual([r['offset'] for r in value['records']], [48,56,112,120])
        self.assertEqual([r['length'] for r in value['records']], [8]*4)
        self.assertTrue(value['complete'])
        self.assertTrue(all(e['iteration_id'] is None for e in value['events']))
        self.assertEqual(value['clock_status'], 'unverified')
        self.assertEqual(value['boundary_status'], 'unverified')
        self.assertIsNone(value['observers'][0]['physical_identity'])

    def test_v2_endpoint_stream_keeps_stricter_time_order(self):
        value = convert()
        value['observers'][0]['record_order'] = 'endpoint_stream'
        value['records'][2]['tick'] = 35
        value['events'][1]['start_tick'] = 35
        for event in value['events']:
            event['occurrence_basis'] = 'complete_entry_order'
        validate_raw_batch(value)
        value['records'][2]['tick'] = 10
        value['events'][1]['start_tick'] = 10
        with self.assertRaises(ValueError): validate_raw_batch(value)

    def test_export_local_ids_do_not_alias_owning_sessions(self):
        first, second = convert(namespace='session-one'), convert(namespace='session-two')
        for field in ['records', 'events', 'observers']:
            self.assertTrue({r['id'] for r in first[field]}.isdisjoint(r['id'] for r in second[field]))
        self.assertNotEqual(first['identity']['invocation_id'], second['identity']['invocation_id'])

    def test_raw_and_returned_snapshot_are_independent(self):
        capture, metadata = fixture()
        raw = capture['raw_base64']; value = convert(capture, metadata)
        value['observers'][0]['attributes']['enflame.native_association']['session_ids'].append(10)
        self.assertEqual(capture['runtime_metadata']['profiler_association_evidence']['session_ids'], [5])
        self.assertEqual(capture['raw_base64'], raw)

    def test_dropped_pairs_are_not_overwritten_or_synthetic_endpoints(self):
        capture, metadata = fixture()
        replace_raw(capture, lambda b: struct.pack_into('<8I', b, 0, 3,2,1,1,64,160,3,0))
        value = convert(capture, metadata); observer = value['observers'][0]
        self.assertFalse(value['complete'])
        self.assertEqual((observer['attempted_records'], observer['committed_records'],
                          observer['retained_records'], observer['dropped_records'],
                          observer['overwritten_records']), (6,4,4,2,0))
        self.assertEqual(len(value['events']), 2)
        self.assertTrue(all(e['kind']=='interval' for e in value['events']))

    def test_filtering_is_not_missing_history(self):
        capture, metadata = fixture(); metadata['debug_dynamic_sample_every'] = 2
        def alter(b):
            struct.pack_into('<I', b, 24, 4)
            struct.pack_into('<Q', b, 32+64+48, 2)
        replace_raw(capture, alter)
        value = convert(capture, metadata); observer = value['observers'][0]
        self.assertTrue(value['complete'])
        self.assertEqual(observer['filtered_records'], 4)
        self.assertEqual(observer['attempted_records'], 8)
        self.assertEqual(observer['dropped_records'], 0)

    def test_wrong_commit_site_actor_or_phase_ticks_rejected(self):
        mutations = [(32+56,'<Q',0), (32+4,'<I',99), (32+40,'<I',1),
                     (32+8,'<Q',1), (32+16,'<Q',1<<46), (32+24,'<Q',19),
                     (32+32,'<Q',11), (32+44,'<I',1), (32+48,'<Q',1)]
        for offset, fmt, value in mutations:
            capture, metadata = fixture()
            replace_raw(capture, lambda b: struct.pack_into(fmt,b,offset,value))
            with self.assertRaises(ValueError): convert(capture, metadata)

    def test_missing_or_wrong_launch_compiler_binding_rejected(self):
        for change in [lambda c,m: m.update(hash='b'*64),
                       lambda c,m: c['runtime_metadata'].update(profiler_invocation_id='other'),
                       lambda c,m: c['runtime_metadata']['profiler_association_evidence'].update(session_ids=[]),
                       lambda c,m: m.update(debug_dynamic_selected_program=True),
                       lambda c,m: m.update(debug_protocol_version=True),
                       lambda c,m: m.update(debug_clock_bits=64),
                       lambda c,m: m.update(debug_record_capacity=3),
                       lambda c,m: (m['debug_tracked_table'][0].update(scopeId=True),
                                    c['runtime_metadata']['record_plan'][0].update(scope_id=1)),
                       lambda c,m: c['runtime_metadata']['record_plan'][0].update(scope_id=3),
                       lambda c,m: m['debug_tracked_table'].append(copy.deepcopy(m['debug_tracked_table'][0]))]:
            capture, metadata = fixture(); change(capture, metadata)
            with self.assertRaises(ValueError): convert(capture, metadata)

    def test_bad_header_and_original_sha_rejected(self):
        for word, value in [(0,3),(1,3),(2,1),(3,1),(4,32),(5,32),(6,1),(7,1)]:
            capture, metadata = fixture()
            replace_raw(capture, lambda b: struct.pack_into('<I',b,word*4,value))
            with self.assertRaises(ValueError): convert(capture, metadata)
        capture, metadata = fixture(); capture['raw_sha256']='b'*64
        with self.assertRaises(ValueError): convert(capture, metadata)

    def test_pair_completion_cannot_regress_or_cross_pair_sequences(self):
        value = convert(); value['records'][3]['tick'] = 29
        value['events'][1]['end_tick'] = 29
        with self.assertRaises(ValueError): validate_raw_batch(value)
        value = convert(); value['records'][0]['sequence'] = 1
        with self.assertRaises(ValueError): validate_raw_batch(value)

    def test_count_types_and_unknown_order_or_version_rejected(self):
        for field, data in [('attempted_records', True), ('committed_records', 6),
                            ('dropped_records', 1), ('filtered_records', 1),
                            ('overwritten_records', 1), ('record_order', 'sort_by_clock')]:
            value = convert(); value['observers'][0][field] = data
            with self.assertRaises(ValueError): validate_raw_batch(value)
        for version in [True, 0, 3, 1]:
            value = convert(); value['schema_version'] = version
            with self.assertRaises(ValueError): validate_raw_batch(value)


if __name__ == '__main__':
    unittest.main()
