"""Actual GCU dynamic loop/branch, sampling, capacity, and launch isolation.

The oracle counts the two compiled store sites against runtime loop parity;
other operations may be optimized and are not assumed to have source iteration.
"""
import os
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("FLAGPRISM_TEST_ENFLAME") != "1",
                                reason="requires selected real Enflame hardware")


def _run(tmp_path, steps, *, capacity=512, sample_every=1, selected_program=1, work_items=1, launches=1, sites=None):
    import json
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler import ObservationRequest

    @triton.jit(do_not_specialize=["STEPS"])
    def retained_loop(X, Y, N: tl.constexpr, B: tl.constexpr, STEPS):
        offset = tl.program_id(0) * B + tl.arange(0, B)
        x = tl.load(X + offset, offset < N, 0)
        for iteration in range(STEPS):
            if iteration % 2 == 0:
                tl.store(Y + iteration * N + offset, x + iteration, offset < N)
            else:
                tl.store(Y + iteration * N + offset, x - iteration, offset < N)

    n, block = 173, 64
    cpu = torch.arange(n, dtype=torch.float32, device="cpu")
    x = cpu.to("gcu")
    y = torch.full((max(1, steps), n), float("nan"), dtype=torch.float32, device="gcu")
    output = tmp_path / "bundle"
    profiler.start(str(output), backend="enflame", hook="instrumentation",
                   observation_request=ObservationRequest(programs=(selected_program,),
                       sites=sites, max_events_per_instance=capacity, sample_every=sample_every))
    for _ in range(launches):
        try:
            kernel = retained_loop[(triton.cdiv(n, block),)](x, y, n, block, steps, num_warps=work_items)
        except BaseException as error:
            try:
                profiler.finalize()
            except Exception as cleanup_error:
                error.add_note(f"profiling finalization after rejected compilation: {cleanup_error}")
            raise
    torch.gcu.synchronize()
    profiler.finalize()
    if steps:
        expected = torch.stack([cpu + i if i % 2 == 0 else cpu - i for i in range(steps)])
        torch.testing.assert_close(y.cpu(), expected)
    else:
        assert torch.isnan(y.cpu()).all()
    metadata = kernel.metadata._asdict()
    metadata.pop("target", None)
    (tmp_path / "compiled-metadata.json").write_text(json.dumps(metadata, default=str, indent=2))
    for key, value in kernel.asm.items():
        if isinstance(value, str):
            (tmp_path / key).write_text(value)
    document = json.loads((output / "ai/observations.json").read_text())
    events = [e for e in document["observations"] if e.get("storage") == "selected_dynamic_append"]
    stores = [e["opId"] for e in metadata["debug_tracked_table"] if e["mlirOpName"] == "tt.store"]
    assert metadata["debug_record_layout"] == "selected_dynamic_timeline_v1"
    assert metadata["debug_dynamic_index_bits"] == 32
    assert metadata["debug_clock_carrier"] == "llvm_i64_words"
    assert metadata["enable_i64"] is False
    # The observer must not feed TTIR/SCF arithmetic with an i64 carrier.
    import re
    for line in kernel.asm["ttir"].splitlines():
        if re.match(r"\s*(?:%[\w.$]+(?::\d+)?\s*=\s*)?(?:arith\.|scf\.)", line):
            assert not re.search(r"\bi64\b", line), line
    assert metadata["debug_clock_primitive"] == "_ZN4tops12global_timerEv"
    assert len(stores) == 2
    assert events
    assert all(e["program"] == selected_program and e["actor"] == 0 for e in events)
    assert all(e["clock"]["domain"] == "enflame.sdk.global_timer" for e in events)
    assert all(e["start_tick"] > 0 and e["duration_ns"] is None for e in events)
    assert all(e["association_status"] == "verified" for e in events)
    assert all(e["association_evidence"]["evidence"] == "same_launch_metadata_object" for e in events)
    for capture in {e["capture_id"] for e in events}:
        retained = [e for e in events if e["capture_id"] == capture]
        assert [e["sequence"] for e in retained] == list(range(len(retained)))
    assert all(e["attempted_ordinal"] % sample_every == 0 for e in events)
    return document, events, stores


