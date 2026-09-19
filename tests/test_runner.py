"""Exercise acceptance decisions without a device or an installed FlagTree."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("fault_at", ["capture", "baseline"])
@pytest.mark.parametrize("source", ["error", "traceback", "log"])
def test_device_fault_never_becomes_warning(tmp_path, monkeypatch, fault_at,
                                            source):
    code, summary, calls = _run(tmp_path, monkeypatch, fault_at, source)
    assert code == 1
    assert summary["status"] != "PASS"
    assert summary["counts"] == {"ERROR": 1, "BLOCKED": 1}
    row = summary["results"][0]
    assert not row["accepted"]
    fault = row if fault_at == "capture" else row["baseline_result"]
    assert fault["device_fault"]
    assert calls == (["debugger"]
                     if fault_at == "capture" else ["debugger", "execute"])


@pytest.mark.parametrize("baseline_passes", [False, True])
def test_ordinary_failure_keeps_baseline_policy(tmp_path, monkeypatch,
                                                baseline_passes):
    code, summary, calls = _run(tmp_path,
                                monkeypatch,
                                baseline_passes=baseline_passes)
    expected = "ERROR" if baseline_passes else "WARNING"
    assert code == int(baseline_passes)
    assert summary["counts"] == {expected: 2}
    assert calls == ["debugger", "execute", "profiler", "execute"]


def _run(tmp_path,
         monkeypatch,
         fault_at=None,
         source=None,
         baseline_passes=False):
    path = Path(__file__).resolve().parents[1] / "test.py"
    spec = importlib.util.spec_from_file_location("operator_runner", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    calls = []

    def command(argv, log, timeout):
        stage = argv[argv.index("--stage") + 1]
        calls.append(stage)
        result_path = Path(argv[argv.index("--result") + 1])
        case = json.loads(Path(argv[argv.index("--worker") + 1]).read_text())
        passed = stage == "execute" and baseline_passes
        data = dict(op=case["op"],
                    case_id=case["case_id"],
                    stage=stage,
                    status="PASS" if passed else "FAIL")
        log.write_text("")
        if not passed:
            data["error"] = "Unsupported operator"
        if ((fault_at == "capture" and stage != "execute")
                or (fault_at == "baseline" and stage == "execute")):
            message = "topsErrorInvalidDevice: device is out of service"
            if source == "log":
                log.write_text(message)
            else:
                data[source] = message
        runner.write_json(result_path, data)
        return 0 if passed else 1

    monkeypatch.setattr(runner, "command", command)
    monkeypatch.setattr(runner, "git_revision", lambda path: "test")
    monkeypatch.setattr(
        runner.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="True\n"))
    monkeypatch.setattr(sys, "argv", [
        str(path), "--out",
        str(tmp_path), "--ops", "abs", "--min-ops", "1", "--stages",
        "debugger", "profiler", "--level", "1"
    ])
    code = runner.main()
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text())
    return code, summary, calls
