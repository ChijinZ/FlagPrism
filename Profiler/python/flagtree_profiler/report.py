"""Offline TOPSPTI analysis. Run directly with Python; no device or native module needed."""

import argparse
from collections import Counter, defaultdict
import json
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


def analyze(path):
    document = json.loads(Path(path).read_text())
    if document.get("backend") != "enflame":
        raise ValueError(
            "This report currently accepts Enflame .vendor.json artifacts")
    events = []
    rejected = Counter()
    for index, row in enumerate(document.get("associations", [])):
        raw = row["runtime_event"]
        metrics = row.get("metrics", {})
        kind = metrics.get(
            "enflame.kind",
            "kernel" if row.get("source") == "topspti_activity" else "unknown")
        start, end = int(raw["start_time_ns"]), int(raw["end_time_ns"])
        if row.get("state") != "collected" or start <= 0 or end < start:
            rejected[row.get("note") or row.get("state", "invalid")] += 1
            continue
        host = kind in ("runtime", "driver")
        lane = (
            f'{kind} PID {metrics.get("enflame.process_id", "?")} / TID {metrics.get("enflame.thread_id", "?")}'
            if host else
            f'Device {raw["device_id"]} / Context {metrics.get("enflame.context_id", "?")} / Stream {raw["stream_id"]}'
        )
        name = raw["op_name"]
        if kind == "memcpy":
            direction = {
                1: "H2D",
                2: "D2H",
                8: "D2D",
                9: "H2H",
                10: "P2P"
            }.get(metrics.get("enflame.copy_kind"), "unknown")
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
                 effective_gbps=(sum(r["metrics"].get("enflame.bytes", 0)
                                     for r in rows) / (sum(times) * 1000)
                                 if kind in ("memcpy", "memset") and sum(times)
                                 else None),
                 bytes=sum(r["metrics"].get("enflame.bytes", 0)
                           for r in rows)))
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
    for event in sorted(events, key=lambda e: (e["end_ns"], e["id"])):
        m = event["metrics"]
        if event["kind"] != "runtime" or "enflame.memory_action" not in m:
            continue
        space = m["enflame.memory_space"]
        key = (m.get("enflame.process_id"), m.get("enflame.context_id"), space,
               m["enflame.address"])
        if m["enflame.memory_action"] == "allocate":
            current[space] -= live.get(key, 0)
            live[key] = m["enflame.allocation_bytes"]
            current[space] += live[key]
        elif key in live:
            current[space] -= live.pop(key)
        else:
            unmatched_frees += 1
        peak[space] = max(peak[space], current[space])
        memory.append(
            dict(time_us=event["end_us"], space=space, bytes=current[space]))
    api_errors = [
        e for e in events if e["kind"] == "runtime"
        and e["metrics"].get("enflame.return_value", 0) != 0
    ]
    return dict(
        schema_version=1,
        source=str(path),
        backend="enflame",
        origin_ns=origin,
        events=events,
        hotspots=hotspots,
        devices=devices,
        memory=memory,
        counts=dict(Counter(e["kind"] for e in events)),
        api_error_count=len(api_errors),
        rejected=dict(rejected),
        degrade_reasons=document.get("degrade_reasons", []),
        observed_peak_bytes=dict(peak),
        unmatched_frees=unmatched_frees,
        limitations=[
            "Coverage describes captured device activity, not hardware utilization.",
            "Observed allocation bytes exclude allocations before capture and caching allocator tensor lifetimes.",
            "No hardware counters, cache statistics, or intra-kernel warp/Core timing are collected.",
            "Driver activity is requested but may produce no records with the installed SDK.",
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
        if event["kind"] == "runtime" and event["correlation_id"]:
            apis[event["correlation_id"]] = event
    for event in report["events"]:
        api = apis.get(event["correlation_id"])
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
    return HTML.replace("__DATA__", data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Enflame .vendor.json")
    parser.add_argument("--out",
                        type=Path,
                        required=True,
                        help="Output directory")
    parser.add_argument("--baseline",
                        type=Path,
                        help="Optional baseline .vendor.json")
    args = parser.parse_args()
    report = analyze(args.input)
    if args.baseline:
        report["comparison"] = comparison(report, analyze(args.baseline))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    (args.out / "trace.json").write_text(json.dumps(chrome_trace(report)))
    (args.out / "index.html").write_text(render(report))
    print(args.out / "index.html")


HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>FlagPrism · Enflame profile</title><style>
:root{color-scheme:dark;font:14px system-ui;background:#101622;color:#dce4f1}body{margin:24px;max-width:1500px}h1{font-size:27px;margin-bottom:4px}h2{font-size:19px;margin-top:30px}.muted{color:#9eafc5}button,input,select{background:#1d2a3c;color:inherit;border:1px solid #49617d;border-radius:5px;padding:7px}button{cursor:pointer}.cards{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.card{padding:15px;background:#1b2739;border-radius:8px;min-width:115px}.card strong{display:block;font-size:25px;color:#77d9d0}table{border-collapse:collapse;width:100%}td,th{padding:9px;text-align:left;border-bottom:1px solid #2e3f55}th{position:sticky;top:0;background:#1b2739;cursor:pointer}td:first-child{max-width:420px;overflow-wrap:anywhere}.scroll{max-height:430px;overflow:auto;border:1px solid #2e3f55;border-radius:6px}canvas{display:block;background:#142032;width:100%;cursor:crosshair}pre{max-height:320px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:#1b2739;padding:12px}.legend span{margin-right:18px}a{color:#77d9d0}.warn{color:#f1c17d}#timeline{overflow:auto;max-height:440px}label{margin-right:12px}details{margin:10px 0}</style>
<h1>FlagPrism <span class="muted">/ Enflame</span></h1><div class="muted">Device and host activity · TOPSPTI · offline report</div>
<div id="cards" class="cards"></div><details><summary>Capture quality & interpretation</summary><div id="quality"></div></details>
<h2>Activity timeline</h2><div><label>Search <input id="search" placeholder="Kernel or API name"></label><select id="kind"><option value="">All categories</option><option>kernel</option><option>memcpy</option><option>memset</option><option>runtime</option><option>driver</option></select> <button id="zoomIn">Zoom in</button> <button id="zoomOut">Zoom out</button> <button id="left">←</button> <button id="right">→</button> <button id="reset">Reset</button></div>
<p class="legend" id="legend"></p><div id="range" class="muted"></div><div id="timeline"><canvas id="canvas"></canvas></div><pre id="detail">Click an event to inspect timestamps, correlation, launch dimensions and metadata. Double-click to focus its duration.</pre>
<h2>Hotspots <span class="muted">· whole capture, matching filters · click a header to sort</span></h2><div class="scroll" id="hotspots"></div>
<h2>Device activity coverage</h2><p class="muted">Union of recorded intervals within each device's first-to-last captured activity; not SM/Core utilization or whole-session utilization.</p><div id="devices"></div>
<h2>Observed allocations</h2><p class="muted">Only successful runtime allocations/frees observed during capture. Not total VRAM usage or PyTorch tensor memory. Unmatched frees indicate incomplete history.</p><canvas id="memory" height="180"></canvas>
<div id="compare"></div><p><a href="trace.json" download>Download Perfetto-compatible trace</a> · <a href="report.json" download>Download analyzed data</a></p>
<script id="data" type="application/json">__DATA__</script><script>
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
const fmt = x => typeof x === 'number' ? (Number.isInteger(x) ? x.toLocaleString() : x.toLocaleString(undefined, {
  maximumFractionDigits: 3
})) : (x ?? '—');

function el(tag, text) {
  const e = document.createElement(tag);
  e.textContent = text;
  return e
}

function table(id, rows, cols) {
  const t = document.createElement('table'),
    head = document.createElement('tr');
  let reverse = false;
  for (const [key, title] of cols) {
    let th = el('th', title);
    th.onclick = () => {
      reverse = !reverse;
      rows.sort((a, b) => {
        let x = a[key],
          y = b[key];
        return (typeof x === 'number' ? x - y : String(x ?? '').localeCompare(String(y ?? ''))) * (reverse ? -1 : 1)
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
  $(id).replaceChildren(t)
}
for (const [name, value] of Object.entries({
    ...r.counts,
    'API errors': r.api_error_count,
    'Rejected events': Object.values(r.rejected).reduce((a, b) => a + b, 0)
  })) {
  let d = el('div', name);
  d.className = 'card';
  d.prepend(el('strong', fmt(value)));
  $('cards').append(d)
}
for (const text of [...r.limitations, ...r.degrade_reasons, ...Object.entries(r.rejected).map(([k, v]) => `${k}: ${v}`), `Unmatched frees: ${r.unmatched_frees}; observed peaks: ${JSON.stringify(r.observed_peak_bytes)}`]) $('quality').append(el('p', text));
for (const [k, c] of Object.entries(colors)) {
  let s = el('span', '● ' + k);
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
    w = Math.max(700, $('timeline').clientWidth);
  c.width = w;
  c.height = Math.max(70, lanes.length * 30 + 25);
  const g = c.getContext('2d');
  g.font = '11px system-ui';
  hits = [];
  const pad = 275,
    scale = (w - pad - 15) / (hi - lo);
  lanes.forEach((lane, i) => {
    g.fillStyle = '#adbed3';
    g.fillText(lane, 8, i * 30 + 23, pad - 16);
    g.strokeStyle = '#26384e';
    g.beginPath();
    g.moveTo(pad, i * 30 + 30);
    g.lineTo(w, i * 30 + 30);
    g.stroke()
  });
  for (const e of events) {
    if (e.end_us < lo || e.start_us > hi) continue;
    let x = pad + (Math.max(lo, e.start_us) - lo) * scale,
      y = lanes.indexOf(e.lane) * 30 + 7,
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
$('canvas').onclick = ev => {
  let e = pick(ev);
  if (e) {
    let related = r.events.filter(x => x.correlation_id === e.correlation_id);
    $('detail').textContent = JSON.stringify({
      event: e,
      correlated_events: related.map(x => ({
        kind: x.kind,
        name: x.name,
        start_us: x.start_us,
        duration_us: x.duration_us
      }))
    }, null, 2)
  }
};
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
window.onresize = draw;
table('devices', r.devices, [
  ['device', 'Device'],
  ['window_us', 'Window µs'],
  ['activity_covered_us', 'Activity union µs'],
  ['kernel_covered_us', 'Kernel union µs'],
  ['uncovered_us', 'Uncovered µs'],
  ['activity_coverage', 'Coverage fraction']
]);
const mc = $('memory');
mc.width = 1100;
const mg = mc.getContext('2d'),
  max = r.memory.reduce((m, p) => Math.max(m, p.bytes), 1);
mg.font = '12px system-ui';
mg.fillStyle = '#cdd8e8';
mg.fillText(r.memory.length ? `Observed peak scale ${fmt(max)} bytes` : 'No allocation lifecycle events in this capture', 10, 18);
for (const [space, color] of [
    ['device', '#65d2c5'],
    ['host', '#edbc71']
  ]) {
  mg.strokeStyle = color;
  mg.beginPath();
  let y = 160;
  mg.moveTo(45, y);
  for (const p of r.memory.filter(p => p.space === space)) {
    let x = 45 + p.time_us / full * 1040;
    mg.lineTo(x, y);
    y = 160 - p.bytes / max * 125;
    mg.lineTo(x, y)
  }
  mg.stroke()
}
if (r.comparison) {
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
</script></html>'''

if __name__ == "__main__":
    main()
