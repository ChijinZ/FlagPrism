# Ascend method acceptance: recovery and boundaries

The formal hidden-only path is implemented in source and **awaits a new compiler binding build and Ascend hardware validation**. The gateway currently returns `no available gateway`, sometimes with exit 0. That output is a connection failure, never a passed build/test. Do not retry SSH until access is restored. Run builds, imports, tests, CPU oracles and workloads inside `chijin_v3.5.x`; physical device4 is the reserved device.

## What is established, what remains pending

| Path | Evidence and boundary |
| --- | --- |
| Native CANN tasks | Earlier fresh runtime builds captured three real device4 vector-add tasks and passed CPU checks. Native records survive missing source association. Recent current-device/default-query changes and public joint routing require a fresh run. |
| msprof PMU | Earlier real vector-add replay produced Arithmetic/Pipe actor aggregates. Every replay has its own directory/UUID; raw CSV rows and unknown values are retained. Latest explicit SDK kernel-replay/device checks await rerun. PMU records are independent replay aggregates, never foreground busy intervals. |
| Final actor handoff | The private FlagTree driver patch and upstream opt15 pass captured real SDK-generated actor LLVM and role/loop/wait manifests. Original and adapted LLVM/object hashes are separate. |
| LLVM dynamic64 | An explicit extra-buffer **test adapter** produced real records and correct math. This does not validate the formal hidden-only ABI. |
| Public detailed request | Frontend appends a compiler-owned hidden pointer; runtime allocates a separate actor log. New `prepare_late_observation_abi` binding, unused-pointer preservation through SDK split, formal role validation and runtime transfer must be built/run together. |
| Source origin | Full `(file,line,column,inline chain)` may match the exact retained TrackedOpTable snapshot. A unique candidate establishes debug origin, not exclusive source-region cost. Missing/multiple candidates remain unassociated/ambiguous. |
| Joint SYS/native clock | **Automatic producer and finalize wiring are missing**, not merely untested. Parser/alignment helpers exist, but no formal collector currently creates the exact SDK packet→source invocation proof. A reported frequency or caller-supplied evidence dictionary cannot fill this gap. |

The three-slot dynamic ABI currently supports actual `dav-c220-cube`/`dav-c220-vec` targets (910B): AIC slot0 and AIV subblocks in slots1/2. Other dynamic targets are rejected. Supported request semantics are `issue`, `wait_bracket`, `control_checkpoint`; exactly one logical program, all sites, `sample_every=1`. Capacity must be 1..1,000,000. Natural loop-header records are zero-length checkpoints and their occurrence is not an induction variable. Signal/wait brackets measure scalar source control, not engine busy or engine completion.

The compiler rejects missing/ambiguous main LLVM input, multiple kernel entries, absent/conflicting compiler synchronization/workspace roles, invalid hidden formal identity/type/role, snapshot instrumentation already inserted, missing textual source ABI, missing plugin/capture dependency, or absent dynamic-ABI manifests. Unsupported scalar-prefix types/MLIR bytecode exports remain explicit failures. Do not use a guessed final argument index: `FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX` is permitted only with the explicit test-adapter opt-in and cannot establish formal product completion.

## Required toolchains and source identity

The earlier environment was Triton3.5.1, CANN9.0.0, torch2.9.0+torch_npu, Ascend910B4. Import order is torch, torch_npu, then triton, with `TORCH_DEVICE_BACKEND_AUTOLOAD=0`.

Two LLVM installations have distinct jobs:

- FlagTree/compiler Debugger plugin: the LLVM22 cache at `/root/.triton/llvm/llvm-ubuntu-arm64`. The Debugger compiler binding lives inside newly linked `FlagTree/python/triton/_C/libtriton.so`; building a runtime `_native.so` alone cannot provide it.
- Late actor pass: upstream LLVM15.0.7 development files and `/usr/bin/opt-15`. Build `Profiler/llvm` with `/usr/lib/llvm-15/lib/cmake/llvm`. The pass executes **out of process**, then the private driver forwards validated IR to the SDK compiler. Loading this upstream plugin directly into the vendor bisheng LLVM fork previously crashed; do not repeat that path or overwrite SDK binaries.

Pinned independent core worktree:

```text
/tmp/flagprism-method-ascend/FlagTree
branch: flagprism-method-ascend-handoff
baseline: 0364ed4bc39d1dfae483741ec272298297fa5bda
shared component source: /tmp/flagprism-method-ascend/source
```

FlagTree declares AscendNPU-IR through `python/setup_tools/utils/ascend.py`: official GitCode repository, commit `4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9`. FLIR is the official `flagos-ai/flir` dependency declared unpinned by this baseline; recover and record the actual existing FLIR HEAD before a reproducibility claim. Do not replace the user's `/workspace/FlagTree` checkout or its untracked files.

