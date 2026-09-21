# Detailed activity reports

The report pipeline is backend independent. Each collector translates SDK records into
normalized `activity.*` fields in internal collector records. Analysis and HTML rendering
consume this contract without selecting a backend. Enflame is the first hardware-validated
producer; other backend names in unit tests exercise the contract, not hardware support.

```python
from flagtree import profiler

session = profiler.start("profile-run", hook="triton")
# Execute the workload.
profiler.finalize(session)
```

Finalization directly creates a self-contained output directory. No report command or
conversion script is needed. TCU is disabled by default; ordinary Python API usage needs
no special launcher. Existing output directories are never overwritten.
Outputs include `report/index.html`, analyzed `report/report.json` and, when timed events
exist, Perfetto `report/timeline.json`. Legacy `.vendor.json`, `.meta.json` and `.hatchet`
files are internal temporary intermediates, not user-facing output. Original event records
are retained in `ai/events.jsonl` (accepted) and `ai/rejected.jsonl` (excluded); native scope
metrics are retained in `ai/call_tree.json` when available.

The same capture also produces a machine-readable `ai/` directory:

| File | Contents |
| --- | --- |
| `README.md` | Reading order, units, scope and interpretation limits |
| `summary.json` | Objective statistics, activity coverage, data gaps and rejected-record counts |
| `context.json` | Producer capture metadata and supplied hardware/software/workload/compilation context |
| `kernels.json` | Statistics grouped by device/context, name, grid/block and available binary/argument identity; event IDs |
| `launches.json` | Launch IDs, binary references and deduplicated argument IDs |
| `arguments.json` | Argument-ID map: tensor shape/dtype/stride and scalar parameters; no tensor contents |
| `binaries.json` | Compiler cache identity, binary hash, effective compiler metadata and source links |
| `sources/` | Deduplicated kernel text and source-file snapshots |
| `events.jsonl` | Complete normalized events with original runtime fields and vendor metrics; omitted without events |
| `counters.json` | Counter groups, units, sources, scopes and per-instance statistics; omitted without counters |

`manifest.json` records schema version, capture ID, relative file paths, sizes and SHA-256
hashes, excluding itself. No findings or optimization recommendations are generated.
Missing observations are unknown, not zero or proof of unsupported hardware; explicit
producer availability states such as not_enabled are used by the top-level summary.
Context sections distinguish partial data from unknown data. Device clocks are static
properties in kHz, not live frequency samples; processor counts are backend-defined.
The call tree omits legacy summed activity/runtime IDs, timestamps and configurations. TCU aggregates are not joined to
individual launches or turned into artificial timelines.

Optional context can be provided as `profiler.start(..., metadata={...})`, a dictionary with
`hardware`, `software`, `workload` and `compilation` sections. For example:

```python
workload = {
    "operator": "my_operator",
    "parameters": {"shape": [65536], "dtype": "float32"},
    "warmup": {"iterations": 3},
    "measurement": {
        "iterations": 10,
        "scope": "ten calls followed by one synchronization",
        "synchronization": "after the measured calls"
    },
    "validation": {"status": "not_checked"}
}
# Fill this with facts from the workload you actually execute.
session = profiler.start("profile-run", hook="triton", metadata={"workload": workload})
try:
    # Execute the measured calls and synchronize; retain outputs to check.
    ...
finally:
    profiler.deactivate(session)
    try:
        # Perform your actual correctness check here.
        # Set workload["validation"] to passed/failed only after that check.
        ...
    finally:
        profiler.finalize(session, metadata={"workload": workload})
```

Unknown facts may be omitted or null. Optional section/type problems are saved in
`context.metadata_issues` with exact paths; recommended missing facts are separate
`metadata_missing_fields`. Structural issues do not raise Python warnings or fail
capture under `-Werror`. Root metadata must be an object containing finite JSON;
Python tuples retain the existing conversion to arrays. Nonstring object keys,
nonfinite numbers, cycles and unsupported objects are rejected. Inputs are deep
snapshots: later caller mutation has no effect until another API call supplies it.
Finalize replaces matching top-level sections, not nested fields. If final metadata
cannot be serialized, the prior metadata and capture are saved and hooks released
before ValueError is raised; rejected-update diagnostics remain in context.json.
CLI file context takes precedence over inner script context. Repeated start for the
same active session applies metadata with the same top-level replacement rule.

