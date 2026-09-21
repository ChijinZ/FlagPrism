"""Cross-backend contracts and failure recovery without an accelerator."""
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def capture(monkeypatch):
    package = ModuleType("portable_capture_test")
    package.__path__ = [
        str(Path(__file__).parents[1] / "python/flagtree_profiler")
    ]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return importlib.import_module(package.__name__ + "._capture")


def record(**raw):
    return dict(source="future_sdk",
                state="collected",
                metrics={"activity.kind": "kernel"},
                runtime_event={
                    "op_name": "kernel",
                    "start_time_ns": 100,
                    "end_time_ns": 200,
                    **raw
                })


@pytest.mark.parametrize(
    "field", ["device_id", "stream_id", "scope_id", "correlation_id"])
@pytest.mark.parametrize("value", [None, -1, "unsupported"])
def test_missing_identity_keeps_timing(capture, field, value):
    result = capture._report.analyze(
        dict(backend="future", associations=[record(**{field: value})]))
    event = result["events"][0]
    assert event[field] is None
    assert event["duration_us"] == .1
    assert event["correlation_key"] is None
    assert not result["rejected"]


def test_zero_identity_and_explicit_unknown_mask(capture):
    row = record(device_id=0, stream_id=0, scope_id=0, correlation_id=0)
    report = capture._report
    event = report.analyze(dict(backend="future",
                                associations=[row]))["events"][0]
    assert event["device_id"] == event["stream_id"] == 0
    assert event["scope_id"] is event["correlation_id"] is None
    row["metrics"]["activity.unknown_fields"] = "device_id,stream_id"
    event = report.analyze(dict(backend="future",
                                associations=[row]))["events"][0]
    assert event["device_id"] is event["stream_id"] is None


def test_unknown_identities_never_join(capture):
    rows = [record(), record()]
    for row in rows:
        row["runtime_event"]["correlation_id"] = 1
        row["metrics"]["activity.process_id"] = None
    report = capture._report.analyze(dict(backend="future", associations=rows))
    assert len(report["hotspots"]) == 2
    assert len({e["lane"] for e in report["events"]}) == 2
    assert all(e["correlation_key"] is None for e in report["events"])
    assert capture._report.comparison(report, report) == []
    assert not any(
        e["ph"] in ("s", "f")
        for e in capture._report.chrome_trace(report)["traceEvents"])


def test_untimed_records_remain_machine_readable(capture, tmp_path):
    row = record(start_time_ns=None)
    document = dict(backend="future", associations=[row])
    report = capture._report.analyze(document)
    assert not report["events"] and not report["rejected"]
    event = report["untimed_events"][0]
    assert event["duration_us"] is event["start_us"] is event["end_us"] is None
    capture._report.write_bundle(report, document, tmp_path / "bundle")
    exported = json.loads((tmp_path / "bundle/ai/events.jsonl").read_text())
    assert exported["original_record"] == row
    assert not (tmp_path / "bundle/report/timeline.json").exists()


@pytest.mark.parametrize("status",
                         ["unsupported", "not_enabled", "failed", "unknown"])
def test_availability_is_owned_by_producer(capture, tmp_path, status):
    document = dict(backend="future",
                    associations=[],
                    availability={
                        "counters": {
                            "status": status,
                            "reason": "producer evidence"
                        }
                    })
    base = tmp_path / "capture"
    base.with_suffix(".vendor.json").write_text(json.dumps(document))
    capture.export_capture(base, tmp_path / "bundle")
    summary = json.loads((tmp_path / "bundle/ai/summary.json").read_text())
    assert summary["availability"]["counters"] == document["availability"][
        "counters"]


def test_backend_extensions_are_lazy_and_replaceable(capture, monkeypatch):
    backends = importlib.import_module(capture.__package__ + "._backends")
    monkeypatch.setitem(sys.modules, "fake_accelerator",
                        SimpleNamespace(__version__="1.2"))
    monkeypatch.setitem(backends._BACKENDS, "future",
                        backends.CaptureBackend(("fake_accelerator", )))
    assert capture.capture_software(
        "future")["versions"]["fake_accelerator"] == "1.2"
    assert "fake_accelerator" not in capture.capture_software(
        "other")["versions"]
    assert backends.capture_backend("other").collect_counters is None


