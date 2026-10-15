"""Actual GCU stream isolation; this tests identity, not overlap or performance."""
import hashlib
import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("FLAGPRISM_TEST_ENFLAME") != "1",
    reason="requires selected real Enflame hardware")


def test_interleaved_two_streams_preserve_launch_identity(tmp_path):
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler import ObservationRequest
    from flagtree.profiler.hooks.launch import LaunchHook

    @triton.jit
    def stream_payload(X, Y, N: tl.constexpr, B: tl.constexpr,
                       SCALE: tl.constexpr):
        offsets = tl.program_id(0) * B + tl.arange(0, B)
        values = tl.load(X + offsets, offsets < N, 0)
        tl.store(Y + offsets, values * SCALE + 3, offsets < N)

    n, block, guard = 173, 64, 16
    sentinel = -12345.0
    streams = [torch.gcu.Stream(device=0), torch.gcu.Stream(device=0)]
    handles = [int(s.gcu_stream) for s in streams]
    assert handles[0] and handles[1] and handles[0] != handles[1]
    schedule = [(0, 1), (1, 1), (0, 1), (1, 1), (0, 2), (1, 2)]
    inputs, outputs, originals = [], [], []
    for index, _ in enumerate(schedule):
        cpu = torch.full((n + 2 * guard, ),
                         sentinel,
                         dtype=torch.float32,
                         device="cpu")
        cpu[guard:guard + n] = torch.arange(
            n, dtype=torch.float32, device="cpu") + index * 100
        originals.append(cpu)
        inputs.append(cpu.to("gcu:0"))
        outputs.append(
            torch.full((n + 2 * guard, ),
                       sentinel,
                       dtype=torch.float32,
                       device="gcu:0"))
    torch.gcu.synchronize(0)
    output = tmp_path / "bundle"
    session = profiler.start(str(output),
                             backend="enflame",
                             hook="instrumentation",
                             observation_request=ObservationRequest(
                                 programs=(1, ), max_events_per_instance=64))
    host_receipts, kernels = [], {}
    try:
        for index, (stream_index, scale) in enumerate(schedule):
            before = {
                row["id"]
                for row in LaunchHook.snapshot(session)["launches"]
            }
            with torch.gcu.stream(streams[stream_index]):
                actual_handle = int(torch.gcu.current_stream(0).gcu_stream)
                assert actual_handle == handles[stream_index]
                kernel = stream_payload[(triton.cdiv(n, block), )](
                    inputs[index][guard:guard + n],
                    outputs[index][guard:guard + n],
                    n,
                    block,
                    scale,
                    num_warps=1)
            added = [
                row for row in LaunchHook.snapshot(session)["launches"]
                if row["id"] not in before
            ]
            assert len(added) == 1
            launch = added[0]
            assert launch["binary_id"] == kernel.hash
            host_receipts.append(
                dict(index=index,
                     stream_index=stream_index,
                     stream_handle=actual_handle,
                     scale=scale,
                     launch_id=launch["id"],
                     scope_id=launch["scope_id"],
                     binary_id=kernel.hash))
            kernels[kernel.hash] = kernel
        torch.gcu.synchronize(0)
    finally:
        profiler.finalize(session)
    (tmp_path / "host-receipts.json"
     ).write_text(json.dumps(host_receipts, indent=2) + "\n")
    for index, (_, scale) in enumerate(schedule):
        torch.testing.assert_close(inputs[index].cpu(),
                                   originals[index],
                                   rtol=0,
                                   atol=0)
        expected = originals[index].clone()
        expected[guard:guard + n] = expected[guard:guard + n] * scale + 3
        torch.testing.assert_close(outputs[index].cpu(),
                                   expected,
                                   rtol=0,
                                   atol=0)
    document = json.loads((output / "ai/observations.json").read_text())
    native = [
        json.loads(line)
        for line in (output / "ai/events.jsonl").read_text().splitlines()
    ]
    native = [row for row in native if row["kind"] == "kernel"]
    assert len(host_receipts) == len(native) == len(document["captures"]) == 6
    assert len(kernels) == 2
    assert len({r["binary_id"] for r in host_receipts[:4]}) == 1
    assert host_receipts[4]["binary_id"] == host_receipts[5][
        "binary_id"] != host_receipts[0]["binary_id"]
    by_stream, seen_captures, seen_tasks = {}, set(), set()
    for receipt in host_receipts:
        launch_id = receipt["launch_id"]
        peers = [row for row in native if row.get("launch_id") == launch_id]
        assert len(peers) == 1
        event = peers[0]
        assert event["binary_id"] == receipt["binary_id"]
        assert event["scope_id"] == receipt["scope_id"]
        assert event["device"] == 0 and event["source"] == "topspti_activity"
        assert event["stream_id"] is not None
        assert event["process_id"] == os.getpid()
        assert event["context_id"] is not None
        assert isinstance(event["correlation_domain"],
                          str) and event["correlation_domain"]
        assert type(
            event["correlation_id"]) is int and event["correlation_id"] > 0
        by_stream.setdefault(receipt["stream_index"],
                             set()).add(event["stream_id"])
        task = (event["source"], event["process_id"], event["context_id"],
                event["correlation_domain"], event["correlation_id"],
                event["device"], event["stream_id"])
        assert task not in seen_tasks
        seen_tasks.add(task)
        events = [
            e for e in document["observations"]
            if e.get("invocation_id") == launch_id
        ]
        assert events and all(e["association_status"] == "verified"
                              for e in events)
        assert all(e["association_evidence"]["evidence"] ==
                   "same_launch_metadata_object" for e in events)
        captures = {e["capture_id"] for e in events}
        assert len(captures) == 1 and not captures & seen_captures
        seen_captures.update(captures)
        assert all(e["program"] == 1 and e["actor"] == 0 for e in events)
        receipt.update(native_stream_id=event["stream_id"],
                       native_task_id=event["task_id"],
                       correlation_id=event["correlation_id"],
                       native_process_id=event["process_id"],
                       native_context_id=event["context_id"],
                       native_correlation_domain=event["correlation_domain"],
                       native_task_id_status=event.get("field_issues", {}).get(
                           "task_id", "reported"),
                       capture_id=next(iter(captures)),
                       observation_count=len(events))
    assert all(len(ids) == 1 for ids in by_stream.values())
    assert by_stream[0].isdisjoint(by_stream[1])
    for binary, kernel in kernels.items():
        metadata = kernel.metadata._asdict()
        metadata.pop("target", None)
        assert metadata["debug_dynamic_index_bits"] == 32
        assert metadata["enable_i64"] is False
        assert metadata[
            "debug_record_layout"] == "selected_dynamic_timeline_v1"
        folder = tmp_path / binary
        folder.mkdir()
        (folder / "metadata.json").write_text(
            json.dumps(metadata, default=str, indent=2))
        for name, value in kernel.asm.items():
            if isinstance(value, str):
                (folder / name).write_text(value)
    files = {
        str(p.relative_to(tmp_path)):
        hashlib.sha256(p.read_bytes()).hexdigest()
        for p in tmp_path.rglob("*") if p.is_file()
    }
    (tmp_path / "two-stream-summary.json").write_text(
        json.dumps(dict(
            status="passed",
            limitation=
            "SDK grid/task ID remains unknown when raw gridId=0; identity verified using process/context/provider/domain/correlation/scope/binary/stream, not task/grid ID",
            device=0,
            mathematical_oracle="exact CPU FP32 plus input/output guards",
            real_stream_handles=handles,
            host_receipts=host_receipts,
            scope=
            "interleaved actual streams; no simultaneous-overlap or clock-alignment claim",
            launch_identity_basis=
            "exact newly observed LaunchHook ID per controlled API call; native SDK scope/correlation and binary IDs",
            files_sha256=files),
                   indent=2) + "\n")