Kernel groups now provide direct argument/binary/source references and bounded
`scalar_arguments`/`compiler_metadata` previews (128 items / 8 KiB each). A partial
preview reports omitted_count; full evidence remains in the referenced files. Unknown
and genuinely empty summaries are distinguished. No parameter role is guessed from
its name. Tensor descriptions may include output or scratch arguments, not only inputs.

`sampling` counts observed timed/untimed kernel events and single-sample groups.
Each hotspot's `measurement` lists producer source labels and interval semantics.
These are observations, not necessarily independent trials or hardware-clock time;
caller measurement policy is displayed separately. A single interval cannot estimate
run-to-run variability. Capture-local IDs, PID/stream ordinals and binary hashes do
not establish cross-run workload equivalence. See generated ai/README.md for a direct
query example and backend-override/source navigation steps.

The existing command-line launcher accepts the same metadata via `--metadata context.json`. Supplied metadata is preserved
without inference; missing sections are listed explicitly. Use actual compile settings,
not requested settings, and record checks/warmup/repetitions when known. The exporter does
not inspect the reporting host or execute the workload to fill gaps. Copy the whole bundle
to preserve access to original evidence. Export never reruns the workload or enables TCU.
The HTML embeds exact export data so its download buttons work without adjacent files or a web
server, including when opened via `file://`. This increases HTML size but preserves integer precision.
The UI includes searchable activity lanes, zoom, correlated event details, hotspot sorting,
P50/P95/P99, effective transfer throughput, observed allocation history, and per-capture statistics.

## Collector contract (version 2)

The existing vendor artifact envelope remains unchanged: `backend` identifies the producer;
`associations` holds records; `degrade_reasons` explains capture limitations. Each association
retains `source`, `state`, `note`, `runtime_event`, and `metrics`. `collected` means an activity was actually observed, even when its identities or timestamps are incomplete. Unsupported metric placeholders are not collected activities. Producers must distinguish real captured timestamps from synthetic or estimated timing.

`runtime_event` supplies `op_name`, `start_time_ns`, `end_time_ns`, `device_id`, `stream_id`,
`correlation_id`, and `scope_id`. Timestamps are integer nanoseconds in one aligned clock domain
within the artifact; zero denotes unknown. Equal nonzero start/end is a valid zero-duration API.
Do not combine clocks from independent devices/processes without backend clock alignment.

| Normalized metric | Meaning |
| --- | --- |
| `activity.kind` | Required: `kernel`, `runtime`, `driver`, `memcpy`, or `memset` |
| `activity.process_id`, `activity.thread_id` | Process and host thread identity; thread ID semantics belong in producer documentation |
| `activity.context_id` | Device context identity |
| `activity.correlation_domain` | Optional correlation namespace, default `default`; IDs must be unique within process + namespace |
| `activity.scope_name` | User/Triton scope label, separate from the real kernel name |
| `activity.grid_x/y/z`, `activity.block_x/y/z` | Launch dimensions when available |
| `activity.completed_ns` | Completion timestamp including child kernels, if the SDK defines it; zero means unknown |
| `activity.bytes` | Bytes actually reported for memcpy/memset activity |
| `activity.copy_direction` | `H2D`, `D2H`, `D2D`, `H2H`, `P2P`, or `unknown`; never a vendor enum |
| `activity.api_success` | Integer 1 for success, 0 for failure; omit when unknown |
| `activity.memory_action` | `allocate` or `free`, only for successful calls |
| `activity.memory_space`, `activity.address` | `host` or `device`, and allocation identity |
| `activity.allocation_bytes` | Allocation size; required for allocate records |

Identity and measurement fields may be omitted or null; they never invalidate an otherwise observed activity. API/device correlation requires a nonzero correlation
ID and a process ID on both endpoints. Vendor-specific flags, enum values, error codes and extra
metrics retain their vendor namespace; the common UI preserves them in event details without
interpreting their numerical meaning. Return-code normalization is the collector's responsibility.

Memory identities use process + context + memory space + address. A collector must provide enough
identity to avoid address collisions between its devices/contexts. Allocation history is aggregated
by memory space, not a claim about per-device total memory. Only runtime allocation callbacks are
currently interpreted by this report; other memory event models need an explicit contract extension.

The common Session overlay keeps normalized non-kernel activities out of the existing kernel
tree/timeline totals. Existing collectors that do not emit `activity.kind` keep their prior overlay
behavior. They do not automatically gain detailed-report support: add normalization and validate
on their hardware. Older experimental artifacts containing only vendor-prefixed classification
must be recaptured with the updated collector; the report rejects them with an actionable error.

### Unknown fields and identity

