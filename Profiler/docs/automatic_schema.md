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
| `source_locations` | array of objects | Each location has `file` (string), `line` (positive integer), `column` (integer) |
| `operation` | string or null | Actual compiler operation or called primitive |
| `association_status` | string | `verified` or `unassociated` in this reconstructed view |
| `source_status` | string | `located` or `unresolved` |
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

## `ai/observation_plan.json`

The envelope contains `schema_version: 1`, `plans` (array), `capture_evidence`
(array), and `limits` (array of strings). Each entry in `plans` contains
`binary_id` (string or null) and `plan` (object). Applicable entries also include
`capture_id`, `compile_id`, `actor`, `module_sha256`, or `selected_origins`.
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