Recovery inputs live in repository-root `artifacts/method-run/ascend/`:

- `flagtree-driver-handoff.patch`: initial driver-event patch, SHA256 `9a67673d0e55c3ae1e8941552a5f924b3117f101231568231d90e892fcc20c0d`.
- `cache_patch.py`: exact later cache callback addition; the initial exported patch predates this change. The old script appends code and is not safe to rerun indiscriminately.
- `restore_core_handoff.py/.sh`: idempotent recovery on the pinned independent worktree. Copy the script and initial patch into remote `/tmp/flagprism-method-ascend/recovery-input/` first. It restores prepare/finish callbacks and cache key, then writes `recovery/flagtree-driver-handoff-complete.patch` and `recovery/core-handoff.json` with full diff/source/dependency hashes. These outputs have not yet been generated after gateway restoration.
- `RECOVERY_INPUT_SHA256.txt`: local recovery-input identities. The preserved remote independent branch contains the actual later cache modifications; recover that branch preferentially.

The protocol is `compiler.driver.v1`: private command/environment copies plus compiler metadata in `CompilerDriverEvent`; prepare and finish callbacks bracket both Ascend SDK driver paths. `compiler_driver_cache_key()` includes codegen-affecting component state in `AscendOptions.hash`. Original artifact hashes and retained compiler snapshots are provenance; an adapted instrumentation hash must never be presented as unmodified performance.

## Shortest restore/build/run order

1. Restore access; preserve the existing independent worktree and receipts. Synchronize current complete FlagPrism source, including root/GCU edits, to `source`. Restore/verify the core patch and dependencies; retain source/hash manifests. Ensure `FlagTree/third_party/FlagPrism` points to this current source. A CMake source variable alone does not satisfy generated `RegisterTritonDialects.h` includes.
2. Through `scripts/study_remote.py zhiyuan_ascend --command-file ...`, run `compiler_configure.sh`, then `compiler_build.sh`, then `llvm_plugin_build.sh`. The actual core target is **triton**, not libtriton. `ascend;nvidia` supplies the NVGPU/NVWS generated headers needed by this baseline's common targets; it does not authorize NVIDIA execution. The build also needs newly linked profiler/debugger runtime libraries in `compiler-python/flagtree/{profiler,debugger}`. Preserve actual linking logs and library hashes.
3. Run `tests_all.sh` in Docker. Then run `Debugger/test/python/language/test_prepare_late_observation_abi.py` against the newly built core and current source package. This regression intentionally requires the new binding and covers true formal index, idempotency, snapshot guard, stale role/type/index and multiple-entry rejection. It must not skip a missing binding.
4. Run one fresh formal `ObservationRequest` vector/row smoke, with native MSTX and actual task collection enabled. Verify math/inputs/canaries, new core/runtime hashes, source-formal→final role manifest, nonempty records where selected native sites exist, exact per-actor protocol statistics, and absence of unrequested TTIR snapshot stores. Failures are preserved. Only after this passes proceed to the matrix.
5. Send `canonical-inputs-r007.tgz` through `acceptance_inputs_sync.sh`; run `acceptance_run.sh` (operators, then T5). The scripts use device4 explicitly. Add the two long-K Study cases and independent PMU CLI run only after the formal smoke; inspect clock/identity evidence separately before claiming internal timing acceptance.

Do not run the earlier runtime-only `build.sh` as a substitute for the full compiler build. Compiler objects named `TritonDebugger` alone are also insufficient; `triton` must actually link the new compiler plugin. Current compiler sources use `llvm::Expected`/`llvm::Error` failures so the common `-fno-exceptions` core target remains legal; Python binding lambdas translate errors at the boundary. This source change awaits rebuild.

## Public detailed entry and native device selection

After the new packages/core have been made visible, supply both late dependencies before first compilation:

```sh
export FLAGPRISM_ASCEND_LATE_PLUGIN=/tmp/flagprism-method-ascend/llvm-build/FlagPrismAscendLateObserver.so
export FLAGPRISM_ASCEND_OPT=/usr/bin/opt-15
export FLAGPRISM_ASCEND_COMPILER_CAPTURE=/tmp/flagprism-method-ascend/compiler-captures
```

An explicit public request uses `backend='cann', hook='instrumentation'`, e.g. `ObservationRequest(semantics=('issue','wait_bracket','control_checkpoint'), programs=(0,), max_events_per_instance=256)`. The caller does not add a Trace parameter or choose a final formal index. The frontend returns the real TTIR hidden argument index; actual emitted SDK role attributes and final LLVM types/runtime FFTS configuration validate the global-pointer prefix. Trailing removed launch-coordinate scalars remain partial.

The native mode should explicitly contain `device_id=4`, `mstx_enabled=true`, `aclprof_msproftx_enabled=true`, `runtime_host_timing_fallback=false`. A profiler started before an application sets its device sees the current device at start, which may legitimately be device0. Current-device querying does not follow later application device changes. CLI and external counter child must carry the explicit mode; the application also sets torch.npu device4.

