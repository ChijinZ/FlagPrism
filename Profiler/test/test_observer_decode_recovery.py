"""Real decoder failure must preserve bytes and remain a failed capture."""
import base64
import hashlib
import importlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest


# Recorded by the real LLVM15 late pass in the public development test
# test_ascend_semantic_selection::test_real_pass_manifest_binds_cpu_record_fixture
# [AIC, 0]. The original manifest/texts are retained unchanged. The raw buffers
# below are synthetic protocol fixtures, not accelerator execution evidence.
def _bound_handoff():
    path = Path(
        __file__).parent / 'fixtures/ascend_actor_recovery_handoff.json'
    handoff = json.loads(path.read_text())
    from flagtree.profiler.ascend_actor_binding import bind_compiler_sites
    sites = bind_compiler_sites(handoff, require_binding=True)
    assert len(sites) == 1
    assert sites[0]['compiler_actor']['binding_proof'][
        'selection_membership'] == 'selected_dynamic_site_in_exact_module_plan'
    return handoff


@pytest.fixture(autouse=True)
def mocked_eager_capture_state(monkeypatch):
    from flagtree.debugger import graph_guard
    # Every native prepare in this decoder-only suite is a CPU fixture.
    # Capture state itself is tested in dedicated guard/route regressions.
    monkeypatch.setattr(graph_guard, "require_eager", lambda *a, **k: None)


@pytest.mark.parametrize("handler_fails", [False, True])
@pytest.mark.parametrize("failure", ["truncated", "semantic", "program"])
def test_finalize_preserves_truncated_actor_trace_and_original_error(
        monkeypatch, tmp_path, handler_fails, failure):
    from flagtree import debugger
    from flagtree.debugger import api
    from flagtree.debugger.runtime import default_debug_collect_runtime
    from flagtree.profiler import observations, reconstruction
    profile = importlib.import_module("flagtree.profiler.profile")

    handoff = _bound_handoff()
    manifest = handoff['artifacts'][0]['metadata']
    site, = manifest['dynamic_sites']
    assert site['public_semantic'] == 'issue'
    segment_words = manifest['runtime_actor_binding']['segment_words']
    capacity = (segment_words - 4) // 8
    raw = b"\x00" * 8
    expected_error = 'truncated dynamic64 allocation'
    if failure != 'truncated':
        # Raw wait against the actual pass-selected issue site must fail.
        descriptor = (2
                      if failure == 'semantic' else 1) << 32 | site['site_id']
        program = 1 if failure == 'program' else 0
        words = [0] * (3 * segment_words)
        words[:12] = [
            1, 1, 1, 0, descriptor, 0, 100, 120, program, 0, (1 << 64) - 1,
            (1 << 64) - 1
        ]
        raw = struct.pack('<' + 'Q' * len(words), *words)
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
        "flagprism_ascend_trace_capacity": capacity,
        "flagprism_ascend_trace_program": 0,
        "flagprism_ascend_handoff": handoff
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


def test_legacy_finalize_keeps_raw_without_inventing_compiler_authority(
        monkeypatch):
    from flagtree.debugger import api
    from flagtree.profiler.ascend_actor_binding import bind_compiler_sites

    handoff = _bound_handoff()
    artifact = handoff['artifacts'][0]
    manifest = artifact['metadata']
    binding = manifest.pop('runtime_actor_binding')
    artifact['manifest_text'] = json.dumps(manifest)
    artifact['manifest_sha256'] = hashlib.sha256(
        artifact['manifest_text'].encode()).hexdigest()
    assert bind_compiler_sites(handoff) == []
    with pytest.raises(ValueError, match='lacks runtime actor binding'):
        bind_compiler_sites(handoff, require_binding=True)
    segment_words = binding['segment_words']
    capacity = (segment_words - 4) // 8
    site, = manifest['dynamic_sites']
    # The raw wait disagrees with the legacy issue declaration. Without an
    # emitted binding, that declaration cannot authoritatively classify it.
    words = [0] * (3 * segment_words)
    words[:12] = [
        1, 1, 1, 0, (2 << 32) | site['site_id'], 0, 100, 120, 0, 0,
        (1 << 64) - 1, (1 << 64) - 1
    ]
    raw = struct.pack('<' + 'Q' * len(words), *words)
    calls = []
    monkeypatch.setattr(api, '_exported_runs', [])
    monkeypatch.setattr(
        api, '_active_config',
        api.DebuggerConfig(enabled=True, export_handler=calls.append))
    metadata = {
        'name': 'legacy_unbound_fixture',
        'debug_record_layout': 'ascend_actor_dynamic_v1',
        'flagprism_ascend_trace_capacity': capacity,
        'flagprism_ascend_trace_program': 0,
        'flagprism_ascend_handoff': handoff,
        'flagprism_ascend_observation_request': {
            'semantics': ['wait_bracket']
        }
    }
    monkeypatch.setattr(api, '_build_launch_metadata_dict',
                        lambda value: metadata)
    monkeypatch.setattr(api, '_infer_runtime_metadata', lambda *args: {})
    handle = SimpleNamespace(hidden_arg_value=8,
                             finish=lambda: {
                                 'raw_buffer': raw,
                                 'runtime_metadata': {}
                             })
    monkeypatch.setattr(
        api, '_load_binding',
        lambda: SimpleNamespace(prepare_launch=lambda *args: handle))
    api._default_launch_prepare_hook(SimpleNamespace(), 0, None,
                                     ()).finalize(None)
    run, = calls
    assert run['raw_buffer'] == raw
    assert 'decode_error' not in run
    event, = run['semantic_observations']
    assert event['semantic'] == 'wait_bracket'
    assert event['compiler_actor_status'] == 'unverified_legacy'
    assert not event.get('compiler_site')
    assert all(
        actor.get('binding_status') != 'verified_by_committed_records'
        for actor in run['decoded']['actors'])
    assert all(not actor.get('compiler_actors')
               for actor in run['decoded']['actors'])
