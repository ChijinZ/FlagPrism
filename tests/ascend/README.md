# Ascend functional acceptance and measurement boundaries

All builds, Python imports/tests, CPU oracles and hardware runs use the user's
existing `chijin_v3.5.x` Docker, via host user chijin, explicitly on device4.
The user's original FlagTree checkout and other users' processes are untouched.
SSH gateway failures without the command sentinel are not executions; inspect
existing PID/log/terminal state before resuming. Each failed/incomplete output
is retained and never silently reused.

The pinned full integration patch/dependencies and exact binaries are in
[`integration/patches/ascend`](../../integration/patches/ascend/README.md).
The full core, both native modules and isolated LLVM15 observer are required;
a runtime-only build does not supply the hidden compiler ABI.

## Public entry

Set the independent compiler/component paths and these dependencies before first
kernel compilation:

```sh
export FLAGPRISM_ASCEND_LATE_PLUGIN=/tmp/flagprism-method-ascend/llvm-build/FlagPrismAscendLateObserver.so
export FLAGPRISM_ASCEND_OPT=/usr/bin/opt-15
export FLAGPRISM_ASCEND_COMPILER_CAPTURE=/tmp/flagprism-method-ascend/new-compiler-captures
```

A detailed `backend='cann', hook='instrumentation'` session accepts an explicit
`ObservationRequest(semantics=('issue','wait_bracket','control_checkpoint'),
programs=(0,), max_events_per_instance=256)`. The caller adds no Trace formal or
final argument index. The frontend/compiler/actual SDK launch roles resolve the
hidden global-pointer ABI. Select `device_id=4`, MSTX/ACLprof MSProftx enabled and
`runtime_host_timing_fallback=false`; the application selects the same device.
The runner's native-only phase uses the public legacy native hook to avoid TTIR
snapshot stores; its detailed phase uses the explicit instrumentation request.
This difference is recorded and does not certify a default IR joint-capture path.

The actor buffer has three independent segments, each 32+64*C bytes. Valid
C=256 requires **49248 bytes**; C=2048 requires **393312 bytes**. Symmetric native
metadata/runtime checks reject stale or inconsistent layouts before allocation.
11 rejection/metadata tests and both valid zero-buffer allocation/export gates
passed. The earlier underallocation failure remains archived and is never run
again. Per-actor attempted/committed/dropped/saturation headers are checked;
empty capture, decode failure or missing identity cannot count as a detailed pass.

## Completed fixed workloads

| Suite | Fixed requests and actual result |
| --- | --- |
| Native receipt/relative path | Four calls, two binaries, two streams, legal task0; exact worker/SDK identity, original math/inputs/canaries. Relative SDK root survives application chdir. |
| Original operators | **108**: GEMM, GEMM+bias+GELU, Softmax, LayerNorm, row sum, transpose × three shapes × two configurations × off/native/detailed. All original mathematical oracles/input bytes retained; 36 detailed requests produced 7788 records. |
| Fixed T5 | **9** RMSNorm127×769 requests: three batches × off/native/detailed, 30 measured calls each. All nine requests, covering270 measured calls, passed post-profile math/input/canary checks; 180 native/detailed calls had exact task identities. This suite is not heldout shape/config coverage. |
| Heldout | **18** RMSNorm requests: three row shapes × variants0/1 × off/native/detailed. All passed;12 native/detailed identities verified and six nonempty detailed traces. |
| Formal Study | Same canonical 512×512×4096 fused GEMM+bias+GELU at 32/32/32,32/32/256,64/64/256 tiles; stages4/warps4. Three detailed cases and three native controls, each three measured calls, passed unchanged CPU math/inputs/canaries. |
| Typed HIVM/source origin | Fresh ordinary fused128³ detailed capture, optional line info only: exact four tasks,232 source-control records and same-compile typed readiness channel in the public execution manifest.23/23 dynamic sites retain debug locations; explicit source_op_id remains partial. |

`acceptance.py --suite operators`, `--suite t5` and `--suite heldout` generate
the fixed plans; workers can consume a JSON plan with general BM/BN/BK/stages/
warps overrides. New17 CPU plan/identity contracts confirm the original108+9
plans are unchanged and reject invalid overrides. Resume requires identical
plan/source/core/plugin/native hashes; incomplete directories stop execution.
Original tolerances remain GEMM/fused atol.002/rtol.02, row/RMS .0005/.002,
transpose exact. CPU references run in the same Docker. No old instrumented
Study binary or special source/LLVM rewrite substitutes for the public entry.

The formal long-K native medians are308.00/160.64/61.58us; detailed medians
313.98/159.82/61.18us. Three-sample controls preserve the optimization direction
and do not constitute a 3×30 performance acceptance campaign. The AIV wait
brackets decrease from approximately54–56us to11–13us with BK256, but these
source observations do not isolate every contributor to total kernel time.

