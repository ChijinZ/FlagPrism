# Automatic capture JSON, version 1

This is the public field contract for the automatic report. JSON `null` means
unavailable; it never means zero. Readers must check `schema_version == 1`,
ignore additional fields they do not consume, and reject other major versions.
IDs are local to a bundle unless a field explicitly identifies a binary digest.
Lists preserve records, not a global ordering across devices or actors.

The default CLI succeeds only after at least one source-linked, verified internal
dynamic record has been exported. This is a minimum validity check, not proof of
complete coverage. A multi-operation workload should normally have multiple
distinct internal sites. Inspect the plan and loss evidence before interpreting
absence. Failed automatic selection retains `ai/selection_status.json` with
`status: "incomplete"`, a reason, request and suggested action, and exits with an
error. Retained partial artifacts are not a successful capture.

## `ai/fine_grained.json`

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | `1` |
| `status` | string | `dynamic_records_available` or `no_internal_dynamic_records` |
| `records` | array of objects | Normalized dynamic observations, including unresolved ones |
| `captures` | array of objects | Original backend capture and loss evidence |
| `rejected` | array | Records rejected during reconstruction, with reasons |
| `limits` | array of strings | Interpretation limits of the reconstructed view |

Every normalized record has the following keys. Nullable fields are present as
`null` when the producer has no value.

| Field | Type | Meaning |
| --- | --- | --- |
| `id`, `capture_id` | string | Observation identity and originating capture |
| `invocation_id`, `binary_id` | string or null | Verified actual call and compiled binary identity |
| `program` | integer or null | Backend linear program ID; not a source line or actor |
| `actor` | integer, string, object or null | Backend execution identity; keep its type and namespace |
| `site` | integer or null | Compiler-assigned observation site in this binary's protocol |
| `semantic` | string | What was measured, for example `source_control_interval` or `operation_checkpoint` |
| `occurrence` | integer or null | Retained visit ordinal for this capture/call/program/actor/site; not a source iteration variable |
| `iteration` | integer or null | Explicit iteration identity only when supplied by the protocol |
| `source_locations` | array of objects | Navigable positions within an unambiguous digest-checked full-file snapshot; each has `file` (string), `line` (positive integer), `column` (integer) |
| `source_location_candidates` | array of objects | Original source positions, distinct compiler/inline/interval roles and snapshot validation results, including invalid or unavailable candidates |
| `source_links` | array of objects | Validated candidates with `source_id`, snapshot digest/line count and report-relative `href` |
| `operation` | string or null | Actual compiler operation or called primitive |
| `association_status` | string | `verified` or `unassociated` in this reconstructed view |
| `source_status` | string | `located` when at least one position has a validated captured snapshot anchor; otherwise `unresolved` |
| `association_evidence` | object or null | Original call/binary association evidence |
| `native_event_ids` | array | Native event IDs associated with the same actual invocation; may be empty |
| `clock` | object or null | Counter domain and comparability evidence, described below |
| `start_tick`, `end_tick`, `duration_ticks` | integer or null | Original local counter values and validated difference |
| `duration_ns`, `relative_start_ns` | number or null | Derived only with explicit conversion/origin evidence |
| `unit` | string or null | Producer unit; inspect the clock even when this is absent |
| `truncated` | boolean or null | Record-level loss indication; capture accounting remains authoritative |
| `sampling` | object or null | Backend selection/sampling evidence; missing does not mean all instances |

For example, the following abbreviated record describes one retained interval;
it is illustrative, not an expected duration or a device-independent site ID:

```json
{
  "id": "capture-a:p0:w0:r0",
  "capture_id": "capture-a",
  "invocation_id": "launch-1",
  "binary_id": "binary-digest",
  "program": 0,
  "actor": "SM:0/warp:0",
  "site": 0,
  "semantic": "source_control_interval",
  "occurrence": 0,
  "iteration": null,
  "source_locations": [{"file": "/app/kernel.py", "line": 12, "column": 27}],
  "operation": "tt.load",
  "association_status": "verified",
  "source_status": "located",
  "clock": {"domain": "nvidia.SM.clock", "scope": "SM:0", "alignment": "instance_local", "tick_ns": null},
  "start_tick": 100,
  "end_tick": 107,
  "duration_ticks": 7,
  "duration_ns": null,
  "relative_start_ns": null
}
```

