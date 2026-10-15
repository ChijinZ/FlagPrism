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
  Profiler/test/test_reconstruction.py Profiler/test/test_hook_rollback.py \
  Profiler/test/test_ascend_launch.py \
  Profiler/test/test_cann_launch_receipts.py Profiler/test/test_cann_joint.py \
  Profiler/test/test_observer_allocation_contract.py \
  Profiler/test/test_observer_decode_recovery.py \
  Profiler/test/test_native_observation_recovery.py \
  Profiler/test/test_cann_artifacts.py Profiler/test/test_cann_native.py \
  Profiler/test/test_cann_raw_sys.py Profiler/test/test_cann_source_clock.py
```

These cover malformed records, unknown IDs, rejected joins, unverified clocks,
lossless raw artifacts, manifest hashes, replay separation and cleanup preserving
the original exception. Browser skips remain skips. Also run applicable native
`test_api.py`, `test_profile.py`, `test_instrumentation.py` and backend suites;
mock-only passes cannot establish native lifecycle or SDK support.

The CANN receipt tests cover the packaged ABI, successful zero task IDs,
failed queries, ambiguous source tokens and export errors. The SDK identity
producer tests use explicit simulated capture directories and connection tables;
they reject missing/old/ambiguous directory seals and repeated task/token
identities. Also compile the actual `CannProfiler.cpp` for the CPU registry and
`ProfilerStartRecoveryTest.cpp` tests: retained queued-callback lifetime,
concurrent publication/close, session epochs, capacity recovery and failed-start
retry must hold independently of SDK availability. These CPU checks do not
certify the actual generated launcher's worker query or raw counter domain.

The observer allocation contract checks derived metadata after the real
post-pass callback and rejects inconsistent native actor layouts before any
device allocation. Decode recovery uses the real truncated-record decoder and
checks that raw bytes and the original exception survive, while failed decode
captures produce no reconstructed execution events. CANN SDK retention tests
verify file hashes, successful public bundle export, temporary-only cleanup,
and source preservation on partial export failure.

Native-observation recovery tests cover repeat finalization, durable recovery
files, atomic replacement, session-specific acknowledgement, conflicting
capture identities, truncated Proton decoding and failure before bundle export.
The CANN native-task tests include a retained actual SDK fixture alongside
simulated negative cases; native report identity does not certify a source
clock. Raw SYS tests preserve original packet offsets and hashes. Source-rate
tests require exact task/binary/compiler/device evidence and leave clock epoch
and cross-actor alignment separate; an existing independently aligned clock
must remain unchanged.

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

NVIDIA performance experiments are currently deferred by the user's explicit
instruction. Continue compilation, correctness and short GPU functional
checks; preserve the earlier performance results and the pending cost gate.
Do not use correctness passes to certify performance.

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
