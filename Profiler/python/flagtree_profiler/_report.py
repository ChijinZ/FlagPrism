"""Offline accelerator activity analysis. Run directly with Python; no device or native module needed."""

import hashlib
import uuid
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from ._metadata import snapshot as metadata_snapshot, diagnose as diagnose_metadata, TEMPLATE


def union_ns(intervals):
    end = None
    total = 0
    for start, stop in sorted(intervals):
        total += max(0, stop - max(start, end if end is not None else start))
        end = max(stop, end if end is not None else stop)
    return total


def percentile(values, fraction):
    values = sorted(values)
    at = (len(values) - 1) * fraction
    low = int(at)
    return values[low] + (values[min(low + 1,
                                     len(values) - 1)] - values[low]) * (at -
                                                                         low)


def validate_counters(groups):
    """Counter aggregates are separate from timed events; never infer a join."""
    if not isinstance(groups, list):
        raise ValueError("counter_groups must be a list")

    def numeric(value):
        return type(value) in (int, float) and math.isfinite(value)

    for group in groups:
        if not isinstance(group, dict) or not all(
                isinstance(group.get(k), str)
                for k in ("name", "scope", "source")):
            raise ValueError(
                "Counter groups require name, scope and source strings")
        if not isinstance(group.get("metrics"), list):
            raise ValueError("Counter groups require a metrics list")
        for metric in group["metrics"]:
            if not isinstance(metric, dict) or not all(
                    isinstance(metric.get(k), str) for k in ("name", "unit")):
                raise ValueError("Counters require name and unit strings")
            if metric.get("value") is not None and not numeric(
                    metric["value"]):
                raise ValueError(
                    "Counter values must be finite numbers or null (unavailable)"
                )
            if not isinstance(metric.get("instances", []), list):
                raise ValueError("Counter instances must be a list")
            for instance in metric.get("instances", []):
                if not isinstance(instance, dict) or not isinstance(
                        instance.get("instance"), str) or not all(
                            numeric(instance.get(k))
                            for k in ("minimum", "maximum", "mean", "count")):
                    raise ValueError("Invalid counter instance statistics")
    return groups


def _normalize_event(row, index):
    """Optional observations never gate the record; null is explicitly unknown."""
    raw = row["runtime_event"]
    metrics = dict(row.get("metrics", {}))
    issues = {}
    # C++ envelopes use integer storage. Producers may explicitly mark fields
    # unavailable without changing their SDK/runtime event structures.
    unavailable = metrics.get("activity.unknown_fields", "")
    unavailable = {
        field.strip()
        for field in unavailable.split(",") if field.strip()
    } if isinstance(unavailable, str) else set()

    def integer(name, value, minimum=0):
        if name in unavailable or "activity." + name in unavailable or value is None:
            issues[name] = "not_reported"
            return None
        if type(value) is not int or value < minimum:
            issues[name] = "legacy_unknown" if type(
                value) is int and value == 0 and minimum == 1 else "invalid"
            return None
        return value

    kind = metrics["activity.kind"]
    host = kind in ("runtime", "driver")
    identities = {
        key:
        integer(key, raw.get(key),
                1 if key in ("correlation_id", "scope_id", "task_id") else 0)
        for key in ("device_id", "stream_id", "correlation_id", "scope_id",
                    "task_id")
    }
    if host:
        # Legacy host API envelopes have dummy device/stream zeros. Only an
        # explicit activity identity can attribute a host call to a device.
        for key in ("device_id", "stream_id"):
            identities[key] = integer(key, metrics.get("activity." + key))
            metrics["activity." + key] = identities[key]
    for key in ("process_id", "thread_id", "context_id"):
        identities[key] = integer(key, metrics.get("activity." + key))
        metrics["activity." + key] = identities[key]
    for key in ("bytes", "api_success", "allocation_bytes", "address",
                "completed_ns"):
        value = integer(key, metrics.get("activity." + key),
                        1 if key == "completed_ns" else 0)
        if key == "api_success" and value not in (None, 0, 1):
            value = None
            issues[key] = "invalid"
        metrics["activity." + key] = value
    for prefix in ("grid", "block"):
        for axis in "xyz":
            key = f"{prefix}_{axis}"
            metrics["activity." + key] = integer(
                key, metrics.get("activity." + key), 1)
    domain = metrics.get("activity.correlation_domain", "default")
    if "activity.correlation_domain" in unavailable or not isinstance(
            domain, str) or not domain:
        domain = None
    start = integer("start_time_ns", raw.get("start_time_ns"), 1)
    end = integer("end_time_ns", raw.get("end_time_ns"), 1)
    timed = start is not None and end is not None and end >= start
    if start is not None and end is not None and end < start:
        issues["timestamps"] = "end_before_start"
    name = raw.get("op_name")
    if "op_name" in unavailable or not isinstance(name, str) or not name:
        name = None
        issues["name"] = "not_reported"
    if kind == "memcpy":
        name = f"memcpy {metrics.get('activity.copy_direction') or 'unknown'}"
    lane = (
        f"{kind} PID {identities['process_id']} / TID {identities['thread_id']}"
        if host else
        f"PID {identities['process_id']} / Device {identities['device_id']} / Context {identities['context_id']} / Stream {identities['stream_id']}"
    )
    lane = lane.replace("None", "unknown")
    lane_keys = ("process_id",
                 "thread_id") if host else ("process_id", "device_id",
                                            "context_id", "stream_id")
    if any(identities[key] is None for key in lane_keys):
        lane += f" / record {index}"  # Unknown streams/threads are not one queue.
    correlation = identities["correlation_id"]
    process = identities["process_id"]
    return dict(
        id=index,
        kind=kind,
        name=name,
        **identities,
        device=None if host else identities["device_id"],
        correlation_key=json.dumps([process, domain, correlation])
        if process is not None and domain is not None
        and correlation is not None else None,
        correlation_domain=domain,
        start_ns=start,
        end_ns=end,
        duration_us=(end - start) / 1000 if timed else None,
        start_us=None,
        end_us=None,
        timing_status="available" if timed else
        "invalid" if issues.get("timestamps") == "end_before_start" or any(
            issues.get(key) == "invalid"
            for key in ("start_time_ns", "end_time_ns")) else "unknown",
        field_issues=issues,
        lane=lane,
        metrics=metrics,
        source=row.get("source"))