A clock has nonempty string `domain` and `scope`, string `alignment`, and nullable
numeric `tick_ns`. `conversion_evidence`, `alignment_evidence`, `origin_tick` and
counter wrap fields occur when applicable. A known tick period permits duration
conversion; it does not prove a common epoch. `verified_shared` alignment requires
separate alignment evidence. NVIDIA SM-local counters and Enflame SDK ticks are
not automatically converted to a native host timeline. Ascend counter conversion
evidence can establish a local duration while the cross-actor epoch remains
unverified. A checkpoint with equal start/end ticks reports an occurrence; its
zero duration does not describe operation latency. Source-control intervals do
not establish asynchronous completion or engine occupancy.

Current writers validate source bounds against captured full-file bytes before
setting `located`. Earlier version-1 writers accepted positive compiler line
numbers without snapshot bounds checks; readers needing this stronger guarantee
must check candidates for `validation_status: "in_range_snapshot_position"`.
Candidates also retain `outside_snapshot_line_range`, `snapshot_unavailable` or
`ambiguous_snapshot_versions`. Compiler-supplied directories can resolve a
relative inline filename; basename-only matching to another file is forbidden.
Roles include `compiler_primary`, `inline_callsite`, `interval_entry`,
`interval_exit`, `captured_location_reference` and `frontend_source`. Duplicate
roles may point to the same position. Valid bounds prove that a captured line
exists, not compiled-text alignment or exclusive operation cost.

## `ai/observation_plan.json`

The envelope contains `schema_version: 1`, `plans` (array), `capture_evidence`
(array), and `limits` (array of strings). Each entry in `plans` contains
`binary_id` (string or null) and `plan` (object). Applicable entries also include
`capture_id`, `compile_id`, `actor`, `module_sha256`, `plan_kind`, or `selected_origins`.
Multiple entries can describe separate actors or captures of the same binary;
do not collapse them by kernel name.

The nested plan is backend-specific. Ascend's `operation_plan` includes
`candidate_count`, `selected_count`, `max_sites`, `policy` and `inventory`.
Inventory entries retain actual source and late compiler operation information,
`site_id`, boolean `selected` and `selection_reason`. Enflame's automatic plan
has `schema_version: 1`, `candidate_count`, `max_sites`, `policy`, `selected_sites`
(integer array) and `inventory`. Its inventory entries retain the compiler's
`opId`/`op_id`, `mlirOpName` and source information, plus `automatic_eligible`,
`exclusion_reason`, `selected`, and a `selection_reason` on selected entries.
Native IR bookkeeping is not interchangeable with source operations.

Current Enflame plans additionally have `policy_version: 2` and `control_regions`.
Inventory entries carry `controlFlowSchemaVersion: 1` and actual outer-to-inner
`controlFlowAncestors`, each with `controlId`, `parentOpId`, `operation`,
`regionIndex`, `blockIndex` and `repeated`. These come from IR owners, not source
line proximity. `parentOpId: 0` means the owner is not a tracked operation.
Regions expose eligible/direct/selected site lists and coverage status/reason;
absence of eligible operations differs from exclusion by the finite site budget.
Repeated regions receive priority before class filling. Default eight-site
coverage is bounded: a plan may still leave regions uncovered, which must remain
visible. Older round-robin plans remain readable and have no such coverage proof.

