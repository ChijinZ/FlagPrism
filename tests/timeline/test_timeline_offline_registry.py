"""Provider selection contracts; no synthetic device/time qualification."""
import unittest

from flagtree.profiler.timeline_offline import offline_provider


class OfflineRegistryTests(unittest.TestCase):

    def capture(self, compiler=None, owner=None):
        return dict(metadata=dict(compiler_metadata=compiler or {}),
                    owner=owner or {})

    def test_actual_provider_entry_points_are_callable(self):
        inputs = [
            ('nvidia', self.capture(dict(target=dict(backend='cuda')))),
            ('ascend',
             self.capture(
                 dict(debug_record_layout='ascend_source_timeline_v1'))),
            ('enflame', self.capture(owner=dict(native_export_metadata={}))),
        ]
        for expected, capture in inputs:
            with self.subTest(expected):
                provider = offline_provider(capture)
                self.assertEqual(provider.backend_name, expected)
                for name in ('matches', 'decode_capture', 'decoder_rules',
                             'reexport_views'):
                    self.assertTrue(callable(getattr(provider, name)))

    def test_gcu_rules_include_the_actual_delegated_native_decoder(self):
        from flagtree.profiler import timeline_events_enflame_native
        provider = offline_provider(
            self.capture(owner=dict(native_export_metadata={})))
        self.assertIn(timeline_events_enflame_native,
                      provider.decoder_rules({}))

    def test_missing_and_malformed_identities_are_rejected(self):
        for capture in (None, [], {}, dict(owner={}, metadata=[]),
                        self.capture(), self.capture(dict(target='cuda'))):
            with self.subTest(capture=capture):
                with self.assertRaises(ValueError):
                    offline_provider(capture)

    def test_competing_physical_producer_claims_are_rejected(self):
        for compiler in (dict(target=dict(backend='cuda')),
                         dict(
                             debug_record_layout='ascend_source_timeline_v1')):
            with self.subTest(compiler=compiler):
                with self.assertRaisesRegex(ValueError, 'ambiguous'):
                    offline_provider(
                        self.capture(compiler,
                                     dict(native_export_metadata={})))


if __name__ == '__main__':
    unittest.main()
