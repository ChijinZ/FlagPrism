"""Canonical semantics tests in Docker; synthetic records are not GPU evidence."""
import copy
import unittest

from flagtree.profiler.timeline_events import stable_id, validate_raw_batch
from flagtree.profiler.timeline_events_nvidia import canonicalize_nvidia_capture


def fixture(*, lost=False):
    owner = dict(capture_id='capture', invocation_id='invocation', binary_id='binary',
        layout=dict(grid=[3, 1, 1], raw_bytes=256),
        plan=dict(binary_id='binary', timeline_record_version=2, inventory=[
            dict(selected=True, scope_id=i, operation='test.op', selected_scope_name=f'site-{i}',
                 timeline_semantic='wait_bracket' if i else 'observer_region_elapsed',
                 location={'file':'kernel.py','line':i+1}) for i in (0, 1)]))
    pairs = [(0, 'entry', 10), (1, 'entry', 20), (1, 'exit', 30), (0, 'exit', 40)]
    if lost:
        pairs = [(1, 'exit', 20), (0, 'entry', 30), (0, 'exit', 40), (1, 'entry', 50)]
    start = 4 if lost else 0
    records = [dict(program=2, warp=0, site=site, phase=phase, tick=tick,
                    sequence=start+i, raw_byte_offset=32+i*16, raw_byte_length=16)
               for i, (site, phase, tick) in enumerate(pairs)]
    decoded = dict(record_version=2, complete=not lost, records=records,
        observers=[dict(program=2, warp=0, sm=5, complete=not lost,
            saturated=False, overwritten_records=start, written_records=start+4, retained_records=4)])
    return decoded, owner, dict(binary_id='binary', scope_id_origins={})


def normalize(*, lost=False):
    decoded, owner, metadata = fixture(lost=lost)
    return canonicalize_nvidia_capture(decoded, owner=owner, metadata=metadata,
                                      raw_sha256='a'*64, raw_bytes=256)