Current Ascend handoffs also export a distinct `control_plan`; the public
envelope labels actor plans with `plan_kind: "operation"` or `"control"`.
Both use the same actual binary-local site allocation. The kind is not a
separate numeric namespace. Control inventory names actual original primitives
and loop headers, their public semantics, selected status and reason. Its
`policy` is `all_requested_original_control_sites`, `budget_scope` is
`existing_primitives_and_original_loop_headers`, `max_sites` is null and
`operation_max_sites_applies` is false. `record_capacity_per_actor` separately
bounds retained dynamic records. The operation plan's finite `max_sites` applies
only to source-operation candidates (`budget_scope:
"source_operation_candidates_only"`, `control_sites_included: false`). Do not
interpret eight operation sites as a total bound including control checkpoints.
For membership checks, use the selected inventories for the actual binary,
module, actor and semantic class. Older operation-only plans cannot establish a
complete control-site selection proof; raw compiler-site provenance remains
available but is not a substitute for a missing plan.

Ascend entries also preserve `compiler_actors` with actual `function`,
`actor_kind` and the same `late_llvm:<module_sha256>:<function>` compiler identity
as the execution mapping. These are compiler declarations, not runtime actor
slots. The older nullable `actor` label is retained for compatibility; it is
often null because actual artifacts supply actor declarations instead of one
actor label. Never equate an AIV label with a fixed runtime slot. Read the raw
capture's actor/manifest association before using a module-local site ID.

The NVIDIA nested plan uses its own `schema_version: 2` (the outer envelope
remains version 1), actual `proton.automatic_candidates` and
`proton.automatic_selected` counts, `max_sites`, `policy`, `semantics`,
`compiler_stage` and `inventory`. Each inventory entry has `candidate_ordinal`
(integer), `operation` (string), `location` (structured actual MLIR location),
`selected` (boolean), `candidate_class` (string), `selection_reason` (string),
`selected_scope_name` (string or null), and `scope_id` (integer or null).
Applicable source statements also retain `source_statement`. Selected scope IDs
are resolved using actual compiler scope allocation by name, not copied from
the candidate ordinal. `selected_origins` retains the corresponding source
region evidence. Older captures with count-only plans remain readable, but do
not provide a full candidate inventory.

An inventory ordinal is not necessarily the eventual recording site ID. Use the
actual compiler scope/site mapping for the binary. An unselected candidate means
it was outside this plan's observation coverage, not that it did not execute.
Selection occurs in multiple stages: compile-time inserted sites, device record
publication predicates, and output filters have different costs. Read the
recorded stage/policy instead of treating an output filter as reduced collection.

## `ai/observations.json` and backend loss evidence

This original typed-observation document has `schema_version: 1`, `observations`
(array of producer records), and `captures` (array of backend objects). It does
not have the reconstruction's `groups` envelope. Source/binary verification is
performed during reconstruction; use `fine_grained.json` for the normalized,
verified view. Original observations preserve producer fields such as
`compiler_site`, `original_record` and raw occurrence ordinals where applicable.

`capture_evidence` in the plan and `captures` in the normalized view retain this
same capture evidence. Accounting is protocol-specific:

| Backend | Evidence path within each capture | Units and interpretation |
| --- | --- | --- |
| NVIDIA | `decoded.losses[]` and `decoded.unpaired_records`; aggregate `decoded.dropped_records` | Each loss row has `program`, `sm`, `warp`, `written_records`, `retained_records`, `dropped_records`, `capacity_records`. These count primitive entry/exit records, not reconstructed intervals. `written = retained + dropped`; unmatched retained entry/exit records remain explicit. |
| Ascend | `actors[]`, aggregate `dropped`, `counter_saturated`, `capture_status`, `decode_error` | Per-actor `attempted`, `committed`, `dropped` count dynamic records, with `attempted = committed + dropped`. `state: "no_records"` carries `execution_status: "unknown"`; it does not prove that actor did not execute. Decode failure is not zero loss. |
| Enflame | `header`, `record_layout`, `runtime_metadata`, `counter_saturated`, `capture_status`, `decode_error` and original event ordinals | For `selected_dynamic_timeline_v1`, `header.reserved0` counts attempts before temporal sampling; `header.write_idx` counts sampled publication attempts. Retained records are `min(write_idx, capacity)`; `overflow_count = max(0, write_idx - capacity)`. `flags & 1` denotes overflow; `flags & 16` denotes saturation. `reserved0 - write_idx` describes sampling omissions, not overflow. Legacy snapshot layouts do not provide a dynamic visit history. |

