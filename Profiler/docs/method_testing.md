# Method acceptance tests

Run installations, compilation, tests, CPU references and hardware experiments
inside the target server Docker. Preserve logs, terminal exit status, source
baseline, actual import paths, compiler/native SHA-256, device identity and full
output directories. A successful SSH transport is not a test result.

The legacy `test.py` operator checks remain regression probes. Their WARNING
policy does not establish actual profiling coverage or replace semantic tests.

## Contracts and recovery

Run against the current source and matching built runtime:

```bash
python -m pytest -q \
  Profiler/test/test_report.py Profiler/test/test_portable_capture.py \
  Profiler/test/test_launch_metadata.py Profiler/test/test_tcu.py \
  Profiler/test/test_observation_contract.py \
  Profiler/test/test_internal_time_semantics.py \
  Profiler/test/test_reconstruction.py Profiler/test/test_hook_rollback.py
```

These cover malformed records, unknown IDs, rejected joins, unverified clocks,
lossless raw artifacts, manifest hashes, replay separation and cleanup preserving
the original exception. Browser skips remain skips. Also run applicable native
`test_api.py`, `test_profile.py`, `test_instrumentation.py` and backend suites;
mock-only passes cannot establish native lifecycle or SDK support.

## Compiler, protocol and actual hardware

* Debugger C++ `DecodeTest`: record width, bounds/capacity, commit tag,
  dynamic sequence/attempt counts, timestamp and partial-publication rejection.
  Use the actual backend CMake/gtest target.
* NVIDIA: `tests/nvidia/test_execution_nvidia.py`, `test_proton_ring.py`,
  `protongpu_lowering.mlir`; actual runners `native_smoke.py`,
  `execution_hardware.py`, `instrumentation_hardware.py`, `request_hardware.py`,
  `lifecycle_hardware.py`, `graph_hardware.py`, `operator_validation.py` and
  `overhead_hardware.py`. `run_pytest.py` supports the independent compiler
  worktree and prints actual import/native provenance.
* Enflame: `Profiler/test/test_execution_enflame*.py` plus
  `enflame_method_matrix.py` and `enflame_method_fidelity.py`. Cooperative-writer
  tests require correct published record bytes as well as mathematical output.
  Bounded-index metadata must reject missing or oversized actual launch grids,
  flat-grid overflow, oversized trace capacity and selected ids before buffer
  allocation. Clock words must preserve the full SDK counter width. Compare
  uninstrumented and instrumented LLVM/options: enabling global 64-bit arithmetic
  only for the observer changes the reference program and requires a controlled
  ablation, not a new baseline or relaxed overhead target.
* Ascend: `Profiler/test/test_ascend*.py`, `test_execution_ascend.py`,
  `test_observations_ascend.py`, `test_cann_importer.py`; actual acceptance and
  held-out workloads in `tests/ascend/`. Follow its README. A native smoke or
  explicit pointer experiment is not hidden-only ABI acceptance.

Six families use three shapes and two configurations with frozen Study inputs
and unchanged CPU tolerances. Retain input hashes, output canaries and actual
invocations. RMSNorm was preselected as held-out and must not be replaced after
failures. Runtime loop tests must avoid constant specialization when claiming
that different control paths execute the same binary.

## Fidelity and cost

Run at least three interleaved/randomized batches of thirty calls per mode, with
warmup reported separately. Retain every sample, including failures/slow calls.
Separate off/native/selected detailed/full trace. Hold any independent task
reference collector constant across compared modes and report its perturbation.

Report actual device-task duration, host latency, stream envelope, compile time,
trace bytes, register/shared/workspace changes and processing cost separately.
Host/stream intervals are not isolated device tasks; unknown-frequency ticks do
not provide microseconds. <=5% native and <=10% selected detailed median device
perturbation are engineering goals, not universal bounds. Retain over-target
results and test genuinely reduced device collection before reporting success.

Math changes, out-of-bounds writes, races, false joins and silent event loss block
acceptance. Unknown source ownership, absent clock conversion, unsupported
concurrency/graphs/counters must be explicit and tested. Retain failed partial
captures and original application exceptions even if cleanup also fails.
