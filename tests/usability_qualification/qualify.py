"""Server-Docker qualification coordinator; never imports workload/math locally.

Baseline freezes eligibility BEFORE profile executes. Failed eligible cases
remain failures. No private profiler APIs, environment knobs, or site selection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PRIMARY = ["rational_blend", "reflected_contrast", "weighted_covariance",
           "absolute_deviation", "squared_distance", "gated_product"]
CASES = PRIMARY + ["runtime_recurrence"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def execute(command, dest, env, timeout):
    start = time.monotonic()
    with (dest / "stdout.log").open("wb") as out, (dest / "stderr.log").open("wb") as err:
        proc = subprocess.Popen(command, stdout=out, stderr=err, env=env,
                                start_new_session=True)
        write(dest / "active.json", {"pid": proc.pid, "argv": command,
                                      "timeout_s": timeout})
        try:
            code = proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code, timed_out = proc.returncode, True
    result = {"argv": command, "pid": proc.pid, "returncode": code,
              "timeout": timed_out, "wall_s": time.monotonic() - start}
    write(dest / "terminal.json", result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["baseline", "profile"])
    p.add_argument("--backend", choices=["nvidia", "enflame", "ascend"], required=True)
    p.add_argument("--device", required=True)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--booking", type=Path, required=True,
                   help="root-issued booking JSON with backend/container/device/owner")
    p.add_argument("--product-freeze", type=Path,
                   help="required for profile: actual source/install/native/plugin/document hashes")
    args = p.parse_args()
    booking = json.loads(args.booking.read_text())
    assert Path("/.dockerenv").exists(), "server Docker required"
    assert os.environ.get("FLAGPRISM_QUALIFICATION_SERVER_DOCKER") == "1", "explicit server dispatch required"
    assert booking["backend"] == args.backend and booking["device"] == args.device
    assert booking["owner"] == "usability_qualification" and booking["container"]
    args.root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        assert sha(HERE / name) == expected, f"heldout source changed: {name}"
    eligibility_path = args.root / "eligibility.json"
    if args.phase == "baseline":
        assert not eligibility_path.exists(), "never overwrite frozen baseline evidence"
        eligibility = {"backend": args.backend, "source_manifest_sha256": sha(HERE / "manifest.json"),
                       "booking": booking, "cases": []}
        write(args.root / "baseline-started.json", eligibility)
        for case in CASES:
            for si in [0, 1]:
                for ci in [0, 1]:
                    key = f"{case}-s{si}-c{ci}"
                    dest = args.root / "baseline" / key
                    dest.mkdir(parents=True, exist_ok=False)
                    env = dict(os.environ, TRITON_CACHE_DIR=str(dest / "cache"))
                    command = [sys.executable, str(HERE / "workload.py"), "--case", case,
                               "--shape-index", str(si), "--config-index", str(ci),
                               "--backend", args.backend, "--device", args.device,
                               "--receipt", str(dest / "receipt.json"),
                               "--startup-ledger", str(dest / "startup.jsonl")]
                    result = execute(command, dest, env, 300)
                    receipt = dest / "receipt.json"
                    ledger = dest / "startup.jsonl"
                    eligible = result["returncode"] == 0 and receipt.exists()
                    assert not eligible or len(ledger.read_text().splitlines()) == 1
                    entry = {"key": key, "case": case, "shape_index": si,
                             "config_index": ci, "eligible": eligible,
                             "baseline": result, "receipt_sha256": sha(receipt) if receipt.exists() else None}
                    if eligible:
                        actual = json.loads(receipt.read_text())
                        baseline_compile = actual["calls"][0]["compile_launch_sync_wall_s"]
                        entry["cold_timeout_s"] = min(300, max(120, 3 * baseline_compile))
                    eligibility["cases"].append(entry)
                    write(args.root / "baseline-progress.json", eligibility)
        write(eligibility_path, eligibility)
        write(args.root / "eligibility-seal.json", {"sha256": sha(eligibility_path)})
        return
    assert args.product_freeze and args.product_freeze.is_file(), "freeze installed candidate and public docs first"
    eligibility = json.loads(eligibility_path.read_text())
    seal = json.loads((args.root / "eligibility-seal.json").read_text())
    assert sha(eligibility_path) == seal["sha256"]
    assert eligibility["source_manifest_sha256"] == sha(HERE / "manifest.json")
    profile_dir = args.root / "profile"
    profile_dir.mkdir(exist_ok=False)  # repair passes require a NEW evidence root
    write(profile_dir / "product-freeze.json", json.loads(args.product_freeze.read_text()))
    write(profile_dir / "booking.json", booking)
    outcomes = []
    for entry in eligibility["cases"]:
        if not entry["eligible"]:
            outcomes.append({"key": entry["key"], "status": "baseline_ineligible"})
            continue
        shared_cache = profile_dir / "cache" / entry["key"]
        for repetition in [0, 1]:
            dest = profile_dir / f"{entry['key']}-run{repetition}"
            dest.mkdir()
            env = dict(os.environ, TRITON_CACHE_DIR=str(shared_cache))
            command = [sys.executable, "-m", "flagtree.profiler.cli", "--detail", "auto",
                       "-n", str(dest / "bundle"), str(HERE / "workload.py"),
                       "--case", entry["case"], "--shape-index", str(entry["shape_index"]),
                       "--config-index", str(entry["config_index"]), "--backend", args.backend,
                       "--device", args.device, "--receipt", str(dest / "receipt.json"),
                       "--startup-ledger", str(dest / "startup.jsonl")]
            # Entire command capped at cold budget: stricter than compiler-only
            # budget. Export <=60 s separately needs public timing evidence.
            result = execute(command, dest, env, entry["cold_timeout_s"])
            failures = []
            if result["returncode"] != 0:
                failures.append("default_cli_failed")
            receipt = dest / "receipt.json"
            if not receipt.exists():
                failures.append("missing_numerical_receipt")
            else:
                actual = json.loads(receipt.read_text())
                baseline = json.loads((args.root / "baseline" / entry["key"] / "receipt.json").read_text())
                for field in ["input_sha256", "config", "shape", "grid"]:
                    if actual[field] != baseline[field]:
                        failures.append(f"baseline_mismatch:{field}")
                # Each path independently passed the ORIGINAL CPU tolerance.
                # Identical output bytes are recorded, not required: harmless
                # compiler contraction differences must not alter the oracle.
            ledger = dest / "startup.jsonl"
            if not ledger.exists() or len(ledger.read_text().splitlines()) != 1:
                failures.append("hidden_script_replay_or_no_startup")
            bundle = dest / "bundle"
            total_bytes = sum(x.stat().st_size for x in bundle.rglob("*") if x.is_file())
            if total_bytes > 64 * 1024 * 1024:
                failures.append("bundle_exceeds_64MiB")
            outcome = {"key": entry["key"], "repetition": repetition,
                       "cache_state": "cold" if repetition == 0 else "warm",
                       "process": result, "bundle_bytes": total_bytes,
                       "failures": failures,
                       "status": "requires_public_report_validation" if not failures else "fail"}
            outcomes.append(outcome)
            write(profile_dir / "outcomes.json", outcomes)


if __name__ == "__main__":
    main()
