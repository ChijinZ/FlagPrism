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
bdist_wheel(skip_build=True), copying supplied native artifacts without changing
their bytes. Those artifacts must match the component native inputs; a previous
validation of an older core is insufficient after common compiler targets change.
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

The SDK compiler wrapper enforces a 120-second deadline for each actual SDK
compiler job, including its child tools. `FLAGPRISM_ASCEND_COMPILE_TIMEOUT_S`
may explicitly select 1 through 300 seconds. A deadline failure stops that
job's process group, returns exit 124 and retains partial output plus its
`timed_out` receipt, child PID/group, requested deadline and elapsed time. This
is compiler-stage enforcement; the public export receipt separately measures
full finalization/export and must not be described as a compiler deadline.

The usability native audit found that the Ascend core and packaged
`triton-mlir-opt` both link the common Proton targets. Consequently the current
`AutomaticScopes.cpp`, its registration/header and `triton_proton.cc` require a
real incremental build even though Ascend's observations use the separate late
LLVM plugin. With the pinned parent integration and current component source:

```sh
export FLAGTREE_BACKEND=ascend
cmake --build "$ASCEND_CORE_BUILD" --target triton flagtree_profiler_native flagtree_debugger_native -j 4
cmake --build "$ASCEND_CORE_BUILD" --target triton-mlir-opt -j 4
```

The actual run independently sealed the new core, frontend tool and checked
runtime artifacts under
`/tmp/flagprism-usability-ascend/run-001/native-final/native-runtime`.
`native-final/native-provenance.json` records the pinned parent commit, all
component native input hashes, exact commands and original/new artifact hashes;
its build logs record successful compilation of the changed pass/binding and
relinking of both compiler artifacts. Runtime/debugger inputs remained byte
identical and their requested targets were up to date. The independently built
LLVM15 observer's unchanged C++ source hash and existing clean-build/test logs
justify its reuse. Original baseline compiler/runtime paths were restored after
sealing, so the baseline distribution is preserved. Supply the sealed
`native-runtime/python` and `native-runtime/core/libtriton.so` to the wheel
helper; the sibling core tool is included automatically. This is an incremental
component rebuild against the pinned parent, not a rebuild of every vendor SDK
component or a claim that unrelated repository targets were compiled.

## Build from pinned sources in a fresh directory

`build_from_source.py` is the source-build entrypoint. It takes no old core,
component native or observer binary. `build_automatic_wheel.py` remains an
advanced **assembly-only** helper and is invoked after the source builds finish.
Run the source entrypoint inside the matching Linux aarch64/Python 3.11 Ascend
SDK environment. No NPU is initialized by the installation check.

Required dependencies are a C/C++ toolchain, Git, CMake >=3.20, Ninja, Python
build headers, setuptools/wheel, pybind11 (validated 3.0.4), nanobind (validated
2.12.0), matching Torch/torch_npu packages, nlohmann JSON headers, and CANN 9.0.0
with `include/acl/acl.h`, `lib64/libascendcl.so`, and `bin/bisheng`. Supply the
supported Ascend LLVM22/MLIR dependency prefix corresponding to FlagTree's
`cmake/llvm-hash.txt` revision
`7d5de3033187c8a3bb4d2e322f5462cdaf49808f`; a bare system LLVM22 installation is
not assumed equivalent to the vendor-compatible distribution. Separately
supply upstream LLVM15.0.7 with development headers, CMake package and `opt`.
For Debian/Ubuntu the latter is supplied by `llvm-15-dev llvm-15-tools`; the
prefix is normally `/usr/lib/llvm-15`. The two LLVM prefixes must remain
separate: the LLVM15 plugin is loaded by upstream opt15, never by bisheng.

