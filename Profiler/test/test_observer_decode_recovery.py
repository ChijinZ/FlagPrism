"""Real decoder failure must preserve bytes and remain a failed capture."""
import base64
import hashlib
import importlib
import json
import struct
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("handler_fails", [False, True])
@pytest.mark.parametrize("failure", ["truncated", "semantic", "program"])
def test_finalize_preserves_truncated_actor_trace_and_original_error(
        monkeypatch, tmp_path, handler_fails, failure):
    from flagtree import debugger
    from flagtree.debugger import api
    from flagtree.debugger.runtime import default_debug_collect_runtime
    from flagtree.profiler import observations, reconstruction
    profile = importlib.import_module("flagtree.profiler.profile")

    raw = b"\x00" * 8
    expected_error = 'truncated dynamic64 allocation'
    if failure != 'truncated':
        descriptor = (1 if failure == 'semantic' else 2) << 32 | 7
        program = 1 if failure == 'program' else 0
        words = [
            1, 1, 1, 0, descriptor, 0, 100, 120, program, 0, (1 << 64) - 1,
            (1 << 64) - 1
        ] + [0] * 24
        raw = struct.pack('<36Q', *words)
        expected_error = 'dynamic64 event semantic contradicts authoritative compiler site' if failure == 'semantic' else 'dynamic64 program contradicts compiled program selection'
    calls = []

    def export_handler(run):
        calls.append(run)
        if handler_fails:
            raise RuntimeError("secondary handler failure")

    monkeypatch.setattr(api, "_exported_runs", [])
    monkeypatch.setattr(
        api, "_active_config",
        api.DebuggerConfig(enabled=True,
                           export_on_error=True,
                           export_handler=export_handler))
    metadata = {
        "name": "decode_failure_fixture",
        "debug_record_level": 1,
        "debug_addr_level": 0,
        "debug_record_layout": "ascend_actor_dynamic_v1",
        "flagprism_ascend_trace_capacity": 1,
        "flagprism_ascend_trace_program": 0,
        "flagprism_ascend_handoff": {
            "phase":
            "finished",
            "artifacts": [{
                "metadata": {
                    "actors": [{
                        "actor_kind": "AIC"
                    }],
                    "dynamic_sites": [{
                        "site_id":
                        7,
                        "callee":
                        "llvm.hivm.WAIT.FLAG.IMM",
                        "semantics":
                        "existing_readiness_wait_source_control"
                    }]
                }
            }]
        }
    }
    monkeypatch.setattr(api, "_build_launch_metadata_dict",
                        lambda value: dict(metadata))
    monkeypatch.setattr(api, "_infer_runtime_metadata", lambda *args: {})
    finishes = []

    def finish():
        finishes.append(True)
        return {"raw_buffer": raw, "runtime_metadata": {}}

    handle = SimpleNamespace(hidden_arg_value=8, finish=finish)
    monkeypatch.setattr(
        api, "_load_binding",
        lambda: SimpleNamespace(prepare_launch=lambda *args: handle))
    prepared = api._default_launch_prepare_hook(SimpleNamespace(), 0, None, ())
    with pytest.raises(ValueError, match=expected_error):
        prepared.finalize(None)
    assert finishes == [True]
    assert len(calls) == 1
    failed = calls[0]
    assert failed["raw_buffer"] == raw
    assert failed["capture_status"] == "decode_failed"
    assert failed["decode_error"]["type"] == "ValueError"
    assert failed["decoded"] == {}
    assert failed["semantic_observations"] == []
    assert bool(failed.get("recovery_export_error")) == handler_fails

    monkeypatch.setattr(debugger, "take_exported_runs", api.take_exported_runs)
    monkeypatch.setattr(default_debug_collect_runtime, "take_exported_runs",
                        lambda: [])
    runs = profile._take_instrumentation_runs()
    assert len(runs) == 1 and runs[0]["capture_status"] == "decode_failed"
    assert base64.b64decode(runs[0]["raw_base64"]) == raw
    assert runs[0]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert observations.from_ir_runs(runs) == []
    for name in ("_augment_timeline", "_augment_hatchet", "_augment_ir_meta",
                 "_augment_ir_vendor"):
        monkeypatch.setattr(profile, name, lambda *args, **kwargs: None)
    base = tmp_path / "capture"
    profile._augment_instrumentation_artifacts(str(base), runs)
    payload = json.loads(base.with_suffix(".observations.json").read_text())
    assert payload["observations"] == []
    capture = payload["captures"][0]
    assert capture["capture_status"] == "decode_failed"
    assert capture["decode_error"]["message"] == expected_error
    assert base64.b64decode(capture["raw_base64"]) == raw
    view = reconstruction.reconstruct(payload, [], [], [])
    assert view["groups"] == []
    rendered = reconstruction.render(view)
    assert "Failed observation captures" in rendered
    assert "provide no decoded execution evidence" in rendered