The acceptance runner uses the public native-only `FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY=1` option for its native phase to avoid the default IR snapshot path. Its detailed phase uses `hook='instrumentation'` and the explicit request. This configuration difference is recorded; it does not establish that the default IR path provides a same-call native joint capture.

## Independent counters and joint clock proof

`cann.collect_msprof([...], fresh_output, replay_mode='independent', expected_device_id=4)` invokes SDK `--replay-mode=kernel` explicitly. `expected_device_id` validates actual `OpBasicInfo` device metadata; it **does not select or switch** the application's device. Receipts preserve selected expectation and actual SDK device IDs. Missing/mismatched expected device fails. Each new output directory owns its raw captures and replay UUID. The public CLI/backend currently passes replay command/environment; caller-level expected-device validation is optional until common routing forwards it. Always preserve explicit child device selection.

Actor PMU activities can overlap. Ratios/cycles may describe several SDK measurement passes or replays, never the busy interval of a foreground logical invocation. A same-looking binary/kernel name/task number across replay directories cannot join them. Capture raw output, collector version, receipts and bytes; incomplete/failed collection remains failure.

`ascend_clock.import_deviceprof` implements the public msopprof 910B/A2 128-byte schema, including hardware stream/task encoding normalization. Schema source is pinned Ascend/msopprof `b28488fa3ac6e42683bf2917c9d3149993942332` `data_bean.cpp`. Historical packet fixture provenance retains original/fixture SHA and exact record offsets. Device/capture IDs are not in those records and cannot be invented.

`align_same_call` needs a producer-established invocation/capture/device/stream/task/connection/scope/packetSHA binding, nonempty actual identity evidence **and counter-domain evidence**. Native actor containment is checked only after this binding; it never chooses an invocation. All matching events share one clock descriptor with top-level proof.invocation_id, actual packet identity, verified actor list and a common origin from the selected programs' bound unique native actors. Individual native record/containment is retained as event evidence. Unknown events retain raw ticks. `read_hwts_frequency` derives period from the actual SDK hwts report; absent report leaves nanoseconds unknown. SDK converted-nanosecond SQLite task times alone do not prove the source SYS_CNT epoch. Generic same-call packet collection through the formal entry is still a hardware/integration requirement.

Current Debugger finalization does not collect/read the SDK packet or invoke an automatic exact-proof builder. `align_same_call` accepts declared evidence for descriptor processing; that input is not itself authenticated producer evidence. The missing producer and public finalization integration must be implemented before M3 acceptance. The preferred investigation uses one native ACLprof owner with actual host MSTX scope/API connection linkage and official raw SYS/program decoding. External application-replay is conditional on supported identity retention and disabling conflicting inner ACLprof. Collector compatibility must be tested after restoration.

The old Study has valid campaign/source-buffer provenance: three OS application processes, each with one target call and logical program0 actor logs, under one SDK application-replay command. Its exact all-actor integer SYS-window matching gives a unique recorded invocation under a common reported-epoch assumption. `Pid=NA` does not invalidate that campaign or conditional match; the unfilled link is an independent source scope/connection/PID→specific packet proof. See repository-root `artifacts/method-run/ascend/JOINT_CLOCK_AUDIT.md` for the bounded audit and minimum implementation gates.

## Matrix and T5 interpretation

`acceptance.py --suite operators` fixes six original math operators at three shapes/two configurations, plus preselected RMSNorm at three shapes/two configurations. It reuses only the original mathematical workload/oracle and frozen input bytes; every binary compiles through current tooling. Original tolerances remain: GEMM/fused `atol=.002, rtol=.02`, row ops/RMSNorm `.0005/.002`, transpose exact. No Trace parameter or old Study binary substitution is allowed.

T5 fixes RMSNorm127×769, seed1729, random phase order, three batches ×30 calls per off/native/detailed phase. Prewarm/first compile, host launch, stream envelope, native task records, finalization/export and trace bytes remain separate. CPU math/input/canary checks occur after profiling. Native task statistics require actual scope identity; incomplete matching remains partial. Off-mode task duration is unavailable, so the NPU stream envelope cannot establish the ≤5%/≤10% device-task goals. A separate real reference is required for that comparison.

Successful jobs resume only under the same source/core/plugin/native-library plan hashes. Failed or incomplete job directories and logs are retained and stop execution; choose a new output after fixing the mechanism. Partial source identity is recorded separately and leaves per-task timing unknown; it does not turn a narrow math/native result into full capability acceptance. `completed_math_native_matrix` means that narrow result only. Zero selected detailed events, missing native identity, unverified clock, hidden ABI failure or absent precise source-region relation cannot be presented as method completion.