Normalized reports and manifests use schema version 2. Unknown observations are JSON `null`,
not zero. Device, stream, context, process and thread ID zero remain valid. Under the legacy
runtime contract, scope/correlation/task ID zero and timestamp zero mean unknown.
`field_issues` explains missing or invalid fields; `original_record` preserves the producer's evidence.
C++ producers whose integer envelopes cannot express null can supply `activity.unknown_fields`,
a comma-separated string of runtime field names (`device_id,stream_id,start_time_ns`, etc.)
or fully qualified metric names (`activity.context_id`). Whitespace is ignored. This declaration
wins over stored integers; collectors must mark unsupported fields rather than claim a default zero.
Host API device/stream identity defaults to unknown; explicit `activity.device_id` and
`activity.stream_id` can supply observed identities.

`events` contains timed activities; `untimed_events` retains activities without usable timing.
Both are exported to `ai/events.jsonl`. `counts` includes both, while `timed_counts` and
`untimed_counts` distinguish them. Without timed activity, `origin_ns` is null. Untimed activity
never contributes zero duration, coverage, percentiles or fabricated Perfetto events; it appears
in the HTML capture notes with its recorded fields.

Correlation requires known process, domain and correlation ID. Ambiguous API endpoints do not
produce flows (one unique runtime endpoint is preferred over driver endpoints). Launch metadata
requires a unique known scope plus matching name. Incomplete lane identities are displayed per
record, not as one physical queue. Kernel groups require known process/device/context/name and
all grid/block dimensions; otherwise they remain separate `partial` groups and cannot be matched
by `comparison()`. Missing binary/arguments remain null: even a complete observed configuration
is not proof of identical workloads. Device coverage is separated by process and device ordinal.

Allocation accounting requires explicit successful API status and known process identity.
Device allocations additionally require a context identity unique within the process; backends
with device-local contexts must provide device identity or normalize the context namespace.
Host addresses belong to the process independent of context. Missing identity/status leaves
the API visible but excludes it from the allocation curve.

### Export failures and backend extensions

Successful exports remove internal intermediate files. Failed collection/finalization/export
retains them in the directory named by the raised error. `finalize()` attempts tracked sessions
independently, releases hooks and reports failures with session/phase information. A bundle is
complete only after its `manifest.json` is written. Recover from retained artifacts into a fresh
output directory; partial outputs are never silently overwritten.

Backend-specific software module names and optional external counter callbacks live in the
small `_backends.py` policy table. SDK imports remain lazy. Counter defaults, units, replay
semantics and scope explanations belong to the counter producer. Common export merges counter
records and retains both producers' capture/availability metadata. Explicit availability is never
replaced by a default; missing declarations remain unknown. Adding a backend requires no vendor
conditions in HTML or the common exporter. Existing ixKN/MCU launch options remain separate.

## Interpretation and extension

Missing categories/fields mean unreported data, not zero activity. Device activity coverage is
an interval union within the first-to-last recorded device activity, not hardware utilization.
Effective transfer GB/s uses bytes divided by recorded duration, not measured HBM bandwidth.
Allocation history excludes pre-capture allocations and caching-allocator tensor lifetimes.
CPU API time can overlap device time and must not be added to it. Compare matching inputs,
launch configurations, devices and capture settings; the report does not enforce their equality.

To add a chip, implement SDK normalization in its collector, preserve raw vendor fields, then run
`Profiler/test/test_report.py` and hardware tests checking numerical results, captured event fields,
correlation, session isolation, and existing kernel summaries. The report needs no backend branch.
New concepts such as counters or instruction-level samples should extend the common contract and
visualization explicitly instead of encoding backend semantics in the HTML layer.

## Report validation

Unknown or malformed timestamps preserve an untimed activity with a reason; only structurally invalid or unclassified records are excluded from the activity view. Invalid
allocation metadata is counted separately and does not mutate the observed memory curve. Missing
byte counts or API status remain unknown. Non-finite JSON numbers must be encoded as strings.

The offline regressions run without a device:

```bash
python3 -m pytest Profiler/test/test_report.py -q
```

An opt-in browser regression uses Playwright and Chromium. Install them in a test environment,
including Chromium's system dependencies, then run:

```bash
python3 -m pip install playwright
python3 -m playwright install --with-deps chromium
FLAGPRISM_TEST_BROWSER=1 python3 -m pytest Profiler/test/test_report.py -q
```

