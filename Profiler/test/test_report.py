"""Offline report semantics, independent of an installed FlagTree or accelerator."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

# Load the pure-Python report package without importing the native runtime.
import importlib
import sys
import types

package = types.ModuleType("offline_profiler")
package.__path__ = [
    str(Path(__file__).parents[1] / "python/flagtree_profiler")
]
sys.modules[package.__name__] = package
report = importlib.import_module("offline_profiler._report")


def event(kind, start, end, name="probe", **metrics):
    return dict(source="test_source",
                state="collected",
                metrics={
                    "activity.kind": kind,
                    "activity.process_id": 1,
                    "activity.context_id": 0,
                    "activity.thread_id": 1,
                    **{
                        f"activity.{dim}_{axis}": 1
                        for dim in ("grid", "block")
                        for axis in "xyz"
                    },
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
    p.write_text(json.dumps(dict(backend="test_vendor", associations=rows)))
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
                "activity.memory_action": "free",
                "activity.api_success": 1,
                "activity.address": 42,
                "activity.memory_space": "device"
            })
    ])
    assert len(result["untimed_events"]) == 2
    assert not result["rejected"]
    assert result["unmatched_frees"] == 1
    assert result["observed_peak_bytes"] == {"device": 0}


def test_allocations_and_free_are_observed_not_total_memory(tmp_path):
    common = {
        "activity.address": 42,
        "activity.memory_space": "device",
        "activity.api_success": 1
    }
    result = load(tmp_path, [
        event(
            "runtime", 100, 200, **common, **{
                "activity.memory_action": "allocate",
                "activity.allocation_bytes": 4096
            }),
        event("runtime", 300, 400, **common, **
              {"activity.memory_action": "free"})
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
            "activity.address": address,
        })])
    embedded = report.render(result).split(
        '<script id="data" type="application/json">')[1].split('</script>')[0]
    data = json.loads(embedded)
    assert data["events"][0]["metrics"]["activity.address"] == str(address)


def test_transfer_bandwidth_and_multi_device_lanes(tmp_path):
    first = event("memcpy", 1000, 2000, **{
        "activity.bytes": 4096,
        "activity.copy_direction": "H2D"
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


@pytest.mark.parametrize("backend",
                         ["enflame", "cuda", "hip", "future_vendor"])
def test_common_contract_does_not_dispatch_on_backend(tmp_path, backend):
    path = tmp_path / "capture.json"
    path.write_text(
        json.dumps(
            dict(backend=backend, associations=[event("kernel", 100, 200)])))
    result = report.analyze(path)
    assert result["backend"] == backend
    assert result["counts"] == {"kernel": 1}
    assert result["hotspots"][0]["total_us"] == .1


def test_legacy_unclassified_artifact_has_actionable_error(tmp_path):
    row = event("kernel", 100, 200)
    del row["metrics"]["activity.kind"]
    with pytest.raises(ValueError, match="update the backend collector"):
        load(tmp_path, [row])


def test_cross_process_correlation_ids_do_not_link(tmp_path):
    api = event("runtime", 1000, 3000)
    kernel = event("kernel", 2000, 4000, **{"activity.process_id": 2})
    trace = report.chrome_trace(load(tmp_path, [api, kernel]))["traceEvents"]
    assert not any(row["ph"] in ("s", "f") for row in trace)


def test_backend_metadata_is_not_interpreted_by_report(tmp_path):
    result = load(tmp_path, [
        event(
            "runtime", 100, 200, **{
                "test_vendor.raw_return_code": 200,
                "activity.api_success": 1,
            })
    ])
    assert result["api_error_count"] == 0
    assert result["events"][0]["metrics"]["test_vendor.raw_return_code"] == 200


def test_missing_transfer_size_is_not_zero_bandwidth(tmp_path):
    result = load(tmp_path, [event("memcpy", 100, 200)])
    assert result["hotspots"][0]["bytes"] is None
    assert result["hotspots"][0]["effective_gbps"] is None
    result = load(tmp_path, [event("runtime", 100, 200)])
    assert result["api_error_count"] == 0
    assert result["api_unknown_status_count"] == 1


@pytest.mark.parametrize("field,value", [("start_time_ns", "bad"),
                                         ("device_id", None),
                                         ("end_time_ns", 99)])
def test_malformed_event_keeps_valid_records(tmp_path, field, value):
    broken = event("kernel", 100, 200)
    broken["runtime_event"][field] = value
    result = load(tmp_path, [broken, event("kernel", 300, 400)])
    assert result["counts"] == {"kernel": 2}
    assert len(result["events"]) == (2 if field == "device_id" else 1)
    assert not result["rejected"]


def test_invalid_memory_metadata_does_not_invent_free(tmp_path):
    common = {
        "activity.address": 42,
        "activity.memory_space": "device",
        "activity.api_success": 1
    }
    result = load(tmp_path, [
        event(
            "runtime", 100, 200, **common, **{
                "activity.memory_action": "allocate",
                "activity.allocation_bytes": 4096
            }),
        event("runtime", 300, 400, **common, **
              {"activity.memory_action": "unsupported_action"}),
        event(
            "runtime", 500, 600, **{
                **common, "activity.memory_action": "free",
                "activity.api_success": 0
            }),
        event("runtime", 700, 800, **{"activity.memory_action": "allocate"}),
    ])
    assert result["invalid_memory_events"] == 2
    assert result["unknown_memory_events"] == 1
    assert result["memory"][-1]["bytes"] == 4096
    assert result["unmatched_frees"] == 0


@pytest.mark.skipif(os.environ.get("FLAGPRISM_TEST_BROWSER") != "1",
                    reason="Opt-in Playwright browser regression")
def test_report_browser(tmp_path):
    from playwright.sync_api import sync_playwright
    rows = [
        event("kernel",
              100,
              200,
              name="vector kernel",
              **{
                  "activity.grid_x": 2,
                  "activity.grid_y": 1,
                  "activity.grid_z": 1
              }),
        event("runtime", 50, 120, name="launch")
    ]
    result = load(tmp_path, rows)
    path = tmp_path / "index.html"
    path.write_text(report.render(result))
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(path.as_uri())
            assert page.locator("#backend").inner_text() == "test_vendor"
            assert page.locator("#cards .card").count() == 4
            assert not page.locator("#compare").inner_text()
            page.select_option("#kind", "kernel")
            page.select_option("#eventSelect", index=1)
            assert "Grid" in page.locator("#detail").inner_text()
            page.locator(".inspector summary").click()
            assert "launch" in page.locator("#rawDetail").inner_text()
            before = page.locator("#range").inner_text()
            page.click("#zoomIn")
            assert before != page.locator("#range").inner_text()
            page.click("#reset")
            page.fill("#search", "missing")
            assert "No matching records" in page.locator(
                "#hotspots").inner_text()
            assert "Select an event" in page.locator("#detail").inner_text()
            page.fill("#search", "")
            page.select_option("#kind", "")
            page.locator("#hotspots th button").nth(3).click()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth")
            empty = tmp_path / "empty.html"
            empty.write_text(report.render(load(tmp_path, [])))
            page.goto(empty.as_uri())
            assert "No matching records" in page.locator(
                "#hotspots").inner_text()
            assert page.locator("#eventSelect option").count() == 1
            assert page.locator('a[href="timeline.json"]').is_hidden()
            for label, key in [("Download analysis JSON", "events")]:
                with page.expect_download() as info:
                    page.get_by_role("link", name=label, exact=False).click()
                assert info.value.suggested_filename == (
                    "timeline.json" if key == "traceEvents" else "report.json")
                exported = json.loads(Path(info.value.path()).read_text())
                assert exported[key] == []
            counter = tmp_path / "counter.vendor.json"
            counter.write_text(
                json.dumps(
                    dict(backend="test_vendor",
                         counter_groups=[
                             dict(name="kernel config",
                                  scope="kernel_config_aggregate",
                                  source="test_tool",
                                  invocations=2,
                                  metrics=[
                                      dict(name="cycles",
                                           unit="cycles",
                                           value=12,
                                           instances=[
                                               dict(instance="unit 0",
                                                    minimum=10,
                                                    maximum=14,
                                                    mean=12,
                                                    count=1)
                                           ])
                                  ])
                         ],
                         capture=dict(replay_mode="none"))))
            counter_document = json.loads(counter.read_text())
            counter_document["counter_groups"][0]["metrics"].append(
                dict(name="z_other",
                     unit="events",
                     value=99,
                     description="second metric",
                     instances=[]))
            counter.write_text(json.dumps(counter_document))
            page_html = tmp_path / "counter.html"
            page_html.write_text(report.render(report.analyze(counter)))
            page.goto(page_html.as_uri())
            assert page.locator("#counters").is_visible()
            assert page.locator("#activityPanel").is_hidden()
            assert page.locator('a[href="timeline.json"]').is_hidden()
            assert page.locator("#counterSummary tbody tr").count() == 2
            assert page.locator("#counterInstances tbody tr").count() == 1
            page.locator("#counterSummary th button").first.click()
            page.select_option("#counterMetric", "1")
            assert page.locator(
                "#counterDescription").inner_text() == "second metric"
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
        finally:
            browser.close()


@pytest.mark.parametrize("number", ["NaN", "Infinity", "1e999"])
def test_nonfinite_json_has_actionable_error(tmp_path, number):
    path = tmp_path / "bad.json"
    path.write_text('{"backend":"test","extra":' + number +
                    ',"associations":[]}')
    with pytest.raises(ValueError, match="Non-finite JSON numbers"):
        report.analyze(path)


def test_embedded_download_preserves_large_integer_types(tmp_path):
    address = 2**55 + 1
    result = load(tmp_path, [
        event("runtime",
              100,
              200,
              name="__DATA____EXPORTS__",
              **{"activity.address": address})
    ])
    embedded = report.render(result).split(
        '<script id="exports" type="application/json">')[1].split(
            '</script>')[0]
    downloads = json.loads(embedded)
    exported = json.loads(downloads["report.json"])
    assert exported["events"][0]["metrics"]["activity.address"] == address
    assert isinstance(exported["events"][0]["metrics"]["activity.address"],
                      int)
    assert exported["events"][0]["name"] == "__DATA____EXPORTS__"


def test_counter_aggregates_do_not_invent_timeline(tmp_path):
    path = tmp_path / "counter.json"
    group = dict(name="kernel config",
                 source="test_tool",
                 scope="kernel_config_aggregate",
                 invocations=2,
                 metrics=[
                     dict(name="test_counter",
                          unit="cycles",
                          value=12,
                          instances=[
                              dict(instance="unit 0",
                                   minimum=10,
                                   maximum=14,
                                   mean=12,
                                   count=1)
                          ])
                 ])
    path.write_text(
        json.dumps(dict(backend="future_vendor", counter_groups=[group])))
    result = report.analyze(path)
    assert result["events"] == [] and result["hotspots"] == []
    assert result["counter_groups"] == [group]
    assert report.chrome_trace(result)["traceEvents"] == []
    group["metrics"][0]["value"] = "not a number"
    path.write_text(
        json.dumps(dict(backend="future_vendor", counter_groups=[group])))
    with pytest.raises(ValueError, match="Counter values"):
        report.analyze(path)


def test_bundle_preserves_evidence_and_unknown_context(tmp_path):
    result = load(tmp_path, [
        event("kernel", 100, 200, **{
            "activity.grid_x": 8,
            "test_vendor.extra": 2**60 + 1
        }),
        event("kernel", 0, 200)
    ])
    source = tmp_path / "profile.vendor.json"
    out = tmp_path / "bundle"
    report.write_bundle(result, source, out)
    manifest = json.loads((out / "manifest.json").read_text())
    import hashlib
    for name, metadata in manifest["files"].items():
        data = (out / name).read_bytes()
        assert metadata["sha256"] == hashlib.sha256(data).hexdigest()
        assert metadata["bytes"] == len(data)
    assert not (out / "raw/profile.vendor.json").exists()
    assert not (out / "ai/rejected.jsonl").exists()
    events = [
        json.loads(line)
        for line in (out / "ai/events.jsonl").read_text().splitlines()
    ]
    kernels = json.loads((out / "ai/kernels.json").read_text())
    assert kernels["groups"][0]["event_ids"] == [events[0]["id"]]
    assert events[0]["metrics"]["test_vendor.extra"] == 2**60 + 1
    context = json.loads((out / "ai/context.json").read_text())
    assert "workload" in context["missing_sections"]
    summary = json.loads((out / "ai/summary.json").read_text())
    assert not summary["rejected"]
    assert summary["untimed_counts"] == {"kernel": 1}
    assert summary["availability"]["counters"]["status"] == "unknown"
    assert not (out / "ai/counters.json").exists()
    assert not (out / "ai/findings.json").exists()
    assert (out / "report/timeline.json").exists()
    with pytest.raises(ValueError, match="already contains"):
        report.write_bundle(result, source, out)


def test_bundle_context_and_empty_capture(tmp_path):
    result = load(tmp_path, [])
    source = tmp_path / "profile.vendor.json"
    context = {"workload": {"shape": [256], "dtype": "float32"}}
    out = tmp_path / "bundle"
    report.write_bundle(result, source, out, context)
    saved = json.loads((out / "ai/context.json").read_text())
    assert saved["supplied"]["workload"]["shape"] == [256]
    assert "workload" not in saved["missing_sections"]
    assert not (out / "ai/events.jsonl").exists()
    assert not (out / "report/timeline.json").exists()


def test_automatic_export_retains_legacy_evidence_without_legacy_files(
        tmp_path, monkeypatch):
    import sys
    import types
    import importlib
    package = types.ModuleType("capture_export_test")
    package.__path__ = [
        str(Path(__file__).parents[1] / "python/flagtree_profiler")
    ]
    monkeypatch.setitem(sys.modules, "capture_export_test", package)
    capture = importlib.import_module("capture_export_test._capture")
    base = tmp_path / "native"
    original = {
        "source": "legacy",
        "metrics": {
            "vendor.value": 17
        },
        "state": "collected"
    }
    base.with_suffix(".vendor.json").write_text(
        json.dumps({
            "backend": "other",
            "associations": [original]
        }))
    tree = [{"frame": {"name": "scope"}, "metrics": {"time (ns)": 123}}]
    base.with_suffix(".hatchet").write_text(json.dumps(tree))
    native_trace = {
        "traceEvents": [{
            "ph": "X",
            "name": "kernel",
            "ts": 1,
            "dur": 2
        }]
    }
    base.with_suffix(".chrome_trace").write_text(json.dumps(native_trace))
    output = tmp_path / "bundle"
    with pytest.raises(RuntimeError, match="no profiling data"):
        capture.export_capture(tmp_path / "missing", output)
    assert not output.exists()
    capture.export_capture(base, output)
    assert json.loads((output / "ai/call_tree.json").read_text()) == tree
    assert json.loads(
        (output / "report/timeline.json").read_text()) == native_trace
    assert json.loads(
        (output /
         "ai/rejected.jsonl").read_text())["original_record"] == original
    assert not list(output.rglob("*.vendor.json"))
    manifest = json.loads((output / "manifest.json").read_text())
    assert "ai/call_tree.json" in manifest["files"]
    assert manifest["availability"]["producer"]["counters"][
        "status"] == "unknown"


def test_kernel_groups_split_launch_configuration_and_arguments(tmp_path):
    rows = [
        event("kernel", 100 + i * 100, 150 + i * 100, **{
            "activity.grid_x": grid,
            "activity.block_x": 4
        }) for i, grid in enumerate((1, 4, 4))
    ]
    for i, row in enumerate(rows):
        row["runtime_event"]["scope_id"] = i + 1
    document = dict(
        backend="test",
        associations=rows,
        launches=[
            dict(id=f"launch-{i+1}",
                 scope_id=i + 1,
                 name="probe",
                 binary_id="binary",
                 arguments={"x": {
                     "shape": [size],
                     "dtype": "float16"
                 }}) for i, size in enumerate((128, 512, 1024))
        ])
    result = report.analyze(document)
    assert len(result["hotspots"]) == 3
    assert all(row["count"] == 1 for row in result["hotspots"])
    assert len({row["group_id"] for row in result["events"]}) == 3
    report.write_bundle(result, document, tmp_path / "bundle")
    kernels = json.loads((tmp_path / "bundle/ai/kernels.json").read_text())
    assert all(len(row["event_ids"]) == 1 for row in kernels["groups"])


def test_context_partial_hardware_and_explicit_counter_state(tmp_path):
    document = dict(
        backend="test",
        associations=[],
        availability={
            "counters": {
                "status": "not_enabled",
                "reason": "opt-in"
            }
        },
        session_metadata={"device": {
            "arch": "example",
            "clock_rate": 123
        }})
    report.write_bundle(report.analyze(document), document,
                        tmp_path / "bundle")
    folder = tmp_path / "bundle"
    context = json.loads((folder / "ai/context.json").read_text())
    assert "hardware" not in context["missing_sections"]
    assert context["sections"]["hardware"]["status"] == "partial"
    for filename in ("manifest.json", "ai/summary.json"):
        assert json.loads((folder / filename).read_text(
        ))["availability"]["counters"]["status"] == "not_enabled"
