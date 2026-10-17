"""Pure GCU admission and debugger completion policy; not device qualification."""
import importlib
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from flagtree.profiler.timeline_enflame import plan_enflame_storage


class EnflameDeferredTests(unittest.TestCase):
    def setUp(self):
        self.plan = dict(binary_id='actual-binary', compiler_metadata=dict(
            hash='actual-binary', debug_dynamic_storage_version=2,
            debug_dynamic_publisher_version=2, debug_dynamic_index_bits=32,
            debug_record_layout='gcu_first_last_timeline_v2',
            debug_dynamic_program_policy='runtime_first_last',
            debug_record_capacity=8, debug_dynamic_slot_bytes=544))

    def layout(self, **kwargs):
        args = dict(grid=(3, 2, 1), scratch_size=544, alignment=8,
                    num_ctas=None, max_raw_bytes=2048)
        args.update(kwargs)
        return plan_enflame_storage(self.plan, **args)

    def test_actual_grid_controls_compact_physical_slots(self):
        actual = self.layout()
        self.assertEqual(actual['slots'], ((0, 0), (1, 5)))
        self.assertEqual(actual['raw_bytes'], 1088)
        self.assertEqual(self.layout(grid=(1, 1, 1))['raw_bytes'], 544)
        self.assertEqual(self.layout(grid=(3, 0, 1))['raw_bytes'], 0)

    def test_budget_stride_and_geometry_reject_before_allocation(self):
        for kwargs in [dict(max_raw_bytes=1087), dict(scratch_size=512),
                       dict(grid=(0x7fffffff, 2, 1)), dict(grid=(True, 1, 1)),
                       dict(num_ctas=1), dict(alignment=4)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.layout(**kwargs)

    def test_unknown_publisher_cannot_use_compact_allocator(self):
        for value in [1, True, None]:
            self.plan['compiler_metadata']['debug_dynamic_publisher_version'] = value
            with self.assertRaises(ValueError):
                self.layout()

    def test_launch_policy_explicitly_preserves_or_defers_legacy_wait(self):
        from flagtree.debugger import api
        guard = importlib.import_module('flagtree.debugger.graph_guard')
        import torch
        import torch_gcu  # noqa: F401
        metadata = SimpleNamespace(debug_enabled=True, debug_launch_hidden_arg=True)
        for synchronize in [True, False]:
            actions = []
            prepared = api.PreparedKernelLaunch(kernel_args=(123,),
                finalize=lambda error: actions.append(('finalize', error)),
                synchronize=synchronize)
            with patch.object(api, '_launch_prepare_hook', lambda *a: prepared), \
                 patch.object(guard, 'require_eager', lambda *a, **kw: None), \
                 patch.object(torch.gcu, 'synchronize', lambda: actions.append('host_wait')):
                with api.launch_context('enflame', metadata, (1, 1, 1), 0) as args:
                    self.assertEqual(args, (123,))
                    actions.append('submitted')
            expected = ['submitted', 'host_wait', ('finalize', None)] if synchronize else [
                'submitted', ('finalize', None)]
            self.assertEqual(actions, expected)

    def test_invalid_defer_policy_cannot_silently_disable_completion(self):
        from flagtree.debugger import api
        prepared = api.PreparedKernelLaunch(kernel_args=(123,), synchronize=0)
        with patch.object(api, '_launch_prepare_hook', lambda *a: prepared):
            with self.assertRaises(TypeError):
                api.prepare_kernel_launch(SimpleNamespace(debug_enabled=True), 0)


if __name__ == '__main__':
    unittest.main()
