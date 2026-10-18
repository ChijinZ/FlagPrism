"""No legacy allocator may initialize a new paired source-timeline protocol."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from flagtree.debugger import api


def test_new_layout_rejected_before_native_allocation_or_device_probe():
    metadata = SimpleNamespace(debug_record_layout='ascend_source_timeline_v1',
                               debug_enabled=True, debug_launch_hidden_arg=True)
    with patch.object(api, '_load_binding', side_effect=AssertionError('native allocation forbidden')), \
         patch.object(api, '_infer_runtime_metadata', side_effect=AssertionError('legacy planning forbidden')):
        with pytest.raises(RuntimeError, match='dedicated collector'):
            api._default_launch_prepare_hook(metadata, 0, {'grid': [5, 1, 1]}, ())