The browser regression checks category/search filters, keyboard-accessible event selection,
event details, sorting, zoom, empty captures and narrow-screen overflow. The report itself has
no Playwright, JavaScript package, network, or browser-server dependency. Wide tables and the
timeline scroll within their panels on narrow screens. The event selector shows at most 500
visible records; use search, category filters or zoom to narrow larger captures. This limit does
not discard data from the report or trace exports.

## Counter aggregates

A producer may add `counter_groups` independently of timestamped `associations`. Each group has
`name`, `source`, `scope`, optional `invocations`, and a `metrics` list. Each metric has `name`,
`unit`, `value` (finite number, or null when unavailable), optional `description`, and `instances`.
Instances have a backend-provided display `instance` label and numerical `minimum`, `maximum`,
`mean`, `count` statistics. The common UI does not interpret vendor metric names or aggregate
values further. Preserve SDK units and missing values; do not sum efficiencies or average averages
without a defined weighting. Producer-supplied descriptions explain the scope and denominator.

Optional `kernel_summaries` contain `name`, `count`, `total_us`, `mean_us`, `min_us`, `max_us`.
These are aggregate instrumented timings, not per-launch samples; percentiles and timestamps
cannot be reconstructed. Optional `capture` metadata records the source tool, version, command,
requested metrics and replay policy. Optional `capture_notes` explain tool-specific collection
semantics; `degrade_reasons` remains reserved for degraded collection. Counter-only captures render aggregate views without an
invented timeline or an empty Perfetto download. Their analyzed JSON export includes all counters.

TCU is the first validated external counter producer; see [Enflame TCU usage](../../docs/enflame.md).
Adding another vendor's importer should populate the same contract and provenance, without adding
vendor-specific logic to the report renderer. No cross-capture or name-only joins are performed.


## Launch identity

FlagPrism temporarily wraps the existing `CompiledKernel.launch_metadata` method while
its launch hook is active; no FlagTree patch is required. The wrapper preserves user
metadata callbacks and existing metadata keys. It describes the compiled kernel, grid
and arguments on every launch, including kernels prewarmed before profiling, without
recompilation or reading tensor contents. Pausing the last active launch hook or
finalizing releases the wrapper. If another tool wrapped the method in the meantime,
FlagPrism disables its own closure without overwriting that tool's method. Unsupported
metadata objects retain the activity-only path; identities are never inferred from names. Compiler resource metadata is preserved; loader register/spill placeholders
are not measurements. Source file snapshots reflect capture-time files, not a guarantee
about external dependencies. High-level semantics, warmup policy and correctness remain
caller metadata; the profiler does not infer them from kernel arguments.


Callers can attach measured experiment facts at the end without an extra command:

```python
profiler.deactivate(session)  # exclude reference checks from the measured region
# Validate outputs here, then supply the actual result and measurement policy.
profiler.finalize(session, metadata={"workload": {
    "operator": "my_operator", "parameters": {"causal": True},
    "warmup": {"iterations": 3}, "measurement": {"iterations": 10},
    "validation": {"status": "passed", "reference": "CPU reference", "atol": 0.003}
}})
```

Final metadata replaces supplied top-level sections of the selected session. It is
explicitly caller-supplied evidence, not a profiler-generated correctness verdict.
Omit information you did not check. Metadata is optional; normal start/finalize usage
and TCU defaults are unchanged. Neither a second run nor a baseline is required.
`missing_sections` lists wholly unknown sections; `partial_sections` and section-level
`missing` lists describe incomplete context. Kernel groups have representative launch
IDs and tensor input summaries for quick navigation before reading event details.

## Evidence overview and provenance

The generated AI README opens with capture-specific evidence counts. Both
`ai/summary.json` and `report/report.json` expose `evidence_overview`: timed and
untimed kernel records, kernel-event links to launches/arguments/binaries/source
snapshots, an inventory of captured metadata, and root-relative evidence file
paths (null when absent). Link counts use all observed kernel events as their
denominator; inventories count records or deduplicated objects and can include
unassociated launches. Source snapshot counts deduplicate exported file paths.
These counts do not establish whether all application work was captured.

The HTML presents the same overview before the timeline. No observed kernel
records is a neutral observation; runtime/copy events can still be available.
Untimed kernels, unassociated launches and aggregate summaries remain preserved.
No registration failure, unsupported hardware or inactivity is inferred.

Collector device properties and captured kernel source/compiler metadata are
observed evidence. `context.supplied` (also `report.caller_context`) contains
caller declarations, including validation outcomes and guessed source paths;
the profiler does not verify those claims or infer semantic contradictions.
The report labels these origins separately, even if they disagree.
