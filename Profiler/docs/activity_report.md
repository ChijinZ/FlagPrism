# Detailed activity reports

The report pipeline is backend independent. Each collector translates SDK records into
normalized `activity.*` fields in `.vendor.json` associations. Analysis and HTML rendering
consume this contract without selecting a backend. Enflame is the first hardware-validated
producer; other backend names in unit tests exercise the contract, not hardware support.

```bash
python3 Profiler/python/flagtree_profiler/report.py profile.vendor.json --out profile-report
python3 Profiler/python/flagtree_profiler/report.py profile.vendor.json \
    --baseline baseline.vendor.json --out profile-comparison
```

After installation, `flagtree-profiler-report` provides the same CLI. Direct script execution
requires only the Python standard library; no accelerator or native FlagTree module is needed.
Outputs are self-contained `index.html`, analyzed `report.json`, and Perfetto `trace.json`.
The UI includes searchable activity lanes, zoom, correlated event details, hotspot sorting,
P50/P95/P99, effective transfer throughput, observed allocation history, and baseline comparison.

## Collector contract (version 1)

The existing vendor artifact envelope remains unchanged: `backend` identifies the producer;
`associations` holds records; `degrade_reasons` explains capture limitations. Each association
retains `source`, `state`, `note`, `runtime_event`, and `metrics`. The report only analyzes
`collected` records with valid timestamps. Producers must distinguish real captured timestamps
from synthetic or estimated timing before setting that state.

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

Fields are optional unless required above. API/device correlation requires a nonzero correlation
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