Missing counters are unknown, not zero. Do not add counts from different units or
protocols. Retained visits, sampled instances, unselected sites, overflow, invalid
publication and capture failure are separate conditions. Raw bytes/encoding and
digests remain available in capture objects or referenced `raw/` artifacts.

The following small examples show the exact nesting and literal key names used
by a reader. They are projections: raw bytes, additional metadata and additional
inventory entries are omitted for readability. They are not replacement capture
files or evidence of an actual run.

NVIDIA plan entry and matching original capture:

```json
{
  "binary_id": "compiler-cache-hash",
  "capture_id": "capture-a",
  "plan": {
    "schema_version": 2,
    "proton.automatic_candidates": 2,
    "proton.automatic_selected": 1,
    "max_sites": 1,
    "inventory": [
      {"candidate_ordinal": 0, "operation": "tt.load", "location": {"kind": "file_line_column", "file": "/app/kernel.py", "line": 12, "column": 4}, "selected": true, "candidate_class": "source_statement", "selection_reason": "source_statement_priority", "selected_scope_name": "auto/0/tt.load", "scope_id": 0},
      {"candidate_ordinal": 1, "operation": "arith.addf", "location": {"kind": "file_line_column", "file": "/app/kernel.py", "line": 13, "column": 4}, "selected": false, "candidate_class": "internal_operation", "selection_reason": "site_budget_excluded", "selected_scope_name": null, "scope_id": null}
    ]
  }
}
```

```json
{
  "capture_id": "capture-a",
  "invocation_id": "launch-1",
  "binary_id": "compiler-cache-hash",
  "decoded": {
    "losses": [{"program": 0, "sm": 0, "warp": 0, "written_records": 2, "retained_records": 2, "dropped_records": 0, "capacity_records": 256}],
    "unpaired_records": [],
    "dropped_records": 0
  }
}
```

Ascend plan entries contain the operation plan directly as `plan`; they do not
contain another `plan.operation_plan` wrapper. Actor counters are directly in
each element of `captures[].actors`:

```json
{
  "binary_id": "compiler-cache-hash",
  "compile_id": "compile-a",
  "module_sha256": "actual-module-digest",
  "plan": {
    "candidate_count": 1,
    "selected_count": 1,
    "max_sites": 8,
    "policy": "source_location_class_per_original_block_evenly_spaced",
    "inventory": [{"site_id": 6, "operation": "mul", "compiler_opcode": "mul", "source_file": "/app/kernel.py", "line": 12, "column": 4, "selected": true, "selection_reason": "source_location_class_evenly_spaced"}]
  }
}
```

```json
{
  "capture_id": "capture-a",
  "capture_status": "decoded",
  "decode_error": null,
  "record_layout": "ascend_actor_dynamic_v1",
  "counter_saturated": false,
  "actors": [{"actor_slot": 1, "state": "complete", "attempted": 2, "committed": 2, "dropped": 0}],
  "dropped": 0
}
```

Enflame capture `record_layout` is a string. `header.capacity` is an integer
record capacity; `capture_id` is the capture identity. The automatic plan is
found in `plans[].plan`, bound to `binary_id`:

```json
{
  "binary_id": "compiler-cache-hash",
  "plan": {
    "schema_version": 1,
    "candidate_count": 1,
    "max_sites": 8,
    "policy": "bounded_class_round_robin",
    "selected_sites": [3],
    "inventory": [{"opId": 3, "mlirOpName": "arith.addf", "sourceLoc": "loc(\"/app/kernel.py\":12:4)", "automatic_eligible": true, "exclusion_reason": null, "selected": true, "selection_reason": "bounded_class_round_robin"}]
  }
}
```

