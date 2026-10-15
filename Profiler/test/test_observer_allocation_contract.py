"""Compiler ABI precedence and actual pre-allocation rejection, without launch."""
from types import SimpleNamespace

import pytest


def test_post_lowering_metadata_outweighs_request_defaults(monkeypatch):
    from flagtree.debugger import api, compiler

    request = {
        "debug_record_capacity": 256,
        "debug_record_size": 32,
        "debug_enabled": True,
        "debug_addr_level": 0
    }
    monkeypatch.setattr(compiler, "_instrumentation_mode", "")
    monkeypatch.setattr(api, "current_compile_config", lambda: dict(request))

    def lower(module, metadata):
        metadata.update(debug_record_capacity=769,
                        debug_record_size=64,
                        flagprism_ascend_trace_capacity=256)

    monkeypatch.setattr(compiler, "run_ttir_debug_passes_if_needed", lower)
    metadata = {"instrumentation_mode": "debugger_auto"}
    event = SimpleNamespace(metadata=metadata,
                            phase="post_override",
                            ir_kind="ttir",
                            module=object())
    compiler.run_compiler_event(event)
    assert metadata["debug_record_capacity"] == 769
    assert metadata["debug_record_size"] == 64
    assert metadata["flagprism_ascend_trace_capacity"] == 256
    assert metadata["debug_addr_level"] == 0
    assert metadata["debug_enabled"] is True


def test_request_does_not_reenable_a_resolved_metadata_only_kernel(
        monkeypatch):
    from flagtree.debugger import api, compiler

    monkeypatch.setattr(api, "current_compile_config",
                        lambda: {"debug_enabled": True})
    metadata = {
        "instrumentation_mode": "debugger_auto",
        "debug_enabled": False,
        "debug_launch_hidden_arg": False
    }
    compiler.update_compile_metadata(metadata)
    assert metadata["debug_enabled"] is False
    assert metadata["debug_launch_hidden_arg"] is False


@pytest.mark.parametrize("change,runtime_layout,message", [
    ({
        "debug_record_capacity": 256
    }, "ascend_actor_dynamic_v1", "3 \\* per-actor capacity \\+ 1"),
    ({
        "debug_record_capacity": 768
    }, "ascend_actor_dynamic_v1", "allocation capacity"),
    ({
        "debug_record_capacity": 770
    }, "ascend_actor_dynamic_v1", "allocation capacity"),
    ({
        "flagprism_ascend_trace_capacity": 0
    }, "ascend_actor_dynamic_v1", "per-actor capacity"),
    ({
        "flagprism_ascend_trace_capacity": (1 << 32) // 3
    }, "ascend_actor_dynamic_v1", "per-actor capacity"),
    ({
        "debug_record_size": 32
    }, "ascend_actor_dynamic_v1", "64-byte records"),
    ({
        "debug_record_layout": "other_layout"
    }, "ascend_actor_dynamic_v1", "layout metadata"),
    ({}, "other_layout", "layout metadata"),
    ({}, "", "layout metadata"),
])
def test_real_native_rejects_actor_allocation_mismatch_before_device_use(
        change, runtime_layout, message):
    from flagtree.debugger.native import runtime_binding

    binding = runtime_binding()
    assert binding is not None, "actual rebuilt native binding is required"
    metadata = {
        "name": "actor_allocation_preflight",
        "debug_enabled": True,
        "debug_backend_name": "ascend",
        "debug_record_level": 1,
        "debug_record_layout": "ascend_actor_dynamic_v1",
        "debug_record_size": 64,
        "debug_record_capacity": 769,
        "flagprism_ascend_trace_capacity": 256
    }
    metadata.update(change)
    with pytest.raises(ValueError, match=message):
        binding.prepare_launch(metadata, 0, {"record_layout": runtime_layout})
