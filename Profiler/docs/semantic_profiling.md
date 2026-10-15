# Compiler-assisted semantic profiling

This branch adds compiler execution manifests, explicit observation requests,
and invocation-associated reconstruction. Build the FlagTree core, FlagPrism
compiler bindings and native runtime together. New Python on an old native
library is unsupported.

## What one capture provides

The three mechanisms share `profiler.start()` / `profiler.finalize()` and the
same bundle. They are not three separate collectors to invoke in sequence:

1. **Program–execution mapping** records the actual compiled binary, compiler
   configuration, available source origins and backend execution organization.
   Read `ai/execution.json` and `ai/binaries.json`; a layout description alone
   does not establish which source operation owns a generated instruction.
2. **Semantic observation** lowers a typed request to the backend's supported
   logger. Read the effective selection, semantic, unit, clock scope and loss
   fields in `ai/observations.json`, not just the requested configuration.
3. **Program-associated reconstruction** groups observations by proven launch,
   binary, program and actor identities. Read `ai/reconstruction.json` and
   `report/observations.html`. A source association does not certify a shared
   time axis with native SDK activity.

Native activity can be collected without a detailed request. Compiler and
source evidence is present only when the corresponding launch metadata survives;
empty or partial mapping is reported rather than filled from a kernel name.

## Public interface

```python
from flagtree import profiler

request = profiler.ObservationRequest(
    semantics=("source_control_interval",), programs=(0,),
    max_events_per_instance=64,
)
sid = profiler.start(
    "detailed-run", backend="enflame", hook="instrumentation",
    observation_request=request,
)
try:
    # Execute your existing kernel here; no new source buffer argument.
    pass
finally:
    profiler.finalize(sid)
```

Choose the backend explicitly when comparing collection modes:

| Device / purpose | `backend` | `hook` / request |
| --- | --- | --- |
| NVIDIA native CUDA activity | `"cupti"` | `"triton"`, no request |
| NVIDIA explicit source scopes | `"instrumentation"` | `"instrumentation"`, `source_control_interval` |
| Enflame native activity | `"enflame"` | `"triton"`, no request |
| Enflame source-site intervals | `"enflame"` | `"instrumentation"`, `source_control_interval` |
| Ascend late LLVM source control | `"cann"` | `"instrumentation"`, `issue`, `wait_bracket`, `control_checkpoint` |

The API can select a backend from the active runtime when `backend=None`, but
that does not replace a deliberate native-versus-instrumented choice. A CUDA
request is not accepted with `backend="cupti"` and is never silently redirected
to that collector. Do not supply both an explicit CUDA instrumentation `mode`
and `observation_request`.

For NVIDIA, change the example above to `backend="instrumentation"` and ensure
the kernel contains explicit profiling scopes. For a simple Triton DSL kernel,
opt in to that frontend before compilation and bracket the region in its body:

```python
from flagtree.profiler import language as pl

pl.enable_semantic("triton")

# Inside your @triton.jit kernel:
# pl.enter_scope("region")
# ... the existing region ...
# pl.exit_scope("region")
```

Gluon scopes are enabled by default. The Triton opt-in does not promise valid
coverage for arbitrary pipelining or compiler transformations. An explicit
request on an unannotated NVIDIA kernel raises an actionable error; it does not
produce an empty successful detailed capture. A valid scope not executed by a
branch, or a selected program not launched by the grid, may yield no records.

For Ascend, use its supported semantic tuple instead of the interval request:

```python
request = profiler.ObservationRequest(
    semantics=("issue", "wait_bracket", "control_checkpoint"),
    programs=(0,), sites=None, max_events_per_instance=64, sample_every=1,
)
# Pass this to start(..., backend="cann", hook="instrumentation", ...).
```

The supported hidden ABI and required compiler/SDK/worker integration are listed
in [Ascend prerequisites](../../tests/ascend/README.md). This request cannot make
an unsupported target or an unpatched launch worker supported. No source-level
scratch-buffer parameter is needed on the validated hidden-ABI path.

