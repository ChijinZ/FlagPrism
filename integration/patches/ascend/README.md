# Ascend integration: pinned source builds

The current source recipe uses two complete diffs against exact upstream pins:

| Repository | Upstream commit | Complete patch |
| --- | --- | --- |
| FlagTree | `0364ed4bc39d1dfae483741ec272298297fa5bda` | `flagtree-source-census-v2.patch` |
| FLIR | `ff91e64b6042a27e0db053f28ea3741be65d24d0` | `flir-source-census-v2.patch` |
| AscendNPU-IR | `4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9` | none |

Apply each complete patch once to its own repository. Do not layer the old
`flagtree-source.patch`, `automatic-source-origins.patch`,
`automatic-import-order.patch`, or `initial-handoff.patch` onto the new patch.
Those files describe earlier build checkpoints and remain for provenance.

The FlagTree patch includes SDK callbacks, source-origin retention, launch
receipts, packaging/import fixes, source-program marker transport through
AutoBlockify, and effective AutoBlockify options in the compiler cache key.
The FLIR patch records roles and source-axis information at actual ABI argument
creation. The component supplies the source marker pass, late LLVM observer,
runtime transport and decoder. The current transport is physical version 3:
a 64-byte header followed by three actor banks per program, each occupying
`alignUp(S * 8, 64)` bytes for the actual selected source-site count S.
Separating actor banks on cache-line boundaries prevents the cross-actor lost
writes reproduced with the compact version 2 layout. Physical byte and cell
budgets include the header and padding. Version 1/2 captures remain readable,
but their counters have unknown visibility loss and are not exact; a zero cell
cannot establish non-execution. See the
[source-site census protocol](../../../Profiler/docs/source_site_census.md).
The complete patch filenames retain `v2` for compatibility with the build
recipe; the FlagTree patch carries the current version 3 marker transport.

Current validation checkpoint: component Python source `a829a331` is installed
in the fresh Ascend environment with byte-verified native inputs from the
actual `bd61acd` build. The isolated SDK scalar-store legality repair passed
[public strict device checks](../../evidence/usability-r15-public-sdk-strict12/),
the [two original failing combinations](../../evidence/usability-r15-independent-finite2/),
and the [complete original independent cohort](../../evidence/usability-r15-ascend-main24/):
24 ordinary combinations and 48 cold/warm default profile runs. An additional
[two independent mathematical kernels](../../evidence/usability-r15-ascend-new8/)
passed 8 ordinary combinations and 16 cold/warm profile runs. These are
repaired-version results with original inputs, numerical tolerances, State
checks and full raw/source gates; they do not rewrite first-pass history.

Historical checkpoint: `ec75a9f` with the original SDK ended at 42/44 with two
real State assertion failures. Its unchanged
[original qualification report](../../evidence/usability-v3-ec75a9f/qualification-final/REPORT.md)
and [v3 engineering checkpoint](../../evidence/usability-v3-ec75a9f/README.md)
remain available. Public development cases alone were not used to close those
failures; the current independent revalidation above supplies that evidence.
The historical paths and build results below describe their earlier snapshots,
not installation receipts for current sources.

FlagTree0364 leaves FLIR unpinned; the later 516ad31 revision uses a TLE API
absent from this baseline and fails compilation. The compatible pin above
retains FLIR; disabling the feature is not the validated build. The compiler
uses the existing LLVM22 cache. The late observer is a separate upstream
LLVM15.0.7 `opt-15` plugin. **Do not load this plugin into vendor bisheng**;
that LLVM fork is ABI-incompatible.

The SDK tiling-legality work uses a separate LLVM19 standalone compiler pinned
to the actual CANN SDK source revision `428ab8fdab46`, in an isolated prefix.
It does not replace the LLVM22 parent dialect build or overwrite system CANN.
The [SDK build recipe](../../../tools/ascend_sdk_legality/README.md) records
source pins, material hashes, real build PIDs and the unmodified-tool replay
required before applying the repair. After installing the compiler-identity
parent patch, select a validated replacement through
`TRITON_ASCEND_COMPILER=/absolute/path/to/bishengir-compile`; the
[compiler identity contract](compiler_identity.md) applies equally to ordinary
and profiled compilation. Retain old caches when verifying an upgrade.

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

