"""Synthetic GCU compact-ring fixtures; not producer/clock/device qualification."""
import base64
import copy
import hashlib
import struct
import unittest
from flagtree.profiler.timeline_events_enflame import canonicalize_enflame_capture
from flagtree.profiler.observations import ObservationRequest


def fixture(grid=(3,2,1)):
    total=grid[0]*grid[1]*grid[2]
    programs=[0] if total==1 else [0,total-1]
    rings=[]
    for index,program in enumerate(programs):
        ring=bytearray(160)
        struct.pack_into('<8I',ring,0,2,2,0,32,64,160,2,program)
        for ordinal,(site,begin,end) in enumerate([(7,20,30),(8,10,40)]):
            begin+=index*100;end+=index*100
            struct.pack_into('<HHIQQQQIIQQ',ring,32+ordinal*64,
                7,0,site,program,begin,end,end-begin,0,ordinal,ordinal,0x465044594e563031)
        rings.append(ring)
    raw=b''.join(rings)
    capture=dict(capture_status='raw_complete',record_layout='gcu_first_last_timeline_v2',
        raw_base64=base64.b64encode(raw).decode(),raw_sha256=hashlib.sha256(raw).hexdigest(),
        runtime_metadata=dict(record_layout='gcu_first_last_timeline_v2',grid=list(grid),
            profiler_invocation_id='launch-1',profiler_association_evidence=dict(
                binary_id='a'*64,invocation_id='launch-1',scope_id=99,
                session_ids=[5],evidence='same_launch_metadata_object'),
            record_plan=[dict(op_id=i,scope_id=2,record_kind=7) for i in (7,8)]))
    metadata=dict(hash='a'*64,debug_protocol_version=2,debug_record_layout='gcu_first_last_timeline_v2',
        debug_clock_bits=46,debug_clock_domain='enflame.sdk.global_timer',debug_record_capacity=2,
        debug_dynamic_selected_actor=0,debug_dynamic_sample_every=1,debug_dynamic_storage_version=2,
        debug_dynamic_index_bits=32,debug_dynamic_publisher_version=2,debug_dynamic_program_policy='runtime_first_last',debug_dynamic_slot_bytes=160,
        debug_automatic_plan=dict(selected_sites=[7,8]),debug_tracked_table=[
            dict(opId=i,scopeId=2,mlirOpName='test.op',sourceLoc=f'loc("kernel.py":{i}:1)') for i in (7,8)])
    return capture,metadata


def mutate_raw(capture,callback):
    data=bytearray(base64.b64decode(capture['raw_base64']));callback(data)
    capture['raw_base64']=base64.b64encode(data).decode();capture['raw_sha256']=hashlib.sha256(data).hexdigest()


def convert(capture,metadata):
    return canonicalize_enflame_capture(capture,compiler_metadata=metadata,capture_id='owning-session')