Use a new output path for each run; existing directories are never overwritten.
For NVIDIA/Enflame ordinary native collection use the native backend in the
table with `hook="triton"` and no request.
The legacy CANN default Triton hook can enable Debugger instrumentation; consult
[Ascend prerequisites](../../tests/ascend/README.md) before using it as an
uninstrumented native reference. Set the device before starting the collector;
a CLI collector starting before application device selection needs an explicit
device in its mode.

`activate()`, `deactivate()` and `finalize()` default to all current sessions.
Pass an initialized session ID to address one session. Unknown activate/deactivate
IDs are rejected before hook state changes. CANN overlapping sessions and
concurrent detailed launches have explicit backend-specific restrictions.

The CLI accepts the same request fields from a JSON file:

```bash
python -m flagtree.profiler.cli -n detailed-run -b enflame \
  -k instrumentation --observation-request request.json workload.py
```

```json
{
  "semantics": ["source_control_interval"],
  "programs": [0], "sites": null,
  "max_events_per_instance": 64, "sample_every": 1
}
```

For NVIDIA scopes, use the same JSON with `-b instrumentation -k instrumentation`.
For Ascend, replace its `semantics` array with
`["issue", "wait_bracket", "control_checkpoint"]`, select `-b cann`, and supply
the device/SDK mode required by the Ascend prerequisites. The CLI owns the
session around the script; an API `start()` inside that script does not create a
second capture.

Unsupported semantics/selection modes fail explicitly. The JSON form uses
arrays where the Python request uses tuples. `programs=None`
and `sites=None` mean all instances/sites only where the backend supports that
selection. A semantic appearing in the common request vocabulary does not imply
that every backend implements it. Site IDs belong to the current compiled
observer manifest, not source line order or another binary.
Collection provenance distinguishes device selection from output filtering.
A filtered output alone does not establish lower device cost.

* NVIDIA `backend="instrumentation"` observes explicit Triton profiling scopes
  on a selected warp. Unannotated kernels cannot provide those intervals.
  Program selection is lowered to the device for `num_ctas=1`; site selection
  filters exported observations and does not reduce device instrumentation.
  Sampling other than every occurrence is rejected on this path.
  SM-local cycle ticks have no certified nanosecond conversion here.
* Enflame `backend="enflame"` observes compiler-assigned source sites using one
  selected program and a sole work-item writer. The SDK's 46-bit global timer
  has unknown frequency; its ticks are not TCU compute cycles.
  Compiler debug-location chains retain source-origin candidates, including
  ambiguous and missing origins, without claiming exclusive cost ownership.
  The default publisher writes scalar record words. For SDK compilation that
  expands this path excessively, set
  `FLAGPRISM_GCU_DYNAMIC_PUBLISHER=vector16_per_work_item` before compiling to
  select the alternate vector publisher. Its actual work-item count and mode
  are recorded and enter the JIT cache key. This is an explicit compilation
  option: it does not guarantee lower perturbation or faster compilation.
* Ascend `backend="cann"` lowers `issue`, `wait_bracket` and
  `control_checkpoint` at late SDK LLVM sites through a hidden observer ABI.
  The hidden-only row-kernel smoke passes numerical/input/canary checks and
  exports actual dynamic records. A fresh fused GEMM+bias+GELU capture also
  passes math/input/canary checks, with four exact native task associations
  and 232 local-duration records from one AIC and two AIV actors for the
  selected tile. The earlier full matrix and held-out coverage are summarized
  below, with their original source versions. The launch-worker path
  has single-task evidence across two binaries and two streams, including
  task zero. Original SDK retention and public normalized task association are
  available. Retained MIX evidence distinguishes compute members through exact
  SDK context membership and `COMPUTE_TASK_INFO.globalTaskId`; dispatch context
  views are preserved separately. Multiple compute members retain their native
  tasks without claiming one source binding.
  Verified A2/c220 source records can obtain local duration conversion from
  retained task/device frequency evidence and the actual compiled SYS counter
  instruction. The conversion keeps an actor-local clock and supplies no
  shared epoch or absolute placement.
  Automatic same-call clock alignment additionally requires raw counter/domain
  evidence that remains **pending**; a task identity or clock-proof validator
  alone does not provide that service.

