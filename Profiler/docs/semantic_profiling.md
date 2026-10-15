# Compiler-assisted semantic profiling

This branch adds compiler execution manifests, explicit observation requests,
and invocation-associated reconstruction. Build the FlagTree core, FlagPrism
compiler bindings and native runtime together. New Python on an old native
library is unsupported.

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

Use a new output path for each run; existing directories are never overwritten.
For ordinary native collection start with `hook="triton"` and no request.
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

Unsupported semantics/selection modes fail explicitly. Site IDs belong to the
current compiled observer manifest, not source line order or another binary.
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
  exports actual dynamic records; the full matrix and fused-actor acceptance
  remain pending. The generated launch worker and SDK connection-table path
  pass four actual calls across two binaries and two streams, including task
  zero. Default temporary SDK retention and public normalized task association
  are being integrated and require a new combined hardware acceptance.
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
| `ai/cann_native_tasks.json` | Canonical CANN tasks, superseded export views and unclassified native rows with their association evidence |
| `ai/native_task_sys.json` | Original SDK task SYS endpoints, packet offsets/hashes, or explicit unavailable reasons; separate from source-clock alignment |
| `report/observations.html` | Source site, occurrence and control timestamps with explicit limits |
| `raw/native/` | Original collector outputs, including unverified legacy traces |
| `raw/native/capture.cann-launch-receipts.json` | CANN retained worker tokens, original query status/IDs and SDK capture lifetime metadata when supported |
| `raw/native/capture.cann-task-identities.json` | SDK task identity candidates and exact connection-table evidence; clock status remains separate |
| `raw/native/cann_sdk/`, `raw/native/cann-sdk-retention.json` | Original SDK session files and original-to-bundle path/SHA mapping; temporary source removal is deferred until successful bundle export |
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
varied shapes/configurations, and held-out RMSNorm checks. Full acceptance still
requires frozen-source fidelity, lifecycle and overhead runs. The controlled
Enflame scalar one-store experiment measured about 3% device-task perturbation,
whereas its vector alternative measured about 26%. Host and stream latency were
much higher, and neither result establishes the cost of all-site collection.
NVIDIA performance remains deferred by the user; functional development continues.
Ascend hidden-only acceptance is
pending environment restoration. See [method tests](method_testing.md) and the
backend evidence manifests for actual results and supported versions.
