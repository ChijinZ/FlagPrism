"""Offline report semantics, independent of an installed FlagTree or accelerator."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "offline_report",
    Path(__file__).parents[1] / "python/flagtree_profiler/report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def event(kind, start, end, name="probe", **metrics):
    return dict(source="test_source",
                state="collected",
                metrics={
                    "activity.kind": kind,
                    "activity.process_id": 1,
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
                "activity.address": 42,
                "activity.memory_space": "device"
            })
    ])
    assert sum(result["rejected"].values()) == 2
    assert result["unmatched_frees"] == 1
    assert result["observed_peak_bytes"] == {"device": 0}


def test_allocations_and_free_are_observed_not_total_memory(tmp_path):
    common = {"activity.address": 42, "activity.memory_space": "device"}
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
    assert result["counts"] == {"kernel": 1}
    assert sum(result["rejected"].values()) == 1
    assert "collected" not in result["rejected"]


def test_invalid_memory_metadata_does_not_invent_free(tmp_path):
    common = {"activity.address": 42, "activity.memory_space": "device"}
    result = load(tmp_path, [
        event(
            "runtime", 100, 200, **common, **{
                "activity.memory_action": "allocate",
                "activity.allocation_bytes": 4096
            }),
        event("runtime", 300, 400, **common, **
              {"activity.memory_action": "unsupported_action"}),
        event("runtime", 500, 600, **common, **{
            "activity.memory_action": "free",
            "activity.api_success": 0
        }),
        event("runtime", 700, 800, **{"activity.memory_action": "allocate"}),
    ])
    assert result["invalid_memory_events"] == 3
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
            for label, key in [("Download analysis JSON", "events"),
                               ("Export Perfetto trace", "traceEvents")]:
                with page.expect_download() as info:
                    page.get_by_role("link", name=label, exact=False).click()
                exported = json.loads(Path(info.value.path()).read_text())
                assert exported[key] == []
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