class FirstLastTests(unittest.TestCase):
    def test_two_real_coordinate_slots_and_whole_raw_offsets(self):
        capture,metadata=fixture();result=convert(capture,metadata)
        self.assertEqual([o['program_coordinates'] for o in result['observers']],[[0,0,0],[2,1,0]])
        self.assertEqual(len(result['events']),4)
        self.assertEqual(len(result['sources']),2)
        self.assertEqual([r['offset'] for r in result['records']],[48,56,112,120,208,216,272,280])
        self.assertEqual(result['raw_artifact'],dict(sha256=capture['raw_sha256'],bytes=320))
        self.assertEqual(len(result['backend_record_map']['enflame.dynamic_pairs.v2']),8)
        self.assertEqual(len({r['id'] for r in result['records']}),8)
        self.assertEqual(len({o['clock_domain_id'] for o in result['observers']}),2)
        self.assertTrue(result['complete'])
        self.assertEqual(result['clock_status'],'unverified')
        self.assertEqual(result['boundary_status'],'unverified')
        self.assertTrue(all(e['iteration_id'] is None for e in result['events']))

    def test_single_program_has_one_ring_and_no_duplicate_events(self):
        result=convert(*fixture((1,1,1)))
        self.assertEqual((len(result['observers']),len(result['events']),result['raw_artifact']['bytes']),(1,2,160))

    def test_slot_header_and_payload_programs_must_match_actual_grid(self):
        for offset,fmt,value in [(28,'<I',1),(160+28,'<I',0),(32+8,'<Q',5),(160+32+8,'<Q',0)]:
            capture,metadata=fixture()
            mutate_raw(capture,lambda b:struct.pack_into(fmt,b,offset,value))
            with self.assertRaises(ValueError):convert(capture,metadata)

    def test_initialized_empty_ring_is_not_mistaken_for_observed_program(self):
        capture,metadata=fixture()
        mutate_raw(capture,lambda b:struct.pack_into('<8I',b,160,0,2,0,0,64,160,0,5))
        with self.assertRaisesRegex(ValueError,'writer arrival'):
            convert(capture,metadata)
        # An actual entry marker with no selected region executions is distinct.
        mutate_raw(capture,lambda b:struct.pack_into('<I',b,160+12,32))
        value=convert(capture,metadata)
        self.assertEqual(value['observers'][1]['retained_records'],0)
        self.assertTrue(value['complete'])

    def test_loss_is_checked_for_every_selected_slot(self):
        capture,metadata=fixture()
        mutate_raw(capture,lambda b:struct.pack_into('<8I',b,0,3,2,1,33,64,160,3,0))
        result=convert(capture,metadata)
        self.assertFalse(result['complete'])
        self.assertEqual([o['complete'] for o in result['observers']],[False,True])
        self.assertEqual([o['dropped_records'] for o in result['observers']],[2,0])
        self.assertTrue(all(o['overwritten_records']==0 for o in result['observers']))
        self.assertEqual(len(result['events']),4)

    def test_layout_versions_types_and_extent_fail_closed(self):
        for field,value in [('debug_dynamic_storage_version',True),('debug_dynamic_storage_version',1),
            ('debug_dynamic_publisher_version',1),('debug_dynamic_publisher_version',True),('debug_dynamic_index_bits',64),('debug_dynamic_slot_bytes',161),
            ('debug_dynamic_program_policy','fixed'),('debug_dynamic_selected_program',0)]:
            capture,metadata=fixture();metadata[field]=value
            with self.assertRaises(ValueError):convert(capture,metadata)
        capture,metadata=fixture()
        mutate_raw(capture,lambda b:b.extend(bytes(160)))
        with self.assertRaises(ValueError):convert(capture,metadata)

    def test_returned_snapshot_and_native_namespaces_are_isolated(self):
        capture,metadata=fixture();saved=copy.deepcopy((capture,metadata));first=convert(capture,metadata)
        first['observers'][0]['attributes']['enflame.native_association']['session_ids'].append(23)
        self.assertEqual((capture,metadata),saved)
        second=canonicalize_enflame_capture(capture,compiler_metadata=metadata,capture_id='different-owner')
        self.assertNotEqual(first['identity'],second['identity'])

    def test_advanced_export_uses_exact_rows_and_separate_unverified_clocks(self):
        from flagtree.profiler.timeline_events_enflame import attach_enflame_timeline_export
        from flagtree.profiler.observations import from_ir_runs
        capture,metadata=fixture()
        source=dict(raw_buffer=base64.b64decode(capture['raw_base64']),
                    runtime_metadata=capture['runtime_metadata'],meta={})
        result=attach_enflame_timeline_export(source,metadata,capture_id='actual-export-owner')
        rows=from_ir_runs([result])
        self.assertEqual(len(rows),4)
        self.assertTrue(all(row['semantic']=='observer_region_elapsed' for row in rows))
        self.assertTrue(all(row['duration_ns'] is None for row in rows))
        self.assertEqual({row['program'] for row in rows},{0,5})
        self.assertEqual(len({row['clock']['domain'] for row in rows}),2)
        self.assertTrue(all(row['clock']['alignment']=='unverified' for row in rows))
        self.assertEqual(result['raw_buffer'],source['raw_buffer'])
        self.assertNotIn('capture_id',source['runtime_metadata'])
        self.assertEqual(result['canonical_timeline']['raw_artifact']['sha256'],capture['raw_sha256'])

    def test_canonical_capture_document_is_bound_to_retained_raw_bytes(self):
        from flagtree.profiler.timeline_events_enflame import attach_enflame_timeline_export
        from flagtree.profiler.profile import _validated_timeline_capture
        capture,metadata=fixture()
        run=dict(raw_buffer=base64.b64decode(capture['raw_base64']),
                 runtime_metadata=capture['runtime_metadata'])
        attached=attach_enflame_timeline_export(run,metadata,capture_id='actual-owner')
        normalized=dict(canonical_timeline=attached['canonical_timeline'],
                        raw_base64=capture['raw_base64'],raw_sha256=capture['raw_sha256'])
        self.assertEqual(_validated_timeline_capture(normalized),attached['canonical_timeline'])
        mutate_raw(normalized,lambda b:b.__setitem__(32,1))
        with self.assertRaisesRegex(ValueError,'contradicts retained raw'):
            _validated_timeline_capture(normalized)

    def test_other_advanced_lowering_cannot_silently_treat_first_last_as_all_grid(self):
        from flagtree.profiler.observations_nvidia import lower_request
        request=ObservationRequest(programs=None,program_policy='runtime_first_last',automatic=True)
        with self.assertRaisesRegex(ValueError,'does not support this program policy'):
            lower_request(request)

    def test_first_last_request_is_explicit_and_bounded(self):
        request=ObservationRequest(programs=None,program_policy='runtime_first_last',automatic=True,
                                   max_events_per_instance=4096)
        self.assertEqual(ObservationRequest.from_dict(request.as_dict()),request)
        for overrides in [{'programs':(0,)},{'automatic':False},{'max_events_per_instance':16385},
                          {'semantics':('counter',)}]:
            kwargs=dict(programs=None,program_policy='runtime_first_last',automatic=True)
            kwargs.update(overrides)
            with self.assertRaises(ValueError):ObservationRequest(**kwargs)


if __name__=='__main__':
    unittest.main()
