# Automatic internal profiling

This development branch adds automatic fine-grained profiling for kernels
compiled through its matching FlagTree integration. Operator source does not
need scopes, observer IDs, hidden arguments, or per-kernel instrumentation edits.
The compiler selects bounded internal locations from the actual specialization.

## Install the matching compiler and component

Use a wheel built from this component and the pinned backend integration in
[`integration/patches`](../../integration/patches/README.md). A stock compiler
wheel without these callbacks/passes is insufficient. Existing compatible Torch
and vendor SDK installations remain prerequisites. The automatic NVIDIA pass
and Ascend late plugin must be built; copying Python over an older installation
does not add these capabilities.

For NVIDIA, layer `nvidia/automatic-scopes.patch` on the pinned integration.
For Ascend, layer `ascend/automatic-source-origins.patch` on the complete pinned
integration, and build/package the LLVM15 observer. The observer runs out of
process with upstream opt; it must not be loaded into the vendor LLVM fork.
For Enflame, use its pinned combined compiler integration and this component's
automatic planner. Backend wheel recipes and independent installation evidence
are being qualified in this branch; development smoke tests alone are not a
claim that every supported compiler structure has passed product acceptance.

Select the installed compiler backend explicitly in multi-backend environments:

```bash
export FLAGTREE_BACKEND=enflame   # or ascend; omit for the NVIDIA build
```

This is particularly important with torch_gcu environments that redirect the
CUDA device API: otherwise both Enflame and CUDA drivers may appear active.
Select devices with the vendor runtime's visibility controls before Python
starts, or set the current device before starting a session in the API path.
The script must use logical device indices consistent with that visibility.
The CLI also accepts `--device N` before the script name to select the runtime
logical device before starting the collector. The application must use that
same logical device; for example, profiling an application that chooses NPU4
requires `--device 4`. Backend selection and device selection are separate.
Do not set line-info, plugin-path, capture-directory or publisher environment
variables for normal automatic profiling; those are advanced overrides.

The new Ascend census also requires the source-coordinate lowering bridge and
matching native census ABI. Its complete clean-build recipe is still being
finalized in this development branch. An older checkpoint-only wheel does not
implement the new default; Python file replacement alone is insufficient.

## Run your own script

With the installed environment active and its SDK environment initialized:

```bash
python -m flagtree.profiler.cli --detail auto -n profile-run my_kernel_script.py
```

`--detail auto` enables automatic internal observation. Omitting `--detail`
keeps the CLI's native collection mode, which can complete successfully without
internal dynamic records. For the session API, use `start(detail="auto", ...)`;
omitting `detail` likewise does not enable automatic internal instrumentation.

Normal arguments after the script name belong to the script. Use a fresh output
directory for each capture. The script executes once in a supervised worker; the basic command does
not request an application replay or external counter collection. The CLI
preserves Python interpreter flags such as `-I` and `-O` in that worker.

Automatic CLI compilation phases default to a 120-second deadline (explicit
`--compile-timeout` values may be 1–300). The cumulative export budget in a
worker defaults to 60 seconds (`--export-timeout` may select 1–60). Application
runtime between these phases is unbounded. A timeout returns status 124 and
retains a diagnostic directory and capture paths; cancellation also cleans up
the invocation's worker/descendants, including SDK children in separate sessions.
Other server processes are not terminated. Successful CLI captures include
`ai/deadlines.json`, whose bytes are covered by the bundle manifest.

The automatic quickstart covers eager kernel launches. Automatic internal
collection rejects NVIDIA, Ascend/NPU and Enflame/GCU stream graph capture.
Run the kernels outside graph capture to collect internal observations. On CANN
and Enflame this also applies to legacy IR/instrumentation modes: capture is
checked before starting an internal session and before instrumentation prepares
a launch. A missing, failed or indeterminate capture-state query raises an
error; it is never treated as evidence of an eager launch. Eager launches on
explicit streams remain eligible for collection.

Native-only collection has its own backend support rules; the internal-mode
checks do not establish native graph support. For NVIDIA native graph
activities, use the separately documented CUPTI graph mode. An existing graph
replay without ordinary JIT launches does not supply per-kernel automatic
source records. Simultaneous host-thread JIT calls in one supervised automatic
CLI worker are rejected; use separate capture processes. Interleaving eager
launches on streams does not by itself prove simultaneous recording support.

Direct session API calls remain in the caller's process. They report measured
finalization cost, and external SDK compiler jobs have their own watchdog, but
Python cannot safely preempt a native collector holding the GIL. Use the CLI
when a hard compile/export deadline is required.

Alternatively, initialize the device in your ordinary script and wrap the
launches at the outer level:

```python
import flagtree.profiler as profiler

session = profiler.start("profile-run", detail="auto")
try:
    # Launch your ordinary @triton.jit kernels here.
    run_my_kernels()
finally:
    profiler.finalize(session)
```

