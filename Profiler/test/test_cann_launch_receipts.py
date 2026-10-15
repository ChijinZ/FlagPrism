"""Worker token provenance contracts; these are not NPU hardware acceptance."""
import copy
import importlib
import json
from types import SimpleNamespace

import pytest

profile = importlib.import_module("flagtree.profiler.profile")


def _capture(monkeypatch, tmp_path, receipt_change=None, launches=None):
    receipt = {
        "scope_id": 0,
        "session_id": 0,
        "token_id": 19,
        "status": "collected",
        "late_callback": False,
        "publish_count": 1,
        "capture_epoch": 3,
        "collector_output_path": "/sdk/actual-capture",
        "worker": {
            "abi_version": 1,
            "struct_size": 64,
            "process_id": 41,
            "thread_id": 43,
            "stream_handle": 900,
            "task_id": 0,
            "stream_id": 0,
            "device_id": 4,
            "task_query_status": 0,
            "stream_query_status": 0,
            "device_query_status": 0,
            "launch_status": 0
        },
    }
    if receipt_change:
        receipt.update(receipt_change)
    if launches is None:
        launches = [{
            "scope_id": 0,
            "id": "launch-0",
            "binary_id": "actual-binary"
        }]
    monkeypatch.setattr(
        profile, "profiler_native",
        SimpleNamespace(
            supports_cann_launch_receipts=lambda: True,
            drain_cann_launch_receipts=lambda sid: copy.deepcopy([receipt])))
    monkeypatch.setattr(profile.LaunchHook, "snapshot",
                        lambda sid: {"launches": launches})
    base = tmp_path / "capture"
    profile._snapshot_cann_launch_receipts({
        "backend": "cann",
        "session": 0,
        "name": str(base)
    })
    return json.loads(
        base.with_suffix(".cann-launch-receipts.json").read_text())


def test_successful_zero_ids_keep_source_token_provenance(
        monkeypatch, tmp_path):
    document = _capture(monkeypatch, tmp_path)
    receipt = document["receipts"][0]
    assert receipt["worker"]["task_id"] == 0
    assert receipt["worker"]["task_query_status"] == 0
    assert receipt["invocation_identity"] == {
        "invocation_id": "launch-0",
        "scope_id": 0,
        "session_id": 0,
        "binary_id": "actual-binary",
        "evidence": "retained_per_launch_worker_receipt",
    }
    assert "clock" not in receipt
    assert receipt["capture_epoch"] == 3


@pytest.mark.parametrize("roots", [[], ["one", "two"]])
def test_task_export_rejects_missing_or_ambiguous_sdk_owner(tmp_path, roots):
    base = tmp_path / "capture"
    base.with_suffix(".cann-launch-receipts.json").write_text(
        json.dumps({
            "schema_version":
            1,
            "receipts": [{
                "sdk_capture_binding_status": "sealed_unique_sdk_capture",
                "collector_output_path": str(tmp_path / root)
            } for root in roots],
        }))
    profile._export_cann_task_identities({
        "backend": "cann",
        "name": str(base)
    })
    proof = json.loads(
        base.with_suffix(".cann-task-identities.json").read_text())
    assert proof["task_identity_proofs"] == []
    assert proof["clock_status"] == "unverified"
    assert proof["status"] == "unassociated"


@pytest.mark.parametrize("raw_error", [None, FileNotFoundError, ValueError])
def test_task_export_invokes_native_producer_and_retains_unverified_clock(
        monkeypatch, tmp_path, raw_error):
    joint = importlib.import_module("flagtree.profiler.cann_joint")
    raw_module = importlib.import_module("flagtree.profiler.cann_raw_sys")
    base = tmp_path / "capture"
    root = tmp_path / "sdk"
    receipt_file = base.with_suffix(".cann-launch-receipts.json")
    receipt_file.write_text(
        json.dumps({
            "schema_version":
            1,
            "receipts": [{
                "sdk_capture_binding_status": "sealed_unique_sdk_capture",
                "collector_output_path": str(root)
            }],
        }))
    calls = []

    def producer(capture_root, source):
        calls.append((capture_root, source))
        return {
            "schema_version": 1,
            "clock_status": "unverified",
            "task_identity_proofs": [{
                "status": "verified_task_identity"
            }]
        }

    monkeypatch.setattr(joint, "build_native_task_proofs", producer)
    raw_calls = []

    def raw_producer(capture_root, source):
        raw_calls.append((capture_root, source))
        if raw_error is not None:
            raise raw_error("SDK counter schema is unavailable")
        return {
            "schema_version": 1,
            "clock_status": "unverified",
            "task_sys_envelopes": [{
                "status": "raw_task_envelope_extracted"
            }]
        }

    monkeypatch.setattr(raw_module, "build_raw_task_sys", raw_producer)
    profile._export_cann_task_identities({
        "backend": "cann",
        "name": str(base)
    })
    assert calls == [(str(root.resolve()), receipt_file)]
    assert raw_calls == calls
    proof = json.loads(
        base.with_suffix(".cann-task-identities.json").read_text())
    assert proof["clock_status"] == "unverified"
    assert proof["task_identity_proofs"][0][
        "status"] == "verified_task_identity"
    raw = json.loads(base.with_suffix(".cann-raw-sys.json").read_text())
    assert raw["clock_status"] == "unverified"
    if raw_error is None:
        assert raw["task_sys_envelopes"][0][
            "status"] == "raw_task_envelope_extracted"
    else:
        assert raw["status"] == "unavailable"
        assert raw["task_sys_envelopes"] == []
        assert raw["reason"] == "SDK counter schema is unavailable"