```json
{
  "capture_id": "capture-a",
  "capture_status": "decoded",
  "decode_error": null,
  "record_layout": "selected_dynamic_timeline_v1",
  "counter_saturated": false,
  "runtime_metadata": {"profiler_invocation_id": "launch-1"},
  "header": {"write_idx": 2, "capacity": 256, "overflow_count": 0, "flags": 0, "record_size": 64, "payload_offset": 16416, "reserved0": 2, "reserved1": 0}
}
```

## Binary, launch and source identities

`ai/launches.json` and `ai/binaries.json` are top-level JSON arrays, not wrapped
objects. A launch has string `id` (for example `launch-1`), `binary_id`, numeric
`scope_id`, `name`, `grid` and `argument_id`. Join the normalized record's
`invocation_id` to the launch's `id`, and its `binary_id` to the binary's `id`.
Names are labels, not join evidence.

For a compiler-linked binary, `identity` is `compiler_cache_hash` and `id` is the
actual `CompiledKernel.hash`. `binary_sha256` separately hashes the actual binary
bytes; it is not the compiler cache hash. Different instrumented configurations
can produce different cache identities. A baseline uninstrumented hash is not
expected to equal its instrumented specialization's hash.

The binary's `source` object contains `path` (capture-machine path), `line`,
`sha256` (JIT function text digest), `file_sha256` (full captured source file
digest), `text_file` and `file_snapshot_file` (bundle-relative exported paths).
Verify each digest against its corresponding file; function text and full file
are different byte sequences. Null source fields mean unavailable. A source
file snapshot describes what was read during capture, not every external Python
dependency or a separately compiled caller. For example:

```json
{
  "id": "compiler-cache-hash",
  "identity": "compiler_cache_hash",
  "binary_sha256": "actual-device-binary-digest",
  "source": {
    "path": "/app/kernel.py",
    "line": 9,
    "sha256": "jit-text-digest",
    "file_sha256": "whole-file-digest",
    "text_file": "ai/sources/jit-text-digest.py",
    "file_snapshot_file": "ai/sources/whole-file-digest.py"
  }
}
```

`compiler_artifact_files` maps actual stages such as `ttir`, `ttgir`, `llir` or
`ptx` to objects with `file`, `sha256`, `bytes` and `basis`. These are captured
compiled artifacts. A source location identifies the original absolute source
path, while the source snapshot is found using the binary record above; a
consumer must not try to open that original path on a different machine.

New binary records also carry `source_snapshots`: capture-time snapshots of
other files explicitly referenced by structured compiler positions or frontend
source locations (for example, imported JIT helpers). A captured entry has
`file`, `status: "captured"`, `sha256`, `snapshot_file`, `capture_boundary` and
`compiled_text_alignment`; unavailable entries preserve their reason instead.
Bytes are acquired at binary registration, not by reopening paths while viewing
or exporting. Export verifies the digest and deduplicates by bytes. CRLF and
declared Python file encodings are preserved. Only exact compiler file identities
or explicit directory/relative-file combinations create source anchors; no
neighboring or basename search is performed.

## `ai/source_index.json` and report navigation

The source index has `schema_version: 1`, `sources`, `diagnostics` and `limits`.
Each source has an `id` derived from binary/path/digest/kind, `binary_id`, `file`,
`sha256`, bundle-relative `snapshot_file`, `line_count`, `capture_basis`,
`compiled_text_alignment` and `observed_lines`. `kind` is `file_snapshot` or
`jit_function_text`. The latter has relative lines and is never used to guess a
file-line offset. `observed_lines` maps line numbers to retained record counts
for this binary/source, deduplicating repeated candidates of one record. These
are neither complete execution counts nor iteration counts. Different bytes
for the same binary/path remain separate and make file anchors ambiguous.

