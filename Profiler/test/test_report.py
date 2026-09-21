"""Offline report semantics, independent of an installed FlagTree or accelerator."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "offline_report",
    Path(__file__).parents[1] / "python/flagtree_profiler/report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def event(kind, start, end, name="probe", **metrics):
    return dict(source="topspti_activity" if kind == "kernel" else "topspti_" +
                kind,
                state="collected",
                metrics={
                    "enflame.kind": kind,
                    **metrics
                },
                runtime_event=dict(op_name=name,
                                   start_time_ns=start,
                                   end_time_ns=end,
                                   device_id=0,
                                   stream_id=0,
                                   correlation_id=1,
                                   scope_id=1))


def load(tmp_path, rows):
    p = tmp_path / "profile.vendor.json"
    p.write_text(json.dumps(dict(backend="enflame", associations=rows)))
    return report.analyze(p)


def test_overlap_and_host_time_do_not_inflate_device_coverage(tmp_path):
    result = load(tmp_path, [
        event("kernel", 1000, 4000),
        event("kernel", 2000, 5000),
        event("memcpy", 6000, 7000),
        event("runtime", 1, 20000)
    ])
    d = result["devices"][0]
    assert d["activity_covered_us"] == 5
    assert d["uncovered_us"] == 1
    row = next(x for x in result["hotspots"] if x["kind"] == "kernel")
    assert row["count"] == 2 and row["total_us"] == 6
    assert row["p95_us"] == 3


def test_bad_time_and_unknown_preexisting_allocation(tmp_path):
    result = load(tmp_path, [
        event("kernel", 0, 40),
        event("kernel", 100, 90),
        event(
            "runtime", 100, 200, **{
                "enflame.memory_action": "free",
                "enflame.address": 42,
                "enflame.memory_space": "device"
            })
    ])
    assert sum(result["rejected"].values()) == 2
    assert result["unmatched_frees"] == 1
    assert result["observed_peak_bytes"] == {"device": 0}


def test_allocations_and_free_are_observed_not_total_memory(tmp_path):
    common = {"enflame.address": 42, "enflame.memory_space": "device"}
    result = load(tmp_path, [
        event(
            "runtime", 100, 200, **common, **{
                "enflame.memory_action": "allocate",
                "enflame.allocation_bytes": 4096
            }),
        event("runtime", 300, 400, **common, **
              {"enflame.memory_action": "free"})
    ])
    assert result["observed_peak_bytes"]["device"] == 4096
    assert result["memory"][-1]["bytes"] == 0
    assert report.chrome_trace(result)["traceEvents"]


def test_embedded_html_and_comparison(tmp_path):
    base = load(
        tmp_path,
        [event("kernel", 100, 200, name="</script><script>alert(1)</script>")])
    now = load(
        tmp_path,
        [event("kernel", 100, 300, name="</script><script>alert(1)</script>")])
    rendered = report.render(now)
    assert "</script><script>alert(1)" not in rendered
    assert report.comparison(now,
                             base)[0]["delta_percent"] == pytest.approx(100)


def test_empty_report(tmp_path):
    result = load(tmp_path, [])
    assert result["devices"] == []
    assert report.chrome_trace(result)["traceEvents"] == []


def test_large_addresses_remain_exact_in_html(tmp_path):
    address = 2**55 + 1
    result = load(
        tmp_path,
        [event("runtime", 100, 200, **{
            "enflame.address": address,
        })])
    embedded = report.render(result).split(
        '<script id="data" type="application/json">')[1].split('</script>')[0]
    data = json.loads(embedded)
    assert data["events"][0]["metrics"]["enflame.address"] == str(address)


def test_transfer_bandwidth_and_multi_device_lanes(tmp_path):
    first = event("memcpy", 1000, 2000, **{
        "enflame.bytes": 4096,
        "enflame.copy_kind": 1
    })
    second = event("kernel", 1000, 2000)
    second["runtime_event"]["device_id"] = 1
    result = load(tmp_path, [first, second])
    copy = next(row for row in result["hotspots"] if row["kind"] == "memcpy")
    assert copy["name"] == "memcpy H2D"
    assert copy["effective_gbps"] == pytest.approx(4.096)
    assert len({e["lane"] for e in result["events"]}) == 2
    assert len(result["devices"]) == 2


def test_trace_links_only_actual_api_correlations(tmp_path):
    api = event("runtime", 1000, 3000)
    kernel = event("kernel", 2000, 4000)
    unmatched = event("kernel", 5000, 6000)
    unmatched["runtime_event"]["correlation_id"] = 2
    trace = report.chrome_trace(load(tmp_path,
                                     [api, kernel, unmatched]))["traceEvents"]
    flows = [row for row in trace if row["ph"] in ("s", "f")]
    assert len(flows) == 2
    assert flows[0]["id"] == flows[1]["id"]
    assert flows[0]["ts"] < flows[1]["ts"]