The pinned FlagTree source publishes its matching LLVM22 distribution in
`python/setup_tools/setup_helper.py`:
[LLVM22 aarch64/Python3.11 compatibility archive](https://baai-cp-web.ks3-cn-beijing.ksyuncs.com/trans/llvm-7d5de303-ubuntu-aarch64-python311-compat_v0.6.0.tar.gz).
Its JSON dependency in `setup.py` is
[nlohmann JSON 3.11.3 include.zip](https://github.com/nlohmann/json/releases/download/v3.11.3/include.zip).
These are dependency distributions, not a FlagPrism compiler/native build.
Download/extract them into a chosen dependency directory and set the two prefix
arguments to the extracted LLVM directory and directory containing
`nlohmann/json.hpp`. Record the downloaded archive SHA256 alongside the recipe.
Build tooling can be installed with `python -m pip install cmake ninja setuptools
wheel pybind11==3.0.4 nanobind==2.12.0`; retain the matching SDK Torch packages.

The caller owns these dependency installations. The helper checks major
versions, records tools/configuration/header and all top-level LLVM library
hashes, and binds the actual CMake source/LLVM inputs and output native hashes
to `recipe.json`. A version string alone does not certify an LLVM source commit;
retain the dependency distributor's archive/source provenance alongside that
receipt. The recipe does not require a previous FlagPrism build, its artifacts,
or any fixed `/tmp` directory.

```sh
# Run in the SDK environment; these paths are explicit installation inputs.
export COMPONENT=/path/to/FlagPrism
export WORK=/path/to/fresh-ascend-build
export LLVM22_PREFIX=/path/to/ascend-compatible-llvm22
export LLVM15_PREFIX=/usr/lib/llvm-15
export CANN_ROOT=/path/to/cann-9.0.0
export JSON_INCLUDE=/path/to/json/include  # contains nlohmann/json.hpp

python "$COMPONENT/integration/patches/ascend/build_from_source.py" \
  --component "$COMPONENT" --work-dir "$WORK" \
  --llvm22-prefix "$LLVM22_PREFIX" --llvm15-prefix "$LLVM15_PREFIX" \
  --cann-root "$CANN_ROOT" --json-include "$JSON_INCLUDE" --jobs 4

# Successful installation is a normal wheel install in this fresh venv.
"$WORK/venv/bin/python" -I -m flagtree.profiler.cli --help
```

The default source repositories are the public FlagTree, AscendNPU-IR and FLIR
repositories listed above. Offline users may pass `--flagtree-repository`,
`--ascend-ir-repository`, and `--flir-repository` as local **source Git mirrors**;
these are cloned into the independent work directory and exact commits checked.
No native/build directory is read from those mirrors. The helper applies the
three complete patch layers in this order: `flagtree-source.patch`,
`automatic-source-origins.patch`, `automatic-import-order.patch`. It snapshots
current component sources under `$WORK/component`, configures a fresh Ninja
graph, builds `triton`, `triton-mlir-opt`, `flagtree_profiler_native`,
`flagtree_debugger_native`, and the separate LLVM15 observer, and only then
assembles the wheel. AMD/NVIDIA backend generated-header targets are common
compiler dependencies; enabling them does not run another backend or device.

Outputs are `$WORK/core-build`, `native-python`, `observer-build`, `wheel/dist`,
and `venv`. The venv deliberately reuses the matching SDK's Torch dependencies
through `--system-site-packages`; compiler and FlagPrism imports must resolve to
the new venv. `check-install` records native/helper/plugin/header paths and
hashes, validates package prefixes, and asserts that NPU initialization remains
false. Wheel assembly additionally checks all component Python and native/header
bytes against the ZIP. This is CPU installation evidence, not a kernel or
independent qualification pass.

To inspect configuration before a long build, add `--stop-after configure`.
To compile and seal the native outputs before packaging, use `--stop-after native`.
Resume with the same inputs and `--resume`; when intentionally updating the
component source, also pass `--refresh-component`. The latter replaces the
snapshot, regenerates the graph and rebuilds affected targets, including common
compiler C++ even when Ascend observes kernels through the late plugin. Changed
LLVM/SDK dependency identities or parent patches require a new work directory.
Each invocation/command records argv, PID, start/end, exit and a distinct log;
failures raise the original error or identify the exact retained log. A command
watchdog defaults to 7200 seconds (explicit `--command-timeout`); interrupted
commands stop their own process group. Installation limits are independent of
public profiling compile/export deadlines. No successful installation is
reported until all required builds, wheel installation and cold import checks
finish.

The Ascend manifest exports separate `operation_plan` and `control_plan`
inventories. The operation budget limits selected source-operation regions;
it is not a total timestamp/site budget. The control inventory is formed at
the actual LLVM site-ID allocation points for recognized existing primitives
and original `LoopInfo` headers. It records `public_semantic`, `operation`,
`selected`, selection reason, real source/inline evidence and loop structure.
All requested control sites are selected (`max_sites: null`), and unrequested
semantic classes remain visible as unselected candidates. Controls therefore
add real collection cost beyond the default eight operation regions; the
per-actor dynamic record capacity/loss protocol still applies. No numeric
site-ID namespace is used to classify or exempt records. Both plans bind to
the actual compiler/module/actor handoff and are exported by the public plan
view. This inventory addition requires rebuilding the LLVM15 observer; it is
not a report-only reconstruction of earlier buffers.
