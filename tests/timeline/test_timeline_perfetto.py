"""Counter projection/serialization contracts; fixtures are not clock evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest

from flagtree.profiler.timeline_views import CounterUnitProof, derive_counter_ns_views, document_sha256
from flagtree.profiler.timeline_perfetto import encode_counter_trace, validate_counter_view
from flagtree.profiler.timeline_unit_nvidia import nvidia_counter_unit_proofs


def fixture_module(name):
    spec = importlib.util.spec_from_file_location(
        name,
        Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def batch_fixture(pair=False):
    return (fixture_module('test_enflame_timeline_events').convert()
            if pair else fixture_module('test_timeline_events').normalize())


def proof_for(batch, **overrides):
    args = dict(**batch['identity'],
                raw_sha256=batch['raw_artifact']['sha256'],
                observer_id=batch['observers'][0]['id'],
                period_numerator_ns=1,
                period_denominator=1,
                max_elapsed_ns=1000,
                provider='test.fixture_only',
                evidence_ids=('explicit_synthetic_test_fixture_not_device', ))
    args.update(overrides)
    return CounterUnitProof(**args)


class CounterPerfettoTests(unittest.TestCase):

    def test_projection_keeps_raw_and_unknown_precision(self):
        batch = batch_fixture()
        original = document_sha256(batch)
        view = derive_counter_ns_views(batch, [proof_for(batch)])[0]
        self.assertEqual(view['clock_status'], 'counter_unit_only')
        self.assertEqual(view['source_boundary_status'], 'unverified')
        self.assertFalse(view['time_arrows_verified'])
        self.assertTrue(
            all(e['endpoint_error_ns'] is None for e in view['events']))
        self.assertEqual([(e['start_ns'], e['end_ns'])
                          for e in view['events']], [(10, 20), (0, 30)])
        self.assertEqual(document_sha256(batch), original)

    def test_large_absolute_ticks_never_use_float(self):
        batch = batch_fixture()
        for row in batch['records']:
            row['tick'] += 1 << 60
        for event in batch['events']:
            event['start_tick'] += 1 << 60
            event['end_tick'] += 1 << 60
        view = derive_counter_ns_views(batch, [proof_for(batch)])[0]
        self.assertEqual(view['origin_tick'], (1 << 60) + 10)
        self.assertEqual([(e['start_ns'], e['end_ns'])
                          for e in view['events']], [(10, 20), (0, 30)])

    def test_rational_floor_and_zero_width_are_not_stretched(self):
        batch = batch_fixture()
        view = derive_counter_ns_views(
            batch, [proof_for(batch, period_denominator=100)])[0]
        self.assertTrue(
            all(e['start_ns'] == e['end_ns'] == 0 for e in view['events']))
        self.assertTrue(
            encode_counter_trace(view,
                                 batch,
                                 proof=proof_for(batch,
                                                 period_denominator=100)))

    def test_proof_binding_duplicates_and_missing_proofs(self):
        batch = batch_fixture()
        self.assertEqual(derive_counter_ns_views(batch, []), [])
        for change in [
                dict(capture_id='other'),
                dict(raw_sha256='b' * 64),
                dict(observer_id='other')
        ]:
            with self.assertRaises(ValueError):
                derive_counter_ns_views(batch, [proof_for(batch, **change)])
        with self.assertRaises(ValueError):
            derive_counter_ns_views(
                batch, [proof_for(batch), proof_for(batch)])

    def test_bad_units_and_independent_window_fail_closed(self):
        batch = batch_fixture()
        for change in [
                dict(period_numerator_ns=True),
                dict(period_denominator=0),
                dict(max_elapsed_ns=0),
                dict(evidence_ids=())
        ]:
            with self.assertRaises(ValueError):
                proof_for(batch, **change)
        with self.assertRaises(ValueError):
            derive_counter_ns_views(batch,
                                    [proof_for(batch, max_elapsed_ns=1)])

    def test_tampered_ns_or_claims_rejected_including_optimized_python(self):
        batch = batch_fixture()
        original = derive_counter_ns_views(batch, [proof_for(batch)])[0]
        for mutate in [
                lambda v: v['events'][0].update(start_ns=999),
                lambda v: v.update(time_arrows_verified=True),
                lambda v: v.update(source_boundary_status='verified'),
                lambda v: v.update(canonical_sha256='c' * 64),
                lambda v: v['unit_proof'].update(period_numerator_ns=2),
                lambda v: v.update(schema_version=True)
        ]:
            view = copy.deepcopy(original)
            mutate(view)
            with self.assertRaises(ValueError):
                validate_counter_view(view, batch, proof_for(batch))

    def test_pair_append_order_is_not_rewritten_for_export(self):
        batch = batch_fixture(pair=True)
        before = copy.deepcopy(batch)
        view = derive_counter_ns_views(batch, [proof_for(batch)])[0]
        self.assertEqual([r['tick'] for r in view['records']],
                         [20, 30, 10, 40])
        self.assertTrue(
            encode_counter_trace(view, batch, proof=proof_for(batch)))
        self.assertEqual(batch, before)

    def test_budget_rejection_preserves_input(self):
        batch = batch_fixture()
        view = derive_counter_ns_views(batch, [proof_for(batch)])[0]
        before = copy.deepcopy(view)
        with self.assertRaises(ValueError):
            encode_counter_trace(view,
                                 batch,
                                 proof=proof_for(batch),
                                 max_bytes=64)
        self.assertEqual(view, before)

    def test_nvidia_unit_provider_restricts_actual_target_and_getter(self):
        batch = batch_fixture()
        mapping = dict(status='counter_mapping_complete_region_unverified',
                       binary_id=batch['identity']['binary_id'],
                       expected_sm=[12, 0],
                       counter_pcs=[
                           dict(site_id=i,
                                phase=phase,
                                opcode='CS2R',
                                operands='R4,SR_GLOBALTIMERLO')
                           for i in [0, 1] for phase in ['entry', 'exit']
                       ])
        proofs = nvidia_counter_unit_proofs(batch,
                                            machine_map=mapping,
                                            max_elapsed_ns=1000)
        self.assertEqual(len(proofs), 1)
        for opcode, operands in [('CS2UR', 'UR4,SR_GLOBALTIMERLO'),
                                 ('CS2R', 'R4,SR_GLOBALTIMERLO')]:
            legal = copy.deepcopy(mapping)
            legal['counter_pcs'][0].update(opcode=opcode, operands=operands)
            self.assertEqual(
                len(
                    nvidia_counter_unit_proofs(batch,
                                               machine_map=legal,
                                               max_elapsed_ns=1000)), 1)
        for opcode, operands in [('CS2UR', 'R4,SR_GLOBALTIMERLO'),
                                 ('CS2R', 'UR4,SR_GLOBALTIMERLO'),
                                 ('CS2UR.32', 'UR4,SR_GLOBALTIMERLO'),
                                 ('CS2UR', 'UR4,SR_GLOBALTIMERHI')]:
            bad = copy.deepcopy(mapping)
            bad['counter_pcs'][0].update(opcode=opcode, operands=operands)
            with self.assertRaises(ValueError):
                nvidia_counter_unit_proofs(batch,
                                           machine_map=bad,
                                           max_elapsed_ns=1000)
        for change in [
                dict(expected_sm=[12, False]),
                dict(expected_sm=[9, 0]),
                dict(binary_id='other'),
                dict(counter_pcs=[]),
                dict(counter_pcs=[
                    dict(site_id=0,
                         phase='entry',
                         opcode='CS2R.32',
                         operands='R4,SR_GLOBALTIMERLO')
                ])
        ]:
            bad = dict(mapping, **change)
            with self.assertRaises(ValueError):
                nvidia_counter_unit_proofs(batch,
                                           machine_map=bad,
                                           max_elapsed_ns=1000)


if __name__ == '__main__':
    unittest.main()
