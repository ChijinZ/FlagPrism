"""TCU CSV import is testable without the SDK, device, or native FlagTree."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    "tcu_importer",
    Path(__file__).parents[1] / "python/flagtree_profiler/tcu.py")
tcu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcu)

CSV = '''Type,Time(%),Time,Calls,Avg,Min,Max,Name
GCU activities,100.00%,276.51us,2,138.25us,135.18us,141.33us,vector_add
,Kernel Name,Invocations
,"vector_add <<<256,1,1>>> <<<4,1,1>>> <<<1,1,1>>>",2
,SIP/BUSY,CYCLE,3217.25
Type,Die,SIP,Minimum,Maximum,Average,Invocations
GCU Metric,0,0,3557,3557,3557,1
GCU Metric,1,0,3017,3017,3017,1
,SIP/L1_ICACHE_MISS,EVENT,0
Type,Die,SIP,Minimum,Maximum,Average,Invocations
GCU Metric,0,0,0,0,0,1
'''


def test_import_preserves_scope_units_and_replay_counts(tmp_path):
    path = tmp_path / "capture.csv"
    path.write_text(CSV)
    result = tcu.import_csv(path)
    assert result["associations"] == []  # No fabricated launch timestamps.
    group = result["counter_groups"][0]
    assert group["scope"] == "kernel_config_aggregate"
    assert group["invocations"] == 2
    busy, miss = group["metrics"]
    assert busy["value"] == 3217.25 and busy["unit"] == "CYCLE"
    assert busy["instances"][0]["count"] == 1
    assert miss["value"] == 0 and "not a cache miss rate" in miss["description"]
    assert result["kernel_summaries"][0]["count"] == 2


@pytest.mark.parametrize("suffix",
                         ["unexpected,row\n", ",Kernel Name,Invocations\n"])
def test_truncated_or_unknown_rows_fail_instead_of_partial_import(
        tmp_path, suffix):
    path = tmp_path / "capture.csv"
    path.write_text(CSV + suffix)
    with pytest.raises(ValueError):
        tcu.import_csv(path)


@pytest.mark.parametrize("value", ["NaN", "inf", "-1"])
def test_invalid_counter_value_rejected(value):
    with pytest.raises(ValueError):
        tcu.number(value)


def test_failed_capture_does_not_retry_or_emit_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(tcu.shutil, "which", lambda _: "/tool/tcu")
    invocations = []

    def run(command, **kwargs):
        invocations.append(command)
        return SimpleNamespace(stdout="Build number: test",
                               returncode=0 if "--version" in command else 1)

    monkeypatch.setattr(tcu.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="exited 1"):
        tcu.collect(["python3", "workload.py"], tmp_path)
    assert len(invocations) == 2
    assert invocations[1][invocations[1].index("--replay-mode") + 1] == "none"
    assert not (tmp_path / "manifest.json").exists()


def test_collect_preserves_metrics_and_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(tcu.shutil, "which", lambda _: "/tool/tcu")

    def run(command, **kwargs):
        if "--version" not in command:
            Path(command[command.index("--export-csv") + 1]).write_text(CSV)
        return SimpleNamespace(stdout="Build number: test", returncode=0)

    monkeypatch.setattr(tcu.subprocess, "run", run)
    result = tcu.collect(["python3", "workload.py"], tmp_path)
    assert result["capture"]["replay_mode"] == "none"
    assert len(result["counter_groups"][0]["metrics"]) == 2
    with pytest.raises(ValueError, match="omitted requested"):
        tcu.collect(["python3", "workload.py"],
                    tmp_path,
                    metrics="SIP/2D_EFFICIENCY")
