"""CANN msprof replay collection and lossless per actor counter import.

PMU CSV rows describe independent replay aggregates. Their engine activities
can overlap; no conversion to exclusive timeline intervals is performed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid

_MISSING = {"", "NA", "N/A", "nan", "None"}


def _unit(name):
    match = re.search(r"\(([^)]+)\)$", name)
    if match:
        return match.group(1)
    if name.endswith("_ratio") or name.endswith("_rate"):
        return "ratio"
    if "cycles" in name:
        return "cycles"
    return "count"


def import_msprof(path, *, replay_id=None):
    """Import each OPPROF directory separately, preserving actor and raw data.

    Numeric missing values stay null. Nonfinite or malformed numbers fail with
    a file/row/column diagnostic. CSV names and values are never renamed into
    inferred busy time or associated with a foreground launch.
    """
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    files = sorted(root.rglob("*.csv")) if root.is_dir() else [root]
    groups, raw = [], []
    for file in files:
        if file.stem not in {"PipeUtilization", "ArithmeticUtilization", "Memory", "MemoryL0", "L2Cache", "ResourceConflictRatio", "OpBasicInfo"}:
            continue
        relative = str(file.relative_to(root)) if root.is_dir() else file.name
        raw.append({"path": relative, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
        with file.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if file.stem == "OpBasicInfo":
                for row_index, row in enumerate(reader):
                    groups.append({"name": "OpBasicInfo", "scope": "independent_replay_metadata", "source": "cann_msprof_op", "replay_id": replay_id, "capture_id": str(file.parent.relative_to(root)) if root.is_dir() else file.parent.name, "metrics": [], "raw_row": row, "row_index": row_index})
                continue
            if not reader.fieldnames or not {"block_id", "sub_block_id"}.issubset(reader.fieldnames):
                raise ValueError(f"{relative}: missing actor identity columns")
            for row_index, row in enumerate(reader):
                if None in row or not row.get("block_id") or not row.get("sub_block_id"):
                    raise ValueError(f"{relative}:{row_index + 2}: malformed row or missing actor")
                actor = f"{row['block_id']}:{row['sub_block_id']}"
                metrics = []
                for name, value in row.items():
                    if not name or name in {"block_id", "sub_block_id"}:
                        continue
                    value = value.strip() if isinstance(value, str) else value
                    if value in _MISSING or value is None:
                        number = None
                    else:
                        try:
                            number = float(value)
                        except ValueError as exc:
                            raise ValueError(f"{relative}:{row_index + 2}:{name}: invalid number {value!r}") from exc
                        if not math.isfinite(number):
                            raise ValueError(f"{relative}:{row_index + 2}:{name}: nonfinite number")
                    metrics.append({"name": name, "unit": _unit(name), "value": number})
                groups.append({"name": file.stem, "scope": "independent_replay_actor", "source": "cann_msprof_op", "replay_id": replay_id, "capture_id": str(file.parent.relative_to(root)) if root.is_dir() else file.parent.name, "actor": actor, "metrics": metrics, "raw_row": row, "row_index": row_index, "activity_overlap": "allowed", "measurement_pass": file.stem, "invocation_identity": "not_reported_by_sdk", "source_launch_association": "unassociated"})
    if not groups:
        raise ValueError(f"No supported msprof op counter CSVs under {root}")
    devices = {}
    for group in groups:
        if group['name'] != 'OpBasicInfo':
            continue
        value = group['raw_row'].get('Device Id')
        if value is None or value.strip() in _MISSING:
            continue
        if not re.fullmatch(r'\d+', value.strip()):
            raise ValueError(f"{group['capture_id']}: invalid SDK Device Id {value!r}")
        devices.setdefault(group['capture_id'], set()).add(int(value.strip()))
    for group in groups:
        reported = devices.get(group['capture_id'], set())
        group['actual_device_id'] = next(iter(reported)) if len(reported) == 1 else None
    return {"backend": "cann", "schema_version": 1, "counter_groups": groups, "raw_inputs": raw, "replay_id": replay_id, "clock_alignment": "independent_replay", "actual_device_ids": sorted({device for reported in devices.values() for device in reported})}


def collect_msprof(command, output, *, metrics=("ArithmeticUtilization", "PipeUtilization"), replay_mode="independent", env=None, kernel_name=None, launch_count=1, warm_up=0, timeout=300, expected_device_id=None):
    """Explicitly replay an argv application with msprof op and save provenance.

    Calling this function authorizes replay of the supplied application. Output
    must be new; failure receipts survive and no results are reported as success.
    """
    if replay_mode != "independent":
        raise ValueError("CANN msprof op supports only independent replay")
    if not command or isinstance(command, str):
        raise ValueError("command must be a nonempty argv sequence")
    if isinstance(metrics, str):
        metrics = tuple(value.strip() for value in metrics.split(',') if value.strip())
    else:
        metrics = tuple(metrics)
    if not metrics or any(not isinstance(value, str) or not value.strip() for value in metrics):
        raise ValueError('metrics must contain nonempty SDK metric names')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be finite and positive')
    if any(type(value) is not int or value < minimum for value, minimum in ((launch_count, 1), (warm_up, 0))):
        raise ValueError("launch_count must be positive and warm_up nonnegative")
    if expected_device_id is not None and (type(expected_device_id) is not int or expected_device_id < 0):
        raise ValueError('expected_device_id must be a nonnegative integer or None')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    replay_id = str(uuid.uuid4())
    argv = ["msprof", "op", "--application=" + shlex.join(map(str, command)), "--output=" + str(output / "raw"), "--aic-metrics=" + ",".join(metrics), "--replay-mode=kernel", "--launch-count=" + str(launch_count), "--warm-up=" + str(warm_up)]
    if kernel_name:
        argv.append("--kernel-name=" + kernel_name)
    environment = dict(os.environ)
    if env:
        environment.update(env)
    receipt = {"replay_id": replay_id, "replay_mode": "independent", "sdk_replay_mode": "kernel", "command": argv, "started_unix": time.time(), "timeout_s": timeout, "state": "running", "selected_device_id": expected_device_id, "actual_device_ids": None, "device_selection_policy": "Application owns device selection; expectation validates SDK output and does not switch a device.", "native_foreground_association": "unassociated"}
    receipt_path = output / "receipt.json"
    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2))
    save()
    try:
        version = subprocess.run(["msprof", "--version"], env=environment, capture_output=True, text=True, timeout=30)
        receipt["tool_version"] = (version.stdout + version.stderr).strip()
        receipt['version_probe_exit_code'] = version.returncode
        receipt['tool_version_status'] = 'reported' if version.returncode == 0 else 'unavailable'
        with (output / "collector.log").open("w") as log:
            process = subprocess.Popen(argv, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            receipt["pid"] = process.pid
            save()
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
        receipt["exit_code"] = code
        if code:
            raise RuntimeError(f"msprof failed with exit {code}; see {output / 'collector.log'}")
        document = import_msprof(output / "raw", replay_id=replay_id)
        receipt['actual_device_ids'] = document['actual_device_ids']
        if expected_device_id is not None and document['actual_device_ids'] != [expected_device_id]:
            raise RuntimeError('SDK replay actual device identity is missing or differs from expected_device_id')
        document["collector"] = receipt
        receipt["state"] = "complete"
        receipt['finished_unix'] = time.time()
        (output / "counters.json").write_text(json.dumps(document, indent=2, allow_nan=False))
        return document
    except BaseException as exc:
        receipt["state"] = "failed"
        receipt["error"] = str(exc)
        raise
    finally:
        receipt.setdefault("finished_unix", time.time())
        save()
