"""Enflame session isolation, including kernels without Triton scopes."""

import json

import pytest


def test_enflame_session_launch_membership(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("torch_gcu")
    triton = pytest.importorskip("triton")
    import triton.language as tl
    from flagtree import profiler

    if triton.runtime.driver.active.get_current_target().backend != "gcu":
        pytest.skip("Enflame device required")

    @triton.jit
    def session_probe(X, Y, TAG: tl.constexpr):
        i = tl.arange(0, 32)
        x = tl.load(X + i)
        tl.store(Y + i, x + TAG)

    x = torch.ones(32, device="gcu")
    y = torch.empty_like(x)
    # Compile before collecting to avoid timing compilation or initialization.
    for tag in range(5):
        session_probe[(1, )](x, y, tag)
    torch.gcu.synchronize()
    paths = [tmp_path / "first", tmp_path / "second"]
    # hook=None exercises raw TOPSPTI activities without scope correlation.
    first = profiler.start(
        str(paths[0]),
        backend="enflame",
        context="shadow",
        data="tree",
        mode="runtime_base:runtime_host_timing_fallback=false",
    )
    assert profiler.start(
        str(paths[0]),
        backend="enflame",
        context="shadow",
        data="tree",
        mode="runtime_base:runtime_host_timing_fallback=false") == first
    second = None
    try:
        session_probe[(1, )](x, y, 0)  # first only
        profiler.deactivate(first)
        session_probe[(1, )](x, y, 1)  # paused: neither
        # Vendor adapters currently reject overlapping sessions, even paused
        # ones. Preserve that API contract rather than enabling it implicitly.
        with pytest.raises(RuntimeError, match="does not support overlapping"):
            profiler.start(
                str(paths[1]),
                backend="enflame",
                context="shadow",
                data="tree",
                mode="runtime_base:runtime_host_timing_fallback=false",
            )
        profiler.activate(first)
        session_probe[(1, )](x, y, 3)  # resumed first
        session_probe[(1, )](x, y, 4)  # first only
    finally:
        profiler.finalize(first)
        if second is not None:
            profiler.finalize(second)
    second = profiler.start(
        str(paths[1]),
        backend="enflame",
        context="shadow",
        data="tree",
        mode="runtime_base:runtime_host_timing_fallback=false",
    )
    try:
        session_probe[(1, )](x, y, 2)
    finally:
        profiler.finalize(second)
    events = []
    for path in paths:
        assert (path / "manifest.json").exists()
        assert not (path / "ai/counters.json").exists()
        assert not (path / "raw").exists()
        assert not path.with_suffix(".vendor.json").exists()
        associations = [
            json.loads(line)["original_record"]
            for line in (path / "ai/events.jsonl").read_text().splitlines()
        ]
        # Assert exact launch membership, not merely a nonempty timing report.
        events.append({
            a["runtime_event"]["correlation_id"]
            for a in associations
            if "session_probe" in a["runtime_event"]["op_name"]
        })
    assert len(events[0]) == 3
    assert len(events[1]) == 1
    assert not events[0] & events[1]


def test_enflame_detailed_memory_and_api_capture(tmp_path):
    import ctypes
    pytest.importorskip("torch_gcu")
    triton = pytest.importorskip("triton")
    if triton.runtime.driver.active.get_current_target().backend != "gcu":
        pytest.skip("Enflame device required")
    from flagtree import profiler

    runtime = ctypes.CDLL("/opt/tops/lib/libtopsrt.so")
    runtime.topsMalloc.argtypes = [
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t
    ]
    runtime.topsFree.argtypes = [ctypes.c_void_p]
    runtime.topsMemcpy.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int
    ]
    runtime.topsMemset.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t
    ]
    pointer = ctypes.c_void_p()
    source = (ctypes.c_ubyte * 4096)(*([19] * 4096))
    output = (ctypes.c_ubyte * 4096)()
    path = tmp_path / "detailed"
    session = profiler.start(
        str(path),
        backend="enflame",
        data="tree",
        context="shadow",
        mode="runtime_base:runtime_host_timing_fallback=false")
    try:
        assert runtime.topsMalloc(ctypes.byref(pointer), 4096) == 0
        try:
            assert runtime.topsMemset(pointer, 0, 4096) == 0
            assert runtime.topsMemcpy(pointer, source, 4096, 1) == 0
            assert runtime.topsMemcpy(output, pointer, 4096, 2) == 0
            assert bytes(output) == bytes(source)
        finally:
            assert runtime.topsFree(pointer) == 0
    finally:
        profiler.finalize(session)
    associations = [
        json.loads(line)["original_record"]
        for line in (path / "ai/events.jsonl").read_text().splitlines()
    ]
    kinds = {a["metrics"]["activity.kind"] for a in associations}
    assert {"runtime", "memcpy", "memset"} <= kinds
    # Finalization synchronization belongs to the profiler, not this workload.
    assert not any(a["runtime_event"]["op_name"] == "topsDeviceSynchronize"
                   for a in associations)
    transfers = [a for a in associations if a["source"] == "topspti_memcpy"]
    assert {a["metrics"]["enflame.copy_kind"] for a in transfers} >= {1, 2}
    assert all(a["metrics"]["activity.bytes"] == 4096 for a in transfers)
    api = {
        a["runtime_event"]["correlation_id"]: a
        for a in associations
        if a["source"] in ("topspti_runtime", "topspti_driver")
    }
    assert all(a["runtime_event"]["correlation_id"] in api for a in transfers)
    memory = [
        a for a in associations if "activity.memory_action" in a["metrics"]
    ]
    assert {a["metrics"]["activity.memory_action"]
            for a in memory} == {"allocate", "free"}
    assert all(a["metrics"]["activity.address"] == pointer.value
               for a in memory)