`report/sources.html` embeds captured text, offers binary/source selection and
line anchors, and links observed lines back to the exact binary and line filter
in `report/fine_grained.html`. All source text is rendered as text, not markup.
`report/execution.html` shows measured identity groups separately from complete,
expandable static compiler mapping tables. Its retained-count groups include
invocation/program/actor/semantic/clock and association status. It introduces no
static-to-dynamic actor joins, clock conversion, cross-actor ordering or inferred
busy timeline. Original mapping evidence stays in `ai/execution.json`.

Automatic capture with internal records but no valid snapshot position is
incomplete with reason `internal_records_lack_valid_source_snapshot_positions`;
the action points to source candidates and index diagnostics. This differs from
a selected program producing no internal records. Both retain original data.

## `ai/export_timing.json`

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | `1` |
| `clock`, `unit` | string | `host.monotonic`, `seconds` |
| `phases` | object of nonnegative finite numbers | Nonoverlapping measured host phases |
| `export_wall_s` | number or null | Sum of phases only when the complete finalize/export path was measured |
| `complete_finalize_and_export` | boolean | Whether that complete path was measured |
| `scope` | string | Actual measured boundary |
| `excludes` | array of strings | Includes application execution and final timing receipt persistence |
| `meaning` | string | Interpretation reminder |

API receipts use `session_finalize_and_bundle_export_s` and scope
`finalize_call_all_selected_sessions`. CLI receipts use `collector_finalize_s`
and `bundle_materialization_s`, with scope `collector_finalize_then_bundle_export`.
A standalone legacy materialization can be incomplete with `export_wall_s: null`.
These are host engineering costs, not kernel latency or GPU instrumentation
overhead. Successful supervised automatic CLI captures additionally retain
`ai/deadlines.json` with the enforced limits and worker launch count. Timeout and
cancellation artifacts are failures, not complete timing receipts.

## Read-only inspection

This uses exported files only and can run without GPU libraries. It checks the
envelope and prints verified source-linked internal records; it is not a complete
mathematical, loss or identity verifier:

```python
import json
from pathlib import Path

bundle = Path("profile-run")
records = json.loads((bundle / "ai/fine_grained.json").read_text())
assert records["schema_version"] == 1
for row in records["records"]:
    if (row["association_status"] == "verified" and row["source_locations"]
            and row["operation"] and row["semantic"] != "native_lifecycle"):
        print(row["invocation_id"], row["binary_id"], row["program"],
              row["actor"], row["site"], row["operation"],
              row["source_locations"], row["occurrence"], row["clock"])
timing = json.loads((bundle / "ai/export_timing.json").read_text())
assert timing["schema_version"] == 1
print("Complete export cost:", timing["complete_finalize_and_export"],
      timing["export_wall_s"])
```

`manifest.json` covers exported files with byte lengths and SHA-256 digests,
including timing and successful CLI deadline receipts. A checker should verify
these against the actual bytes rather than trusting receipt presence alone.
Its `files` is an object mapping bundle-relative paths to objects with integer
`bytes` and string `sha256`, not an array. Other manifest metadata may be present:

```json
{
  "files": {
    "ai/export_timing.json": {"bytes": 512, "sha256": "digest-of-exact-file-bytes"},
    "ai/deadlines.json": {"bytes": 320, "sha256": "digest-of-exact-file-bytes"}
  }
}
```

The supervised automatic CLI's deadline receipt has these exact fields:

```json
{
  "schema_version": 1,
  "enforced": true,
  "limits_seconds": {"startup": 120, "compile": 120, "export": 60},
  "supervisor_worker_launches": 1,
  "application_runtime_limit": null,
  "mechanism": "separate_worker_phase_watchdog"
}
```

`supervisor_worker_launches` counts worker processes started by this supervisor;
it alone does not prove the number of device kernel executions. Use the ordinary
application's independent side-effect/launch checks for no-hidden-replay evidence.
The compile/export values reflect the explicitly selected limits; application
runtime remains unbounded. Timeout/cancellation returns a failed invocation and
retains a diagnostic directory instead of a successful deadline receipt.