def analyze(path):

    def finite_number(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(
                "Non-finite JSON numbers must be encoded as strings")
        return number

    document = path if isinstance(path, dict) else json.loads(
        Path(path).read_text(),
        parse_float=finite_number,
        parse_constant=finite_number)
    if not isinstance(document, dict):
        raise ValueError("Activity artifact must be a JSON object")
    backend = document.get("backend")
    if not isinstance(backend, str) or not backend:
        raise ValueError("Activity artifacts must identify their backend")
    counter_groups = validate_counters(document.get("counter_groups", []))
    capture = document.get("capture", {})
    summaries = document.get("kernel_summaries", [])
    if not isinstance(capture, dict) or not isinstance(summaries, list):
        raise ValueError("Invalid capture metadata or kernel_summaries")
    for summary in summaries:
        if not isinstance(summary, dict) or not isinstance(
                summary.get("name"), str) or any(
                    type(summary.get(k)) not in (int, float)
                    or not math.isfinite(summary[k]) or summary[k] < 0
                    for k in ("count", "total_us", "mean_us", "min_us",
                              "max_us")):
            raise ValueError("Invalid kernel timing summary")
    rows = document.get("associations", [])
    if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("metrics", {}), dict) for row in rows):
        raise ValueError(
            "associations must be a list of records with metric objects")
    if rows and not any("activity.kind" in row.get("metrics", {})
                        for row in rows):
        raise ValueError(
            "Artifact has no normalized activity.kind fields; update the backend collector"
        )
    events, untimed_events = [], []
    rejected = Counter()
    for index, row in enumerate(rows):
        kind = row.get("metrics", {}).get("activity.kind")
        if kind not in ("kernel", "runtime", "driver", "memcpy", "memset"):
            rejected["missing or unsupported activity.kind"] += 1
            continue
        if row.get("state") != "collected":
            rejected[row.get("note") or row.get("state", "missing state")] += 1
            continue
        if not isinstance(row.get("runtime_event"), dict):
            rejected["invalid runtime event"] += 1
            continue
        event = _normalize_event(row, index)
        (events if event["timing_status"] == "available" else
         untimed_events).append(event)
    events.sort(key=lambda e: (e["start_ns"], e["id"]))
    origin = min((e["start_ns"] for e in events), default=None)
    for event in events:
        event["start_us"] = (event["start_ns"] - origin) / 1000
        event["end_us"] = (event["end_ns"] - origin) / 1000
    launch_candidates = defaultdict(list)
    for launch in document.get("launches", []):
        scope = launch.get("scope_id")
        if type(scope) is int and scope > 0:
            launch_candidates[scope].append(launch)
    launches = {
        scope: entries[0]
        for scope, entries in launch_candidates.items() if len(entries) == 1
    }
    groups = defaultdict(list)
    for event in events + untimed_events:
        configuration = None
        if event["kind"] == "kernel":
            launch = launches.get(event["scope_id"])
            if launch and launch["name"] == event["name"]:
                event["launch_id"] = launch["id"]
                event["binary_id"] = launch["binary_id"]
                event["argument_signature"] = hashlib.sha256(
                    json.dumps(launch["arguments"],
                               sort_keys=True).encode()).hexdigest()
            metrics = event["metrics"]
            configuration = {
                "process": event["process_id"],
                "device": event["device"],
                "context": metrics.get("activity.context_id"),
                "grid":
                [metrics.get(f"activity.grid_{axis}") for axis in "xyz"],
                "block":
                [metrics.get(f"activity.block_{axis}") for axis in "xyz"],
                "binary_id": event.get("binary_id"),
                "argument_signature": event.get("argument_signature")
            }
        if event["timing_status"] != "available":
            continue
        if configuration and any(
                value is None
                for value in (event["name"], configuration["process"],
                              configuration["device"],
                              configuration["context"], *configuration["grid"],
                              *configuration["block"])):
            configuration["unknown_identity_record"] = event["id"]
        key = (event["kind"], event["name"],
               json.dumps(configuration, sort_keys=True))
        groups[key].append(event)
    hotspots = []
    for (kind, name, config_json), rows in groups.items():
        times = [r["duration_us"] for r in rows]
        byte_count = (sum(r["metrics"]["activity.bytes"] for r in rows) if all(
            r["metrics"].get("activity.bytes") is not None
            for r in rows) else None)
        configuration = json.loads(config_json)
        group_id = "group-" + hashlib.sha256(
            json.dumps([kind, name, configuration],
                       sort_keys=True).encode()).hexdigest()[:16]
        for event in rows:
            event["group_id"] = group_id
        hotspots.append(
            dict(
                kind=kind,
                name=name,
                id=group_id,
                configuration=configuration,
                grouping_status="partial"
                if configuration and "unknown_identity_record" in configuration
                else "observed_configuration",
                configuration_label=
                (f"grid={configuration['grid']} block={configuration['block']} "
                 f"binary={str(configuration['binary_id'])[:12]}"
                 if configuration else "—").replace("None", "unknown"),
                measurement=dict(
                    sample_unit="timed_event",
                    scope="producer_reported_interval",
                    duration_calculation="(end_ns - start_ns) / 1000",
                    sources=[
                        dict(source=source, count=count)
                        for source, count in Counter(
                            r["source"] for r in rows).items()
                    ],
                    sample_note="single_observation"
                    if len(rows) == 1 else None),
                count=len(rows),
                total_us=sum(times),
                mean_us=sum(times) / len(times),
                p50_us=percentile(times, .5),
                p95_us=percentile(times, .95),
                p99_us=percentile(times, .99),
                max_us=max(times),
                effective_gbps=(byte_count / (sum(times) * 1000)
                                if kind in ("memcpy", "memset") and sum(times)
                                and byte_count is not None else None),
                bytes=byte_count))
    hotspots.sort(key=lambda r: -r["total_us"])
    devices = []
    for process, device in sorted({
        (e["process_id"], e["device"])
            for e in events
            if e["device"] is not None and e["process_id"] is not None
    }):
        rows = [
            e for e in events
            if (e["process_id"], e["device"]) == (process, device)
        ]
        first = min(r["start_ns"] for r in rows)
        last = max(r["end_ns"] for r in rows)
        span = last - first
        covered = union_ns([(r["start_ns"], r["end_ns"]) for r in rows])
        kernel = union_ns([(r["start_ns"], r["end_ns"]) for r in rows
                           if r["kind"] == "kernel"])
        devices.append(
            dict(device=device,
                 process_id=process,
                 window_us=span / 1000,
                 activity_covered_us=covered / 1000,
                 kernel_covered_us=kernel / 1000,
                 uncovered_us=(span - covered) / 1000,
                 activity_coverage=covered / span if span else None))
    # This is a lower bound on observed allocations, never total device usage.
    live = {}
    current = Counter()
    peak = Counter()
    memory = []
    unmatched_frees = 0
    invalid_memory_events = 0
    unknown_memory_events = 0
    for event in sorted(events, key=lambda e: (e["end_ns"], e["id"])):
        m = event["metrics"]
        if event["kind"] != "runtime" or "activity.memory_action" not in m:
            continue
        action = m["activity.memory_action"]
        if (event["process_id"] is None
                or m.get("activity.api_success") is None
                or (m.get("activity.memory_space") == "device"
                    and event["context_id"] is None)):
            unknown_memory_events += 1
            continue
        if (action not in ("allocate", "free")
                or m.get("activity.memory_space") not in ("host", "device")
                or type(m.get("activity.address")) is not int
                or m["activity.address"] < 0
                or m.get("activity.api_success") != 1
                or (action == "allocate" and
                    (type(m.get("activity.allocation_bytes")) is not int
                     or m["activity.allocation_bytes"] < 0))):
            invalid_memory_events += 1
            continue
        if m["activity.address"] == 0:
            continue  # Successful free(NULL) does not represent a live allocation.
        space = m["activity.memory_space"]
        key = (event["process_id"],
               event["context_id"] if space == "device" else None,
               event["device_id"] if space == "device" else None, space,
               m["activity.address"])
        if m["activity.memory_action"] == "allocate":
            current[space] -= live.get(key, 0)
            live[key] = m["activity.allocation_bytes"]
            current[space] += live[key]
        elif key in live:
            current[space] -= live.pop(key)
        else:
            unmatched_frees += 1
        peak[space] = max(peak[space], current[space])
        memory.append(
            dict(time_us=event["end_us"], space=space, bytes=current[space]))
    api_errors = [
        e for e in events + untimed_events if e["kind"] in
        ("runtime", "driver") and e["metrics"].get("activity.api_success") == 0
    ]
    return dict(
        schema_version=2,
        source="capture",
        backend=backend,
        launches=document.get("launches", []),
        binaries=document.get("binaries", []),
        counter_groups=counter_groups,
        capture=capture,
        kernel_summaries=summaries,
        sampling=dict(sample_unit="timed_event",
                      timed_kernel_observations=sum(e["kind"] == "kernel"
                                                    for e in events),
                      untimed_kernel_observations=sum(e["kind"] == "kernel"
                                                      for e in untimed_events),
                      single_sample_kernel_groups=sum(
                          g["kind"] == "kernel" and g["count"] == 1
                          for g in hotspots)),
        origin_ns=origin,
        events=events,
        untimed_events=untimed_events,
        hotspots=hotspots,
        devices=devices,
        memory=memory,
        counts=dict(Counter(e["kind"] for e in events + untimed_events)),
        timed_counts=dict(Counter(e["kind"] for e in events)),
        untimed_counts=dict(Counter(e["kind"] for e in untimed_events)),
        api_error_count=len(api_errors),
        api_unknown_status_count=sum(
            e["kind"] in ("runtime", "driver")
            and e["metrics"].get("activity.api_success") is None
            for e in events + untimed_events),
        rejected=dict(rejected),
        degrade_reasons=document.get("degrade_reasons", []),
        capture_notes=document.get("capture_notes", []),
        observed_peak_bytes=dict(peak),
        unmatched_frees=unmatched_frees,
        invalid_memory_events=invalid_memory_events,
        unknown_memory_events=unknown_memory_events,
        limitations=[
            "Coverage describes the first-to-last captured device event window, not full operator latency or hardware utilization.",
            "Observed allocation bytes exclude allocations before capture and caching allocator tensor lifetimes.",
            "Missing activity categories or fields mean unreported data, not zero hardware activity.",
            "Effective transfer GB/s uses recorded bytes divided by summed activity duration, not measured HBM bandwidth.",
            "Runtime and driver API durations may nest; do not add them to device elapsed time.",
            "Synchronization and allocator API timings are available only when called during capture."
        ])


