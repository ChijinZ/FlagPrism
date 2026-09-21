"""Offline accelerator activity analysis. Run directly with Python; no device or native module needed."""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


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


def analyze(path):

    def finite_number(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(
                "Non-finite JSON numbers must be encoded as strings")
        return number

    document = json.loads(Path(path).read_text(),
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
    events = []
    rejected = Counter()
    for index, row in enumerate(document.get("associations", [])):
        raw = row.get("runtime_event", {})
        metrics = row.get("metrics", {})
        kind = metrics.get("activity.kind")
        if kind not in ("kernel", "runtime", "driver", "memcpy", "memset"):
            rejected["missing or unsupported activity.kind"] += 1
            continue
        if row.get("state") != "collected":
            rejected[row.get("note") or row.get("state", "missing state")] += 1
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("op_name"),
                                                       str):
            rejected["invalid runtime event"] += 1
            continue
        required = ("start_time_ns", "end_time_ns", "device_id", "stream_id",
                    "correlation_id", "scope_id")
        if any(
                type(raw.get(key)) is not int or raw[key] < 0
                for key in required):
            rejected["missing or invalid integer event fields"] += 1
            continue
        start, end = raw["start_time_ns"], raw["end_time_ns"]
        if start <= 0 or end < start:
            rejected["unknown or invalid timestamps"] += 1
            continue
        if "activity.bytes" in metrics and (type(
                metrics["activity.bytes"]) is not int
                                            or metrics["activity.bytes"] < 0):
            rejected["invalid activity.bytes"] += 1
            continue
        if "activity.api_success" in metrics and (
                type(metrics["activity.api_success"]) is not int
                or metrics["activity.api_success"] not in (0, 1)):
            rejected["invalid activity.api_success"] += 1
            continue
        host = kind in ("runtime", "driver")
        lane = (
            f'{kind} PID {metrics.get("activity.process_id", "?")} / TID {metrics.get("activity.thread_id", "?")}'
            if host else
            f'PID {metrics.get("activity.process_id", "?")} / Device {raw["device_id"]} / Context {metrics.get("activity.context_id", "?")} / Stream {raw["stream_id"]}'
        )
        name = raw["op_name"]
        if kind == "memcpy":
            direction = metrics.get("activity.copy_direction", "unknown")
            name = f"memcpy {direction}"
        events.append(
            dict(id=index,
                 kind=kind,
                 name=name,
                 start_ns=start,
                 end_ns=end,
                 duration_us=(end - start) / 1000,
                 device=None if host else raw["device_id"],
                 correlation_id=raw["correlation_id"],
                 correlation_key=(json.dumps([
                     metrics.get("activity.process_id"),
                     metrics.get("activity.correlation_domain", "default"),
                     raw["correlation_id"]
                 ]) if raw["correlation_id"]
                                  and "activity.process_id" in metrics else
                                  None),
                 scope_id=raw["scope_id"],
                 lane=lane,
                 metrics=metrics,
                 source=row["source"]))
    events.sort(key=lambda e: (e["start_ns"], e["id"]))
    origin = min((e["start_ns"] for e in events), default=0)
    for event in events:
        event["start_us"] = (event["start_ns"] - origin) / 1000
        event["end_us"] = (event["end_ns"] - origin) / 1000
    groups = defaultdict(list)
    for event in events:
        groups[(event["kind"], event["name"])].append(event)
    hotspots = []
    for (kind, name), rows in groups.items():
        times = [r["duration_us"] for r in rows]
        byte_count = (sum(r["metrics"]["activity.bytes"] for r in rows) if all(
            "activity.bytes" in r["metrics"] for r in rows) else None)
        hotspots.append(
            dict(kind=kind,
                 name=name,
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
    for device in sorted(
        {e["device"]
         for e in events if e["device"] is not None}):
        rows = [e for e in events if e["device"] == device]
        first = min(r["start_ns"] for r in rows)
        last = max(r["end_ns"] for r in rows)
        span = last - first
        covered = union_ns([(r["start_ns"], r["end_ns"]) for r in rows])
        kernel = union_ns([(r["start_ns"], r["end_ns"]) for r in rows
                           if r["kind"] == "kernel"])
        devices.append(
            dict(device=device,
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
    for event in sorted(events, key=lambda e: (e["end_ns"], e["id"])):
        m = event["metrics"]
        if event["kind"] != "runtime" or "activity.memory_action" not in m:
            continue
        action = m["activity.memory_action"]
        if (action not in ("allocate", "free")
                or m.get("activity.memory_space") not in ("host", "device")
                or type(m.get("activity.address")) is not int
                or m["activity.address"] < 0
                or m.get("activity.api_success", 1) != 1
                or (action == "allocate" and
                    (type(m.get("activity.allocation_bytes")) is not int
                     or m["activity.allocation_bytes"] < 0))):
            invalid_memory_events += 1
            continue
        if m["activity.address"] == 0:
            continue  # Successful free(NULL) does not represent a live allocation.
        space = m["activity.memory_space"]
        key = (m.get("activity.process_id"), m.get("activity.context_id"),
               space, m["activity.address"])
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
        e for e in events if e["kind"] in ("runtime", "driver")
        and e["metrics"].get("activity.api_success") == 0
    ]
    return dict(
        schema_version=1,
        source=str(path),
        backend=backend,
        counter_groups=counter_groups,
        capture=capture,
        kernel_summaries=summaries,
        origin_ns=origin,
        events=events,
        hotspots=hotspots,
        devices=devices,
        memory=memory,
        counts=dict(Counter(e["kind"] for e in events)),
        api_error_count=len(api_errors),
        api_unknown_status_count=sum(e["kind"] in (
            "runtime", "driver") and "activity.api_success" not in e["metrics"]
                                     for e in events),
        rejected=dict(rejected),
        degrade_reasons=document.get("degrade_reasons", []),
        capture_notes=document.get("capture_notes", []),
        observed_peak_bytes=dict(peak),
        unmatched_frees=unmatched_frees,
        invalid_memory_events=invalid_memory_events,
        limitations=[
            "Coverage describes captured device activity, not hardware utilization.",
            "Observed allocation bytes exclude allocations before capture and caching allocator tensor lifetimes.",
            "Missing activity categories or fields mean unreported data, not zero hardware activity.",
            "Effective transfer GB/s uses recorded bytes divided by summed activity duration, not measured HBM bandwidth.",
            "Runtime and driver API durations may nest; do not add them to device elapsed time.",
            "Synchronization and allocator API timings are available only when called during capture."
        ])


def comparison(current, baseline):
    old = {(r["kind"], r["name"]): r for r in baseline["hotspots"]}
    new = {(r["kind"], r["name"]): r for r in current["hotspots"]}
    rows = []
    for key in sorted(old.keys() | new.keys()):
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
    apis = {}
    for event in report["events"]:
        if event["kind"] in ("runtime", "driver") and event["correlation_key"]:
            apis.setdefault(event["correlation_key"], event)
    for event in report["events"]:
        api = apis.get(event["correlation_key"])
        if event["device"] is None or api is None or api["start_us"] > event[
                "start_us"]:
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
            "trace.json": json.dumps(chrome_trace(report))
        },
        ensure_ascii=True)
    exports = exports.replace("<", "\\u003c").replace(">", "\\u003e").replace(
        "&", "\\u0026")
    before, after = HTML.split("__DATA__", 1)
    return before + data + after.replace("__EXPORTS__", exports, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input",
                        type=Path,
                        help="Normalized activity .vendor.json")
    parser.add_argument("--out",
                        type=Path,
                        required=True,
                        help="Output directory")
    parser.add_argument("--baseline",
                        type=Path,
                        help="Optional baseline .vendor.json")
    args = parser.parse_args()
    try:
        report = analyze(args.input)
        if args.baseline:
            report["comparison"] = comparison(report, analyze(args.baseline))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    (args.out / "trace.json").write_text(json.dumps(chrome_trace(report)))
    (args.out / "index.html").write_text(render(report))
    print(args.out / "index.html")


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
td:first-child{max-width:320px;white-space:normal;overflow-wrap:anywhere}
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
<details class="quality" id="qualityBox"><summary id="qualitySummary">Capture quality & interpretation</summary><div id="quality"></div></details>
<section class="panel" id="counters" hidden><h2>Hardware counter observations</h2><p class="caption">Tool-reported aggregates. Scope and sample counts are preserved; these values are not joined to timeline events.</p><div class="toolbar"><label>Kernel group <select id="counterGroup"></select></label><label>Metric <select id="counterMetric"></select></label></div><p class="caption" id="counterScope"></p><div class="scroll" id="counterSummary"></div><p id="counterDescription" class="caption"></p><div class="timeline-grid"><div id="counterBars" class="scroll" style="padding:14px"></div><div id="counterInstances" class="scroll"></div></div></section>
<section class="panel" id="kernelSummaries" hidden><h2>Kernel timing summaries</h2><p class="caption">Tool-reported aggregates; invocation counts may include replays. No per-launch timing or percentile distribution is inferred.</p><div class="scroll" id="kernelSummaryTable"></div></section>
<section class="panel" id="activityPanel"><div class="panel-head"><h2>Activity timeline</h2><span class="caption">Select an event to inspect · double-click to focus</span></div>
<div class="toolbar"><label>Search <input id="search" type="search" placeholder="Kernel or API name"></label><label>Category <select id="kind"><option value="">All categories</option><option>kernel</option><option>memcpy</option><option>memset</option><option>runtime</option><option>driver</option></select></label><span class="spacer"></span><button id="zoomIn" aria-label="Zoom in">+</button><button id="zoomOut" aria-label="Zoom out">−</button><button id="left" aria-label="Pan left">←</button><button id="right" aria-label="Pan right">→</button><button id="reset">Reset</button></div>
<div class="legend" id="legend"></div><div id="range" class="muted"></div>
<div class="timeline-grid"><div id="timeline"><canvas id="canvas" aria-label="Activity timeline; use the event selector for keyboard access"></canvas></div><aside class="inspector"><label for="eventSelect" class="caption">INSPECT EVENT</label><select id="eventSelect"></select><div id="detail" class="muted">Select an event to view its timing and launch details.</div><details><summary>Raw record & correlated events</summary><pre id="rawDetail">No event selected.</pre></details></aside></div></section>
<section class="panel" id="hotspotPanel"><div class="panel-head"><h2>Hotspots</h2><span class="caption">Whole capture · matching filters · sort by column</span></div><p class="caption">CPU API time can overlap device execution. Totals are sums of event durations, not elapsed time.</p><div class="scroll" id="hotspots"></div></section>
<div class="bottom-grid"><section class="panel"><h2>Device activity coverage</h2><p class="caption">Interval union within each device's captured window. Not hardware utilization.</p><div id="devices" class="scroll"></div></section>
<section class="panel"><h2>Observed allocations</h2><p class="caption">Successful captured allocations only; excludes pre-capture memory and tensor lifetimes.</p><canvas id="memory" height="180"></canvas><div class="legend"><span style="color:#65d2c5">● Device</span><span style="color:#edbc71">● Host</span></div></section></div>
<div id="compare"></div><footer><a href="trace.json" download>Export Perfetto trace ↗</a><a href="report.json" download>Download analysis JSON ↗</a><span class="muted" id="source"></span></footer>
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
const rejectedCount = Object.values(r.rejected).reduce((a, b) => a + b, 0);
const spanUs = r.events.reduce((m, e) => Math.max(m, e.end_us), 0);
const kernelUs = r.events.filter(e => e.kind === 'kernel').reduce((n, e) => n + e.duration_us, 0);
const overview = [
  ['Capture window', r.events.length ? fmt(spanUs / 1000) + ' ms' : 'Not recorded', 'First to last timed event'],
  ['Kernel duration sum', r.counts.kernel ? fmt(kernelUs / 1000) + ' ms' : 'Not recorded', `${r.counts.kernel || 0} captured kernels · may overlap`],
  ['Recorded activities', fmt(r.events.length), `${r.counter_groups.reduce((n,g)=>n+g.metrics.length,0)} counter metrics · ${r.counts.memcpy || 0} copies`],
  ['API errors / rejected', `${r.api_error_count} / ${rejectedCount}`, `${r.api_unknown_status_count} API results unknown`]
];
const counterOnly = !r.events.length && r.counter_groups.length > 0;
const cards = counterOnly ? [
  ['Kernel groups', fmt(r.counter_groups.length), 'Configuration-level aggregates'],
  ['Counter metrics', fmt(r.counter_groups.reduce((n, g) => n + g.metrics.length, 0)), 'Original units and reported values'],
  ['Instance observations', fmt(r.counter_groups.reduce((n, g) => n + g.metrics.reduce((s, m) => s + (m.instances || []).length, 0), 0)), 'Across metrics; passes may differ'],
  ['Replay policy', r.capture.replay_mode ?? 'Unknown', 'No per-launch timing inferred']
] : overview;
for (const [name, value, hint] of cards) {
  const card = el('div', name);
  card.className = 'card';
  card.prepend(el('strong', value));
  card.append(el('small', hint));
  $('cards').append(card);
}
$('qualitySummary').textContent = `Capture notes · ${r.events.length} timed records · ${rejectedCount} rejected · ${r.degrade_reasons.length} backend notices · ${r.capture_notes.length} capture notes`;
if (rejectedCount || r.api_error_count || r.degrade_reasons.length || r.invalid_memory_events) {
  $('qualityBox').open = true;
  $('qualitySummary').className = 'warn';
}
for (const text of [...(counterOnly ? [] : r.limitations), ...r.capture_notes, ...r.degrade_reasons, ...Object.entries(r.rejected).map(([k, v]) => `${k}: ${v}`), `Ignored invalid memory records: ${r.invalid_memory_events}; unmatched frees: ${r.unmatched_frees}; observed peaks: ${JSON.stringify(r.observed_peak_bytes)}`]) $('quality').append(el('p', text));
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
  return r.events.filter(e => (!k || e.kind === k) && e.name.toLowerCase().includes(q))
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
  table('hotspots', r.hotspots.filter(e => (!$('kind').value || e.kind === $('kind').value) && e.name.toLowerCase().includes($('search').value.toLowerCase())), [
    ['name', 'Name'],
    ['kind', 'Category'],
    ['count', 'Calls'],
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
if (r.counter_groups.length) {
  $('counters').hidden = false;
  if (!r.events.length) {
    $('activityPanel').hidden = true;
    $('hotspotPanel').hidden = true;
    document.querySelector('.bottom-grid').hidden = true;
    document.querySelector('a[href="trace.json"]').hidden = true;
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
    $('counterScope').textContent = `Source: ${group.source} · Scope: ${group.scope} · Reported invocations: ${fmt(group.invocations)} · Replay: ${r.capture.replay_mode ?? 'unknown'}`;
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
    ['baseline_count', 'Baseline calls'],
    ['current_count', 'Current calls'],
    ['delta_mean_us', 'Mean Δ µs'],
    ['delta_percent', 'Mean Δ %']
  ])
}
draw();
</script></main></body></html>'''

if __name__ == "__main__":
    main()