def test_task_export_does_not_hide_invalid_sdk_proof(monkeypatch, tmp_path):
    joint = importlib.import_module("flagtree.profiler.cann_joint")
    base = tmp_path / "capture"
    base.with_suffix(".cann-launch-receipts.json").write_text(
        json.dumps({
            "schema_version":
            1,
            "receipts": [{
                "sdk_capture_binding_status": "sealed_unique_sdk_capture",
                "collector_output_path": str(tmp_path / "sdk")
            }],
        }))

    def producer(*args):
        raise ValueError("invalid SDK lifetime evidence")

    monkeypatch.setattr(joint, "build_native_task_proofs", producer)
    with pytest.raises(ValueError, match="invalid SDK lifetime evidence"):
        profile._export_cann_task_identities({
            "backend": "cann",
            "name": str(base)
        })
    assert not base.with_suffix(".cann-task-identities.json").exists()


@pytest.mark.parametrize("change", [
    {
        "status": "pending"
    },
    {
        "status": "query_failed"
    },
    {
        "status": "cancelled"
    },
    {
        "late_callback": True
    },
    {
        "publish_count": 2
    },
    {
        "session_id": 1
    },
    {
        "scope_id": 7
    },
])
def test_uncertified_receipts_are_preserved_without_source_binding(
        monkeypatch, tmp_path, change):
    receipt = _capture(monkeypatch, tmp_path, change)["receipts"][0]
    assert receipt["invocation_identity"] is None
    assert all(receipt[key] == value for key, value in change.items())
    assert receipt["worker"]["task_id"] == 0


@pytest.mark.parametrize("launches", [
    [{
        "scope_id": 0,
        "id": "launch-0",
        "binary_id": "a"
    }, {
        "scope_id": 0,
        "id": "launch-0-other",
        "binary_id": "b"
    }],
    [{
        "scope_id": 0,
        "id": "launch-0",
        "binary_id": None
    }],
    [{
        "scope_id": 0,
        "id": "launch-0",
        "binary_id": "a",
        "status": "rejected_before_launch"
    }],
])
def test_ambiguous_missing_or_rejected_source_never_binds(
        monkeypatch, tmp_path, launches):
    receipt = _capture(monkeypatch, tmp_path, launches=launches)["receipts"][0]
    assert receipt["invocation_identity"] is None


@pytest.mark.parametrize("change", [
    {
        "task_query_status": 1
    },
    {
        "launch_status": 1
    },
    {
        "abi_version": 2
    },
    {
        "struct_size": 0
    },
    {
        "process_id": 0
    },
    {
        "stream_id": -1
    },
    {
        "task_id": None
    },
])
def test_success_label_cannot_override_failed_or_malformed_worker_query(
        monkeypatch, tmp_path, change):
    worker = {
        "abi_version": 1,
        "struct_size": 64,
        "process_id": 41,
        "thread_id": 43,
        "stream_handle": 900,
        "device_id": 4,
        "task_id": 0,
        "stream_id": 0,
        "launch_status": 0,
        "task_query_status": 0,
        "stream_query_status": 0,
        "device_query_status": 0,
        **change
    }
    receipt = _capture(monkeypatch, tmp_path,
                       {"worker": worker})["receipts"][0]
    assert receipt["status"] == "collected"
    assert receipt["invocation_identity"] is None
    assert receipt["worker"] == worker
