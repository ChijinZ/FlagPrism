"""CPU contracts for drained CANN receipts; no SDK/device session is started."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def capture(monkeypatch, tmp_path):
    profile = importlib.import_module("flagtree.profiler.profile")
    raw = [{
        "session_id": 7,
        "scope_id": 11,
        "token_id": 19,
        "worker": {
            "task_id": 0
        },
        "status": "collected"
    }]
    closed_context = copy.deepcopy(raw)

    def drain(session):
        assert session == 7
        result = copy.deepcopy(closed_context)
        closed_context.clear()  # Native drainedAfterClose permits later GC.
        return result

    monkeypatch.setattr(
        profile, "profiler_native",
        SimpleNamespace(supports_cann_launch_receipts=lambda: True,
                        drain_cann_launch_receipts=drain))
    monkeypatch.setattr(profile.LaunchHook, "snapshot",
                        lambda sid: {"launches": []})
    state = {
        "backend": "cann",
        "session": 7,
        "name": str(tmp_path / "capture")
    }
    return profile, state, raw, closed_context


@pytest.mark.parametrize("phase", ["snapshot", "atomic_write"])
def test_post_drain_failure_keeps_original_error_and_cross_process_raw(
        capture, monkeypatch, phase):
    profile, state, raw, closed_context = capture
    original = OSError(f"original {phase} failure")
    sidecar = Path(state["name"]).with_suffix(".cann-launch-receipts.json")
    sidecar.write_text("original sidecar")
    if phase == "snapshot":

        def fail(sid):
            raise original

        monkeypatch.setattr(profile.LaunchHook, "snapshot", fail)
    else:
        replace = profile.os.replace

        def fail(source, destination):
            if Path(destination) == sidecar:
                raise original
            return replace(source, destination)

        monkeypatch.setattr(profile.os, "replace", fail)
    with pytest.raises(OSError) as caught:
        profile._snapshot_cann_launch_receipts(state)
    assert caught.value is original
    journal = Path(state["cann_receipt_recovery_path"])
    assert any(str(journal) in note for note in caught.value.__notes__)
    assert closed_context == []
    closed_context.extend([{
        "session_id": 8
    }])  # Next session replaces old context.
    state.clear()
    assert sidecar.read_text() == "original sidecar"
    expected = hashlib.sha256(
        json.dumps(raw, allow_nan=False, sort_keys=True).encode()).hexdigest()
    script = "import hashlib,json,sys;d=json.load(open(sys.argv[1]));h=hashlib.sha256(json.dumps(d['raw_receipts'],allow_nan=False,sort_keys=True).encode()).hexdigest();assert h==d['raw_receipts_sha256'];print(h)"
    assert subprocess.check_output(
        [sys.executable, "-c", script,
         str(journal)], text=True).strip() == expected
    assert "invocation_identity" not in json.loads(
        journal.read_text())["raw_receipts"][0]
    shutil.rmtree(journal.parent)


def test_success_publishes_durable_receipts_before_owned_journal_cleanup(
        capture, monkeypatch):
    profile, state, raw, _ = capture
    synchronized = []
    fsync = profile.os.fsync

    def track(descriptor):
        synchronized.append(descriptor)
        return fsync(descriptor)

    monkeypatch.setattr(profile.os, "fsync", track)
    profile._snapshot_cann_launch_receipts(state)
    sidecar = Path(state["name"]).with_suffix(".cann-launch-receipts.json")
    document = json.loads(sidecar.read_text())
    assert document["receipts"][0]["token_id"] == raw[0]["token_id"]
    assert document["receipts"][0]["invocation_identity"] is None
    assert len(synchronized) >= 6
    assert "cann_receipt_recovery_path" not in state
    assert "cann_receipt_recovery_undurable_raw" not in state
    assert not list(sidecar.parent.glob("flagprism-cann-receipt-recovery-*"))


def test_stage_failure_uses_independent_recovery_directory(
        capture, monkeypatch):
    profile, state, raw, _ = capture
    mkdtemp = profile.tempfile.mkdtemp
    fallback = Path(state["name"]).parent / "independent"
    fallback.mkdir()

    def create(*args, **kwargs):
        if kwargs.get("dir") is not None:
            raise OSError("stage unwritable")
        return mkdtemp(*args, **{**kwargs, "dir": fallback})

    monkeypatch.setattr(profile.tempfile, "mkdtemp", create)

    def fail(sid):
        raise ValueError("source lookup failed")

    monkeypatch.setattr(profile.LaunchHook, "snapshot", fail)
    with pytest.raises(ValueError, match="source lookup failed"):
        profile._snapshot_cann_launch_receipts(state)
    journal = Path(state["cann_receipt_recovery_path"])
    assert journal.parent.parent == fallback
    assert json.loads(journal.read_text())["raw_receipts"] == raw
    shutil.rmtree(journal.parent)


def test_all_storage_failures_explicitly_report_not_durable(
        capture, monkeypatch):
    profile, state, raw, closed_context = capture

    def fail(*args, **kwargs):
        raise OSError("all recovery storage unwritable")

    monkeypatch.setattr(profile.tempfile, "mkdtemp", fail)
    with pytest.raises(OSError) as caught:
        profile._snapshot_cann_launch_receipts(state)
    assert any("not durable" in note for note in caught.value.__notes__)
    assert state["cann_receipt_recovery_undurable_raw"] == raw
    assert "cann_receipt_recovery_path" not in state
    assert closed_context == []