## Identity, static relationships and clocks

Canonical native tasks use retained generated-worker identity and sealed SDK
HostTask/connection/TASK tables. MIX dispatch context membership and
COMPUTE_TASK_INFO.globalTaskId select the compute member; parent views remain
extensions. Multiple compute members are explicitly unsupported rather than
arbitrarily selecting one. Task/scope0 are legal. SDK marker/copy/event views
are classified from exact SDK types and do not inflate kernel hotspots.

The actual SDK graph-sync-solver dump is captured with bounded files, stream
SHA/command/tool/input provenance, and both original/adapted actor LLVM.
Typed same-compile sync_block_set/wait records produce static actor/pipeline/
flag channels. Repeated or ambiguous static sites are not dynamically paired.
Source debug locations can be matched to the exact retained tracked table as
origin candidates. They never imply exclusive source-operation cost.
Use `TRITON_DISABLE_LINE_INFO=false` to retain these locations without enabling
TRITON_DEBUG assertion/debug compilation. The setting invalidates compiler cache.
Missing compiler dump/actor/source provenance stays unavailable or partial.

`cann_raw_sys` retains original 64B stars_soc ACSQ packet bytes, exact installed
StructDecoder standard-size schema, hardware stream/task normalization and
whole-dispatch endpoints. Such packets are not AIC/AIV occupancy envelopes.
`cann_source_clock` independently verifies actual worker/task/binary provenance,
compiled MOV SYS_CNT, installed c220 GetSystemCycleImpl, documented50MHz semantics
and the sealed actual device frequency. It computes20ns/tick **local durations**;
actor alignment stays instance_local and absolute/shared origin stays unknown.
Frequency equality, raw window containment or similarly named SYS fields do not
certify a shared epoch. The old Study's unique integer-window match is conditional
on a reported shared-frame assumption, separate from this exact identity path.

Independent msprof PMU replay remains a distinct capture/UUID: it measures actor
aggregates from separate SDK passes, not foreground busy intervals. Do not join
replay tasks by name or task number or treat ratios as a same-call pipeline.

## Cost and unsupported selection

The fixed short RMS T5 exposed real overhead: native device-task medians
6.60/6.33/6.44us versus detailed10.64/10.61/10.49us, increases
**61.21/67.61/62.89%**. Host launch medians were about218–222us versus1.79–1.81ms;
finalization/export costs are recorded separately. These negative results remain.
Off-mode isolated task duration is unavailable, so its NPU stream envelope cannot
certify the native≤5% device-task target. Detailed≤10% is not met here.

Requested issue/wait_bracket/control_checkpoint classes are now selected by the
late compiler before inserting timestamps or records. Original site IDs remain
stable, including sparse wait-only IDs. Actual pass manifests expose the effective
set; the finalizer upgrades its description only when every successful actor
receipt and original/adapted hash agrees. It retains the legacy output-filter
field for compatibility and filters the exported semantic view. Compiler-fixed
program predicates gate record publication; selected timestamps still execute
before that predicate. Arbitrary sites and sample_every!=1 explicitly reject;
do not claim event sampling or cross-actor engine occupancy. Missing dynamic
iterations, exclusive source cost and shared-clock alignment remain explicit.

The additional original RMS wait-only/native campaign retains three batches ×30
measured calls per mode. Wait-only halves records from12 to6 per invocation,
with actual unselected classes containing no counter reads or event writes.
Device-task medians were native6.62/6.39/6.00us versus wait-only10.60/10.78/10.68us
(**+60.12/+68.70/+78.00%**); the≤10% target still fails. Host medians remain
about1.71–1.76ms detailed versus216–220us native. Fewer records therefore do
not establish an overhead improvement. The same public wait-only fused smoke
exports100 selected records and exact identities. Final metadata-label correction
is separately CPU-checked against these real manifests; original bundles are
not retroactively rewritten.

The additional preselected P32_K32 long-K cost campaign uses the same canonical
512×512×4096 inputs/config/grid/capacity2048, three batches ×30 measured calls
per native/all-site mode. Device-task native medians311.19/309.74/309.88us versus
310.94/313.76/312.58us detailed yield−0.08/+1.30/+0.87% only for this case.
Detailed host launch remains12.33–12.46ms versus267–272us native; detailed
export15.62–17.21s and complete traces221–229MB per33 calls. Low kernel-task
perturbation is therefore not low end-to-end cost. All six requests retain
original math/input/canary checks and exact identity; each detailed request has
13398 local records and33 valid393312-byte zero-loss captures. The final actual
public metadata describes compiler semantic selection plus output filtering.