def comparison(current, baseline):
    old = {
        (r["kind"], r["name"], r.get("id")): r
        for r in baseline["hotspots"] if r.get("grouping_status") != "partial"
    }
    new = {
        (r["kind"], r["name"], r.get("id")): r
        for r in current["hotspots"] if r.get("grouping_status") != "partial"
    }
    rows = []
    for key in sorted(old.keys() | new.keys(),
                      key=lambda item: tuple(""
                                             if value is None else str(value)
                                             for value in item)):
        a, b = old.get(key), new.get(key)
        delta = b["mean_us"] - a["mean_us"] if a and b else None
        rows.append(
            dict(kind=key[0],
                 name=key[1],
                 baseline_count=a["count"] if a else 0,
                 current_count=b["count"] if b else 0,
                 delta_mean_us=delta,
                 delta_percent=100 * delta /
                 a["mean_us"] if delta is not None and a["mean_us"] else None))
    return rows


def chrome_trace(report):
    if not report["events"] and report.get("native_trace"):
        return report["native_trace"]
    lanes = {
        lane: i
        for i, lane in enumerate(sorted({e["lane"]
                                         for e in report["events"]}))
    }
    trace = [{
        "ph": "M",
        "pid": 1,
        "tid": tid,
        "name": "thread_name",
        "args": {
            "name": name
        }
    } for name, tid in lanes.items()]
    for event in report["events"]:
        trace.append(
            dict(ph="X",
                 pid=1,
                 tid=lanes[event["lane"]],
                 name=event["name"],
                 cat=event["kind"],
                 ts=event["start_us"],
                 dur=event["duration_us"],
                 args=dict(event["metrics"],
                           correlation_id=event["correlation_id"],
                           scope_id=event["scope_id"])))
    # Link actual correlated API/device records; never infer a link by name.
    candidates = defaultdict(list)
    for event in report["events"]:
        if event["kind"] in ("runtime", "driver") and event["correlation_key"]:
            candidates[event["correlation_key"]].append(event)
    apis = {}
    for key, entries in candidates.items():
        preferred = [e for e in entries if e["kind"] == "runtime"] or entries
        if len(preferred) == 1:
            apis[key] = preferred[0]
    for event in report["events"]:
        api = apis.get(event["correlation_key"])
        if event["kind"] not in (
                "kernel", "memcpy", "memset"
        ) or api is None or api["start_us"] > event["start_us"]:
            continue
        for phase, endpoint in (("s", api), ("f", event)):
            trace.append(
                dict(ph=phase,
                     pid=1,
                     tid=lanes[endpoint["lane"]],
                     ts=endpoint["start_us"],
                     id=event["id"],
                     name="API → device",
                     cat="correlation",
                     **({
                         "bp": "e"
                     } if phase == "f" else {})))
    for space in sorted({p["space"] for p in report["memory"]}):
        for point in report["memory"]:
            if point["space"] == space:
                trace.append(
                    dict(ph="C",
                         pid=1,
                         tid=0,
                         ts=point["time_us"],
                         name=f"Observed {space} allocations",
                         args={"bytes": point["bytes"]}))
    return {"traceEvents": trace, "displayTimeUnit": "ms"}


