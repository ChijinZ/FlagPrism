# Evidence in this capture

Observed kernel events: **30** (30 timed, 0 untimed).
Kernel events linked to launch / arguments / binary / source snapshot: **30 / 30 / 30 / 30**, out of 30.
Inventory: 30 launch records, 1 argument sets, 1 binaries, 2 source snapshots.

Start with [kernel groups](kernels.json) and [evidence coverage](summary.json). Untimed events and unassociated launch records remain in their referenced files; empty timed groups do not mean all evidence is absent. Links do not imply complete metadata. Check the links before using a source file as evidence of the executed kernel.

**Observed evidence:** kernel source links and effective compiler metadata come from captured launches. [Context](context.json) sections.hardware.device contains collector device properties.
**Caller declarations:** context.supplied contains user-provided workload, source paths and validation outcomes. They are not independently verified and do not establish the executed implementation. The profiler does not diagnose contradictions between these descriptions.

# FlagPrism machine-readable capture

Schema version 2: unknown observations are null, never zero. events.jsonl includes
both timed and untimed observations; timing_status determines timing eligibility.
Untimed records do not contribute duration/percentiles/coverage or timeline events.
counts includes all observations; timed_counts and untimed_counts distinguish them.
Incomplete identities never prove correlation or identical workloads. Partial kernel
groups are event-local and must not be matched across independent captures.

Read summary.json first, then context.json and kernels.json. Use kernel event_ids
to retrieve events.jsonl records; launch_id links to launches.json and binary_id
to binaries.json (source file links/hashes, actual compiler metadata).
launch.argument_id indexes arguments.json. Kernel groups include representative
launch IDs and short tensor input summaries, so full event scans are unnecessary.
Source text is deduplicated under ai/sources/. Tensor arguments contain
shape/dtype/stride/device, never contents. Read counters.json
only if manifest availability says it is available. manifest.json lists available files and data gaps.
Package file links are relative to the capture directory; original source.path
is an informational absolute path on the capture machine. No diagnosis is generated. call_tree.json preserves additive scope metrics;
legacy summed IDs/configuration/timestamps are omitted, not measurements.

Event IDs are original capture record indices; original records are retained
in events.jsonl or rejected.jsonl. Kernel
IDs identify groups by device/context, name, grid/block, and binary/argument
identity when available. Unknown identity remains unknown; identical grid/block
does not prove identical work. Do not mix group distributions by kernel name. Each kernel lists its event IDs; launch parameters
and vendor-specific metrics remain on those events. Counter group IDs are local
to this capture and do not imply a link to an event or kernel statistical group.

Timestamps ending in _ns are integer nanoseconds in the collector clock domain;
_us values are microseconds. origin_ns is the reference for relative event times.
Preserve JSON integer precision. Missing values mean unknown, never zero.
Availability is unknown unless the producer explicitly reports a reason such as
unsupported, not_enabled or failed. Empty event sets do not prove inactivity.

Kernel durations are instrumented measurements. Percentiles use linear interpolation
between ordered samples; small-sample tails are descriptive, not confidence bounds. Summed durations may overlap;
coverage is not hardware utilization. Memory allocation observations are not total
VRAM usage. Effective transfer GB/s is not measured HBM bandwidth. API durations
may nest. Counter units, sources, descriptions, scopes and instance statistics
are retained verbatim. Aggregate counters must not be joined by kernel name to
individual launches. Replay can run the application multiple times; consult
context.json capture metadata. No per-launch timing is inferred from aggregates.

Context fields are producer/user supplied, not inferred from the report host.
events.jsonl preserves original accepted records; rejected.jsonl preserves all
records excluded from analysis. Producer metadata is retained in context.json.


## Direct evidence lookup

Kernel groups expose scalar_arguments, compiler_metadata, source and direct full-data
references. Previews have a 128-item / 8 KiB values budget; partial means some values
were omitted, not absent from the capture. Unknown previews use values=null; a known
empty set uses {}. Scalar argument names do not establish their semantic/tuning role.
input_summary contains tensor arguments, possibly including outputs and scratch.

From the capture root, run this standard-library snippet:
```python
import json
from pathlib import Path
p = Path(".")
groups = json.loads((p / "ai/kernels.json").read_text())["groups"]
if not groups:
    raise SystemExit("No timed kernel groups; inspect summary, untimed events or aggregates.")
g = max(groups, key=lambda item: item["total_us"])
print({key: g.get(key) for key in ("name", "count", "measurement", "source",
       "scalar_arguments", "compiler_metadata", "argument_id", "binary_id")})
if g["argument_id"] is not None:
    print(json.loads((p / g["arguments_file"]).read_text())[g["argument_id"]])
if g["binaries_file"] is not None:
    print(next(b for b in json.loads((p / g["binaries_file"]).read_text())
               if b["id"] == g["binary_id"]))
```

Before editing, inspect source.path: the executed implementation may be a backend
override, not the library's generic ops file. Read the captured source, then follow
its imports/decorators/configuration logic in the actual checkout. Source snapshots
do not promise to include every dependency. After editing, use a new output directory
and inspect actual parameters/compiler options and binary_sha256. Equal binary bytes
do not prove inputs, dispatch or host behavior stayed the same; different bytes alone
do not establish a speedup or its cause. Correctness and timing need separate evidence.

IDs for events/launches/groups are capture-local. Argument descriptors omit tensor
contents. To compare runs, inspect caller operator/parameters, tensor shapes/dtypes/
strides, relevant scalar semantics, hardware/software and measurement policy. PID,
stream/context ordinals and a changed compiler hash are not workload identity tests.
Matching descriptors alone do not establish equivalent work. comparison() is not a
general cross-process workload matcher.

count means timed activity observations, not independent trials or caller iterations.
measurement.sources preserves producer labels; interval timing is not automatically
hardware-clock timing. Single-observation percentiles cannot estimate variability.
Work may be repeated within one capture; the profiler never requires a second run.
Host wall benchmarks include launch/synchronization overhead and need separate labels.

## Optional caller metadata

Use this object with start(metadata=...), finalize(metadata=...) or CLI --metadata.
Fill only facts you actually know; null is unknown. Submit passed/failed only after
performing a correctness check. Finalize replaces matching top-level sections, so
submit the full workload object when adding validation. The caller's object is
snapshotted; subsequent mutations do not alter stored context. Tuples become arrays.
Structural issues are retained in context.metadata_issues; recommended missing facts
are separately listed in metadata_missing_fields. They do not invalidate the capture.
Non-JSON start/CLI inputs are rejected before collection; invalid finalize updates
are rejected after saving the capture, with the previous valid metadata retained.
```json
{
  "workload": {
    "operator": null,
    "parameters": {},
    "warmup": {
      "iterations": null
    },
    "measurement": {
      "iterations": null,
      "scope": null,
      "synchronization": null
    },
    "validation": {
      "status": "not_checked",
      "reference": null,
      "atol": null,
      "rtol": null
    }
  }
}
```
