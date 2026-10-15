# Ascend integration: pinned source and validated boundaries

Use `flagtree-source.patch` as the **complete diff against FlagTree
0364ed4bc39d1dfae483741ec272298297fa5bda**. Do not layer the historical
`initial-handoff.patch` or the packaging-only patches onto it. The full patch
includes both SDK compiler callbacks/cache identity, the retained CANN launch
receipt bridge, standalone-tool link/include repairs, packaged receipt header,
and backend-specific offline setup metadata handling.

The actual independent Docker worktree committed these six tracked source files
as `00650233fcaa9c55134e8aae690067a32d97ad45`. Its tracked worktree is clean;
untracked build products and dependency checkouts are retained. The full patch
SHA256 is `d18294b2e01805de1f18d395bf5ef88e95763499883957b1db56c17ec7cb68c3`.
`flagtree-source-manifest.json` records exact source and binary provenance.

Required official dependencies, both tracked-clean in that actual worktree:

- AscendNPU-IR: `4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9`.
- FLIR: `ff91e64b6042a27e0db053f28ea3741be65d24d0`.

FlagTree0364 leaves FLIR unpinned; the later 516ad31 revision uses a TLE API
absent from this baseline and fails compilation. The compatible pin above
retains FLIR; disabling the feature is not the validated build. The compiler
uses the existing LLVM22 cache. The late observer is a separate upstream
LLVM15.0.7 `opt-15` plugin. **Do not load this plugin into vendor bisheng**;
that LLVM fork is ABI-incompatible.

All compilation, CPU tests/oracles and workloads run inside the user's existing
`chijin_v3.5.x` Docker via the `chijin` host user, with device4 explicitly
selected. The independent paths are:

```text
/tmp/flagprism-method-ascend/FlagTree       # integration checkout
/tmp/flagprism-method-ascend/source         # pinned FlagPrism component
/tmp/flagprism-method-ascend/compiler-build # full core/native build
/tmp/flagprism-method-ascend/compiler-python/flagtree/{debugger,profiler}
/tmp/flagprism-method-ascend/llvm-build/FlagPrismAscendLateObserver.so
```

For a new checkout, apply the full patch to the exact baseline, install the two
pinned dependencies, and make `third_party/FlagPrism` point to the desired
component source. Configure the real `triton` target plus debugger/profiler and
standalone tool with the configured AMD/NVIDIA generated-header dependencies;
these supply common build requirements and do not authorize their devices.
Build the LLVM15 observer separately. Do not substitute a runtime-only build or
copy old component libraries over the newly built core.

`compiler.driver.v1` wraps the actual source-bearing SDK command on both FlagTree
SDK routes. The component retains source IR, final actor LLVM, original/adapted
hashes, target/launch ABI and codegen receipts. The generated worker embeds the
packaged `CannLaunchReceipt.h` bytes in its cache identity and queries actual
worker PID/TID/device/stream/task immediately after the original runtime launch.
SDK association uses sealed connection/context tables and the official
COMPUTE_TASK_INFO global-task foreign key; parent context views do not become
additional kernel hotspots. No kernel-name/order/time-containment matching is
used. SDK directories are retained through bundle export, including failed
exports. Explicit relative SDK paths are normalized before application chdir.

The current component also retains actual graph-sync-solver diagnostic IR via
an argv-only SDK wrapper. Typed HIVM sync_block_set/wait operations expose
**compiler_static** producer/consumer actors, pipelines and flag channels.
Their identity is bound to the same compile/source and actual actor artifacts;
dynamic flag generations and encoded LLVM instruction pairs remain unproven.
Optional `TRITON_DISABLE_LINE_INFO=false` preserves real DILocation origins in
both supported SDK routes and participates in compiler cache identity. These
are source-origin candidates, not exclusive operation cost. `TRITON_DEBUG=1`
is unnecessary and separately enables a Triton debug path requiring triton-opt.

Validated functional evidence and remaining limits are in
[`tests/ascend/README.md`](../../../tests/ascend/README.md). Key boundaries:
local SYS_CNT durations are calibrated from actual sealed device frequency,
compiled instruction and official c220 rate semantics; the source/ACSQ shared
epoch is not certified. Source-control brackets are not engine-busy intervals.
Requested primitive classes are selected at compile time before timestamps and
event writes; pass manifests preserve original site IDs and the effective set.
Program predicates still gate publication rather than all counter reads. Unknown
source operations, dynamic generation, sampling and unsupported arbitrary site
selection remain explicit. Historical failed builds, unsafe-capacity rejection
and incomplete captures remain archived rather than reclassified as passes.

Packaging uses the real setup Distribution, standard build_py and
bdist_wheel(skip_build=True), reusing all three validated binaries unchanged.
`USE_FLIR=OFF` and `USE_FLAGPRISM=OFF` only prevent this old setup's dependency
metadata/download recursion during repacking; `TRITON_BUILD_FLAGPRISM=ON` and
all actual feature binaries/Python modules/header remain present. A subprocess
guard rejects CMake/Ninja/Make or shell builds. Final acceptance checks ZIP
bytes for every component Python file and native library and performs public
imports/compiler ABI/preallocation checks under Python -I with the extracted
wheel as the only triton/flagtree package source. Import installed torch and
torch_npu before triton, as the supported Ascend runner does.

The automatic mode additionally applies `automatic-source-origins.patch` after
`flagtree-source.patch`. Also apply `automatic-import-order.patch` to load the
Ascend Torch runtime before the vendor compiler is discovered during a cold
CLI import. The source-origin patch enables the SDK's real debug locations when the
frozen `NPUOptions.instrumentation_mode` contains an automatic observation
request, on both SDK routes. It does not require `TRITON_DISABLE_LINE_INFO` or
change process-wide compiler flags. The automatic request participates in the
normal compiler option hash.

Build the LLVM15 observer from `Profiler/llvm` using CMake. For an existing
matching, verified native build, `build_automatic_wheel.py` assembles the real
FlagTree setup Distribution with standard `build_py`/`bdist_wheel`. Supply the
patched FlagTree checkout, the complete component source, the matching native
Python tree/core library, the newly built plugin and a fresh output directory.
This helper explicitly reuses those native binaries; it does not claim a new
core build. It creates the official backend marker, packages the late plugin
under `flagtree/profiler/lib`, verifies package bytes and records their hashes.
Install the resulting wheel into a venv (matching system Torch/SDK packages may
be reused). The installed adapter discovers the packaged plugin and creates
immutable compiler capture directories automatically; explicit environment
paths remain available as advanced overrides. Failed compiler captures are
retained and the error names their compiler-stage evidence.

Automatic Ascend observations include zero-interval source-operation
checkpoints from generic original LLVM loads/stores/computations/compiler
calls with surviving debug locations. The default selects at most eight source
location/class regions per actor, spread over the original control flow;
original loop-header checkpoints preserve actual runtime visits. A checkpoint
proves that source control reached the region, and is not a completion barrier
or engine-busy measurement. Adjacent operations at the same source location and
class within one original basic block share a checkpoint. Compiler manifests
retain candidate/selected counts, operation classes, original site identities
and full debug origins. Raw event publication, losses, typed readiness,
per-invocation hidden ABI and actor-local clock boundaries are unchanged.