The complete FlagTree v2 patch loads the Ascend Torch runtime before vendor
compiler discovery during a cold CLI import. Its source-origin changes enable
the SDK's real debug locations when the
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
Build the `flagprism-ascend-structure` target in the same LLVM15 CMake tree
and supply `--actor-structure-tool /path/to/flagprism-ascend-structure` when
assembling the wheel. A reader beside the supplied plugin is also discovered
automatically. It enables default observed-fragment path analysis and is a
read-only executable; rebuilding the SDK or late-observer plugin is unnecessary
when only the analysis Python changes. The assembler verifies the reader's
packaged bytes. Without a supplied/beside-plugin reader, existing installation
remains compatible and this analysis explicitly reports unavailable.
Install the resulting wheel into a venv (matching system Torch/SDK packages may
be reused). The installed adapter discovers the packaged plugin and creates
immutable compiler capture directories automatically; explicit environment
paths remain available as advanced overrides. Failed compiler captures are
retained and the error names their compiler-stage evidence.

Default automatic Ascend profiling uses source-site census v3: actual dynamic
visit counts for selected source operations over the admitted launch grid,
with separate physical actor banks. Counts are not checkpoint event streams
or operation durations; clock, occurrence and iteration fields remain null.
See the [source census contract](../../../Profiler/docs/source_site_census.md)
for selection, physical storage, source association and overflow semantics.

Version 3 reserves a 64-byte zero header and rounds every actor bank up to a
64-byte boundary. This gives each independently writing actor exclusive scalar
GM cache lines. All header and actor padding counts toward the byte and cell
budgets and must remain zero. Versions 1 and 2 remain readable as historical
formats. The `flagtree-source-census-v2.patch` filename remains for recipe
compatibility; its contents also transport the explicit version-3 source marker.

The older explicit advanced checkpoint mode retains zero-interval
source-operation events and loop-header visits. Its locations and local ticks
do not establish completion barriers or engine-busy measurements. Historical
checkpoint selection limits do not describe the default census mode.

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
complete FlagTree v2 patch and the complete FLIR v2 patch to their respective
repositories. Each patch has a recorded SHA256 and a tracked diff against HEAD;
resume rejects additional staged or unstaged modifications. It snapshots
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

If a previous attempt created `wheel` or `venv`, resuming uses a new matching
pair `wheel-resumeN` / `venv-resumeN` and separate `check-install-resumeN.py` /
`install-check-resumeN.json` files. Failed attempts and their logs remain intact.
Read `installed_prefix`, `installed_wheel` and `install_check` in `recipe.json`
for the successful paths; `install_attempt` identifies the current attempt,
including one that failed. Do not assume that `$WORK/venv` is the most recent
successful installation after a resume.

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

### Detailed profiling and NPU graphs

Detailed observation sessions require eager launches. Starting an internal CANN
session inside NPU graph capture, or invoking a Triton kernel inside capture
while that session is active, raises `RuntimeError` before debugger buffer
preparation. Leave the graph context before making an eager recovery call. The
same session can continue collecting eager calls; finalization still exports
those original records. A rejected launch has no allocated trace bytes to export.

The Python guard uses TorchNPU's public capture query without caching its result.
An unavailable, failed, or indeterminate query refuses instrumentation and keeps
the original exception as its cause. The per-JIT guard checks the current stream;
ordinary kernel arguments, including an argument named `stream`, pass through
unchanged. Launch metadata and the native backstop check the actual SDK stream.
CANN's native `aclmdlRICaptureGetInfo` check also rejects active or invalidated
capture and checks the SDK return code before allocation. CANN SDK failures in
this prepare/export/release chain become Python exceptions. Preparation rollback
attempts both owned frees and preserves the original failure if cleanup also
fails. This does not turn all internal `failRuntime` assertions or other backend
fatal errors into recoverable exceptions.

The shared Python guard also covers detailed Enflame sessions through TorchGCU's
public query; its checked native backstop uses `topsStreamIsCapturing`. Neither
provider extension is imported for other backends. Native-only sessions are not
reclassified as detailed sessions by this guard.

After installing the matching source-built wheel, the ordinary unannotated
kernel regression can be run through both public entrypoints:

```bash
python tests/ascend/automatic_graph_rejection.py --device 4 --output /tmp/graph-api
python -m flagtree.profiler.cli --backend cann --device 4 --detail auto \
  --name /tmp/graph-cli-bundle tests/ascend/automatic_graph_rejection.py \
  --device 4 --output /tmp/graph-cli-state --cli
```

The API test prewarms ordinary kernels before starting observation sessions. The
CLI test's explicit application prewarm calls are collected by its outer session.
Both check rejection and eager recovery on two actual streams with separate
recovery outputs, input checks and canaries. These are development regressions,
not independent qualification results.