def test_prewarmed_kernel_source_and_arguments(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("torch_gcu")
    triton = pytest.importorskip("triton")
    import triton.language as tl
    from flagtree import profiler
    if triton.runtime.driver.active.get_current_target().backend != "gcu":
        pytest.skip("Enflame device required")

    @triton.jit
    def metadata_probe(X, Y, N: tl.constexpr):
        i = tl.arange(0, N)
        tl.store(Y + i, tl.load(X + i) + 1)

    inputs = [torch.ones(size, device="gcu") for size in (32, 64)]
    outputs = [torch.empty_like(x) for x in inputs]
    for x, y in zip(inputs, outputs):
        metadata_probe[(1, )](x, y, x.numel())
    torch.gcu.synchronize()
    folder = tmp_path / "metadata"
    session = profiler.start(
        str(folder),
        backend="enflame",
        hook="triton",
        metadata={"software": {
            "test_marker": "retained"
        }})
    validation = {"status": "not_checked"}
    try:
        for x, y in zip(inputs, outputs):
            metadata_probe[(1, )](x, y, x.numel())
        torch.gcu.synchronize()
        profiler.deactivate(session)
        for y in outputs:
            assert torch.equal(y.cpu(), torch.full(y.shape, 2.))
        validation = {"status": "passed", "reference": "CPU torch.full"}
    finally:
        profiler.finalize(session,
                          metadata={
                              "workload": {
                                  "operator": "metadata_probe",
                                  "parameters": {},
                                  "warmup": {
                                      "iterations_per_shape": 1
                                  },
                                  "measurement": {
                                      "iterations_per_shape": 1
                                  },
                                  "validation": validation
                              }
                          })
    context = json.loads((folder / "ai/context.json").read_text())
    assert context["supplied"]["software"]["test_marker"] == "retained"
    assert context["supplied"]["workload"]["validation"]["status"] == "passed"
    assert context["sections"]["workload"]["missing"] == []
    launches = json.loads((folder / "ai/launches.json").read_text())
    binaries = json.loads((folder / "ai/binaries.json").read_text())
    arguments = json.loads((folder / "ai/arguments.json").read_text())
    assert {
        tuple(arguments[row["argument_id"]]["X"]["shape"])
        for row in launches
    } == {(32, ), (64, )}
    assert len(binaries) == 2
    assert all(
        (folder /
         row["source"]["text_file"]).read_text() and row["source"]["sha256"]
        for row in binaries)
    assert all(row["binary_sha256"] and row["compiler_metadata"]["num_warps"]
               for row in binaries)
    kernels = json.loads((folder / "ai/kernels.json").read_text())["groups"]
    assert len(kernels) == 2
    assert all(row["count"] == 1 for row in kernels)
    tree = json.loads((folder / "ai/call_tree.json").read_text())

    def check(node):
        assert not any(
            key.startswith(("activity.", "runtime.", "vendor."))
            for key in node.get("metrics", {}))
        for child in node.get("children", []):
            check(child)

    for root in tree:
        check(root)
