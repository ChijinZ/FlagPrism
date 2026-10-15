"""CPU lifecycle/durability contracts; no device or native session is started."""
import base64
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def profile(monkeypatch):
    module = importlib.import_module("flagtree.profiler.profile")
    monkeypatch.setattr(module, "_active_sessions", {})
    monkeypatch.setattr(module.InstrumentationHook, "observation_captures", [])
    monkeypatch.setattr(module, "is_command_line", lambda: False)
    monkeypatch.setattr(module.HookManager, "unregister", lambda *args: None)
    monkeypatch.setattr(module, "set_profiling_off", lambda: None)
    monkeypatch.setattr(module, "_snapshot_session", lambda *args: None)
    monkeypatch.setattr(module, "profiler_native",
                        SimpleNamespace(finalize=lambda *args: None))
    return module


def packet(identifier="a", sessions=(7, ), raw=b"original native ring bytes"):
    return {
        "capture_id": identifier,
        "session_ids": set(sessions),
        "scope_id_names": [(1, "load")],
        "raw_base64": base64.b64encode(raw).decode(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "decoded": {
            "observations": [{
                "id": f"{identifier}:event"
            }]
        }
    }


def state(tmp_path):
    return {
        "session": 7,
        "name": str(tmp_path / "capture"),
        "backend": "cupti"
    }


def assert_recovery(state, expected):
    path = Path(state["native_observation_recovery_path"])
    payload = json.loads(path.read_text())
    assert payload["session_id"] == state["session"]
    assert payload["captures"][0]["raw_base64"] == expected["raw_base64"]
    assert payload["captures"][0]["raw_sha256"] == expected["raw_sha256"]
    # A new process recovers the original bytes without access to the class queue.
    script = "import base64,hashlib,json,sys;d=json.load(open(sys.argv[1]));print(hashlib.sha256(base64.b64decode(d['captures'][0]['raw_base64'])).hexdigest())"
    digest = subprocess.check_output(
        [sys.executable, "-c", script, str(path)], text=True).strip()
    assert digest == expected["raw_sha256"]
    return path


def test_unknown_finalize_is_noop_before_metadata_and_all_side_effects(
        profile, monkeypatch):
    other = {"session": 8}
    profile._active_sessions[8] = other

    def forbidden(*args, **kwargs):
        raise AssertionError("unknown finalize performed a side effect")

    monkeypatch.setattr(profile, "metadata_snapshot", forbidden)
    monkeypatch.setattr(profile, "is_command_line", forbidden)
    monkeypatch.setattr(profile, "_drop_session", forbidden)
    profile.finalize(7, metadata=object())
    assert profile._active_sessions == {8: other}


def test_actual_finalize_twice_keeps_output_and_other_session(
        profile, tmp_path):
    current = state(tmp_path)
    profile._active_sessions.update({7: current, 8: {"session": 8}})
    profile.InstrumentationHook.observation_captures = [packet()]
    profile.finalize(7)
    path = Path(current["name"]).with_suffix(".observations.json")
    original = path.read_bytes()
    profile.finalize(7)
    assert path.read_bytes() == original
    assert profile._active_sessions == {8: {"session": 8}}


def test_peek_ack_are_exact_and_legacy_take_remains_compatible(profile):
    hook = profile.InstrumentationHook
    hook.observation_captures = [packet("a", (7, 8)), packet("b", (8, ))]
    snapshot = hook.peek_observation_captures(7)
    snapshot[0]["decoded"]["observations"].clear()
    assert hook.observation_captures[0]["decoded"]["observations"]
    hook.observation_captures.append(packet("new", (7, )))
    hook.ack_observation_captures(7, ["a"])
    assert [row["capture_id"]
            for row in hook.peek_observation_captures(7)] == ["new"]
    assert [row["capture_id"]
            for row in hook.take_observation_captures(8)] == ["a", "b"]
    assert [row["capture_id"]
            for row in hook.take_observation_captures()] == ["new"]
    assert not hook.observation_captures
    hook.observation_captures = [{"session_ids": [7], "legacy": True}]
    assert hook.take_observation_captures(7) == [{"legacy": True}]


def test_success_ack_follows_atomic_file_and_directory_sync(
        profile, tmp_path, monkeypatch):
    current = state(tmp_path)
    hook = profile.InstrumentationHook
    original_packet = packet()
    hook.observation_captures = [original_packet, packet("other", (8, ))]
    path = Path(current["name"]).with_suffix(".observations.json")
    original_sync, original_ack = os.fsync, hook.ack_observation_captures
    events = []

    def synced(descriptor):
        result = original_sync(descriptor)
        events.append(os.readlink(f"/proc/self/fd/{descriptor}"))
        return result

    def ack(session, identifiers):
        assert events[-1] == str(path.parent)
        assert json.loads(path.read_text(
        ))["captures"][0]["raw_base64"] == original_packet["raw_base64"]
        assert hook.peek_observation_captures(7)
        original_ack(session, identifiers)

    monkeypatch.setattr(profile.os, "fsync", synced)
    monkeypatch.setattr(hook, "ack_observation_captures", ack)
    profile._export_native_observations(current)
    assert len(events) >= 5
    assert not hook.peek_observation_captures(7)
    assert hook.peek_observation_captures(8)[0]["capture_id"] == "other"
    assert "native_observation_recovery_path" not in current
    assert not list(tmp_path.glob("flagprism-observation-recovery-*"))


def test_bad_existing_json_keeps_original_and_durable_raw(profile, tmp_path):
    current = state(tmp_path)
    original = packet()
    profile.InstrumentationHook.observation_captures = [original]
    path = Path(current["name"]).with_suffix(".observations.json")
    path.write_text("{bad original sidecar")
    with pytest.raises(RuntimeError, match="durably retained") as caught:
        profile._export_native_observations(current)
    assert isinstance(caught.value.__cause__, json.JSONDecodeError)
    assert path.read_text() == "{bad original sidecar"
    assert profile.InstrumentationHook.peek_observation_captures(7)
    assert str(assert_recovery(current, original)) in str(caught.value)


@pytest.mark.parametrize("failure", ["allocation", "replace"])
def test_atomic_write_failure_keeps_old_sidecar_and_raw(
        profile, tmp_path, monkeypatch, failure):
    current = state(tmp_path)
    original = packet()
    profile.InstrumentationHook.observation_captures = [original]
    path = Path(current["name"]).with_suffix(".observations.json")
    old = '{"captures":[],"observations":[]}'
    path.write_text(old)
    original_mkstemp, original_replace = profile.tempfile.mkstemp, profile.os.replace

    def allocate(*args, **kwargs):
        if Path(kwargs["dir"]) == path.parent:
            raise OSError("injected sidecar write allocation failure")
        return original_mkstemp(*args, **kwargs)

    def replace(source, destination):
        if Path(destination) == path:
            raise OSError("injected atomic replace failure")
        return original_replace(source, destination)

    if failure == "allocation":
        monkeypatch.setattr(profile.tempfile, "mkstemp", allocate)
    else:
        monkeypatch.setattr(profile.os, "replace", replace)
    with pytest.raises(RuntimeError, match="durably retained") as caught:
        profile._export_native_observations(current)
    assert isinstance(caught.value.__cause__, OSError)
    assert path.read_text() == old
    assert profile.InstrumentationHook.peek_observation_captures(7)
    assert_recovery(current, original)
    assert not list(path.parent.glob(".native-observations-*"))


def test_fallback_journal_survives_finalize_state_drop(profile, tmp_path,
                                                       monkeypatch):
    stage = tmp_path / "stage"
    stage.mkdir()
    current = {**state(stage), "staging": str(stage)}
    profile._active_sessions[7] = current
    original = packet()
    profile.InstrumentationHook.observation_captures = [original]
    Path(current["name"]).with_suffix(".observations.json").write_text("{bad")
    original_mkdtemp = profile.tempfile.mkdtemp

    def mkdtemp(*args, **kwargs):
        if kwargs.get("dir") == stage:
            raise PermissionError(
                "injected primary recovery directory failure")
        return original_mkdtemp(*args, **kwargs)

    monkeypatch.setattr(profile.tempfile, "mkdtemp", mkdtemp)
    with pytest.raises(RuntimeError, match="durably retained") as caught:
        profile.finalize(7)
    assert 7 not in profile._active_sessions
    journal = assert_recovery(current, original)
    try:
        assert stage not in journal.parents and str(journal) in str(
            caught.value)
        shutil.rmtree(stage)
        assert_recovery(current, original)
    finally:
        shutil.rmtree(journal.parent)


def test_all_recovery_locations_fail_without_false_durability(
        profile, tmp_path, monkeypatch):
    current = state(tmp_path)
    profile.InstrumentationHook.observation_captures = [packet()]

    def fail(*args, **kwargs):
        raise OSError("no writable recovery location")

    monkeypatch.setattr(profile.tempfile, "mkdtemp", fail)
    with pytest.raises(RuntimeError,
                       match="could not be durably saved.*unacknowledged"):
        profile._export_native_observations(current)
    assert profile.InstrumentationHook.peek_observation_captures(7)
    assert "native_observation_recovery_path" not in current


def test_retry_after_ack_failure_deduplicates_identical_capture(
        profile, tmp_path, monkeypatch):
    current = state(tmp_path)
    hook = profile.InstrumentationHook
    original = packet()
    hook.observation_captures = [original]

    def fail(*args):
        raise RuntimeError("injected ack failure")

    with monkeypatch.context() as context:
        context.setattr(hook, "ack_observation_captures", fail)
        with pytest.raises(RuntimeError, match="ack failure"):
            profile._export_native_observations(current)
    first_journal = assert_recovery(current, original)
    profile._export_native_observations(current)
    payload = json.loads(
        Path(current["name"]).with_suffix(".observations.json").read_text())
    assert len(payload["captures"]) == len(payload["observations"]) == 1
    assert not hook.peek_observation_captures(7)
    # The same unchanged pending batch reuses its explicitly owned journal and
    # removes that journal only after durable publication and acknowledgement.
    assert not first_journal.exists()


def test_directory_sync_failure_after_replace_can_retry_without_duplicates(
        profile, tmp_path, monkeypatch):
    current = state(tmp_path)
    hook = profile.InstrumentationHook
    original = packet()
    hook.observation_captures = [original]
    path = Path(current["name"]).with_suffix(".observations.json")
    original_replace, original_sync = os.replace, os.fsync
    published = []

    def replace(source, destination):
        result = original_replace(source, destination)
        if Path(destination) == path:
            published.append(True)
        return result

    def sync(descriptor):
        if published and os.readlink(f"/proc/self/fd/{descriptor}") == str(
                path.parent):
            raise OSError("injected directory sync failure")
        return original_sync(descriptor)

    with monkeypatch.context() as context:
        context.setattr(profile.os, "replace", replace)
        context.setattr(profile.os, "fsync", sync)
        with pytest.raises(RuntimeError, match="directory sync failure"):
            profile._export_native_observations(current)
    assert_recovery(current, original)
    assert hook.peek_observation_captures(7)
    profile._export_native_observations(current)
    payload = json.loads(path.read_text())
    assert len(payload["captures"]) == len(payload["observations"]) == 1
    assert not hook.peek_observation_captures(7)


def test_same_id_different_payload_is_not_silently_dropped(profile, tmp_path):
    current = state(tmp_path)
    hook = profile.InstrumentationHook
    hook.observation_captures = [packet(raw=b"first")]
    profile._export_native_observations(current)
    path = Path(current["name"]).with_suffix(".observations.json")
    original_sidecar = path.read_bytes()
    second = packet(raw=b"different")
    hook.observation_captures = [second]
    with pytest.raises(RuntimeError,
                       match="Conflicting native observation capture ID"):
        profile._export_native_observations(current)
    assert path.read_bytes() == original_sidecar
    assert hook.peek_observation_captures(7)
    assert_recovery(current, second)


def test_unserializable_packet_is_explicitly_not_durable(profile, tmp_path):
    current = state(tmp_path)
    original = packet()
    original["invalid_metadata"] = object()
    profile.InstrumentationHook.observation_captures = [original]
    with pytest.raises(RuntimeError, match="not serializable.*unacknowledged"):
        profile._export_native_observations(current)
    assert profile.InstrumentationHook.peek_observation_captures(7)
    assert "native_observation_recovery_path" not in current


def test_actual_truncated_proton_decode_retains_raw_and_original_exception(
        profile, tmp_path, monkeypatch):
    import torch
    from flagtree.profiler.observations_nvidia import decode_proton_ring
    from flagtree.profiler._capture import export_capture

    raw = b"truncated Proton ring"
    hook_class = profile.InstrumentationHook
    hook = hook_class(None)
    hook.observation_metadata = {}
    hook._observation_stack.set(({
        "scope_id": 42,
        "invocation_id": "launch-42",
        "association_evidence": None,
        "session_ids": {7},
    }, ))
    monkeypatch.setattr(
        hook_class, "host_buffer",
        torch.tensor(list(raw), dtype=torch.uint8, device="cpu"))
    raised = []

    def trace(frame, event, argument):
        if event == "exception" and frame.f_code is decode_proton_ring.__code__:
            raised.append(argument[1])
        return trace

    old_trace = sys.gettrace()
    try:
        sys.settrace(trace)
        with pytest.raises(ValueError,
                           match="complete binary header") as caught:
            hook._export_observation_capture(123)
    finally:
        sys.settrace(old_trace)
    assert raised and caught.value is raised[0]
    queued = hook_class.peek_observation_captures(7)
    assert len(queued) == 1
    assert queued[0]["capture_status"] == "decode_failed"
    assert queued[0]["decode_error"]["type"] == "ValueError"
    assert base64.b64decode(queued[0]["raw_base64"]) == raw
    assert queued[0]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert queued[0]["decoded"]["observations"] == []
    current = state(tmp_path)
    profile._export_native_observations(current)
    sidecar = json.loads(
        Path(current["name"]).with_suffix(".observations.json").read_text())
    assert sidecar["observations"] == [] and len(sidecar["captures"]) == 1
    assert not hook_class.peek_observation_captures(7)
    base = Path(current["name"])
    base.with_suffix(".vendor.json").write_text(
        json.dumps({
            "backend": "cupti",
            "associations": []
        }))
    output = tmp_path / "bundle"
    export_capture(base, output)
    report = json.loads((output / "report/report.json").read_text())
    assert report["events"] == [] and report["untimed_events"] == []
    events = output / "ai/events.jsonl"
    assert not events.exists() or not events.read_text().strip()
    assert json.loads(
        (output / "ai/observations.json").read_text())["observations"] == []


@pytest.mark.parametrize(
    "phase", ["native_finalize", "launch_snapshot", "task_producer"])
def test_earlier_finalize_failure_still_durably_saves_completed_host_capture(
        profile, tmp_path, monkeypatch, phase):
    stage = tmp_path / "stage"
    stage.mkdir()
    current = {
        **state(stage), "staging": str(stage),
        "bundle_output": tmp_path / "bundle"
    }
    profile._active_sessions[7] = current
    original = packet()
    profile.InstrumentationHook.observation_captures = [original]
    failure = RuntimeError(f"original {phase} failure")

    def fail(*args):
        raise failure

    if phase == "native_finalize":
        monkeypatch.setattr(profile.profiler_native, "finalize", fail)
    elif phase == "launch_snapshot":
        monkeypatch.setattr(profile, "_snapshot_session", fail)
    else:
        monkeypatch.setattr(profile, "_export_cann_task_identities", fail)

    def forbidden(*args):
        raise AssertionError("failed finalize attempted a complete bundle")

    monkeypatch.setattr(profile, "_export_session", forbidden)
    with pytest.raises(RuntimeError,
                       match=f"original {phase} failure") as caught:
        profile.finalize(7)
    assert caught.value.__cause__ is failure
    assert str(stage) in str(caught.value)
    assert not profile._active_sessions
    assert not profile.InstrumentationHook.peek_observation_captures(7)
    path = Path(current["name"]).with_suffix(".observations.json")
    payload = json.loads(path.read_text())
    assert base64.b64decode(
        payload["captures"][0]["raw_base64"]) == b"original native ring bytes"
    assert payload["captures"][0]["raw_sha256"] == original["raw_sha256"]
    script = "import base64,hashlib,json,sys;d=json.load(open(sys.argv[1]));print(hashlib.sha256(base64.b64decode(d['captures'][0]['raw_base64'])).hexdigest())"
    assert subprocess.check_output(
        [sys.executable, "-c", script, str(path)],
        text=True).strip() == original["raw_sha256"]
    assert stage.exists() and not current["bundle_output"].exists()