An issue bracket around asynchronous work does not measure completion or engine
busy time. A wait bracket includes control waiting; a checkpoint is instantaneous.
Instrumentation observes existing dependencies without adding a completion
barrier to manufacture a measured pipeline.

## Output and interpretation

`report/index.html` links native activity and the semantic observation view.

| Path | Meaning |
| --- | --- |
| `ai/execution.json` | Actual binary/configuration, source operations, backend organization and partial mapping reasons |
| `ai/launches.json`, `ai/binaries.json` | Actual launch, argument and compiled binary identities |
| `ai/observations.json` | Typed records, captures, clock scope, selection/loss and raw-buffer hashes |
| `ai/reconstruction.json` | Invocation/program/actor groups and verified clock alignment sets |
| `ai/cann_native_tasks.json` | Canonical CANN tasks, superseded export views, dispatch/context-ambiguous extensions and unclassified native rows with association evidence |
| `ai/native_task_sys.json` | Original SDK task SYS endpoints, packet offsets/hashes, or explicit unavailable reasons; separate from source-clock alignment |
| `report/observations.html` | Source site, occurrence and control timestamps with explicit limits |
| `raw/native/` | Original collector outputs, including unverified legacy traces |
| `raw/native/capture.cann-launch-receipts.json` | CANN retained worker tokens, original query status/IDs and SDK capture lifetime metadata when supported |
| `raw/native/capture.cann-task-identities.json` | SDK task identity candidates and exact connection-table evidence; clock status remains separate |
| `raw/native/cann_sdk/`, `raw/native/cann-sdk-retention.json` | Original SDK session files and original-to-bundle path/SHA mapping; temporary source removal is deferred until successful bundle export |
| `raw/native/capture.observations.json` | Original observation captures and raw-buffer provenance when emitted; calibrated views do not replace these bytes |
| `raw/compiler/` | Captured kernel IR/PTX text, linked and hashed from `ai/binaries.json` |
| `manifest.json` | Relative paths, sizes and SHA-256 hashes |

Snapshots and dynamic events are distinct. Snapshots can overwrite revisited
sites; only dynamic traces retain occurrences. Occurrence numbers are not source
loop indices. Saturation, overwritten primitive records, partial publication and
unmatched entries/exits remain visible or cause rejection with a reason.

Compiler provenance can be one-to-many or ambiguous. A debug location describes
origin, not exclusive cost ownership. Missing source/launch/clock evidence stays
partial or unassociated. Reconstruction never joins by name/appearance order,
or stretches intervals to a native task duration. Same invocation identity does
not establish timestamp alignment. Cross-actor alignment requires explicit
shared-counter/domain evidence and still describes control, not engine occupancy.

CANN task identity uses a token retained by the actual SDK launch worker,
successful worker-local device/stream/task queries, and a unique connection
tuple within the collector's sealed SDK capture. Missing, duplicate, late or
failed receipts are retained without certified association. Sealing requires
a uniquely created capture directory and matching collector PID/device metadata;
choosing the latest directory is insufficient. Task IDs of zero are legitimate
when their query succeeds. The whole native task envelope is not per-program
occupancy, and task association does not calibrate an internal logger clock.

## Failure and recovery

Keep the `try` / `finally` pattern in the API example so finalization is attempted
after a workload error. The CLI also attempts finalization before propagating a
workload failure. A failed launch, failed decode or missing proof is not evidence
of an empty successful execution. Failed decodes retain raw captures and
`capture_status="decode_failed"`; they do not contribute successful semantic
events. Read the capture errors and raw hashes before interpreting an empty view.

If exporting native observations fails, the error identifies a private recovery
journal such as `flagprism-observation-recovery-*/captures.json`. Capture packets
are acknowledged only after the observation sidecar is durably saved. CANN worker
receipts have a separate `flagprism-cann-receipt-recovery-*/receipts.json` journal
written before source lookup or sidecar augmentation can fail. Journals can be
under the output staging parent or a temporary fallback directory; preserve the
exact path reported by the exception or stderr, together with the original raw
files. Successful durable sidecar export removes its own journal.