@pytest.mark.parametrize("steps", [0, 1, 5, 9])
def test_actual_dynamic_loop_branches(tmp_path, steps):
    document, events, stores = _run(tmp_path, steps)
    counts = sorted(sum(e["site"] == site for e in events) for site in stores)
    assert counts == sorted([(steps + 1) // 2, steps // 2])
    for site in stores:
        assert [e["occurrence"] for e in events if e["site"] == site] == list(range(sum(e["site"] == site for e in events)))
    header = document["captures"][0]["header"]
    assert header["write_idx"] == len(events)
    assert header["overflow_count"] == 0
    assert header["reserved0"] == len(events)


def test_capacity_and_sampling_are_explicit(tmp_path):
    full, events, _ = _run(tmp_path / "full", 5)
    sampled, sparse, _ = _run(tmp_path / "sampled", 5, sample_every=3)
    limited, truncated, _ = _run(tmp_path / "limited", 5, capacity=5)
    attempted = full["captures"][0]["header"]["reserved0"]
    assert sampled["captures"][0]["header"]["reserved0"] == attempted
    assert len(sparse) == (attempted + 2) // 3
    assert [e["attempted_ordinal"] for e in sparse] == list(range(0, attempted, 3))
    assert len(truncated) == 5
    header = limited["captures"][0]["header"]
    assert header["write_idx"] == attempted
    assert header["overflow_count"] == attempted - 5
    assert header["flags"] & 1


def test_cooperative_work_items_keep_single_writer(tmp_path):
    document, events, stores = _run(tmp_path, 5, work_items=4)
    counts = sorted(sum(e["site"] == site for e in events) for site in stores)
    assert counts == [2, 3]
    assert document["captures"][0]["header"]["reserved0"] == len(events)


def test_repeated_same_binary_launch_identity(tmp_path):
    document, events, stores = _run(tmp_path, 5, launches=2)
    assert len(document["captures"]) == 2
    identities = {e["invocation_id"] for e in events}
    assert len(identities) == 2
    for identity in identities:
        retained = [e for e in events if e["invocation_id"] == identity]
        assert sorted(sum(e["site"] == site for e in retained) for site in stores) == [2, 3]


def test_selected_site_sampling_and_capacity(tmp_path):
    _, _, stores = _run(tmp_path / "discover", 9)
    site = stores[0]
    full, events, _ = _run(tmp_path / "selected", 9, sites=(site,))
    assert {e["site"] for e in events} == {site}
    attempted = len(events)
    assert attempted in (4, 5)
    assert full["captures"][0]["header"]["reserved0"] == attempted
    sampled, sparse, _ = _run(tmp_path / "sampled", 9, sites=(site,), sample_every=2)
    assert {e["site"] for e in sparse} == {site}
    assert [e["attempted_ordinal"] for e in sparse] == list(range(0, attempted, 2))
    assert sampled["captures"][0]["header"]["reserved0"] == attempted
    limited, retained, _ = _run(tmp_path / "limited", 9, sites=(site,), capacity=1)
    assert len(retained) == 1
    assert limited["captures"][0]["header"]["overflow_count"] == attempted - 1


@pytest.mark.parametrize("sites", [(2147483647,), (0,), (1, 2147483647)])
def test_nonexistent_or_uninstrumentable_site_rejected(tmp_path, sites):
    with pytest.raises((RuntimeError, ValueError), match="site"):
        _run(tmp_path, 5, sites=sites)


def test_public_pause_resume_keeps_only_active_invocations(tmp_path):
    import json
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler import ObservationRequest

    @triton.jit(do_not_specialize=["ALPHA"])
    def paused_probe(X, Y, N: tl.constexpr, B: tl.constexpr, ALPHA):
        offset = tl.program_id(0) * B + tl.arange(0, B)
        value = tl.load(X + offset, offset < N, 0)
        tl.store(Y + offset, value + ALPHA, offset < N)

    cpu = torch.arange(83, dtype=torch.float32, device="cpu")
    x, y = cpu.to("gcu"), torch.empty((83,), dtype=torch.float32, device="gcu")
    output = tmp_path / "bundle"
    session = profiler.start(str(output), backend="enflame", hook="instrumentation",
                             observation_request=ObservationRequest(programs=(1,)))
    compiled = []
    try:
        compiled.append(paused_probe[(2,)](x, y, 83, 64, 1., num_warps=4))
        torch.gcu.synchronize()
        torch.testing.assert_close(y.cpu(), cpu + 1.)
        profiler.deactivate(session)
        compiled.append(paused_probe[(2,)](x, y, 83, 64, 2., num_warps=4))
        torch.gcu.synchronize()
        torch.testing.assert_close(y.cpu(), cpu + 2.)
        profiler.activate(session)
        compiled.append(paused_probe[(2,)](x, y, 83, 64, 3., num_warps=4))
        torch.gcu.synchronize()
        torch.testing.assert_close(y.cpu(), cpu + 3.)
    finally:
        profiler.finalize(session)
    document = json.loads((output / "ai/observations.json").read_text())
    assert len(document["captures"]) == 2
    events = document["observations"]
    assert events and all(e["association_status"] == "verified" for e in events)
    assert len({e["invocation_id"] for e in events}) == 2
    assert all(e["program"] == 1 and e["actor"] == 0 for e in events)
    native = [json.loads(line) for line in (output / "ai/events.jsonl").read_text().splitlines()]
    assert len([e for e in native if e["kind"] == "kernel"]) == 2
    assert compiled[0].hash == compiled[2].hash != compiled[1].hash
    for index, kernel in enumerate(compiled):
        metadata = kernel.metadata._asdict()
        metadata.pop("target", None)
        (tmp_path / f"phase-{index}-metadata.json").write_text(json.dumps(metadata, default=str, indent=2))
        (tmp_path / f"phase-{index}-llir").write_text(kernel.asm["llir"])
    assert "_ZN4tops12global_timerEv" not in compiled[1].asm["llir"]