def test_cli_failure_retains_intermediates_and_restores_environment(
        capture, tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    stage.mkdir()
    monkeypatch.setattr(capture.tempfile, "mkdtemp", lambda **kw: str(stage))
    monkeypatch.delenv(capture.INTERNAL_ENV, raising=False)
    args = SimpleNamespace(backend="future",
                           counters=False,
                           name=str(tmp_path / "out"),
                           metadata=None)

    def execute(args, target):
        Path(args.name).with_suffix(".vendor.json").write_text("broken JSON")

    with pytest.raises(json.JSONDecodeError) as caught:
        capture.run_capture(args, ["workload.py"], execute)
    assert stage.joinpath("capture.vendor.json").read_text() == "broken JSON"
    assert str(stage) in str(caught.value.__notes__)
    assert capture.INTERNAL_ENV not in capture.os.environ
    assert args.name == str(tmp_path / "out")


@pytest.mark.parametrize("failure", ["native", "export"])
def test_finalize_failure_isolates_sessions_and_preserves_source(
        tmp_path, monkeypatch, failure):
    profile = importlib.import_module("flagtree.profiler.profile")
    monkeypatch.setattr(profile, "_active_sessions", {})
    monkeypatch.setattr(profile, "is_command_line", lambda: False)
    calls = []

    class Native:

        def deactivate_all(self):
            pass

        def finalize(self, session, output_format):
            calls.append(session)
            if failure == "native" and session == 10:
                raise RuntimeError("native failed")

    monkeypatch.setattr(profile, "profiler_native", Native())
    for session in (10, 11):
        stage = tmp_path / str(session)
        stage.mkdir()
        (stage / "capture.vendor.json").write_text("original data")
        profile._active_sessions[session] = dict(session=session,
                                                 staging=str(stage),
                                                 name=str(stage / "capture"),
                                                 bundle_output=tmp_path /
                                                 f"out-{session}")

    def export(state):
        if failure == "export" and state["session"] == 10:
            raise ValueError("export failed")
        state["bundle_output"].mkdir()
        (state["bundle_output"] / "success").write_text("done")

    monkeypatch.setattr(profile, "_export_session", export)
    with pytest.raises(RuntimeError, match="retained at") as caught:
        profile.finalize()
    assert calls == [10, 11]
    assert str(tmp_path / "10") in str(caught.value)
    assert (tmp_path / "10/capture.vendor.json").read_text() == "original data"
    assert not (tmp_path / "11").exists()
    assert (tmp_path / "out-11/success").exists()
    assert not profile._active_sessions


@pytest.mark.parametrize(
    "missing",
    ["activity.process_id", "activity.context_id", "activity.api_success"])
def test_unknown_memory_identity_or_result_does_not_change_memory(
        capture, missing):
    row = record()
    row["metrics"].update({
        "activity.kind": "runtime",
        "activity.process_id": 1,
        "activity.context_id": 0,
        "activity.api_success": 1,
        "activity.address": 42,
        "activity.memory_space": "device",
        "activity.memory_action": "allocate",
        "activity.allocation_bytes": 4096
    })
    row["metrics"].pop(missing)
    result = capture._report.analyze(dict(backend="future",
                                          associations=[row]))
    assert len(result["events"]) == 1
    assert not result["memory"] and not result["observed_peak_bytes"]
    assert result["unknown_memory_events"] == 1


def test_unknown_fields_are_independent_and_original_is_unchanged(capture):
    row = record(device_id=0, stream_id=0)
    row["metrics"].update({
        "activity.context_id": 1,
        "activity.unknown_fields": " activity.context_id , device_id , ",
        "activity.bytes": -1,
        "activity.api_success": 9,
        "activity.grid_x": False
    })
    before = json.dumps(row, sort_keys=True)
    result = capture._report.analyze(dict(backend="future",
                                          associations=[row]))
    event = result["events"][0]
    assert event["device_id"] is event["context_id"] is None
    assert event["stream_id"] == 0
    assert all(event["metrics"][key] is None
               for key in ("activity.bytes", "activity.api_success",
                           "activity.grid_x"))
    assert before == json.dumps(row, sort_keys=True)


def test_duplicate_scope_and_ambiguous_api_never_choose_arbitrary_match(
        capture):
    api = record(correlation_id=1)
    api["metrics"].update({
        "activity.kind": "runtime",
        "activity.process_id": 1
    })
    kernel = record(correlation_id=1, scope_id=7)
    kernel["metrics"]["activity.process_id"] = 1
    launches = [
        dict(scope_id=7, name="kernel", id=name, binary_id="b", arguments={})
        for name in ("a", "b")
    ]
    result = capture._report.analyze(
        dict(backend="future",
             associations=[api, api, kernel],
             launches=launches))
    assert "launch_id" not in result["events"][-1]
    assert not any(
        e["ph"] in ("s", "f")
        for e in capture._report.chrome_trace(result)["traceEvents"])
    # A missing device ID does not remove a reliable API correlation.
    result = capture._report.analyze(
        dict(backend="future", associations=[api, kernel]))
    assert len([
        e for e in capture._report.chrome_trace(result)["traceEvents"]
        if e["ph"] in ("s", "f")
    ]) == 2


def test_late_export_failure_has_no_completion_manifest(
        capture, tmp_path, monkeypatch):
    base = tmp_path / "capture"
    base.with_suffix(".vendor.json").write_text(
        json.dumps(dict(backend="future", associations=[])))
    base.with_suffix(".hatchet").write_text("[]")
    original = Path.write_text

    def fail_tree(path, *args, **kwargs):
        if path.name == "call_tree.json":
            raise OSError("disk failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_tree)
    with pytest.raises(OSError, match="disk failure"):
        capture.export_capture(base, tmp_path / "out")
    assert not (tmp_path / "out/manifest.json").exists()
    assert base.with_suffix(".vendor.json").exists()


def test_counter_merge_preserves_both_producers(capture, tmp_path):
    base = tmp_path / "capture"
    base.with_suffix(".vendor.json").write_text(
        json.dumps(
            dict(backend="future",
                 associations=[],
                 capture={"collector": "native"},
                 availability={
                     "counters": {
                         "status": "unsupported",
                         "reason": "native SDK"
                     }
                 })))
    counters = dict(capture={"tool": "external"},
                    availability={
                        "counters": {
                            "status": "failed",
                            "reason": "external SDK"
                        }
                    },
                    capture_notes=["External collection scope"])
    capture.export_capture(base, tmp_path / "out", counters)
    data = json.loads((tmp_path / "out/ai/context.json").read_text())
    assert data["capture"] == {
        "collector": "native",
        "external_counters": {
            "tool": "external"
        }
    }
    assert data["producer_metadata"][
        "external_counter_availability"] == counters["availability"]
    summary = json.loads((tmp_path / "out/ai/summary.json").read_text())
    assert summary["availability"]["producer"]["counters"][
        "status"] == "unsupported"


@pytest.mark.skipif(__import__("os").environ.get("FLAGPRISM_TEST_BROWSER")
                    != "1",
                    reason="Opt-in browser regression")
def test_untimed_and_unknown_browser(capture, tmp_path):
    from playwright.sync_api import sync_playwright
    rows = [record(op_name=None), record(start_time_ns=None, op_name=None)]
    report = capture._report.analyze(
        dict(backend="future",
             associations=rows,
             capture={"external_counters": {
                 "replay_mode": "application"
             }},
             counter_groups=[
                 dict(name="kernel",
                      source="external",
                      scope="process",
                      metrics=[
                          dict(name="cycles",
                               unit="cycles",
                               value=12,
                               instances=[])
                      ])
             ]))
    page_path = tmp_path / "index.html"
    page_path.write_text(capture._report.render(report))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,
                                             args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(page_path.as_uri())
        assert "1 untimed records" in page.locator(
            "#qualitySummary").inner_text()
        assert "1 timed kernel observations" in page.locator(
            "#samplingNote").inner_text()
        assert "run-to-run variability" in page.locator(
            "#samplingNote").inner_text()
        assert "future_sdk" in page.locator("#samplingScope").inner_text()
        page.locator("#search").fill("unknown")
        assert "Replay: application" in page.locator(
            "#counterScope").inner_text()
        assert not errors
        browser.close()


@pytest.mark.parametrize("start,end,status", [(None, None, "unknown"),
                                              (0, 200, "unknown"),
                                              (-1, 200, "invalid"),
                                              (True, 200, "invalid"),
                                              (300, 200, "invalid"),
                                              (100, 100, "available")])
def test_time_eligibility_is_explicit(capture, start, end, status):
    result = capture._report.analyze(
        dict(backend="future",
             associations=[record(start_time_ns=start, end_time_ns=end)]))
    event = (result["events"] + result["untimed_events"])[0]
    assert event["timing_status"] == status
    assert event["duration_us"] == (0 if status == "available" else None)
    assert result["origin_ns"] == (100 if status == "available" else None)


def test_missing_names_in_descriptive_comparison(capture):
    rows = [record(op_name=None), record(op_name="api")]
    for row in rows:
        row["metrics"]["activity.kind"] = "runtime"
    result = capture._report.analyze(dict(backend="future", associations=rows))
    assert len(capture._report.comparison(result, result)) == 2


@pytest.mark.parametrize(
    "metrics",
    [[], [{
        "name": "metric",
        "unit": "cycles",
        "value": None,
        "instances": []
    }]])
def test_empty_counter_groups_are_not_measurements(capture, tmp_path, metrics):
    document = dict(backend="future",
                    associations=[],
                    counter_groups=[
                        dict(name="kernel",
                             source="SDK",
                             scope="process",
                             metrics=metrics)
                    ],
                    availability={
                        "counters": {
                            "status": "unsupported",
                            "reason": "No API"
                        }
                    })
    result = capture._report.analyze(document)
    capture._report.write_bundle(result, document, tmp_path / "bundle")
    summary = json.loads((tmp_path / "bundle/ai/summary.json").read_text())
    assert summary["availability"]["counters"] == document["availability"][
        "counters"]


def test_cli_workload_error_still_flushes(monkeypatch):
    cli = importlib.import_module("flagtree.profiler.cli")
    monkeypatch.setenv("FLAGPRISM_CAPTURE_INTERNAL", "1")
    calls = []
    monkeypatch.setattr(cli, "start", lambda *a, **kw: calls.append("start"))
    monkeypatch.setattr(cli, "finalize", lambda: calls.append("finalize"))

    def failing(*args):
        raise SystemExit(7)

    monkeypatch.setattr(cli, "do_setup_and_execute", failing)
    args = SimpleNamespace(backend="future",
                           ixkn=False,
                           name="capture",
                           context="shadow",
                           data="tree",
                           mode=None,
                           hook=None)
    with pytest.raises(SystemExit) as caught:
        cli.run_profiling(args, ["workload.py"])
    assert caught.value.code == 7
    assert calls == ["start", "finalize"]


def test_cleanup_error_does_not_skip_other_cleanup(monkeypatch):
    profile = importlib.import_module("flagtree.profiler.profile")
    monkeypatch.setattr(profile, "_active_sessions",
                        {7: {
                            "instrumentation_hook": True
                        }})
    calls = []

    def failing(*args):
        calls.append("hooks")
        raise RuntimeError("hook failure")

    monkeypatch.setattr(profile.HookManager, "unregister", failing)
    monkeypatch.setattr(profile, "_deactivate_instrumentation",
                        lambda: calls.append("instrumentation"))
    monkeypatch.setattr(profile, "set_profiling_off",
                        lambda: calls.append("flags"))
    with pytest.raises(RuntimeError, match="hook failure"):
        profile._drop_session(7)
    assert calls == ["hooks", "instrumentation", "flags"]
    assert not profile._active_sessions


def test_failed_hook_does_not_strand_other_hooks(monkeypatch):
    from flagtree.profiler.hooks.hook import HookManager
    calls = []

    class Failing:

        def deactivate(self):
            calls.append("failed")
            raise RuntimeError("custom hook failed")

    class Working:

        def deactivate(self):
            calls.append("released")

    a, b = Failing(), Working()
    monkeypatch.setattr(HookManager, "active_hooks", [a, b])
    monkeypatch.setattr(HookManager, "session_hooks", {7: {a: True, b: True}})
    with pytest.raises(RuntimeError, match="custom hook failed"):
        HookManager.unregister()
    assert calls == ["failed", "released"]
    assert not HookManager.active_hooks and not HookManager.session_hooks


def test_debugger_cleanup_failure_still_resets_compiler_mode(monkeypatch):
    profile = importlib.import_module("flagtree.profiler.profile")
    debugger = importlib.import_module("flagtree.debugger")
    calls = []

    def failing():
        raise RuntimeError("debugger cleanup failed")

    monkeypatch.setattr(debugger, "deactivate", failing)
    monkeypatch.setattr(profile, "_set_instrumentation_mode",
                        lambda mode: calls.append(mode))
    with pytest.raises(RuntimeError, match="debugger cleanup failed"):
        profile._deactivate_instrumentation()
    assert calls == [""]


def test_cli_system_exit_prints_recovery_path(capture, tmp_path, monkeypatch,
                                              capsys):
    stage = tmp_path / "stage"
    stage.mkdir()
    monkeypatch.setattr(capture.tempfile, "mkdtemp", lambda **kw: str(stage))
    args = SimpleNamespace(backend="future",
                           counters=False,
                           name=str(tmp_path / "out"),
                           metadata=None)

    def execute(*args):
        raise SystemExit(7)

    with pytest.raises(SystemExit) as caught:
        capture.run_capture(args, ["workload.py"], execute)
    assert caught.value.code == 7
    assert str(stage) in capsys.readouterr().err
    assert stage.exists()


def test_kernel_previews_link_complete_evidence(capture, tmp_path):
    row = record(scope_id=7)
    arguments = {
        "tile_for_future_chip": {
            "kind": "scalar_or_metadata",
            "value": 128
        },
        "enabled": {
            "kind": "scalar_or_metadata",
            "value": False
        },
        "optional": {
            "kind": "scalar_or_metadata",
            "value": None
        },
        "compound": {
            "kind": "scalar_or_metadata",
            "value": [1, 2]
        },
        "large": {
            "kind": "scalar_or_metadata",
            "value": "x" * 9000
        },
        "tensor": {
            "kind": "tensor",
            "shape": [16],
            "dtype": "float32"
        }
    }
    document = dict(backend="future",
                    associations=[row],
                    launches=[
                        dict(id="launch",
                             scope_id=7,
                             name="kernel",
                             binary_id="binary",
                             arguments=arguments,
                             grid=[1, 1, 1])
                    ],
                    binaries=[
                        dict(id="binary",
                             compiler_metadata={
                                 "future_option": [1, 2],
                                 "stages": 3
                             },
                             source={
                                 "path": "/actual/backend/kernel.py",
                                 "text": "def kernel(): pass"
                             })
                    ])
    result = capture._report.analyze(document)
    output = tmp_path / "bundle"
    capture._report.write_bundle(result, document, output)
    group = json.loads((output / "ai/kernels.json").read_text())["groups"][0]
    assert group["scalar_arguments"]["values"] == {
        "tile_for_future_chip": 128,
        "enabled": False,
        "optional": None
    }
    assert group["scalar_arguments"]["omitted_count"] == 2
    assert group["scalar_arguments"]["status"] == "partial"
    assert json.loads((output / group["arguments_file"]
                       ).read_text())[group["argument_id"]] == arguments
    assert group["compiler_metadata"]["values"]["future_option"] == [1, 2]
    assert (output /
            group["source"]["text_file"]).read_text() == "def kernel(): pass"
    assert group["source"]["path"] == "/actual/backend/kernel.py"
    assert "text" not in group["source"]
    assert group["measurement"]["sample_note"] == "single_observation"
    assert group["measurement"]["sources"] == [{
        "source": "future_sdk",
        "count": 1
    }]


def test_preview_budget_unknown_and_empty(capture):
    preview = capture._report._preview
    assert preview(None) == dict(status="unknown",
                                 values=None,
                                 omitted_count=None)
    assert preview({}) == dict(status="complete", values={}, omitted_count=0)
    data = {str(i): "中" * 100 for i in range(200)}
    result = preview(data)
    assert len(
        json.dumps(result["values"], ensure_ascii=False,
                   separators=(',', ':')).encode()) <= 8192
    assert result["omitted_count"] + len(result["values"]) == 200
    assert all(value == "中" * 100 for value in result["values"].values())


def test_structure_issues_preserve_metadata_under_werror(capture, tmp_path):
    import warnings
    document = dict(backend="future", associations=[])
    metadata = {
        "workload": {
            "operator": 7,
            "parameters": {},
            "measurement": {
                "iterations": True
            },
            "validation": {
                "status": "passed"
            }
        },
        "software": "custom text",
        "custom": [1, 2]
    }
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        capture._report.write_bundle(capture._report.analyze(document),
                                     document, tmp_path / 'bundle', metadata)
    context = json.loads((tmp_path / 'bundle/ai/context.json').read_text())
    assert context['supplied'] == metadata
    assert {i['path']
            for i in context['metadata_issues']} == {
                '/workload/operator', '/workload/measurement/iterations',
                '/software'
            }
    assert '/workload/operator' not in context['metadata_missing_fields']
    assert '/workload/warmup' in context['metadata_missing_fields']
    assert 'high_level_operator_semantics' in context['sections']['workload'][
        'missing']


@pytest.mark.parametrize('metadata', [{
    'x': float('nan')
}, {
    1: 'key'
}, {
    'x': object()
}, []])
def test_metadata_invalid_before_output(capture, tmp_path, metadata):
    document = dict(backend='future', associations=[])
    with pytest.raises(ValueError, match='metadata'):
        capture._report.write_bundle(capture._report.analyze(document),
                                     document, tmp_path / 'out', metadata)
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('bad_update', [{
    'x': object()
}, ['serializable', 'but_not_object']])
def test_invalid_final_metadata_saves_capture_and_prior_snapshot(
        tmp_path, monkeypatch, bad_update):
    profile = importlib.import_module('flagtree.profiler.profile')
    monkeypatch.setattr(profile, '_active_sessions', {})
    monkeypatch.setattr(profile, 'is_command_line', lambda: False)
    native_paths = []

    def start(name, *args):
        native_paths.append(name)
        return 7

    def finalize(*args):
        Path(native_paths[0]).with_suffix('.vendor.json').write_text(
            json.dumps(dict(backend='future', associations=[])))

    monkeypatch.setattr(profile, 'profiler_native',
                        SimpleNamespace(start=start, finalize=finalize))
    supplied = {
        'workload': {
            'operator': 'original',
            'parameters': {
                'shape': (16, )
            }
        },
        'software': {
            'version': '1'
        }
    }
    output = tmp_path / 'out'
    session = profile.start(str(output), backend='future', metadata=supplied)
    supplied['workload']['operator'] = 'mutated'
    assert profile._active_sessions[session]['metadata']['workload'][
        'operator'] == 'original'
    assert profile.start(str(output),
                         backend='future',
                         metadata={'software': {
                             'version': '2'
                         }}) == session
    with pytest.raises(ValueError, match='Capture finalized and saved'):
        profile.finalize(session, metadata=bad_update)
    assert (output / 'manifest.json').exists()
    context = json.loads((output / 'ai/context.json').read_text())
    assert context['supplied']['workload']['operator'] == 'original'
    assert context['supplied']['software'] == {'version': '2'}
    rejected = context['rejected_metadata_updates'][0]
    assert rejected['applied'] is False
    assert rejected['raw_preserved'] == isinstance(bad_update, list)
    if isinstance(bad_update, list):
        assert rejected['value'] == bad_update
    assert not profile._active_sessions
    assert not Path(native_paths[0]).parent.exists()


def test_caller_iterations_do_not_invent_observations(capture, tmp_path):
    document = dict(backend='future', associations=[record()])
    result = capture._report.analyze(document)
    capture._report.write_bundle(
        result, document, tmp_path / 'out',
        {'workload': {
            'measurement': {
                'iterations': 100
            }
        }})
    report = json.loads((tmp_path / 'out/report/report.json').read_text())
    assert report['sampling']['timed_kernel_observations'] == 1
    assert report['sampling']['single_sample_kernel_groups'] == 1
    assert report['supplied_measurement']['value']['iterations'] == 100


def test_metadata_large_integer_tolerance(capture, tmp_path):
    document = dict(backend="future", associations=[record()])
    capture._report.write_bundle(capture._report.analyze(document), document,
                                 tmp_path / "out", {
                                     "workload": {
                                         "validation": {
                                             "status": "not_checked",
                                             "atol": 10**400
                                         }
                                     }
                                 })
    context = json.loads((tmp_path / "out/ai/context.json").read_text())
    assert context["supplied"]["workload"]["validation"]["atol"] == 10**400


@pytest.mark.parametrize('value', [[], {'workload': float('nan')}])
def test_cli_metadata_preflight(capture, tmp_path, monkeypatch, value):
    path = tmp_path / 'context.json'
    path.write_text(json.dumps(value))
    output = tmp_path / 'out'
    monkeypatch.setattr(capture, 'capture_backend',
                        lambda _: SimpleNamespace())
    args = SimpleNamespace(backend='future',
                           counters=False,
                           name=str(output),
                           metadata=str(path))
    executed = []
    with pytest.raises(ValueError, match='metadata'):
        capture.run_capture(args, ['workload.py'],
                            lambda *_: executed.append(True))
    assert not executed
    assert not output.exists()


def test_evidence_coverage_counts_links_and_preserves_untimed(
        capture, tmp_path):
    rows = [
        record(scope_id=7),
        record(scope_id=7, start_time_ns=None),
        record(scope_id=8)
    ]
    launches = [
        dict(id=name,
             scope_id=scope,
             name='kernel',
             binary_id='binary',
             arguments={},
             grid=[1, 1, 1]) for name, scope in [('linked', 7), ('orphan', 9)]
    ]
    document = dict(backend='future',
                    associations=rows,
                    launches=launches,
                    binaries=[
                        dict(id='binary',
                             source={'text': 'kernel source'},
                             compiler_metadata={})
                    ])
    output = tmp_path / 'out'
    capture._report.write_bundle(capture._report.analyze(document), document,
                                 output)
    summary = json.loads((output / 'ai/summary.json').read_text())
    e = summary['evidence_overview']
    assert e['kernel_events'] == {'total': 3, 'timed': 2, 'untimed': 1}
    assert e['linked_kernel_events'] == dict(launch=2,
                                             arguments=2,
                                             binary=2,
                                             source_snapshot=2)
    assert e['inventory'] == dict(launch_records=2,
                                  argument_sets=1,
                                  binaries=1,
                                  source_snapshots=1)
    assert json.loads(
        (output / 'report/report.json').read_text())['evidence_overview'] == e
    for path in e['files'].values():
        if path is not None:
            assert (output / path).exists()
    assert '2 timed, 1 untimed' in (output / 'ai/README.md').read_text()


@pytest.mark.parametrize('kernel', [False, True])
def test_evidence_absence_does_not_infer_failure(capture, tmp_path, kernel):
    row = record()
    if not kernel:
        row['metrics']['activity.kind'] = 'runtime'
    document = dict(backend='future', associations=[row])
    caller = {'compilation': {'source': '/caller/guess.py'}}
    output = tmp_path / 'out'
    capture._report.write_bundle(capture._report.analyze(document), document,
                                 output, caller)
    summary = json.loads((output / 'ai/summary.json').read_text())
    e = summary['evidence_overview']
    assert summary['availability']['events']['status'] == 'available'
    assert e['kernel_events']['total'] == int(kernel)
    assert e['linked_kernel_events'] == dict(launch=0,
                                             arguments=0,
                                             binary=0,
                                             source_snapshot=0)
    assert e['files']['binaries'] is None
    assert e['files']['launches'] is None
    report = json.loads((output / 'report/report.json').read_text())
    assert report['observed_device'] is None
    assert report['caller_context'] == caller
    readme = (output / 'ai/README.md').read_text()
    assert ('No kernel activity records were observed' in readme) is not kernel
    assert 'not independently verified' in readme


@pytest.mark.skipif(__import__('os').environ.get('FLAGPRISM_TEST_BROWSER')
                    != '1',
                    reason='Opt-in browser regression')
@pytest.mark.parametrize('kernel', [False, True])
def test_evidence_browser_provenance(capture, tmp_path, kernel):
    from playwright.sync_api import sync_playwright
    row = record()
    if not kernel:
        row['metrics']['activity.kind'] = 'runtime'
    document = dict(backend='future',
                    associations=[row],
                    session_metadata={'device': {
                        'name': 'observed-device'
                    }})
    supplied = {
        'hardware': {
            'name': '</script><script>window.injected=true</script>'
        },
        'workload': {
            'operator': 'claimed-operator'
        }
    }
    output = tmp_path / 'out'
    capture._report.write_bundle(capture._report.analyze(document), document,
                                 output, supplied)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((output / 'report/index.html').as_uri())
        assert page.locator('#evidencePanel').is_visible()
        assert page.locator('#evidenceAbsence').is_visible() is not kernel
        assert f'{int(kernel)} observed kernel events' in page.locator(
            '#evidenceCounts').inner_text()
        assert 'observed-device' in page.locator(
            '#observedDevice').text_content()
        assert 'claimed-operator' in page.locator(
            '#callerContext').text_content()
        assert page.evaluate('window.injected === undefined')
        assert page.evaluate(
            'document.documentElement.scrollWidth <= innerWidth')
        assert not errors
        browser.close()