A recovery journal is evidence, not a finished report or a supported automatic
cross-process resume command. Do not overwrite a conflicting capture ID or edit
receipt IDs/seal paths to force a join. A storage failure in every recovery
location is reported explicitly; in that case the remaining in-memory payload is
not a durable backup. Keep the process/session and diagnostics available rather
than assuming finalization created a bundle. Existing output directories and
unrelated session captures are not cleanup targets.

For successful runs, copy the entire output directory to retain offline source,
raw SDK and hash references. Opening `report/index.html` does not rerun the
workload. The native Perfetto timeline, when present, is distinct from independent
SM/actor-local observation clocks; unverified raw traces are not promoted to a
shared-clock timeline.

## Counters, replay and development status

```bash
python -m flagtree.profiler.cli -n counters-run -b enflame -k triton \
  --counters --counter-metrics SIP/BUSY --replay-mode none workload.py
```

TCU/SIP aggregates retain configuration scope and instance statistics. Ascend
msprof groups retain independent capture identities. Neither is joined to an
earlier detailed invocation by name or rendered as simultaneous execution.
Application replay runs the application again, including its side effects.

NVIDIA and Enflame have real native/dynamic captures, six operator families with
varied shapes/configurations, and held-out RMSNorm checks. The final common-source
regression and focused hardware checks are retained under
`integration/evidence/final-common-20261015/`; the earlier full matrices retain
their original compiler, source and native-library manifests. These correctness
checks do not certify diagnostic timing fidelity or universal overhead. The controlled
Enflame scalar one-store experiment measured about 3% device-task perturbation,
whereas its vector alternative measured about 26%. Host and stream latency were
much higher, and neither result establishes the cost of all-site collection.
NVIDIA performance remains deferred by the user; functional development continues.
Ascend completes the six-family, three-shape, two-configuration matrix in
all three modes (108 requests), the separate fixed-shape T5 experiment,
and held-out RMSNorm at three shapes and two configurations (18 requests).
The long-K fusion additionally passes three detailed and three native-only
configuration controls. Independent retained-buffer and bundle audits are in
`integration/evidence/ascend-final-raw-20261015/`. These observations provide
local-duration conversion, not a verified shared actor/native clock origin.
All-site detailed collection increased small RMSNorm device-task medians by
61.2–67.6% in the controlled experiment; bounded output is not a low-overhead
guarantee. Later prespecified long-K batches (three batches of thirty calls per
mode) show -0.08% to +1.30% device-task change, but detailed host calls take
12.33–12.46 ms, export takes 15.62–17.21 s, and each 33-call session occupies
221–229 MB. This distinct cost regime does not supersede the small-kernel
negative result. Compiler wait-only selection still incurs 60.1–78.0%
small-RMSNorm device-task perturbation; fewer records do not ensure lower cost.
See [method tests](method_testing.md) and the backend evidence manifests for
actual results and supported versions. Same-compilation typed SDK readiness
extraction has separate real fused-capture evidence in
`integration/evidence/ascend-static-readiness-20261015/`. It establishes a static
channel, not dynamic flag-generation pairing or shared actor clock alignment;
the earlier full-matrix audits do not certify this later implementation.

### Retained provenance and diagnostic sensitivity

Verified Ascend readiness and source origins require the retained original source
and per-artifact manifest bytes, their hashes and typed JSON consistency, the
successful enclosing/SDK compilation identities, and the corresponding LLVM
and finished driver job. Older hash-only bundles retain raw inventory without
asserting verified associations; separately revalidated sidecars are derived
evidence and do not rewrite those originals. Missing line locations remain
partial even when compilation provenance is complete.

In the three-configuration fusion control, all-site versus wait-only collection
changes the original configuration's local AIV waits by 76.8% and 83.4%. The
first reduction-step intervention preserves its qualitative wait reduction in
both modes; the subsequent output-tile change does not preserve a further wait
reduction. Low whole-task perturbation is therefore not a certificate of local
wait accuracy. The independent minimal two-read control produced 64 zero-tick
spans with advancing start counters: unresolved resolution, not zero cost or a
fusion-error bound. Evidence and original version identities are retained in
`integration/evidence/ascend-wait-fidelity-20261015/`.