`detail="auto"` supplies the backend-specific observation request and hook.
Do not combine it with an explicit observation request or mode. Explicit scopes
and typed requests remain advanced interfaces. Automatic selection defaults to
eight source-operation sites. NVIDIA, Enflame and Ascend use a bounded source-site
visit census across the admitted launch grid: at most 1,048,576 count cells
and 8 MiB of physical storage by default. The byte limit includes alignment,
headers and publisher padding. Both limits are checked before profiling buffer
allocation and the original kernel launch. NVIDIA requires the matching
`preallocation-admission.patch` launcher integration: it supplies the actual
function and grid to the allocator before either scratch allocation. An older
launcher is rejected before allocation instead of bypassing this check. A grid
exceeding either limit is rejected rather than silently truncated to its first
programs. See the [census protocol](source_site_census.md).
Ascend physical version 2 reserves three actor banks with the compiler's actual
selected source-site count S (1–128) per bank: 32 header bytes plus
`program_count * 3 * S * 8` bytes. Both budgets include the reserved actor banks.
The reader retains support for version 1 captures with 128 cells per bank. The actual
backend plan, selected locations, unselected inventory when available, and
protocol-specific loss evidence are retained in the bundle. A bounded selection
is not a claim that every operation was observed.

Ascend automatic mode disables additional aclprof/MSTX activity collection and
host timing fallback. It retains actual JIT invocation/binary association and
source counts; native task timelines may therefore be absent. Its device setting
comes from the current application runtime device at session start. Native-only
and explicit advanced modes remain available for vendor activity collection.

## Read the result

Open `profile-run/report/index.html` and follow **Source-linked internal dynamic
records**. The view can filter by source path, operation, invocation or actor;
each row identifies its source location, compiler operation, binary, call,
program, actor, site and semantic class. Census rows show **Visits**, **Exact**
and **Site role**, rather than an empty timing table. The default display picks
the lowest program with primary-site visits after collecting the admitted grid;
this display choice does not discard other programs' raw cells. The execution and
clock-group view links the related native activity when uniquely associated.

Select a source position to open **Captured source** at that line. This uses
digest-checked snapshots inside the bundle, so the capture-machine filesystem is
not needed. Green marks link each observed line back to retained records for
that exact binary and line. The source selector separates binaries and captured
file versions. Compiler primary locations and inline callsites have distinct
labels. An out-of-range primary remains visible with its reason; a valid inline
callsite can still provide navigation. File bounds alone do not establish that
the snapshot text is identical to the compiled input. Captured JIT text without
a full-file snapshot remains readable with relative lines; file offsets are not
guessed.

**Execution mapping** opens a report page containing observed identities and
retained visits, followed by expandable compiler structure tables. The observed
rows preserve invocation, program, actor, semantic and clock frame. Compiler
organization, layouts, actors and dependencies remain static evidence; the page
does not match static actor names to measured identities or invent an aligned
timeline. The original mapping JSON remains available from that page.

Machine-readable counterparts are:

- `ai/fine_grained.json`: normalized dynamic records and source locations.
- `ai/source_index.json`: captured source identities, digests, line counts,
  retained source-linked record counts and snapshot diagnostics.
- `ai/observation_plan.json`: automatic plans and exact capture evidence.
- `ai/selection_status.json`: automatic validity for each capture and expected
  invocation, including missing captures. Another kernel's records cannot make
  an empty invocation complete. The records page displays the same coverage.
- `ai/observations.json`: original typed observations and backend capture/loss
  data. Raw artifacts remain under `raw/`.
- `ai/execution.json`: actual compiler execution mapping and its evidence limits.
- `ai/export_timing.json`: host finalization/export time. A complete API receipt
  measures the entire finalize call through cleanup; CLI receipts combine
  collector finalization and subsequent bundle materialization. The final timing
  receipt write is excluded. A standalone export of legacy raw files may have
  only materialization time and explicitly reports incomplete total timing.
  These values measure host engineering cost, not GPU/kernel latency.

Large repeated fields in derived JSON can use digest-checked references to the
complete `ai/observations.json`, including clock or compiler-provenance fields.
Report pages resolve these references. Machine consumers should use the public
`restore` reader in the schema guide before inspecting referenced fields.
Large CANN SDK trees are retained losslessly in `raw/native/cann_sdk.zip`, with
member paths, byte counts and SHA-256 in `raw/native/cann-sdk-retention.json`.
Small trees retain the directory layout. Extract an archived tree into a new,
empty directory with standard ZIP tools:

```bash
unzip profile-run/raw/native/cann_sdk.zip -d extracted-cann-sdk
```

The exporter verifies every member before releasing its temporary SDK capture.
Record capacity is bounded, but raw evidence and reports still grow with the
actual capture. Loss, saturation and export-budget failures remain explicit;
the default capacity does not guarantee a complete trace or a 64 MiB bundle
for arbitrary input sizes or loop counts.