class EventsTests(unittest.TestCase):
    def reject(self, mutate):
        batch = normalize()
        mutate(batch)
        with self.assertRaises((ValueError, TypeError)):
            validate_raw_batch(batch)

    def test_nested_scopes_keep_actual_ticks_and_semantics(self):
        batch = normalize()
        self.assertTrue(batch['complete'])
        self.assertEqual(len(batch['events']), 2)
        self.assertEqual({e['semantic'] for e in batch['events']},
                         {'wait_bracket', 'observer_region_elapsed'})
        self.assertEqual({(e['start_tick'],e['end_tick']) for e in batch['events']},
                         {(10,40),(20,30)})
        self.assertTrue(all(e['iteration_id'] is None for e in batch['events']))

    def test_loss_keeps_orphans_without_fabricated_ends(self):
        batch = normalize(lost=True)
        self.assertFalse(batch['complete'])
        partial = [e for e in batch['events'] if e['kind']=='incomplete']
        self.assertEqual(len(partial), 2)
        self.assertEqual({(e['start_tick'],e['end_tick']) for e in partial}, {(None,20),(50,None)})
        self.assertEqual(len([e for e in batch['events'] if e['kind']=='interval']), 1)

    def test_wrong_capture_identity_rejected(self):
        self.reject(lambda b: b['identity'].update(invocation_id='another-call'))

    def test_wrong_binary_site_rejected(self):
        self.reject(lambda b: b['identity'].update(binary_id='another-binary'))

    def test_dangling_source_and_record(self):
        self.reject(lambda b: b['sites'][0].update(source_ids=['missing']))
        self.reject(lambda b: b['events'][0].update(record_ids=['missing']))

    def test_tick_bool_range_and_actual_boundary(self):
        self.reject(lambda b: b['records'][0].update(tick=True))
        self.reject(lambda b: b['records'][0].update(tick=1<<64))
        self.reject(lambda b: b['events'][0].update(start_tick=True))
        self.reject(lambda b: b['events'][0].update(end_tick=99))

    def test_raw_bounds_and_aliases(self):
        self.reject(lambda b: b['records'][0].update(offset=255))
        self.reject(lambda b: b['records'][1].update(offset=32))

    def test_fake_clock_or_boundary_certification_rejected(self):
        self.reject(lambda b: b.update(clock_status='verified'))
        self.reject(lambda b: b.update(boundary_status='verified'))
        self.reject(lambda b: b.update(time_ns=123))

    def test_silent_record_drop_and_duplicate_duration(self):
        self.reject(lambda b: b['events'].pop())
        self.reject(lambda b: b['events'].append(copy.deepcopy(b['events'][0])))

    def test_false_occurrence_is_not_a_loop_iteration(self):
        self.reject(lambda b: b['events'][0].update(iteration_id=0))
        self.reject(lambda b: b['events'][0].update(occurrence=7))

    def test_complete_stream_rejects_mismatched_nesting(self):
        decoded, owner, metadata = fixture()
        decoded['records'][2]['site'] = 0
        with self.assertRaises(ValueError):
            canonicalize_nvidia_capture(decoded, owner=owner, metadata=metadata,
                                       raw_sha256='a'*64, raw_bytes=256)

    def test_missing_snapshot_is_only_a_compiler_location(self):
        decoded, owner, metadata = fixture()
        metadata['scope_id_origins'] = {}
        batch = canonicalize_nvidia_capture(decoded, owner=owner, metadata=metadata,
                                           raw_sha256='a'*64, raw_bytes=256)
        self.assertTrue(batch['sources'])
        self.assertTrue(all(s['source_sha256'] is None and s['provenance'] ==
            'actual_compiler_location_without_retained_source_snapshot'
            for s in batch['sources']))

    def test_large_ticks_stay_exact(self):
        decoded, owner, metadata = fixture()
        for record in decoded['records']:
            record['tick'] += (1<<63)
        batch = canonicalize_nvidia_capture(decoded, owner=owner, metadata=metadata,
                                            raw_sha256='a'*64, raw_bytes=256)
        self.assertIn((1<<63)+10, [r['tick'] for r in batch['records']])

    def test_backend_record_map_has_explicit_membership(self):
        batch = normalize()
        self.assertEqual(len(batch['backend_record_map']['nvidia.cp_async.groups.v1']),4)
        self.reject(lambda b: b.update(backend_record_map={'new.backend':{'r':'missing'}}))

    def test_common_contract_accepts_nonwarp_role_without_export_branch(self):
        batch = normalize()
        observer = batch['observers'][0]
        identity = tuple(batch['identity'][k] for k in ('capture_id','invocation_id','binary_id'))
        observer.update(kind='example.vector_observer', local_id='vector-7', physical_identity=None)
        observer['id'] = stable_id(identity, 'observer', observer['kind'], observer['local_id'], observer['program_coordinates'])
        replacements = {}
        for record in batch['records']:
            old = record['id']
            record['observer_id'] = observer['id']
            record['id'] = stable_id(identity,'record',observer['id'],record['sequence'])
            replacements[old] = record['id']
        for event in batch['events']:
            event['observer_id'] = observer['id']
            event['record_ids'] = [replacements[r] for r in event['record_ids']]
            event['id'] = stable_id(identity,'event',*event['record_ids'])
        batch['backend_record_map'] = {}
        self.assertTrue(validate_raw_batch(batch)['complete'])

    def test_validation_returns_isolated_snapshot_and_budget_rejects(self):
        batch = normalize()
        snapshot = validate_raw_batch(batch)
        batch['sites'][0]['name'] = 'mutated'
        self.assertNotEqual(snapshot['sites'][0]['name'], 'mutated')
        with self.assertRaises(ValueError):
            validate_raw_batch(snapshot, max_events=1)


if __name__ == '__main__':
    unittest.main()
