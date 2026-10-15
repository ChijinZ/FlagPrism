"""Bounded public-tool Softmax diagnostic, not a performance experiment."""
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("FLAGPRISM_TEST_ENFLAME") != "1",
    reason="requires selected real Enflame hardware and canonical Study inputs"
)


@pytest.mark.parametrize("work_items", [4, 1])
def test_public_softmax_organization_diagnostic(tmp_path, work_items):
    import torch
    import torch_gcu  # noqa: F401
    import flagtree.profiler as profiler
    from fixtures.enflame_method import kernels

    root = Path(os.environ["FLAGPRISM_ENFLAME_CANONICAL_INPUT_DIR"])
    expected_hashes = [
        "cfaffaf5a0806a2f44aa8bf82dbb29d367ec27d4bbbb2c7979523d1753325f2d",
        "54ea02d10c9642507f147125ee2efbe7fcd3d832fb0bb4d0ffe40a960da80a8e",
        "9de112a3efa65bf5a1798a3bae097c5ff840b3a5b9a5d4d90fec8a8a8330e915",
    ]
    raw = [(root / f"rows-127x769-{index}.bin").read_bytes()
           for index in range(3)]
    assert [hashlib.sha256(value).hexdigest()
            for value in raw] == expected_hashes
    cpu = [
        torch.frombuffer(bytearray(value),
                         dtype=torch.float32).clone().reshape((
                             127, 769) if index == 0 else (769, ))
        for index, value in enumerate(raw)
    ]
    x, w, bias = [value.to("gcu:0") for value in cpu]
    sentinel, guard = -12345.75, 32
    output_storage = torch.full((x.numel() + 2 * guard, ),
                                sentinel,
                                dtype=torch.float32,
                                device="gcu:0")
    y = output_storage[guard:-guard].view(127, 769)
    reference = torch.softmax(cpu[0], dim=-1)
    torch.gcu.synchronize(0)
    bundle = tmp_path / "bundle"
    request = profiler.ObservationRequest(programs=(0, ),
                                          sites=(29, ),
                                          max_events_per_instance=64)
    session = profiler.start(str(bundle),
                             backend="enflame",
                             hook="instrumentation",
                             observation_request=request)
    try:
        compiled = kernels.rows[(127, )](x,
                                         w,
                                         bias,
                                         y,
                                         127,
                                         769,
                                         1024,
                                         1,
                                         "softmax",
                                         num_warps=work_items,
                                         num_stages=1)
        torch.gcu.synchronize(0)
    finally:
        profiler.finalize(session)
    actual = y.cpu()
    torch.testing.assert_close(actual, reference, rtol=.002, atol=.0005)
    for value, original in zip((x, w, bias), cpu):
        torch.testing.assert_close(value.cpu(), original, rtol=0, atol=0)
    guards = output_storage.cpu()
    assert (guards[:guard] == sentinel).all() and (guards[-guard:]
                                                   == sentinel).all()
    metadata = compiled.metadata._asdict()
    metadata.pop("target", None)
    selected = [
        row for row in metadata["debug_tracked_table"] if row["opId"] == 29
    ]
    assert len(selected) == 1 and selected[0]["mlirOpName"] == "tt.store"
    assert metadata["enable_i64"] is False
    assert metadata["debug_dynamic_index_bits"] == 32
    assert metadata["debug_record_layout"] == "selected_dynamic_timeline_v1"
    observations = json.loads((bundle / "ai/observations.json").read_text())
    assert len(observations["captures"]) == 1
    events = observations["observations"]
    assert len(events) == 1
    assert events[0]["site"] == 29 and events[0]["program"] == 0
    assert events[0]["association_status"] == "verified"
    assert events[0]["association_evidence"][
        "evidence"] == "same_launch_metadata_object"
    assert events[0]["duration_ns"] is None
    native = [
        json.loads(row)
        for row in (bundle / "ai/events.jsonl").read_text().splitlines()
    ]
    native = [row for row in native if row["kind"] == "kernel"]
    assert len(native) == 1
    assert native[0]["launch_id"] == events[0]["invocation_id"]
    assert native[0]["binary_id"] == compiled.hash
    binary, = json.loads(
        (bundle / "ai/execution.json").read_text())["binaries"]
    assert binary["binary_id"] == compiled.hash
    mapping = binary["mapping"]
    assert mapping["work_item_count"] == work_items
    counts = Counter(site["kind"] for site in mapping["sites"])
    user_exchange = [
        site for site in mapping["sites"]
        if site["kind"] in ("barrier", "partial_exchange_storage")
    ]
    # These are static IR sites, not ten physical exchanges or exclusive cost.
    assert counts["barrier"] == (2 if work_items == 4 else 0)
    assert counts["partial_exchange_storage"] == (10 if work_items == 4 else 0)
    if work_items == 4:
        assert any("memref<1x4xf32, 2>" in site["evidence"]
                   for site in user_exchange)
        assert any("work_item.x" in expression for site in user_exchange
                   for expression in site.get("operand_expressions", []))
    assert mapping["status"] == "partial"
    asm = tmp_path / "asm"
    asm.mkdir()
    for name, value in compiled.asm.items():
        if isinstance(value, str):
            (asm / name).write_text(value)
        elif isinstance(value, bytes):
            (asm / name).write_bytes(value)
    (tmp_path / "compiled-metadata.json").write_text(
        json.dumps(metadata, default=str, indent=2))
    summary = dict(
        work_items=work_items,
        shape=[127, 769],
        ROWS=1,
        BLOCK=1024,
        grid=[127],
        num_stages=1,
        input_sha256=expected_hashes,
        binary_id=compiled.hash,
        math=dict(passed=True,
                  reference="CPU PyTorch FP32",
                  rtol=.002,
                  atol=.0005,
                  max_abs_error=float((actual - reference).abs().max()),
                  input_unchanged=True,
                  output_guards_unchanged=True),
        request=dict(programs=[0], sites=[29], max_events_per_instance=64),
        compiler_site_counts=dict(counts),
        user_exchange_sites=user_exchange,
        symbolic_ownership_sites=[
            site for site in mapping["sites"]
            if site["ownership_status"] == "symbolic"
        ],
        native=native,
        retained_observations=events,
        kernel_python_file_sha256=hashlib.sha256(
            Path(kernels.__file__).read_bytes()).hexdigest(),
        limits=[
            "Static compiler sites and symbolic ownership, not measured worker utilization.",
            "One detailed invocation is a functional diagnostic, not performance evidence.",
            "Raw counter frequency/alignment remains unverified; no exclusive source cost."
        ])
    (tmp_path /
     "diagnostic.json").write_text(json.dumps(summary, indent=2) + "\n")