See the [version 1 JSON field contract](automatic_schema.md) for field types,
identity namespaces, backend loss accounting and a read-only inspection example.

Read the semantic and clock columns together. The automatic
census records the number of times a selected source control position was
reached. It does not measure duration: its clock, occurrence, iteration and
timing fields are null. A count of five is one record with five visits, not
five fabricated intervals. All-false data masks can still reach a source
position; visits do not establish productive memory transactions or engine busy
time. Saturation in any retained program makes the capture inexact, including
programs outside the default display.

Explicit fixed-program interval requests remain a separate advanced mode.
NVIDIA intervals use SM-local counter ticks; Enflame intervals use the SDK timer,
whose frequency is not assumed. Ascend's explicit checkpoint path can record
source-operation and loop checkpoints as well as existing issue/wait classes.
A checkpoint is evidence of an occurrence, not operation duration. No view
turns an issue interval into engine occupancy or an instrumented interval into
an uninstrumented performance measurement. `None` means unavailable; unverified
clock frames are not overlaid on native timelines.

For interval and checkpoint protocols, `occurrence` counts retained visits of a
site for its invocation/program/actor;
it is not automatically a loop iteration number. Loop conditions may execute
once more than their bodies. Sampling, unselected sites and dropped records
have different meanings. Use the original capture statistics; an unselected
site is not proof of nonexecution. The compiler selection policy reserves
up to two entry-level control positions before distributing the remaining
default budget across actual repeating/branch regions. It observes real scalar
control computations and SCF control intervals; bounded entry evidence does not
mean every branch body was observed. Explicit one- or two-site requests retain
region-first selection and may leave entry context unobserved. Enflame similarly
uses compiler-verified public kernel entry operations, with condition producers
preferred. Ascend's census binds selected frontend operations to their actual
emitted source markers and compiler actors. Context positions may describe
coordinate or condition computation;
they do not establish that a tensor branch body executed. Entry context policies
prefer distinct source lines where the candidates permit it.
A selected program that takes an empty branch can therefore expose its own
entry or control activity. Census entry/context rows alone do not satisfy the
automatic body-observation gate; a source-linked, exact, nonzero primary count
is required. An interval
around `scf.if` describes the control operation; it does not mean that the
conditional body ran. Fixed-program interval mode remains a bounded instance/site
sample. Census mode collects selected positions across every admitted program,
while still bounding the selected sites and logical observers. Neither mode
claims to observe every hardware lane or operation. Plans distinguish
regions with no eligible operation, direct or descendant coverage, and regions
excluded by the finite site budget.

Every captured invocation must have its own verified, source-linked internal
records. An empty, unassociated or unlocated invocation makes automatic export
incomplete even when another kernel has useful records. Failed captures retain
`ai/selection_status.json`, the plan and raw data. Inspect their selection and
loss state. For census captures, query retained programs with the public
`CensusReader`; changing the displayed program cannot recover a missing site or
make an overflow exact. For fixed-program modes, a public `ObservationRequest`
can select another program for a future capture. The tool does not replay the
application to discover another selection.

## Diagnose installation provenance

Run this in the environment used for capture, before running a workload:

```bash
python - <<'PY'
import hashlib
import os
import torch
# Initialize the Ascend runtime before importing its vendor Triton compiler.
# Set FLAGTREE_BACKEND=ascend in this installed environment as described above.
if os.environ.get('FLAGTREE_BACKEND') == 'ascend':
    import torch_npu
import triton
import flagtree.profiler
import flagtree.debugger
from flagtree.profiler.native import runtime_binding as profiler_binding
from flagtree.debugger.native import runtime_binding as debugger_binding
import triton._C.libtriton as compiler
for name, module in [('compiler', compiler), ('profiler', profiler_binding()),
                     ('debugger', debugger_binding())]:
    path = module.__file__
    with open(path, 'rb') as file:
        digest = hashlib.sha256(file.read()).hexdigest()
    print(name, path, digest)
print('Torch:', torch.__version__, 'Triton:', triton.__version__)
print('Profiler:', flagtree.profiler.__file__)
print('Debugger:', flagtree.debugger.__file__)
PY
```

Package paths must resolve to the intended installed environment. Compare native
hashes against the installation/build receipt. Include the command, SDK/compiler
versions, installation receipt, original application exception and retained
failure artifacts in a bug report; numerical correctness alone does not prove
that the internal trace is correct.

For advanced CUPTI library-path selection, configure the path before CUPTI is
first loaded in the process. Changing an already loaded library path is rejected;
use a new process to select another SDK library. A rejected session must leave an
existing collector's mode and path unchanged. The PC sampling capability probe
also checks the live native collector before touching the SDK. Matching active
PC sessions reuse their configuration without probing again; a conflicting mode
or path is rejected before the probe. If SDK shutdown fails, the original
error is reported and remaining owned cleanup is attempted. Unreleased resources
remain pending; a later start must complete their cleanup before acquiring a new
collector, and repeated cleanup failure remains an error.