def render(report):
    # Prevent a recorded kernel/API name from escaping the embedded JSON script.
    def safe_numbers(value):
        if isinstance(value, dict):
            return {key: safe_numbers(item) for key, item in value.items()}
        if isinstance(value, list):
            return [safe_numbers(item) for item in value]
        if isinstance(value, int) and abs(value) > 2**53 - 1:
            return str(value)
        return value

    data = json.dumps(safe_numbers(report), ensure_ascii=True).replace(
        "<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    # Keep exact integer literals in downloadable JSON; the UI uses safe strings.
    # Embedded exports also work when opening a standalone HTML via file://.
    exports = json.dumps(
        {
            "report.json": json.dumps(report),
            "timeline.json": json.dumps(chrome_trace(report))
        },
        ensure_ascii=True)
    exports = exports.replace("<", "\\u003c").replace(">", "\\u003e").replace(
        "&", "\\u0026")
    before, after = HTML.split("__DATA__", 1)
    return before + data + after.replace("__EXPORTS__", exports, 1)


AI_README = """# FlagPrism machine-readable capture

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
"""

AI_README += """

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
""" + json.dumps(TEMPLATE, indent=2) + "\n```\n"


def _preview(values, omitted=0):
    if values is None:
        return dict(status="unknown", values=None, omitted_count=None)
    result = {}
    for name, value in sorted(values.items()):
        candidate = {**result, name: value}
        if len(candidate) > 128 or len(
                json.dumps(candidate,
                           ensure_ascii=False,
                           separators=(",", ":"),
                           allow_nan=False).encode()) > 8192:
            omitted += 1
        else:
            result[name] = value
    return dict(status="partial" if omitted else "complete",
                values=result,
                omitted_count=omitted)


def evidence_overview(report, launches, binaries):
    """Count captured records and explicit links, never infer missing execution."""
    events = [
        e for e in report["events"] + report["untimed_events"]
        if e["kind"] == "kernel"
    ]
    launch_map = {row["id"]: row for row in launches}
    binary_map = {row["id"]: row for row in binaries}
    linked = dict(launch=0, arguments=0, binary=0, source_snapshot=0)
    for event in events:
        launch = launch_map.get(event.get("launch_id"))
        if launch is None:
            continue
        linked["launch"] += 1
        linked["arguments"] += launch.get("argument_id") is not None
        binary = binary_map.get(launch.get("binary_id"))
        if binary is not None:
            linked["binary"] += 1
            source = binary.get("source") or {}
            linked["source_snapshot"] += bool(
                source.get("text_file") or source.get("file_snapshot_file"))
    snapshots = {
        row["source"][key]
        for row in binaries
        for key in ("text_file", "file_snapshot_file")
        if (row.get("source") or {}).get(key)
    }
    return dict(
        source="captured_records_and_explicit_links",
        semantics=
        "Counts describe this capture, not executed workload completeness. Zero observed records do not establish inactivity or unsupported hardware. Links count kernel events, not unique launches; a link does not imply that every metadata field is known.",
        kernel_events=dict(total=len(events),
                           timed=report["timed_counts"].get("kernel", 0),
                           untimed=report["untimed_counts"].get("kernel", 0)),
        linked_kernel_events=linked,
        inventory=dict(launch_records=len(launches),
                       argument_sets=len(
                           {row["argument_id"]
                            for row in launches}),
                       binaries=len(binaries),
                       source_snapshots=len(snapshots)),
        files=dict(kernels="ai/kernels.json",
                   events="ai/events.jsonl"
                   if report["events"] or report["untimed_events"] else None,
                   launches="ai/launches.json" if launches else None,
                   arguments="ai/arguments.json" if launches else None,
                   binaries="ai/binaries.json" if binaries else None,
                   context="ai/context.json"))


def evidence_readme(overview):
    kernels, linked, inventory = (overview[key]
                                  for key in ("kernel_events",
                                              "linked_kernel_events",
                                              "inventory"))
    return (
        "# Evidence in this capture\n\n"
        f"Observed kernel events: **{kernels['total']}** ({kernels['timed']} timed, {kernels['untimed']} untimed).\n"
        f"Kernel events linked to launch / arguments / binary / source snapshot: "
        f"**{linked['launch']} / {linked['arguments']} / {linked['binary']} / {linked['source_snapshot']}**, out of {kernels['total']}.\n"
        f"Inventory: {inventory['launch_records']} launch records, {inventory['argument_sets']} argument sets, "
        f"{inventory['binaries']} binaries, {inventory['source_snapshots']} source snapshots.\n\n"
        +
        ("No kernel activity records were observed. Runtime/copy events can still be present; "
         "this does not identify the cause or establish that no kernel executed.\n\n"
         if not kernels['total'] else "") +
        "Start with [kernel groups](kernels.json) and [evidence coverage](summary.json). "
        "Untimed events and unassociated launch records remain in their referenced files; empty timed groups do not mean all evidence is absent. "
        "Links do not imply complete metadata. Check the links before using a source file as evidence of the executed kernel.\n\n"
        "**Observed evidence:** kernel source links and effective compiler metadata come from captured launches. "
        "[Context](context.json) sections.hardware.device contains collector device properties.\n"
        "**Caller declarations:** context.supplied contains user-provided workload, source paths and validation outcomes. "
        "They are not independently verified and do not establish the executed implementation. "
        "The profiler does not diagnose contradictions between these descriptions.\n\n"
    )


def write_bundle(report, source, output, context=None, *, complete=True):
    """Export one normalized capture for humans and machines without recapture."""
    output = Path(output)
    document = source if isinstance(source, dict) else json.loads(
        Path(source).read_text())
    supplied = document.get("context", {}) if context is None else context
    supplied = metadata_snapshot(supplied)
    diagnostics = diagnose_metadata(supplied)
    for name in ("manifest.json", "ai", "report"):
        if (output / name).exists():
            raise ValueError(
                f"Output already contains {name}; use a new directory")
    for name in ("ai", "report"):
        (output / name).mkdir(parents=True, exist_ok=True)
    report = dict(report,
                  source="capture",
                  metadata_issues=diagnostics["metadata_issues"],
                  metadata_rejections=document.get("metadata_rejections", []))
    supplied_workload = supplied.get("workload")
    policy = supplied_workload.get("measurement") if isinstance(
        supplied_workload, dict) else None
    report["supplied_measurement"] = dict(
        source="caller", value=policy if isinstance(policy, dict) else None)

    def write(name, value):
        (output /
         name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

    availability = {}
    for name, present in (("events",
                           bool(report["events"] or report["untimed_events"])),
                          ("counters",
                           any(
                               metric.get("value") is not None or any(
                                   instance.get("count", 0) > 0
                                   for instance in metric.get("instances", []))
                               for group in report["counter_groups"]
                               for metric in group["metrics"]))):
        declared = document.get("availability", {}).get(name)
        availability[name] = (
            dict(status="available", reason=None)
            if present else dict(declared) if isinstance(declared, dict) else
            dict(status="unknown", reason="No usable records were reported"))
    availability["producer"] = document.get("availability", {})
    device = document.get("session_metadata", {}).get("device", {})
    hardware = {
        "status": "partial" if device else "unknown",
        "device": device,
        "source": "collector_device_properties",
        "semantics": {
            "clock_rate":
            "static device clock property in kHz, not a frequency measured during capture",
            "memory_clock_rate":
            "static device clock property in kHz, not a frequency measured during capture",
            "bus_width":
            "static global memory bus width in bits",
            "num_sms":
            "backend-defined processor count; not comparable across architectures"
        }
    }
    sections = {
        "hardware": hardware,
        "software": document.get("software", {"status": "unknown"}),
        "workload": {
            "status":
            "partial" if report["launches"] else "unknown",
            "launches_file":
            "ai/launches.json" if report["launches"] else None,
            "missing": [
                "high_level_operator_semantics",
                "warmup_and_measurement_policy", "correctness_result"
            ]
        },
        "compilation": {
            "status": "available" if report["binaries"] else "unknown",
            "binaries_file": "ai/binaries.json" if report["binaries"] else None
        }
    }
    context_data = dict(
        backend=report["backend"],
        capture=report["capture"],
        supplied=supplied,
        **diagnostics,
        rejected_metadata_updates=document.get("metadata_rejections", []),
        sections=sections,
        producer_metadata={
            key: value
            for key, value in document.items()
            if key not in ("associations", "counter_groups",
                           "kernel_summaries", "context", "capture",
                           "launches", "binaries")
        },
        missing_sections=[
            key for key, value in sections.items()
            if value["status"] == "unknown" and key not in supplied
        ])
    workload = supplied.get("workload", {})
    if isinstance(workload, dict):
        sections["workload"]["missing"] = [
            label for label, present in (
                ("high_level_operator_semantics",
                 bool(
                     isinstance(workload.get("operator"), str)
                     and workload["operator"].strip()
                     and isinstance(workload.get("parameters"), dict))),
                ("warmup_and_measurement_policy",
                 isinstance(workload.get("warmup"), dict)
                 and isinstance(workload.get("measurement"), dict)),
                ("correctness_result",
                 isinstance(workload.get("validation"), dict) and
                 workload["validation"].get("status") in ("passed", "failed")))
            if not present
        ]
    for key in supplied:
        if key in sections:
            sections[key]["supplied"] = supplied[key]
            if sections[key]["status"] == "unknown":
                sections[key]["status"] = "partial"
    context_data["partial_sections"] = [
        key for key, value in sections.items() if value["status"] == "partial"
    ]
    write("ai/context.json", context_data)
    launch_lookup = {row["id"]: row for row in report["launches"]}
    argument_sets = {}
    exported_launches = []
    for launch in report["launches"]:
        arguments = launch["arguments"]
        argument_id = hashlib.sha256(
            json.dumps(arguments, sort_keys=True).encode()).hexdigest()
        argument_sets[argument_id] = arguments
        exported_launches.append({
            **{
                key: value
                for key, value in launch.items() if key != "arguments"
            }, "argument_id": argument_id
        })
    if exported_launches:
        write("ai/launches.json", exported_launches)
        write("ai/arguments.json", argument_sets)
    binaries = []
    if report["binaries"]:
        for binary in report["binaries"]:
            entry = dict(binary)
            source = dict(binary.get("source", {}))
            for key in ("text", "file_snapshot"):
                content = source.pop(key, None)
                if content is not None:
                    name = "ai/sources/" + hashlib.sha256(
                        content.encode()).hexdigest() + ".py"
                    (output / "ai/sources").mkdir(exist_ok=True)
                    (output / name).write_text(content)
                    source[key + "_file"] = name
            source[
                "line_semantics"] = "Capture-machine decorated function definition start, not necessarily the def line"
            entry["source"] = source
            binaries.append(entry)
        write("ai/binaries.json", binaries)
    kernels = []
    for row in report["hotspots"]:
        if row["kind"] == "kernel":
            kernels.append(
                dict(
                    row,
                    grouping="device_context_name_grid_block_binary_arguments",
                    event_ids=[
                        event["id"] for event in report["events"]
                        if event["kind"] == "kernel"
                        and event["group_id"] == row["id"]
                    ]))
    event_lookup = {row["id"]: row for row in report["events"]}
    binary_lookup = {row["id"]: row for row in binaries}
    exported_launch_lookup = {row["id"]: row for row in exported_launches}
    for group in kernels:
        launch_id = next((event_lookup[event_id].get("launch_id")
                          for event_id in group["event_ids"]
                          if event_lookup[event_id].get("launch_id")), None)
        group["representative_launch_id"] = launch_id
        launch = launch_lookup.get(launch_id, {})
        group["input_summary"] = {
            key: value
            for key, value in launch.get("arguments", {}).items()
            if value.get("kind") == "tensor"
        }
        binary = binary_lookup.get(launch.get("binary_id"), {})
        source = binary.get("source")
        scalars = {
            name: value.get("value")
            for name, value in launch.get("arguments", {}).items()
            if value.get("kind") == "scalar_or_metadata"
            and type(value.get("value")) in (type(None), bool, int, float, str)
        }
        omitted = sum(
            value.get("kind") != "tensor"
            for value in launch.get("arguments", {}).values()) - len(scalars)
        group.update(
            argument_id=exported_launch_lookup.get(launch_id,
                                                   {}).get("argument_id"),
            arguments_file="ai/arguments.json" if launch else None,
            binary_id=launch.get("binary_id"),
            binaries_file="ai/binaries.json" if binary else None,
            source={
                key: source.get(key)
                for key in ("path", "line", "sha256", "file_sha256",
                            "text_file", "file_snapshot_file")
            } if source else None,
            scalar_arguments=_preview(scalars if launch else None, omitted),
            compiler_metadata=_preview(binary.get("compiler_metadata")),
            identity_scope=
            "capture_local; descriptors do not include tensor contents and do not establish cross-run workload equivalence"
        )
        group[
            "identity_limits"] = "Groups use available identities; missing binary/arguments cannot prove identical work."
    write(
        "ai/kernels.json",
        dict(groups=kernels,
             instrumented_aggregate_summaries=report["kernel_summaries"]))
    summary = {
        key: report[key]
        for key in ("origin_ns", "counts", "timed_counts", "untimed_counts",
                    "hotspots", "devices", "api_error_count",
                    "api_unknown_status_count", "rejected", "degrade_reasons",
                    "capture_notes", "observed_peak_bytes", "memory",
                    "unmatched_frees", "invalid_memory_events",
                    "unknown_memory_events", "sampling", "limitations")
    }
    summary.update(context_file="ai/context.json",
                   kernels_file="ai/kernels.json",
                   metadata_issue_count=len(diagnostics["metadata_issues"]),
                   rejected_metadata_update_count=len(
                       document.get("metadata_rejections", [])),
                   partial_context_sections=context_data["partial_sections"],
                   missing_context_sections=context_data["missing_sections"],
                   availability=availability,
                   kernel_ids=[row["id"] for row in kernels],
                   counter_group_ids=[
                       f"counter-{i}"
                       for i in range(len(report["counter_groups"]))
                   ])
    overview = evidence_overview(report, exported_launches, binaries)
    summary["evidence_overview"] = overview
    report["evidence_overview"] = overview
    report["observed_device"] = device or None
    report["caller_context"] = supplied
    write("ai/summary.json", summary)
    if report["events"] or report["untimed_events"]:
        with (output / "ai/events.jsonl").open("w") as stream:
            for event in report["events"] + report["untimed_events"]:
                stream.write(
                    json.dumps(dict(event,
                                    original_record=document["associations"][
                                        event["id"]]),
                               allow_nan=False) + "\n")
    accepted = {
        event["id"]
        for event in report["events"] + report["untimed_events"]
    }
    rejected = [(i, row)
                for i, row in enumerate(document.get("associations", []))
                if i not in accepted]
    if rejected:
        with (output / "ai/rejected.jsonl").open("w") as stream:
            for index, row in rejected:
                stream.write(
                    json.dumps(dict(id=index, original_record=row),
                               allow_nan=False) + "\n")
    if report["counter_groups"]:
        write("ai/counters.json", [
            dict(group, id=f"counter-{index}")
            for index, group in enumerate(report["counter_groups"])
        ])
    (output / "ai/README.md").write_text(evidence_readme(overview) + AI_README)
    write("report/report.json", report)
    if report["events"] or report.get("native_trace"):
        write("report/timeline.json", chrome_trace(report))
    (output / "report/index.html").write_text(render(report))
    if complete:
        write_manifest(output, report)


def write_manifest(output, report):
    output = Path(output)
    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[path.relative_to(output).as_posix()] = dict(
                bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    availability = json.loads(
        (output / "ai/summary.json").read_text())["availability"]
    manifest = dict(schema_version=2,
                    capture_id=str(uuid.uuid4()),
                    files=files,
                    availability=availability)
    (output /
     "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlagPrism · Activity profile</title>
<style>
:root{color-scheme:dark;font:14px/1.5 system-ui,sans-serif;background:#0b1220;color:#e4ecf7;--muted:#99abc2;--line:#2a3850;--accent:#71e4d3}

*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0}
main{max-width:1560px;margin:auto;padding:32px}

header{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:26px}
.brand{display:flex;gap:14px;align-items:center}
.mark{display:grid;place-items:center;width:44px;height:44px;border:1px solid #438378;border-radius:12px;color:var(--accent);font-size:24px;font-weight:750;background:#163331}
h1{font-size:25px;letter-spacing:-.6px;margin:0}
h2{font-size:17px;margin:0 0 6px}
h3{font-size:14px;margin:0 0 12px}
.muted,.caption{color:var(--muted)}
.caption{font-size:12px;margin:0 0 16px}
.pill{border:1px solid var(--line);border-radius:20px;padding:5px 12px;color:var(--accent)}

.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:18px}
.card{padding:18px 20px;border:1px solid var(--line);border-radius:12px;background:linear-gradient(135deg,#18273b,#111c2c);color:var(--muted);font-size:12px}
.card strong{display:block;color:#edf6ff;font-size:27px;letter-spacing:-.6px;margin-bottom:3px}
.card small{display:block;margin-top:8px}

.panel{background:#121d2d;border:1px solid var(--line);border-radius:12px;padding:20px;margin:18px 0}
.panel-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:16px 0}
.toolbar label{display:flex;align-items:center;gap:8px;max-width:100%;min-width:0}select{min-width:0;max-width:100%}#counterGroup{width:min(620px,65vw)}#counters .timeline-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}#counterSummary table{min-width:650px}#counterInstances table{min-width:470px}#kernelSummaryTable table{min-width:600px}@media(max-width:1100px){#counters .timeline-grid{grid-template-columns:1fr}}
.toolbar input{width:230px}
.spacer{flex:1}

button,input,select{font:inherit;background:#1a293e;color:inherit;border:1px solid #42536c;border-radius:7px;padding:7px 10px}
button{cursor:pointer}
button:hover{background:#294059}
button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;margin:12px 0}
.timeline-grid{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:18px;align-items:start}
#timeline{overflow:auto;max-height:390px;border:1px solid var(--line);border-radius:8px}
canvas{display:block;background:#0d1726;max-width:100%}
#canvas{max-width:none;width:auto;min-width:100%;cursor:crosshair}
#memory{width:100%}
.inspector{background:#0d1726;border:1px solid var(--line);border-radius:8px;padding:16px;min-width:0;max-height:360px;overflow:auto}
.inspector select{width:100%;margin-bottom:14px}
.inspector h3{overflow-wrap:anywhere;color:var(--accent)}
dl{margin:0;display:grid;grid-template-columns:85px minmax(0,1fr);gap:8px}
dt{font-size:11px;color:var(--muted);margin:0}
dd{margin:0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
pre{font-size:11px;max-height:240px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}
details{color:var(--muted)}
summary{cursor:pointer}
#quality p{margin:8px 0;font-size:12px}
.quality{padding:12px 16px;border:1px solid var(--line);border-radius:9px;background:#101a29}
.warn{color:#ffc477}

.scroll{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:12px}
td,th{padding:11px 12px;text-align:right;border-bottom:1px solid #253449;white-space:nowrap;font-variant-numeric:tabular-nums}
td:first-child,th:first-child{text-align:left}
td:first-child{min-width:90px;max-width:320px;white-space:normal;overflow-wrap:anywhere}
#hotspots td:first-child{min-width:240px}
th{position:sticky;top:0;background:#1b2a40;color:var(--muted);font-weight:500}
th button{border:0;padding:0;background:transparent;font-size:inherit;color:inherit}
tbody tr:hover{background:#1b2c43}
tbody tr:last-child td{border-bottom:0}
#hotspots table{min-width:1050px}
#devices table{min-width:600px}
.empty{padding:24px;color:var(--muted);text-align:center}
.bottom-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.bottom-grid .panel{min-width:0;margin-top:0}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
footer{display:flex;gap:20px;flex-wrap:wrap;padding:8px 0 20px;font-size:12px}
#source{max-width:620px;overflow-wrap:anywhere}
#range{font-size:12px;margin:8px 0}

@media(max-width:1100px){.timeline-grid{grid-template-columns:1fr}
.bottom-grid{grid-template-columns:1fr}
.cards{grid-template-columns:repeat(2,minmax(0,1fr))}
}

@media(max-width:600px){main{padding:16px}
.panel{padding:14px}
header{align-items:flex-start}
.card{padding:14px}
.card strong{font-size:22px}
.toolbar input{width:170px}
.spacer{display:none}
}

</style></head><body><main>
<header><div class="brand"><div class="mark" aria-hidden="true">F</div><div><h1>FlagPrism</h1><div class="muted">Single-capture activity report</div></div></div><span class="pill" id="backend"></span></header>
<div id="cards" class="cards"></div>
<section class="panel" id="evidencePanel" hidden><h2>Evidence in this capture</h2><p id="evidenceCounts"></p><p id="evidenceLinks"></p><p id="evidenceInventory" class="caption"></p><p id="evidenceAbsence" class="warn" hidden>No kernel activity records were observed. Runtime/copy events may still be present; this does not identify the cause or establish that no kernel executed.</p><p class="caption">Link counts describe captured kernel events, not workload completeness. Unassociated launch records and untimed activity remain available in the bundle.</p><div class="bottom-grid"><div><h3>Observed evidence</h3><p class="caption">Kernel source and compiler settings come from captured launches. Device properties below come from the collector.</p><details><summary>Collector device properties</summary><pre id="observedDevice"></pre></details><a href="../ai/kernels.json">Kernel groups and source references ↗</a></div><div><h3>Caller declarations · not verified</h3><p class="caption">Workload descriptions, source paths and validation outcomes supplied by the caller do not establish the executed implementation.</p><details><summary>Supplied context</summary><pre id="callerContext"></pre></details><a href="../ai/context.json">Full context and provenance ↗</a></div></div></section>
<details class="quality" id="qualityBox"><summary id="qualitySummary">Capture quality & interpretation</summary><div id="quality"></div></details>
<section class="panel" id="counters" hidden><h2>Hardware counter observations</h2><p class="caption">Tool-reported aggregates. Scope and sample counts are preserved; these values are not joined to timeline events.</p><div class="toolbar"><label>Kernel group <select id="counterGroup"></select></label><label>Metric <select id="counterMetric"></select></label></div><p class="caption" id="counterScope"></p><div class="scroll" id="counterSummary"></div><p id="counterDescription" class="caption"></p><div class="timeline-grid"><div id="counterBars" class="scroll" style="padding:14px"></div><div id="counterInstances" class="scroll"></div></div></section>
<section class="panel" id="kernelSummaries" hidden><h2>Kernel timing summaries</h2><p class="caption">Tool-reported aggregates; invocation counts may include replays. No per-launch timing or percentile distribution is inferred.</p><div class="scroll" id="kernelSummaryTable"></div></section>
<section class="panel" id="activityPanel"><div class="panel-head"><h2>Activity timeline</h2><span class="caption">Select an event to inspect · double-click to focus</span></div>
<p id="samplingNote"></p><p id="samplingScope"></p>
<div class="toolbar"><label>Search <input id="search" type="search" placeholder="Kernel or API name"></label><label>Category <select id="kind"><option value="">All categories</option><option>kernel</option><option>memcpy</option><option>memset</option><option>runtime</option><option>driver</option></select></label><span class="spacer"></span><button id="zoomIn" aria-label="Zoom in">+</button><button id="zoomOut" aria-label="Zoom out">−</button><button id="left" aria-label="Pan left">←</button><button id="right" aria-label="Pan right">→</button><button id="reset">Reset</button></div>
<div class="legend" id="legend"></div><div id="range" class="muted"></div>
<div class="timeline-grid"><div id="timeline"><canvas id="canvas" aria-label="Activity timeline; use the event selector for keyboard access"></canvas></div><aside class="inspector"><label for="eventSelect" class="caption">INSPECT EVENT</label><select id="eventSelect"></select><div id="detail" class="muted">Select an event to view its timing and launch details.</div><details><summary>Raw record & correlated events</summary><pre id="rawDetail">No event selected.</pre></details></aside></div></section>
<section class="panel" id="hotspotPanel"><div class="panel-head"><h2>Hotspots</h2><span class="caption">Whole capture · matching filters · sort by column</span></div><p class="caption">CPU API time can overlap device execution. Totals are sums of event durations, not elapsed time.</p><div class="scroll" id="hotspots"></div></section>
<div class="bottom-grid"><section class="panel"><h2>Device activity coverage</h2><p class="caption">Interval union within each device's captured window. Not hardware utilization.</p><div id="devices" class="scroll"></div></section>
<section class="panel"><h2>Observed allocations</h2><p class="caption">Successful captured allocations only; excludes pre-capture memory and tensor lifetimes.</p><canvas id="memory" height="180"></canvas><div class="legend"><span style="color:#65d2c5">● Device</span><span style="color:#edbc71">● Host</span></div></section></div>
<div id="compare"></div><footer><a href="timeline.json" download>Export Perfetto trace ↗</a><a href="report.json" download>Download analysis JSON ↗</a><span class="muted" id="source"></span></footer>
<script id="data" type="application/json">__DATA__</script>
<script id="exports" type="application/json">__EXPORTS__</script><script>
'use strict';
const r = JSON.parse(document.getElementById('data').textContent),
  $ = id => document.getElementById(id),
  colors = {
    kernel: '#65d2c5',
    memcpy: '#edbc71',
    memset: '#c599f5',
    runtime: '#72adf3',
    driver: '#a7b5ce'
  };
const exports = JSON.parse(document.getElementById('exports').textContent);
for (const link of document.querySelectorAll('a[download]')) {
  const name = link.getAttribute('href');
  link.onclick = event => {
    event.preventDefault();
    const url = URL.createObjectURL(new Blob([exports[name]], {
      type: 'application/json'
    }));
    const download = document.createElement('a');
    download.href = url;
    download.download = name;
    document.body.append(download);
    download.click();
    download.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
}
$('backend').textContent = r.backend;
$('source').textContent = 'Source: ' + r.source.split(/[\\/]/).pop();
const fmt = x => typeof x === 'number' ? (Number.isInteger(x) ? x.toLocaleString() : x.toLocaleString(undefined, {
  maximumFractionDigits: 3
})) : (x ?? '—');

function el(tag, text) {
  const e = document.createElement(tag);
  e.textContent = text;
  return e
}

function table(id, rows, cols) {
  rows = [...rows]; // Sorting a view must not reorder metric selector identities.
  const t = document.createElement('table'),
    head = document.createElement('tr');
  let reverse = false;
  for (const [key, title] of cols) {
    let th = el('th', '');
    const sortButton = el('button', title);
    th.append(sortButton);
    sortButton.onclick = () => {
      reverse = !reverse;
      rows.sort((a, b) => {
        let x = a[key],
          y = b[key];
        if (x == null) return y == null ? 0 : 1;
        if (y == null) return -1;
        return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * (reverse ? -1 : 1)
      });
      body()
    };
    head.append(th)
  }
  t.append(head);
  const b = document.createElement('tbody');
  t.append(b);

  function body() {
    b.replaceChildren();
    for (const row of rows) {
      let tr = document.createElement('tr');
      for (const [key] of cols) tr.append(el('td', fmt(row[key])));
      b.append(tr)
    }
  }
  body();
  $(id).replaceChildren(rows.length ? t : el('div', 'No matching records.'));
  if (!rows.length) $(id).firstChild.className = 'empty'
}
if (r.evidence_overview) {
  const e = r.evidence_overview, k = e.kernel_events, l = e.linked_kernel_events, i = e.inventory;
  $('evidencePanel').hidden = false;
  $('evidenceCounts').textContent = `${k.total} observed kernel events · ${k.timed} timed · ${k.untimed} untimed`;
  $('evidenceLinks').textContent = `Kernel events linked to launch / arguments / binary / source snapshot: ${l.launch} / ${l.arguments} / ${l.binary} / ${l.source_snapshot}, out of ${k.total}`;
  $('evidenceInventory').textContent = `Inventory: ${i.launch_records} launch records · ${i.argument_sets} argument sets · ${i.binaries} binaries · ${i.source_snapshots} source snapshots`;
  $('evidenceAbsence').hidden = k.total !== 0;
  $('observedDevice').textContent = JSON.stringify(r.observed_device ?? null, null, 2);
  $('callerContext').textContent = JSON.stringify(r.caller_context ?? {}, null, 2);
}
$('samplingNote').textContent = `${r.sampling.timed_kernel_observations} timed kernel observations · ${r.sampling.untimed_kernel_observations} untimed · ${r.sampling.single_sample_kernel_groups} groups with one observation. ` + (r.sampling.single_sample_kernel_groups ? 'One recorded interval makes mean/P50/P95/P99 equal that observation; it does not estimate run-to-run variability.' : 'Sample counts do not establish independent repetitions.');
$('samplingScope').textContent = 'Times are producer-reported intervals, not necessarily complete operator latency or hardware-clock measurements. Sources: ' + [...new Set(r.events.map(e => e.source ?? 'unknown'))].join(', ') + '. Caller-declared region: ' + JSON.stringify(r.supplied_measurement?.value ?? null);
const rejectedCount = Object.values(r.rejected).reduce((a, b) => a + b, 0);
const spanUs = r.events.reduce((m, e) => Math.max(m, e.end_us), 0);
const kernelUs = r.events.filter(e => e.kind === 'kernel').reduce((n, e) => n + e.duration_us, 0);
const overview = [
  ['Capture window', r.events.length ? fmt(spanUs / 1000) + ' ms' : 'Not recorded', 'First to last timed event'],
  ['Kernel duration sum', r.timed_counts.kernel ? fmt(kernelUs / 1000) + ' ms' : 'Not recorded', `${r.timed_counts.kernel || 0} timed kernels · may overlap`],
  ['Recorded activities', fmt(r.events.length + r.untimed_events.length), `${r.counter_groups.reduce((n,g)=>n+g.metrics.length,0)} counter metrics · ${r.counts.memcpy || 0} copies`],
  ['API errors / rejected', `${r.api_error_count} / ${rejectedCount}`, `${r.api_unknown_status_count} API results unknown`]
];
const counterOnly = !r.events.length && r.counter_groups.length > 0;
const cards = counterOnly ? [
  ['Kernel groups', fmt(r.counter_groups.length), 'Configuration-level aggregates'],
  ['Counter metrics', fmt(r.counter_groups.reduce((n, g) => n + g.metrics.length, 0)), 'Original units and reported values'],
  ['Instance observations', fmt(r.counter_groups.reduce((n, g) => n + g.metrics.reduce((s, m) => s + (m.instances || []).length, 0), 0)), 'Across metrics; passes may differ'],
  ['Replay policy', r.capture.replay_mode ?? r.capture.external_counters?.replay_mode ?? 'Unknown', 'No per-launch timing inferred']
] : overview;
for (const [name, value, hint] of cards) {
  const card = el('div', name);
  card.className = 'card';
  card.prepend(el('strong', value));
  card.append(el('small', hint));
  $('cards').append(card);
}
$('qualitySummary').textContent = `Capture notes · ${r.events.length} timed records · ${r.untimed_events.length} untimed records · ${rejectedCount} rejected · ${r.degrade_reasons.length} backend notices · ${r.capture_notes.length} capture notes`;
if ((r.metadata_issues || []).length || (r.metadata_rejections || []).length || r.untimed_events.length || rejectedCount || r.api_error_count || r.degrade_reasons.length || r.invalid_memory_events || r.unknown_memory_events) {
  $('qualityBox').open = true;
  $('qualitySummary').className = 'warn';
}
for (const issue of (r.metadata_issues || [])) $('quality').append(el('p', `Metadata ${issue.path}: expected ${issue.expected}; received ${issue.actual_type}. ${issue.hint}`));
for (const rejection of (r.metadata_rejections || [])) $('quality').append(el('p', `Metadata update not applied: ${rejection.reason}`));
for (const event of r.untimed_events) {
  const details = el('details', '');
  details.append(el('summary', `Untimed ${event.kind}: ${event.name ?? 'unknown'} (record ${event.id})`));
  details.append(el('pre', JSON.stringify(event, null, 2)));
  $('quality').append(details);
}
for (const text of [...(counterOnly ? [] : r.limitations), ...r.capture_notes, ...r.degrade_reasons, ...Object.entries(r.rejected).map(([k, v]) => `${k}: ${v}`), `Memory observations skipped for unknown identity/status: ${r.unknown_memory_events}; invalid: ${r.invalid_memory_events}; unmatched frees: ${r.unmatched_frees}; observed peaks: ${JSON.stringify(r.observed_peak_bytes)}`]) $('quality').append(el('p', text));
for (const [k, c] of Object.entries(colors)) {
  let s = el('span', '● ' + k + ' · ' + (r.counts[k] ?? 'not recorded'));
  s.style.color = c;
  $('legend').append(s)
}
let full = r.events.reduce((m, e) => Math.max(m, e.end_us), 1),
  lo = 0,
  hi = full,
  hits = [];

function selected() {
  const q = $('search').value.toLowerCase(),
    k = $('kind').value;
  return r.events.filter(e => (!k || e.kind === k) && (e.name || "unknown").toLowerCase().includes(q))
}

function draw() {
  const events = selected(),
    lanes = [...new Set(events.map(e => e.lane))].sort(),
    c = $('canvas'),
    w = Math.max(600, $('timeline').clientWidth);
  c.width = w;
  c.height = Math.max(70, lanes.length * 30 + 55);
  const g = c.getContext('2d');
  g.font = '11px system-ui';
  hits = [];
  const pad = w < 700 ? 170 : 285,
    scale = (w - pad - 15) / (hi - lo);
  for (let tick = 0; tick <= 4; tick++) {
    const x = pad + (w - pad - 15) * tick / 4;
    g.fillStyle = '#99abc2';
    g.textAlign = tick === 4 ? 'right' : 'left';
    g.fillText(fmt(lo + (hi - lo) * tick / 4) + ' µs', x, 17);
  }
  g.textAlign = 'left';
  if (!events.length) {
    g.fillStyle = '#99abc2';
    g.fillText('No matching activity. Clear the filters to see the capture.', 16, 50);
  }
  lanes.forEach((lane, i) => {
    g.fillStyle = '#adbed3';
    const label = w < 700 ? lane.replace(/PID \d+ \/ /, "").replace(/Context \d+ \/ /, "") : lane;
    g.fillText(label, 8, i * 30 + 53, pad - 16);
    g.strokeStyle = '#26384e';
    g.beginPath();
    g.moveTo(pad, i * 30 + 60);
    g.lineTo(w, i * 30 + 60);
    g.stroke()
  });
  for (const e of events) {
    if (e.end_us < lo || e.start_us > hi) continue;
    let x = pad + (Math.max(lo, e.start_us) - lo) * scale,
      y = lanes.indexOf(e.lane) * 30 + 37,
      bw = Math.max(2, (Math.min(hi, e.end_us) - Math.max(lo, e.start_us)) * scale);
    g.fillStyle = colors[e.kind] || '#888';
    g.fillRect(x, y, bw, 17);
    hits.push({
      x,
      y,
      w: bw,
      e
    })
  }
  const visible = events.filter(e => e.end_us >= lo && e.start_us <= hi);
  const selector = $('eventSelect'),
    previous = selector.value;
  selector.replaceChildren(el('option', visible.length ? 'Select a visible event…' : 'No visible events'));
  selector.firstChild.value = '';
  for (const e of visible.slice(0, 500)) {
    const option = el('option', `${fmt(e.start_us)} µs · ${e.name}`);
    option.value = String(e.id);
    selector.append(option);
  }
  if (visible.length > 500) {
    const option = el('option', 'First 500 shown — narrow filters or zoom');
    option.disabled = true;
    selector.append(option);
  }
  if (visible.some(e => String(e.id) === previous)) selector.value = previous;
  else {
    $('detail').textContent = 'Select an event to view its timing and launch details.';
    $('rawDetail').textContent = 'No event selected.';
  }
  $('range').textContent = `${fmt(lo)} – ${fmt(hi)} µs since first captured event · ${events.length} matching events`;
  table('hotspots', r.hotspots.filter(e => (!$('kind').value || e.kind === $('kind').value) && (e.name || "unknown").toLowerCase().includes($('search').value.toLowerCase())), [
    ['name', 'Name'],
    ['kind', 'Category'],
    ['configuration_label', 'Launch configuration'],
    ['count', 'Timed observations'],
    ['total_us', 'Total µs'],
    ['mean_us', 'Mean µs'],
    ['p50_us', 'P50 µs'],
    ['p95_us', 'P95 µs'],
    ['p99_us', 'P99 µs'],
    ['max_us', 'Max µs'],
    ['bytes', 'Transfer bytes'],
    ['effective_gbps', 'Effective GB/s']
  ])
}

function pick(ev) {
  let rect = $('canvas').getBoundingClientRect(),
    x = (ev.clientX - rect.left) * $('canvas').width / rect.width,
    y = (ev.clientY - rect.top) * $('canvas').height / rect.height;
  return hits.findLast(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + 17)?.e
}

function inspect(e) {
  if (!e) return;
  $('eventSelect').value = String(e.id);
  const related = r.events.filter(x => e.correlation_key !== null && x.correlation_key === e.correlation_key);
  const detail = $('detail');
  detail.replaceChildren(el('h3', e.name));
  const fields = [
    ['Category', e.kind],
    ['Duration', fmt(e.duration_us) + ' µs'],
    ['Start', fmt(e.start_us) + ' µs'],
    ['Lane', e.lane],
    ['Correlation ID', e.correlation_id],
    ['Scope', e.metrics['activity.scope_name'] ?? e.scope_id]
  ];
  for (const key of ['grid', 'block']) {
    const values = ['x', 'y', 'z'].map(axis => e.metrics[`activity.${key}_${axis}`]);
    if (values.every(v => v != null)) fields.push([key === 'grid' ? 'Grid' : 'Block', values.join(' × ')]);
  }
  if (e.metrics['activity.bytes'] != null) fields.push(['Transfer bytes', fmt(e.metrics['activity.bytes'])]);
  const list = document.createElement('dl');
  for (const [label, value] of fields) {
    list.append(el('dt', label), el('dd', fmt(value)));
  }
  detail.append(list);
  $('rawDetail').textContent = JSON.stringify({
    event: e,
    correlated_events: related.map(x => ({
      kind: x.kind,
      name: x.name,
      start_us: x.start_us,
      duration_us: x.duration_us
    }))
  }, null, 2);
}
$('eventSelect').onchange = () => inspect(r.events.find(e => String(e.id) === $('eventSelect').value));
$('canvas').onclick = ev => inspect(pick(ev));
$('canvas').ondblclick = ev => {
  let e = pick(ev);
  if (e) {
    lo = e.start_us;
    hi = Math.max(lo + 1, e.end_us);
    draw()
  }
};

function zoom(f) {
  let mid = (lo + hi) / 2,
    span = Math.min(full, Math.max(0.001, (hi - lo) * f));
  lo = Math.max(0, Math.min(full - span, mid - span / 2));
  hi = lo + span;
  draw()
}
$('zoomIn').onclick = () => zoom(.5);
$('zoomOut').onclick = () => zoom(2);
$('reset').onclick = () => {
  lo = 0;
  hi = full;
  draw()
};
for (const [id, d] of [
    ['left', -1],
    ['right', 1]
  ]) $(id).onclick = () => {
  let span = hi - lo;
  lo = Math.max(0, Math.min(full - span, lo + d * span * .4));
  hi = lo + span;
  draw()
};
$('search').oninput = draw;
$('kind').onchange = draw;
window.onresize = () => {
  draw();
  drawMemory();
};
table('devices', r.devices, [
  ['process_id', 'Process'],
  ['device', 'Device'],
  ['window_us', 'Window µs'],
  ['activity_covered_us', 'Activity union µs'],
  ['kernel_covered_us', 'Kernel union µs'],
  ['uncovered_us', 'Uncovered µs'],
  ['activity_coverage', 'Coverage fraction']
]);

function drawMemory() {
  const canvas = $('memory'),
    width = Math.max(280, canvas.parentElement.clientWidth - 40);
  canvas.width = width;
  const g = canvas.getContext('2d'),
    peak = r.memory.reduce((m, p) => Math.max(m, p.bytes), 1);
  g.font = '11px system-ui';
  g.fillStyle = '#99abc2';
  if (!r.memory.length) {
    g.fillText('No allocation lifecycle events recorded', 12, 30);
    return;
  }
  g.fillText(`Observed peak ${fmt(peak/1048576)} MiB`, 12, 18);
  g.fillText('0', 12, 158);
  g.textAlign = 'right';
  g.fillText(fmt(full / 1000) + ' ms', width - 12, 176);
  for (const [space, color] of [
      ['device', '#65d2c5'],
      ['host', '#edbc71']
    ]) {
    const points = r.memory.filter(p => p.space === space);
    if (!points.length) continue;
    g.strokeStyle = color;
    g.beginPath();
    let y = 155;
    g.moveTo(35, y);
    for (const p of points) {
      const x = 35 + p.time_us / full * (width - 50);
      g.lineTo(x, y);
      y = 155 - p.bytes / peak * 120;
      g.lineTo(x, y);
    }
    g.lineTo(width - 15, y);
    g.stroke();
  }
}
drawMemory();
if (!r.events.length && !r.native_trace?.traceEvents?.length) {
  document.querySelector('a[href="timeline.json"]').hidden = true;
}
if (r.counter_groups.length) {
  $('counters').hidden = false;
  if (!r.events.length) {
    $('activityPanel').hidden = true;
    $('hotspotPanel').hidden = true;
    document.querySelector('.bottom-grid').hidden = true;
    document.querySelector('a[href="timeline.json"]').hidden = true;
  }
  for (const [i, group] of r.counter_groups.entries()) {
    const option = el('option', group.name);
    option.value = i;
    $('counterGroup').append(option);
  }

  function drawCounter() {
    const group = r.counter_groups[Number($('counterGroup').value)];
    const metric = group.metrics[Number($('counterMetric').value)];
    if (!metric) return;
    $('counterScope').textContent = `Source: ${group.source} · Scope: ${group.scope} · Reported invocations: ${fmt(group.invocations)} · Replay: ${r.capture.external_counters?.replay_mode ?? r.capture.replay_mode ?? 'unknown'}`;
    table('counterSummary', group.metrics, [
      ['name', 'Metric'],
      ['unit', 'Unit'],
      ['value', 'Tool-reported value']
    ]);
    $('counterDescription').textContent = metric.description || 'No metric interpretation supplied by the backend.';
    const instances = metric.instances || [];
    table('counterInstances', [...instances], [
      ['instance', 'Instance'],
      ['minimum', 'Min'],
      ['maximum', 'Max'],
      ['mean', 'Mean'],
      ['count', 'Samples']
    ]);
    const bars = $('counterBars');
    bars.replaceChildren();
    const max = instances.reduce((n, x) => Math.max(n, Number(x.mean)), 0);
    bars.append(el('p', 'Per-instance mean · ' + metric.unit));
    if (!instances.length) bars.append(el('p', 'No per-instance measurements.'));
    for (const sample of instances) {
      const row = el('div', '');
      row.style.cssText = 'display:grid;grid-template-columns:110px 1fr 85px;gap:10px;align-items:center;margin:8px 0;font-size:12px';
      const track = el('div', ''),
        fill = el('div', '');
      track.style.cssText = 'height:9px;background:#24374c;border-radius:3px';
      fill.style.cssText = `height:9px;border-radius:3px;background:#65d2c5;width:${max>0?Math.max(0,Number(sample.mean))/max*100:0}%`;
      track.append(fill);
      row.append(el('span', sample.instance), track, el('span', fmt(sample.mean)));
      bars.append(row);
    }
  }

  function chooseGroup() {
    const group = r.counter_groups[Number($('counterGroup').value)];
    $('counterMetric').replaceChildren();
    for (const [i, metric] of group.metrics.entries()) {
      const option = el('option', metric.name);
      option.value = i;
      $('counterMetric').append(option);
    }
    drawCounter();
  }
  $('counterGroup').onchange = chooseGroup;
  $('counterMetric').onchange = drawCounter;
  chooseGroup();
}
if (r.kernel_summaries.length) {
  $('kernelSummaries').hidden = false;
  table('kernelSummaryTable', r.kernel_summaries, [
    ['name', 'Kernel'],
    ['count', 'Reported calls'],
    ['total_us', 'Total µs'],
    ['mean_us', 'Mean µs'],
    ['min_us', 'Min µs'],
    ['max_us', 'Max µs']
  ]);
}
if (r.comparison) {
  $('compare').className = 'panel';
  $('compare').append(el('h2', 'Baseline comparison · grouped by category and name'));
  $('compare').append(el('p', 'Compare only equivalent inputs, launch configurations, devices and profiling settings.'));
  let d = el('div', '');
  d.id = 'diff';
  d.className = 'scroll';
  $('compare').append(d);
  table('diff', r.comparison, [
    ['name', 'Name'],
    ['kind', 'Category'],
    ['configuration_label', 'Launch configuration'],
    ['baseline_count', 'Baseline calls'],
    ['current_count', 'Current calls'],
    ['delta_mean_us', 'Mean Δ µs'],
    ['delta_percent', 'Mean Δ %']
  ])
}
draw();
</script></main></body></html>'''
