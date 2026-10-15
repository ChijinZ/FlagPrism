import functools
import time
import base64
import hashlib
import triton
import os
import json
from pathlib import Path
import pathlib
import tempfile
import shutil
import sys

from .native import runtime_binding
from ._metadata import snapshot as metadata_snapshot
from .hooks import HookManager, InstrumentationHook, LaunchHook
from .flags import set_profiling_off, set_profiling_on, is_command_line
from .mode import BaseMode
from typing import Optional, Union

DEFAULT_PROFILE_NAME = "profile-run"
_CANN_TRITON_LEGACY_ENV = "FLAGTREE_PROFILER_CANN_TRITON_HOOK_LEGACY"
_IR_RECORD_BUFFER_MB_ENV = "FLAGTREE_PROFILER_IR_RECORD_BUFFER_MB"
_IR_RECORD_SIZE_BYTES = 64
_DEFAULT_IR_RECORD_BUFFER_MB = 32
_active_sessions: dict[int, dict[str, object]] = {}
profiler_native = runtime_binding()


def _env_flag_enabled(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on", "legacy"}


def _is_cann_backend(backend: Optional[str]) -> bool:
    return str(backend or "").lower() in {"cann", "ascend", "npu"}


def _is_tianshu_backend(backend: Optional[str]) -> bool:
    return str(backend or "").lower() in {"tianshu", "corex", "iluvatar"}


def _is_mthreads_backend(backend: Optional[str]) -> bool:
    return str(backend or "").lower() in {"mthreads", "musa"}


def _is_enflame_backend(backend: Optional[str]) -> bool:
    return str(backend or "").lower() in {"enflame", "gcu", "tops"}


def _uses_default_ir_triton_hook(backend: Optional[str],
                                 hook: Optional[str]) -> bool:
    return (hook == "triton"
            and (_is_cann_backend(backend) or _is_tianshu_backend(backend))
            and (not _is_cann_backend(backend)
                 or not _env_flag_enabled(_CANN_TRITON_LEGACY_ENV)))


def _mode_with_ir_triton_overrides(mode: Optional[str],
                                   backend: Optional[str]) -> str:
    tokens = [token for token in str(mode or "").split(":") if token]
    if _is_cann_backend(backend):
        tokens.extend([
            "aclprof_runtime_enabled=false",
            "aclprof_auto_export=false",
            "mstx_enabled=false",
            "aclprof_msproftx_enabled=false",
            "runtime_host_timing_fallback=false",
        ])
    return ":".join(tokens)


def _set_instrumentation_mode(value: str) -> None:
    from flagtree.debugger.compiler import set_instrumentation_mode

    set_instrumentation_mode(value)


def _instrumentation_record_capacity() -> int:
    value = os.getenv(_IR_RECORD_BUFFER_MB_ENV, "").strip()
    buffer_mb = _DEFAULT_IR_RECORD_BUFFER_MB if not value else int(value)
    if buffer_mb <= 0:
        raise ValueError(
            f"{_IR_RECORD_BUFFER_MB_ENV} must be a positive integer")
    return buffer_mb * 1024 * 1024 // _IR_RECORD_SIZE_BYTES


def _activate_instrumentation(backend: Optional[str] = None,
                              request=None,
                              *,
                              clear_runs: bool = True) -> None:
    import flagtree.debugger as debugger

    record_capacity = (_instrumentation_record_capacity()
                       if request is None else request.max_events_per_instance)
    if clear_runs:
        debugger.clear_exported_runs()
    debugger.activate(
        record_level=1,
        addr_level=1 if _is_tianshu_backend(backend) else 0,
        record_capacity=record_capacity,
        output_dir=None,
        observation_request=None if request is None else request.as_dict(),
    )
    _set_instrumentation_mode("debugger_auto")


def _deactivate_instrumentation() -> None:
    import flagtree.debugger as debugger

    errors = []
    for operation in (debugger.deactivate,
                      lambda: _set_instrumentation_mode("")):
        try:
            operation()
        except Exception as error:
            errors.append(error)
    if errors:
        raise RuntimeError("Instrumentation cleanup failed: " +
                           "; ".join(str(error)
                                     for error in errors)) from errors[0]


def _take_instrumentation_runs() -> list[dict]:
    import flagtree.debugger as debugger
    from flagtree.debugger.runtime import default_debug_collect_runtime

    runs = list(debugger.take_exported_runs())
    runtime_runs = default_debug_collect_runtime.take_exported_runs()
    normalized = []
    for run in runs:
        raw_buffer = bytes(run.get("raw_buffer", b""))
        meta = dict(run.get("meta") or {})
        runtime_metadata = dict(run.get("runtime_metadata") or {})
        decoded = dict(run.get("decoded") or {})
        normalized.append({
            "meta":
            meta,
            "runtime_metadata":
            runtime_metadata,
            "decoded":
            decoded,
            "capture_status":
            run.get("capture_status", "decoded"),
            "decode_error":
            run.get("decode_error"),
            "recovery_export_error":
            run.get("recovery_export_error"),
            "debug_kernel_name":
            run.get("debug_kernel_name", ""),
            "debug_tracked_table":
            list(run.get("debug_tracked_table") or []),
            "semantic_observations":
            run.get("semantic_observations") or [],
            "raw_encoding":
            ("base64_ascend_actor_dynamic_v1"
             if runtime_metadata.get("record_layout")
             == "ascend_actor_dynamic_v1" else "base64_debugger_protocol_v2"),
            "raw_base64":
            base64.b64encode(raw_buffer).decode("ascii"),
            "raw_sha256":
            hashlib.sha256(raw_buffer).hexdigest(),
        })
    for run in runtime_runs:
        normalized.append({
            "meta": dict(run.meta or {}),
            "runtime_metadata": dict(run.runtime_metadata or {}),
            "decoded": dict(run.decoded or {}),
            "report": run.report,
        })
    return normalized


def _tracked_op_name(entry: dict) -> str:
    mlir_op = str(entry.get("mlir_op") or entry.get("mlirOpName") or "")
    role = str(entry.get("role") or "")
    if role and role != "<none>":
        return f"{mlir_op} {role}".strip()
    return mlir_op or f"op_{entry.get('op_id', entry.get('opId', 0))}"


def _is_ir_control_flow_op(entry: dict) -> bool:
    mlir_op = str(entry.get("mlir_op") or entry.get("mlirOpName") or "")
    return mlir_op.startswith("scf.") or mlir_op.startswith("cf.")


def _records_by_op_instance(
        records: list[dict]) -> dict[tuple[int, int], dict[str, float]]:
    summaries: dict[tuple[int, int], dict[str, float]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        kind = record.get("record_kind")
        if kind not in {
                "SUMMARY_COUNT_BUNDLE_U64", "SUMMARY_VALUE_BUNDLE_F32"
        }:
            continue
        key = (
            int(record.get("op_id", 0)),
            int(record.get("logical_instance_id", 0)),
        )
        bucket = summaries.setdefault(key, {})
        if kind == "SUMMARY_COUNT_BUNDLE_U64":
            for name in ("nan_count", "inf_count", "zero_count",
                         "element_count"):
                if name in record:
                    bucket[name] = float(record[name])
        else:
            for name in ("mean", "min", "max", "l2_norm"):
                if name in record:
                    bucket[name] = float(record[name])
    return summaries


def _internal_timeline_events_for_run(run_index: int, run: dict,
                                      kernel_event: dict | None) -> list[dict]:
    # Kernel/host duration is not a conversion factor for an internal clock.
    # Raw snapshots are exported separately even when calibration is unknown.
    from .observations import from_ir_runs

    events = []
    tracked = _tracked_by_op(run)
    runtime = dict(run.get('runtime_metadata') or {})
    runtime.setdefault('capture_id', f'ir-capture-{run_index}')
    for record in from_ir_runs([dict(run, runtime_metadata=runtime)]):
        clock = record['clock']
        if (record['duration_ns'] is None
                or record['relative_start_ns'] is None
                or clock['alignment'] == 'unverified'):
            continue
        instance = record.get('program')
        op_id = record.get('site')
        entry = tracked.get(op_id, {})
        if _is_ir_control_flow_op(entry):
            continue
        # Unshared clocks remain separate processes/frames; no native overlay.
        pid = 700000 + run_index * 100000
        if clock['alignment'] != 'verified_shared':
            pid += 0 if instance is None else instance + 1
        events.append({
            'name': _tracked_op_name(entry) if entry else f'op_{op_id}',
            'cat': 'flagtree.source_control_snapshot',
            'ph': 'X',
            'pid': pid,
            'tid': instance or 0,
            'ts': record['relative_start_ns'] / 1000,
            'dur': record['duration_ns'] / 1000,
            'args': record,
        })
    return events


def _load_timeline(path: Path) -> dict:
    if path.exists():
        text = path.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return json.loads(text.splitlines()[0])
    return {
        "displayTimeUnit":
        "us",
        "traceEvents": [{
            "name": "process_name",
            "ph": "M",
            "pid": 0,
            "args": {
                "name": "FlagTree Profiler IR"
            },
        }],
    }


def _augment_timeline(path: Path,
                      runs: list[dict],
                      synthesize_kernel_events: bool = False) -> None:
    # Legacy argument retained for callers; host intervals never synthesize a
    # device lifecycle, and kernel names/order never associate internal records.
    timeline = _load_timeline(path)
    events = timeline.setdefault('traceEvents', [])
    additions = []
    for run_index, run in enumerate(runs):
        additions.extend(
            _internal_timeline_events_for_run(run_index, run, None))
    if additions:
        events.extend(additions)
        path.write_text(json.dumps(timeline, indent=2) + '\n')


def _op_metric_name(name: str) -> str:
    return f"flagtree.internal.{name}"


def _ir_metric_name(name: str) -> str:
    return f"flagtree.ir.{name}"


def _tracked_by_op(run: dict) -> dict[int, dict]:
    tracked = {}
    for entry in run.get("debug_tracked_table") or []:
        if isinstance(entry, dict):
            tracked[int(entry.get("op_id", entry.get("opId", 0)))] = entry
    return tracked


def _numeric(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _entry_field(entry: dict, *names: str) -> object:
    current = entry
    for name in names:
        if isinstance(current, dict) and name in current:
            return current[name]
    return None


def _static_vec_width(entry: dict) -> float:
    result = entry.get("result") or {}
    width = _numeric(result.get("vecWidth", result.get("vec_width")), 0.0)
    if width > 0:
        return width
    shape = result.get("shape")
    if isinstance(shape, str) and shape:
        product = 1
        found = False
        for part in shape.replace("x", ",").replace(";", ",").split(","):
            value = part.strip()
            if value.isdigit():
                found = True
                product *= int(value)
        if found:
            return float(product)
    return 1.0


def _memory_access_bytes_per_instance(entry: dict) -> float:
    semantics = entry.get("memory_semantics") or {}
    access_bytes = _numeric(
        entry.get("accessBytes",
                  entry.get("access_bytes", semantics.get("access_bytes"))),
        0.0,
    )
    if access_bytes <= 0:
        return 0.0
    return access_bytes * _static_vec_width(entry)


def _memory_direction(entry: dict) -> str:
    parts = [
        entry.get("role"),
        entry.get("op_category", entry.get("opCategory")),
        entry.get("accessType", entry.get("access_type")),
        entry.get("mlir_op", entry.get("mlirOpName")),
    ]
    text = " ".join(str(part or "").lower() for part in parts)
    if "store" in text or "write" in text:
        return "write"
    if "load" in text or "read" in text:
        return "read"
    return ""


def _add_memory_metrics(metrics: dict[str, float], entry: dict) -> None:
    count = metrics.get(_op_metric_name("count"),
                        metrics.get(_ir_metric_name("count"), 0.0))
    per_instance_bytes = _memory_access_bytes_per_instance(entry)
    total_bytes = per_instance_bytes * count
    if total_bytes <= 0:
        return
    metrics[_ir_metric_name("memory_access_bytes")] = total_bytes
    metrics[_ir_metric_name("memory_bytes")] = total_bytes
    direction = _memory_direction(entry)
    if direction == "read":
        metrics[_ir_metric_name("memory_read_bytes")] = total_bytes
    elif direction == "write":
        metrics[_ir_metric_name("memory_write_bytes")] = total_bytes
    duration = metrics.get(_op_metric_name("duration_cycle"), 0.0)
    if duration > 0:
        metrics[_ir_metric_name("estimated_bandwidth_bytes_per_cycle")] = (
            total_bytes / duration)


def _timeline_records(run: dict) -> list[dict]:
    records = (run.get("decoded") or {}).get("records") or []
    return [
        record for record in records
        if isinstance(record, dict) and record.get("record_kind") == "TIMELINE"
    ]


def _host_time_bounds(run: dict) -> tuple[int, int] | tuple[None, None]:
    runtime_metadata = run.get("runtime_metadata") or {}
    start = int(runtime_metadata.get("host_start_time_ns", 0) or 0)
    end = int(runtime_metadata.get("host_end_time_ns", 0) or 0)
    duration = int(runtime_metadata.get("host_duration_ns", 0) or 0)
    if start > 0 and end <= start and duration > 0:
        end = start + duration
    if start <= 0 or end <= start:
        return None, None
    return start, end


def _run_cycle_bounds(run: dict) -> tuple[int, int] | tuple[None, None]:
    timeline_records = _timeline_records(run)
    if not timeline_records:
        return None, None
    starts = [int(record.get("start_cycle", 0)) for record in timeline_records]
    ends = [int(record.get("end_cycle", 0)) for record in timeline_records]
    return min(starts), max(ends)


def _run_ir_summary(run: dict) -> dict[str, float | int]:
    min_cycle, max_cycle = _run_cycle_bounds(run)
    host_start_ns, host_end_ns = _host_time_bounds(run)
    metrics_by_op = _internal_hatchet_metrics_for_run(run)
    summary: dict[str, float] = {
        "op_event_count":
        sum(
            metrics.get(_ir_metric_name("count"), 0.0)
            for metrics in metrics_by_op.values()),
        "memory_access_bytes":
        0.0,
        "memory_read_bytes":
        0.0,
        "memory_write_bytes":
        0.0,
    }
    if min_cycle is not None and max_cycle is not None:
        summary.update({
            "start_cycle": float(min_cycle),
            "end_cycle": float(max_cycle),
            "duration_cycle": float(max(0, max_cycle - min_cycle)),
        })
    if host_start_ns is not None and host_end_ns is not None:
        summary.update({
            "host_start_time_ns": host_start_ns,
            "host_end_time_ns": host_end_ns,
            "host_duration_ns": host_end_ns - host_start_ns,
        })
    for metrics in metrics_by_op.values():
        for name in (
                "memory_access_bytes",
                "memory_read_bytes",
                "memory_write_bytes",
        ):
            summary[name] += metrics.get(_ir_metric_name(name), 0.0)
    if summary.get("duration_cycle",
                   0.0) > 0 and summary["memory_access_bytes"] > 0:
        summary["estimated_bandwidth_bytes_per_cycle"] = (
            summary["memory_access_bytes"] / summary["duration_cycle"])
    if (min_cycle is None and host_start_ns is None
            and summary["op_event_count"] <= 0
            and summary["memory_access_bytes"] <= 0):
        return {}
    return summary


def _internal_hatchet_metrics_for_run(
        run: dict) -> dict[int, dict[str, float]]:
    records = (run.get("decoded") or {}).get("records") or []
    tracked = _tracked_by_op(run)
    by_op: dict[int, dict[str, float]] = {}
    summary_counts: dict[int, dict[str, float]] = {}
    summary_values: dict[int, dict[str, list[float]]] = {}
    observed_instances: dict[int, set[int]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        op_id = int(record.get("op_id", 0))
        kind = record.get("record_kind")
        if kind == "TIMELINE":
            duration = float(record.get("duration_cycle", 0))
            bucket = by_op.setdefault(
                op_id, {
                    _op_metric_name("count"): 0.0,
                    _ir_metric_name("count"): 0.0,
                    _op_metric_name("duration_cycle"): 0.0,
                    _ir_metric_name("duration_cycle"): 0.0,
                    _op_metric_name("min_duration_cycle"): duration,
                    _ir_metric_name("min_duration_cycle"): duration,
                    _op_metric_name("max_duration_cycle"): duration,
                    _ir_metric_name("max_duration_cycle"): duration,
                })
            bucket[_op_metric_name("count")] += 1.0
            bucket[_ir_metric_name("count")] += 1.0
            bucket[_op_metric_name("duration_cycle")] += duration
            bucket[_ir_metric_name("duration_cycle")] += duration
            bucket[_op_metric_name("min_duration_cycle")] = min(
                bucket[_op_metric_name("min_duration_cycle")], duration)
            bucket[_ir_metric_name("min_duration_cycle")] = min(
                bucket[_ir_metric_name("min_duration_cycle")], duration)
            bucket[_op_metric_name("max_duration_cycle")] = max(
                bucket[_op_metric_name("max_duration_cycle")], duration)
            bucket[_ir_metric_name("max_duration_cycle")] = max(
                bucket[_ir_metric_name("max_duration_cycle")], duration)
        elif kind == "SUMMARY_COUNT_BUNDLE_U64":
            observed_instances.setdefault(op_id, set()).add(
                int(record.get("logical_instance_id", 0)))
            bucket = summary_counts.setdefault(op_id, {})
            for name in ("nan_count", "inf_count", "zero_count",
                         "element_count"):
                if name in record:
                    metric = _op_metric_name(name)
                    bucket[metric] = bucket.get(metric, 0.0) + float(
                        record[name])
        elif kind == "SUMMARY_VALUE_BUNDLE_F32":
            observed_instances.setdefault(op_id, set()).add(
                int(record.get("logical_instance_id", 0)))
            bucket = summary_values.setdefault(op_id, {})
            for name in ("mean", "min", "max", "l2_norm"):
                if name in record:
                    bucket.setdefault(_op_metric_name(name),
                                      []).append(float(record[name]))
        elif kind == "MEMORY_EVENT":
            observed_instances.setdefault(op_id, set()).add(
                int(record.get("logical_instance_id", 0)))
    all_op_ids = set(by_op) | set(summary_counts) | set(summary_values) | set(
        observed_instances)
    for op_id in all_op_ids:
        metrics = by_op.setdefault(op_id, {})
        observed_count = float(len(observed_instances.get(op_id, ())))
        if observed_count > metrics.get(_op_metric_name("count"), 0.0):
            metrics[_op_metric_name("count")] = observed_count
            metrics[_ir_metric_name("count")] = observed_count
        count = metrics.get(_op_metric_name("count"), 0.0)
        if count > 0 and _op_metric_name("duration_cycle") in metrics:
            metrics[_op_metric_name("avg_duration_cycle")] = (
                metrics[_op_metric_name("duration_cycle")] / count)
            metrics[_ir_metric_name("avg_duration_cycle")] = (
                metrics[_ir_metric_name("duration_cycle")] / count)
        metrics.update(summary_counts.get(op_id, {}))
        for name, values in summary_values.get(op_id, {}).items():
            if values:
                metrics[name] = sum(values) / len(values)
        _add_memory_metrics(metrics, tracked.get(op_id, {}))
    return by_op


def _upsert_child(node: dict, name: str) -> dict:
    children = node.setdefault("children", [])
    for child in children:
        if (child.get("frame") or {}).get("name") == name:
            child.setdefault("metrics", {})
            child.setdefault("children", [])
            return child
    child = {
        "frame": {
            "name": name,
            "type": "function"
        },
        "metrics": {},
        "children": [],
    }
    children.append(child)
    return child


def _augment_hatchet(path: Path, runs: list[dict]) -> None:
    if not path.exists():
        return
    database = json.loads(path.read_text())
    if not isinstance(database, list) or not database or not isinstance(
            database[0], dict):
        return
    root = database[0]
    root_metrics = root.setdefault("metrics", {})
    changed = False
    for run_index, run in enumerate(runs):
        metrics_by_op = _internal_hatchet_metrics_for_run(run)
        if not metrics_by_op:
            continue
        tracked = _tracked_by_op(run)
        kernel_name = str(run.get("debug_kernel_name") or "")
        # Keep IR captures apart from native call-tree nodes: names cannot
        # establish invocation or binary identity.
        kernel_node = _upsert_child(
            root, f"IR capture {run_index}: {kernel_name or 'unnamed'}")
        run_summary = _run_ir_summary(run)
        if run_summary:
            kernel_metrics = kernel_node.setdefault("metrics", {})
            if "duration_cycle" in run_summary:
                kernel_metrics.setdefault(
                    _ir_metric_name("kernel_elapsed_cycle"),
                    run_summary["duration_cycle"],
                )
                root_metrics.setdefault(
                    _ir_metric_name("kernel_elapsed_cycle"), 0)
            if "host_duration_ns" in run_summary:
                kernel_metrics.setdefault(
                    _ir_metric_name("host_launch_duration_ns"),
                    run_summary["host_duration_ns"],
                )
                root_metrics.setdefault(
                    _ir_metric_name("host_launch_duration_ns"), 0)
            kernel_metrics.setdefault(
                _ir_metric_name("op_event_count"),
                run_summary["op_event_count"],
            )
            root_metrics.setdefault(_ir_metric_name("op_event_count"), 0)
            for name in (
                    "memory_access_bytes",
                    "memory_read_bytes",
                    "memory_write_bytes",
                    "estimated_bandwidth_bytes_per_cycle",
            ):
                if name in run_summary:
                    kernel_metrics.setdefault(_ir_metric_name(name),
                                              run_summary[name])
                    root_metrics.setdefault(_ir_metric_name(name), 0)
        for op_id in sorted(metrics_by_op):
            entry = tracked.get(op_id, {})
            if _is_ir_control_flow_op(entry):
                continue
            child_name = f"{op_id}:{_tracked_op_name(entry) if entry else f'op_{op_id}'}"
            child = _upsert_child(kernel_node, child_name)
            child_metrics = child.setdefault("metrics", {})
            for name, value in metrics_by_op[op_id].items():
                child_metrics[name] = value
                root_metrics.setdefault(name, 0)
        changed = True
    if changed:
        path.write_text("\n" + json.dumps(database, indent=4, default=str) +
                        "\n")


def _load_json_object(path: Path, default: dict) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return dict(default)


def _append_unique(items: list, value: object) -> None:
    if value not in items:
        items.append(value)


def _filter_default_ir_cann_reasons(reasons: object) -> list:
    if not isinstance(reasons, list):
        return []
    ignored_fragments = (
        "no cann memory/bandwidth csv columns were imported",
        "no vendor summary csv files were found",
        "no runtime_base events could be imported from aclprof exports",
        "bandwidth requested, but no cann memory/bandwidth csv columns were imported",
    )
    filtered = []
    for reason in reasons:
        text = str(reason)
        lower = text.lower()
        if any(fragment in lower for fragment in ignored_fragments):
            continue
        filtered.append(reason)
    return filtered


def _augment_ir_meta(path: Path, runs: list[dict],
                     ir_default_for_triton: bool) -> None:
    meta = _load_json_object(path, {"schema_version": 1})
    backend = str(meta.get("backend") or "").lower()
    summaries = [_run_ir_summary(run) for run in runs]
    config = meta.setdefault("config", {})
    config["flagtree_ir_enabled"] = "true"
    config["flagtree_ir_runs"] = str(len(runs))
    config["flagtree_ir_kernel_events"] = str(
        sum(1 for summary in summaries if summary))
    config["flagtree_ir_device_timeline_events"] = str(
        sum(1 for run in runs if _timeline_records(run)))
    config["flagtree_host_launch_events"] = str(
        sum(1 for run in runs if _host_time_bounds(run)[0] is not None))
    config["flagtree_ir_default_for_triton_hook"] = (
        "true" if ir_default_for_triton else "false")
    if ir_default_for_triton and _is_cann_backend(backend):
        meta["vendor_metrics_enabled"] = []
        config["cann_legacy_profiler_enabled"] = "false"
        config["aclprof_runtime_enabled"] = "false"
        config["aclprof_auto_export"] = "false"
        meta["degrade_reasons"] = _filter_default_ir_cann_reasons(
            meta.get("degrade_reasons", []))
        reasons = meta.setdefault("degrade_reasons", [])
        _append_unique(
            reasons,
            "CANN legacy aclprof is disabled by default for hook=triton; "
            "CANN-only hardware/runtime metrics are unavailable. Set "
            f"{_CANN_TRITON_LEGACY_ENV}=1 to restore the legacy CANN path.",
        )
    path.write_text(json.dumps(meta, indent=4, default=str) + "\n")


def _ir_associations_for_runs(runs: list[dict]) -> list[dict]:
    associations = []
    for run_index, run in enumerate(runs):
        kernel_name = str(
            run.get("debug_kernel_name") or f"instrumentation_run_{run_index}")
        summary = _run_ir_summary(run)
        if not summary:
            continue
        kernel_metrics: dict[str, object] = {
            "kernel_name": kernel_name,
            "op_event_count": summary["op_event_count"],
            "memory_access_bytes": summary["memory_access_bytes"],
            "memory_read_bytes": summary["memory_read_bytes"],
            "memory_write_bytes": summary["memory_write_bytes"],
        }
        for name in (
                "start_cycle",
                "end_cycle",
                "duration_cycle",
                "host_start_time_ns",
                "host_end_time_ns",
                "host_duration_ns",
                "estimated_bandwidth_bytes_per_cycle",
        ):
            if name in summary:
                kernel_metrics[name] = summary[name]
        host_start_ns = int(summary.get("host_start_time_ns", 0.0))
        host_end_ns = int(summary.get("host_end_time_ns", 0.0))
        associations.append({
            "source":
            "flagtree_ir_kernel",
            "state":
            "collected",
            "note":
            ("IR records correlated with synchronized host launch timing."
             if host_end_ns > host_start_ns else
             "Collected from FlagTree IR instrumentation runtime buffer."),
            "runtime_event": {
                "correlation_id": None,
                "device_id": None,
                "stream_id": None,
                "task_id": None,
                "scope_id": None,
                "op_name": kernel_name,
                "start_time_ns": host_start_ns,
                "end_time_ns": host_end_ns,
            },
            "metrics":
            kernel_metrics,
        })

        metrics_by_op = _internal_hatchet_metrics_for_run(run)
        tracked = _tracked_by_op(run)
        for op_id in sorted(metrics_by_op):
            entry = tracked.get(op_id, {})
            if _is_ir_control_flow_op(entry):
                continue
            op_metrics = {
                "kernel_name":
                kernel_name,
                "op_id":
                op_id,
                "op_name":
                _tracked_op_name(entry) if entry else f"op_{op_id}",
                "mlir_op":
                entry.get("mlir_op", entry.get("mlirOpName")),
                "source_loc":
                entry.get("source_loc", entry.get("sourceLoc")),
                "triton_statement":
                entry.get("triton_statement", entry.get("tritonStatement")),
            }
            for name, value in metrics_by_op[op_id].items():
                if name.startswith("flagtree.ir."):
                    op_metrics[name[len("flagtree.ir."):]] = value
            associations.append({
                "source": "flagtree_ir_op",
                "state": "collected",
                "note":
                "Collected from FlagTree IR instrumentation runtime buffer.",
                "runtime_event": {
                    "correlation_id": None,
                    "device_id": None,
                    "stream_id": None,
                    "task_id": None,
                    "scope_id": None,
                    "op_name": kernel_name,
                    "start_time_ns": host_start_ns,
                    "end_time_ns": host_end_ns,
                },
                "metrics": op_metrics,
            })
    return associations


def _refresh_vendor_summary(vendor: dict) -> None:
    associations = [
        association for association in vendor.get("associations", [])
        if isinstance(association, dict)
    ]
    counts_by_source: dict[str, int] = {}
    counts_by_state: dict[str, int] = {}
    timed_count = 0
    for association in associations:
        source = str(association.get("source") or "unknown")
        state = str(association.get("state") or "unknown")
        counts_by_source[source] = counts_by_source.get(source, 0) + 1
        counts_by_state[state] = counts_by_state.get(state, 0) + 1
        event = association.get("runtime_event") or {}
        if int(event.get("end_time_ns",
                         0)) > int(event.get("start_time_ns", 0)):
            timed_count += 1
    summary = vendor.setdefault("summary", {})
    summary["association_count"] = len(associations)
    summary["timed_association_count"] = timed_count
    summary["counts_by_source"] = counts_by_source
    summary["counts_by_state"] = counts_by_state


def _augment_ir_vendor(path: Path, runs: list[dict],
                       ir_default_for_triton: bool) -> None:
    vendor = _load_json_object(
        path, {
            "schema_version": 1,
            "backend": "cann",
            "importer": "flagtree_ir",
            "requested_metrics": [],
            "enabled_metrics": [],
            "raw_inputs": [],
            "degrade_reasons": [],
            "associations": [],
        })
    backend = str(vendor.get("backend") or "").lower()
    is_cann = _is_cann_backend(backend)
    if ir_default_for_triton and is_cann:
        vendor["enabled_metrics"] = []
        vendor["degrade_reasons"] = _filter_default_ir_cann_reasons(
            vendor.get("degrade_reasons", []))
    enabled = vendor.setdefault("enabled_metrics", [])
    if any(_timeline_records(run) for run in runs):
        _append_unique(enabled, "ir_timeline")
    if any(_host_time_bounds(run)[0] is not None for run in runs):
        _append_unique(enabled, "host_launch_timeline")
    if any(
            _run_ir_summary(run).get("memory_access_bytes", 0.0) > 0
            for run in runs):
        _append_unique(enabled, "ir_memory")
    if ir_default_for_triton and is_cann:
        reasons = vendor.setdefault("degrade_reasons", [])
        _append_unique(
            reasons,
            "CANN legacy aclprof is disabled by default for hook=triton; "
            "vendor associations in this file include FlagTree IR records. "
            f"Set {_CANN_TRITON_LEGACY_ENV}=1 to collect legacy CANN metrics.",
        )
    associations = vendor.setdefault("associations", [])
    associations.extend(_ir_associations_for_runs(runs))
    _refresh_vendor_summary(vendor)
    vendor["ir_summary"] = {
        "runs":
        len(runs),
        "kernel_events":
        sum(1 for run in runs if _run_ir_summary(run)),
        "device_timeline_events":
        sum(1 for run in runs if _timeline_records(run)),
        "host_launch_events":
        sum(1 for run in runs if _host_time_bounds(run)[0] is not None),
        "source":
        "flagtree_ir_and_host_launch",
        "default_for_triton_hook":
        ir_default_for_triton,
    }
    path.write_text(json.dumps(vendor, indent=4, default=str) + "\n")


def _augment_instrumentation_artifacts(
    name: str,
    runs: Optional[list[dict]] = None,
    *,
    ir_default_for_triton: bool = False,
) -> None:
    if runs is None:
        runs = _take_instrumentation_runs()
    if not runs:
        return
    base = Path(name)
    from .observations import from_ir_runs
    base.with_suffix('.observations.json').write_text(
        json.dumps(
            {
                'schema_version':
                1,
                'observations':
                from_ir_runs(runs),
                'captures': [{
                    'capture_status':
                    run.get('capture_status', 'decoded'),
                    'decode_error':
                    run.get('decode_error'),
                    'recovery_export_error':
                    run.get('recovery_export_error'),
                    'capture_id': (run.get('runtime_metadata') or {}).get(
                        'capture_id') or f'ir-capture-{index}',
                    'runtime_metadata':
                    run.get('runtime_metadata') or {},
                    'header': (run.get('decoded') or {}).get('header') or {},
                    'actors': (run.get('decoded') or {}).get('actors') or [],
                    'dropped': (run.get('decoded') or {}).get('dropped'),
                    'record_layout':
                    (run.get('runtime_metadata') or {}).get('record_layout'),
                    'counter_saturated':
                    bool(((run.get('decoded') or {}).get('header') or {}
                          ).get('flags', 0) & 16),
                    'raw_encoding':
                    run.get('raw_encoding'),
                    'raw_base64':
                    run.get('raw_base64'),
                    'raw_sha256':
                    run.get('raw_sha256'),
                } for index, run in enumerate(runs)]
            },
            indent=2) + '\n')
    runs = [
        run for run in runs if run.get("capture_status") != "decode_failed"
    ]
    _augment_timeline(
        base.with_suffix(".timeline.json"),
        runs,
        synthesize_kernel_events=ir_default_for_triton,
    )
    _augment_hatchet(base.with_suffix(".hatchet"), runs)
    _augment_ir_meta(base.with_suffix(".meta.json"), runs,
                     ir_default_for_triton)
    _augment_ir_vendor(base.with_suffix(".vendor.json"), runs,
                       ir_default_for_triton)


def _snapshot_session(state):
    if state.get("name"):
        from ._capture import capture_software
        Path(state["name"]).with_suffix(".launches.json").write_text(
            json.dumps(dict(
                LaunchHook.snapshot(state["session"]),
                software=capture_software(state.get("backend")),
                context=state.get("metadata"),
                observation_request=state.get("observation_request"),
                metadata_rejections=state.get("metadata_rejections", [])),
                       allow_nan=False))


def _export_session(state):
    if state.get("bundle_output") is not None:
        from ._capture import export_capture
        export_capture(state["name"],
                       state["bundle_output"],
                       context=state.get("metadata"))


def _snapshot_cann_launch_receipts(state):
    if not _is_cann_backend(str(state.get("backend") or "")):
        return
    supports = getattr(profiler_native, "supports_cann_launch_receipts", None)
    if supports is None or not supports():
        return
    receipts = profiler_native.drain_cann_launch_receipts(state["session"])
    path = Path(
        state["name"]).with_suffix(".cann-launch-receipts.json").absolute()

    def sync_directory(directory):
        descriptor = os.open(directory,
                             os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def atomic_write(destination, data):
        descriptor, temporary = tempfile.mkstemp(prefix=".cann-receipts-",
                                                 dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            sync_directory(destination.parent)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    # Native drain permits closed contexts to be collected. Preserve its exact
    # returned payload before source lookup or augmentation can fail/mutate it.
    state["cann_receipt_recovery_undurable_raw"] = receipts
    try:
        raw = json.dumps(receipts, allow_nan=False, sort_keys=True).encode()
        recovery = json.dumps(
            {
                "schema_version": 1,
                "kind": "cann_launch_receipt_recovery",
                "session_id": state["session"],
                "intended_sidecar": str(path),
                "raw_receipts_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_receipts": receipts,
            },
            allow_nan=False,
            indent=2).encode() + b"\n"
    except (TypeError, ValueError) as error:
        note = "Drained CANN receipts are not durable: serialization failed; raw is retained only in session state."
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.__notes__ = [*getattr(error, "__notes__", []), note]
            print(note, file=sys.stderr)
        raise
    journal = None
    failures = []
    for parent in (path.parent, None):
        directory = None
        try:
            directory = Path(
                tempfile.mkdtemp(prefix="flagprism-cann-receipt-recovery-",
                                 dir=parent))
            atomic_write(directory / "receipts.json", recovery)
            sync_directory(directory.parent)
            journal = directory / "receipts.json"
            break
        except OSError as error:
            failures.append(error)
            if directory is not None:
                shutil.rmtree(directory, ignore_errors=True)
    if journal is None:
        error = failures[-1]
        note = "Drained CANN receipts are not durable: every recovery location failed; raw is retained only in session state."
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.__notes__ = [*getattr(error, "__notes__", []), note]
            print(note, file=sys.stderr)
        raise error
    state["cann_receipt_recovery_path"] = str(journal)
    state.pop("cann_receipt_recovery_undurable_raw", None)
    try:
        launches = LaunchHook.snapshot(state["session"])["launches"]
        for receipt in receipts:
            worker = receipt.get("worker") or {}
            worker_ok = (worker.get("abi_version") == 1
                         and worker.get("struct_size") == 64 and all(
                             type(worker.get(key)) is int and worker[key] == 0
                             for key in ("launch_status", "task_query_status",
                                         "stream_query_status",
                                         "device_query_status"))
                         and all(
                             type(worker.get(key)) is int and worker[key] > 0
                             for key in ("process_id", "thread_id"))
                         and all(
                             type(worker.get(key)) is int and worker[key] >= 0
                             for key in ("device_id", "stream_id", "task_id",
                                         "stream_handle")))
            candidates = [
                row for row in launches
                if row.get("scope_id") == receipt.get("scope_id")
                and row.get("status") != "rejected_before_launch"
            ]
            if (receipt.get("session_id") == state["session"]
                    and receipt.get("status") == "collected"
                    and not receipt.get("late_callback")
                    and receipt.get("publish_count") == 1 and worker_ok
                    and len(candidates) == 1
                    and candidates[0].get("binary_id")):
                launch = candidates[0]
                receipt["invocation_identity"] = {
                    "invocation_id": launch["id"],
                    "binary_id": launch["binary_id"],
                    "scope_id": launch["scope_id"],
                    "session_id": state["session"],
                    "evidence": "retained_per_launch_worker_receipt",
                }
            else:
                receipt["invocation_identity"] = None
        atomic_write(
            path,
            json.dumps(
                {
                    "schema_version":
                    1,
                    "receipts":
                    receipts,
                    "semantics":
                    "Actual SDK worker queries bound to retained launch tokens. Native SDK task matching and clock-domain validation are separate requirements.",
                },
                allow_nan=False,
                indent=2).encode() + b"\n")

    except BaseException as error:
        note = f"Original drained CANN receipts are durably recoverable at {journal}"
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.__notes__ = [*getattr(error, "__notes__", []), note]
            print(note, file=sys.stderr)
        raise
    # Only this invocation's private journal is removed, after durable sidecar.
    journal.unlink()
    journal.parent.rmdir()
    sync_directory(journal.parent.parent)
    state.pop("cann_receipt_recovery_path", None)


def _export_cann_task_identities(state):
    if not _is_cann_backend(str(state.get("backend") or "")):
        return
    receipt_file = Path(
        state["name"]).with_suffix(".cann-launch-receipts.json")
    if not receipt_file.is_file():
        return
    document = json.loads(receipt_file.read_text())
    receipts = document.get("receipts", [])
    roots = {
        str(Path(row["collector_output_path"]).resolve())
        for row in receipts
        if row.get("sdk_capture_binding_status") == "sealed_unique_sdk_capture"
        and isinstance(row.get("collector_output_path"), str)
        and row["collector_output_path"]
    }
    if len(roots) == 1:
        from .cann_joint import build_native_task_proofs
        proof = build_native_task_proofs(next(iter(roots)), receipt_file)
    else:
        proof = {
            "schema_version": 1,
            "producer": "cann_native_worker_connection_tables_v1",
            "task_identity_proofs": [],
            "clock_status": "unverified",
            "status": "unassociated",
            "reason": "Missing or ambiguous owned SDK capture root",
            "receipt_file": str(receipt_file),
        }
    # Exact SDK task identity never certifies the internal logger's clock.
    Path(state["name"]).with_suffix(".cann-task-identities.json").write_text(
        json.dumps(proof, allow_nan=False, indent=2) + "\n")
    if len(roots) == 1:
        from .cann_raw_sys import build_raw_task_sys
        try:
            raw_sys = build_raw_task_sys(next(iter(roots)), receipt_file)
        except (FileNotFoundError, ValueError) as error:
            # An unsupported SDK schema does not erase native task evidence.
            # The unverified source-clock descriptor remains unchanged.
            raw_sys = {
                "schema_version": 1,
                "producer": "cann_raw_acsq_sys_v1",
                "status": "unavailable",
                "clock_status": "unverified",
                "reason": str(error),
                "task_sys_envelopes": [],
            }
        Path(state["name"]).with_suffix(".cann-raw-sys.json").write_text(
            json.dumps(raw_sys, allow_nan=False, indent=2) + "\n")


def _export_native_observations(state):
    captures = InstrumentationHook.peek_observation_captures(state["session"])
    if not captures:
        return
    path = Path(state["name"]).with_suffix(".observations.json").absolute()

    def sync_directory(directory):
        descriptor = os.open(directory,
                             os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def atomic_write(destination, data):
        descriptor, temporary = tempfile.mkstemp(
            prefix=".native-observations-", dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            sync_directory(destination.parent)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    # Preserve the original packet bytes before parsing or rewriting a possibly
    # damaged sidecar. A fallback journal is independent of automatic stage
    # cleanup and its explicit path is included in every subsequent error.
    try:
        recovery = json.dumps(
            {
                "schema_version": 1,
                "kind": "native_observation_recovery",
                "session_id": state["session"],
                "intended_sidecar": str(path),
                "captures": captures,
            },
            indent=2,
            allow_nan=False).encode() + b"\n"
        # Compiler scope metadata can contain tuples. Compare complete payloads
        # in their persisted JSON representation when an export is retried.
        captures = json.loads(recovery)["captures"]
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            f"Native observations are not serializable for durable recovery; "
            f"session {state['session']} captures remain unacknowledged in memory: {error}"
        ) from error
    journal = None
    owned = state.get("_native_observation_recovery_owned")
    if owned is not None:
        previous, device, inode = owned
        try:
            identity = Path(previous).parent.stat()
            if ((identity.st_dev, identity.st_ino) == (device, inode)
                    and Path(previous).read_bytes() == recovery):
                journal = Path(previous)
        except OSError:
            pass
    recovery_errors = []
    for parent in (path.parent, None):
        if journal is not None:
            break
        directory = None
        try:
            directory = Path(
                tempfile.mkdtemp(prefix="flagprism-observation-recovery-",
                                 dir=parent))
            journal = directory / "captures.json"
            atomic_write(journal, recovery)
            sync_directory(directory.parent)
            break
        except OSError as error:
            recovery_errors.append(error)
            journal = None
            if directory is not None:
                shutil.rmtree(directory, ignore_errors=True)
    if journal is None:
        raise RuntimeError(
            f"Native observations could not be durably saved; session {state['session']} "
            f"captures remain unacknowledged in memory: {recovery_errors}"
        ) from recovery_errors[-1]
    state["native_observation_recovery_path"] = str(journal)
    identity = journal.parent.stat()
    state["_native_observation_recovery_owned"] = (str(journal),
                                                   identity.st_dev,
                                                   identity.st_ino)
    try:
        identifiers = [capture["capture_id"] for capture in captures]
        if (len(set(identifiers)) != len(identifiers)
                or any(not isinstance(value, str) or not value
                       for value in identifiers)):
            raise ValueError(
                "Native observations require unique nonempty capture IDs")
        existing = json.loads(path.read_text()) if path.exists() else {
            "schema_version": 1,
            "observations": [],
            "captures": []
        }
        if (not isinstance(existing, dict)
                or not isinstance(existing.get("captures", []), list)
                or not isinstance(existing.get("observations", []), list)):
            raise ValueError(
                "Invalid existing native observation sidecar structure")
        previous = existing.setdefault("captures", [])
        observations = existing.setdefault("observations", [])
        for capture in captures:
            matches = [
                old for old in previous
                if old.get("capture_id") == capture["capture_id"]
            ]
            if matches:
                if any(old != capture for old in matches):
                    raise ValueError(
                        f"Conflicting native observation capture ID: {capture['capture_id']}"
                    )
                continue
            previous.append(capture)
            observations.extend(capture["decoded"]["observations"])
        atomic_write(
            path,
            json.dumps(existing, indent=2, allow_nan=False).encode() + b"\n")
        InstrumentationHook.ack_observation_captures(state["session"],
                                                     identifiers)
    except Exception as error:
        raise RuntimeError(
            f"Native observation export failed: {type(error).__name__}: {error}. "
            f"Original captures durably retained at {journal}") from error
    try:
        shutil.rmtree(journal.parent)
    except OSError as error:
        raise RuntimeError(
            f"Native observations saved at {path}; recovery cleanup failed at {journal}: {error}"
        ) from error
    state.pop("native_observation_recovery_path", None)
    state.pop("_native_observation_recovery_owned", None)


def _drop_sessions(session=None):
    states = list(_active_sessions.values()) if session is None else [
        _active_sessions.get(session, {})
    ]
    if session is None:
        _active_sessions.clear()
    else:
        _active_sessions.pop(session, None)
    operations = [lambda: HookManager.unregister(session)]
    if any(state.get("instrumentation_hook") for state in states) and not any(
            state.get("instrumentation_hook")
            for state in _active_sessions.values()):
        operations.append(_deactivate_instrumentation)
    if not _active_sessions:
        operations.append(set_profiling_off)
    errors = []
    for operation in operations:
        try:
            operation()
        except Exception as error:
            errors.append(error)
    for state in states:
        if state.get("staging") and state.get("exported"):
            try:
                shutil.rmtree(state["staging"])
            except OSError as error:
                errors.append(error)
    if errors:
        raise RuntimeError("Profiling cleanup failed: " +
                           "; ".join(str(error)
                                     for error in errors)) from errors[0]


def _drop_session(session: Optional[int]) -> None:
    _drop_sessions(session)


def _drop_all_sessions() -> None:
    _drop_sessions()


def _select_backend() -> str:
    backend = triton.runtime.driver.active.get_current_target().backend
    if backend == "cuda":
        return "cupti"
    elif backend == "hip":
        return "roctracer"
    elif backend in {"ascend", "npu"}:
        return "cann"
    elif backend in {"tianshu", "corex", "iluvatar"}:
        return "tianshu"
    elif backend in {"gcu", "enflame", "tops"}:
        return "enflame"
    elif backend in {"mthreads", "musa"}:
        return "mthreads"
    else:
        raise ValueError("No backend is available for the current target.")


def _check_env(backend: str) -> None:
    if backend == "roctracer":
        hip_device_envs = ["HIP_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES"]
        for env in hip_device_envs:
            if os.getenv(env, None) is not None:
                raise ValueError(
                    f"FlagTree Profiler does not work when the environment variable {env} is set on AMD GPUs. Please unset it and use `ROCR_VISIBLE_DEVICES` instead"
                )


def _get_backend_default_path(backend: str) -> str:
    if backend not in {"cupti", "cupti_pcsampling"}:
        return ""
    # FlagTree releases exposing the inherited Proton knob remain supported.
    # Do not require applications to monkey-patch the compiler configuration.
    knobs = triton.knobs
    profiler_knobs = getattr(knobs, "profiler", None)
    lib_path = getattr(profiler_knobs, "cupti_dir", None)
    if lib_path is None:
        proton_knobs = getattr(knobs, "proton", None)
        lib_path = getattr(proton_knobs, "cupti_lib_dir", None)
    if lib_path is not None:
        return lib_path
    return str(
        pathlib.Path(triton.__file__).resolve().parent / "backends" /
        "nvidia" / "lib" / "cupti")


def _get_mode_str(backend: str, mode: Optional[Union[str, BaseMode]]) -> str:
    if backend == "instrumentation":
        target_backend = triton.runtime.driver.active.get_current_target(
        ).backend
        return f"{target_backend}:{mode}" if mode else str(target_backend)
    return str(mode) if mode else ""


def _automatic_backend(backend=None):
    """Route the public automatic path to a supported instrumented backend."""
    backend = backend or _select_backend()
    if backend in {"cupti", "instrumentation"}:
        return "instrumentation"
    if _is_cann_backend(backend) or _is_enflame_backend(backend):
        return backend
    raise ValueError(
        f"Automatic fine-grained profiling is unavailable for {backend!r}")


def start(
    name: Optional[str] = None,
    *,
    context: Optional[str] = "shadow",
    data: Optional[str] = "tree",
    backend: Optional[str] = None,
    mode: Optional[Union[str, BaseMode]] = None,
    hook: Optional[str] = None,
    metadata: Optional[dict] = None,
    observation_request=None,
    detail=None,
):
    """
    Start profiling with the given name and backend.

    Set detail="auto" for bounded, automatically selected internal observations.

    Usage:

        ```python
        profiler.start("my_profile")
        # do something
        profiler.finalize()
        ```

    Args:
        name (str, optional): The name (with path) of the profiling session.
                              If not provided, the output directory is "profile-run".
        backend (str, optional): The backend to use for profiling.
        Available options include None, "cupti", "cupti_pcsampling",
            "instrumentation", "roctracer", "enflame", "cann", "mthreads", "tianshu".
                                 Defaults to None, which automatically selects the backend matching the current active runtime.
        context (str, optional): The context to use for profiling.
                                 Available options are ["shadow", "python"].
                                 Defaults to "shadow".
        data (str, optional): The data structure to use for profiling.
                              Available options are ["tree"].
                              Defaults to "tree".
        mode (str, optional): Backend-specific mode string.
                      For "cann", one supported example is
                      "runtime_base:vendor_metrics=aicore,bandwidth".
                      For "mthreads", vendor metrics use the MUPTI activity API.
                      For "tianshu", vendor metrics are imported from an
                      ixKN CSV export when `ixkn_import_path` is provided.
        metadata (dict, optional): Finite JSON context; tuples convert to arrays.
            Recommended workload keys: operator, parameters, warmup, measurement,
            validation. Unknown facts may be null. Optional structure issues are
            exported in ai/context.json without interrupting capture. Values are
            snapshotted now; later caller mutations do not change them.
        hook (str, optional): The hook to use for profiling.
                              Available options are [None, "triton", "instrumentation"].
                              Defaults to None.
        observation_request (ObservationRequest or dict, optional): Explicit
            semantic/instance/site/capacity selection. Requires
            hook="instrumentation" and a supported backend lowering; unsupported
            requests fail explicitly. Clock conversion is not implied.
    Returns:
        session (int): The session ID of the profiling session.
    """
    if is_command_line():
        # Ignore the start() call if the script is run from the command line.
        return

    if name is None:
        name = DEFAULT_PROFILE_NAME

    if detail not in (None, "auto"):
        raise ValueError("detail must be None or 'auto'")
    if detail == "auto":
        if observation_request is not None or mode is not None:
            raise ValueError(
                "detail='auto' cannot be combined with a request or explicit mode"
            )
        if hook not in (None, "instrumentation"):
            raise ValueError("detail='auto' requires the instrumentation hook")
        backend = _automatic_backend(backend)
        if _is_cann_backend(backend):
            mode = (
                "runtime_base:mstx_enabled=true:aclprof_msproftx_enabled=true:"
                "runtime_host_timing_fallback=false")
        hook = "instrumentation"
        from .observations import ObservationRequest
        semantics = (("operation_checkpoint",
                      "control_checkpoint") if _is_cann_backend(backend) else
                     ("source_control_interval", ))
        observation_request = ObservationRequest(semantics=semantics,
                                                 automatic=True)
    if backend is None:
        backend = _select_backend()

    observation_plan = None
    if observation_request is not None:
        from .observations import ObservationRequest
        if isinstance(observation_request, dict):
            observation_request = ObservationRequest.from_dict(
                observation_request)
        if not isinstance(observation_request, ObservationRequest):
            raise TypeError(
                "observation_request must be an ObservationRequest or dictionary"
            )
        if hook != "instrumentation":
            raise ValueError(
                "observation_request requires hook='instrumentation'")
        if backend == "instrumentation":
            target_backend = triton.runtime.driver.active.get_current_target(
            ).backend
            if target_backend != "cuda":
                raise ValueError(
                    "This instrumentation request lowering requires CUDA")
            if mode is not None:
                raise ValueError(
                    "Use either an observation request or explicit instrumentation mode"
                )
            from .observations_nvidia import lower_request
            from .mode import Default
            observation_plan = lower_request(observation_request)
            mode = Default(**observation_plan["mode_options"])
        elif not (_is_enflame_backend(backend) or _is_cann_backend(backend)):
            raise ValueError(
                "Explicit requests support Enflame, CANN, or CUDA backend='instrumentation' modes"
            )

    use_triton_hook = (
        hook in ("triton", "instrumentation") or backend == "instrumentation"
        or (_is_mthreads_backend(backend) and hook is None)
        or (hook == "instrumentation" and
            (_is_cann_backend(backend) or _is_tianshu_backend(backend)
             or _is_enflame_backend(backend))))
    ir_default_for_triton = _uses_default_ir_triton_hook(backend, hook)
    use_instrumentation_hook = (
        (_is_cann_backend(backend) or _is_tianshu_backend(backend)
         or _is_enflame_backend(backend))
        and (hook == "instrumentation" or ir_default_for_triton))
    use_native_instrumentation_hook = backend == "instrumentation" or (
        hook == "instrumentation"
        and not (_is_cann_backend(backend) or _is_tianshu_backend(backend)
                 or _is_enflame_backend(backend)))
    if use_instrumentation_hook and (_is_cann_backend(backend)
                                     or _is_enflame_backend(backend)):
        from flagtree.debugger.graph_guard import require_eager
        require_eager(backend)

    # Native collection exports automatically; external counter tools are opt-in.
    from ._capture import INTERNAL_ENV
    internal = bool(os.environ.get(INTERNAL_ENV))
    if metadata is not None:
        metadata = metadata_snapshot(metadata)
    _check_env(backend)
    if backend == "cupti_pcsampling" or (backend == "cupti" and str(
            mode or "").split(":", 1)[0] == "pcsampling"):
        # Probe before allocating a session: an enabled SDK may still expose
        # zero stall reasons on a particular GPU/toolkit combination.
        profiler_native.validate_pc_sampling_support(
            _get_backend_default_path(backend))

    effective_mode = (_mode_with_ir_triton_overrides(mode, backend) if
                      ir_default_for_triton else _get_mode_str(backend, mode))
    request_spec = None if observation_request is None else observation_request.as_dict(
    )
    if not internal:
        requested_output = Path(name).expanduser().resolve()
        existing = next((state for state in _active_sessions.values()
                         if state.get("bundle_output") == requested_output),
                        None)
        if existing is not None:
            requested = {
                "backend": backend,
                "effective_mode": effective_mode,
                "context": context,
                "data": data,
                "hook": hook,
                "observation_request": request_spec
            }
            if any(
                    existing.get(key) != value
                    for key, value in requested.items()):
                raise ValueError(
                    "An existing session cannot change backend, mode, hook or observation request"
                )
            activate(existing["session"])
            if metadata is not None:
                existing["metadata"] = {
                    **(existing.get("metadata") or {}),
                    **metadata
                }
            return existing["session"]
    if not _active_sessions:
        LaunchHook.reset_capture()
    set_profiling_on()
    ir_session_exists = any(
        state.get("instrumentation_hook", False)
        for state in _active_sessions.values())
    instrumentation_was_active = any(
        state.get("instrumentation_hook") and state.get("active", True)
        for state in _active_sessions.values())
    if ir_session_exists and any(
            state.get("instrumentation_hook")
            and state.get("observation_request") != request_spec
            for state in _active_sessions.values()):
        raise ValueError(
            "Nested IR sessions must use the same observation request")
    instrumentation_activated = use_instrumentation_hook and not instrumentation_was_active
    session = None
    staging = None
    bundle_output = None
    bundle_created = False
    try:
        if instrumentation_activated:
            _activate_instrumentation(backend,
                                      observation_request,
                                      clear_runs=not ir_session_exists)
        if not internal:
            bundle_output = Path(name).expanduser().resolve()
            existing = next((state for state in _active_sessions.values()
                             if state.get("bundle_output") == bundle_output),
                            None)
            if existing:
                name = existing["name"]
            else:
                bundle_output.mkdir(parents=True, exist_ok=False)
                bundle_created = True
                staging = tempfile.mkdtemp(prefix="flagprism-session-")
                name = str(Path(staging) / "capture")
        session = profiler_native.start(
            name,
            context,
            data,
            backend,
            effective_mode,
            _get_backend_default_path(backend),
            hook or "",
        )
        if use_instrumentation_hook and (_is_cann_backend(backend)
                                         or _is_enflame_backend(backend)):
            from .hooks.graph_guard import graph_guards
            guard_backend = 'cann' if _is_cann_backend(backend) else 'enflame'
            HookManager.register(graph_guards[guard_backend], session)
        if use_triton_hook:
            HookManager.register(LaunchHook(), session)
        if use_native_instrumentation_hook:
            HookManager.register(
                InstrumentationHook(mode, observation_plan=observation_plan),
                session)
    except BaseException as error:
        # Compiler/debugger activation can fail before native start. Unwind all
        # owned resources without replacing the application's original error.
        cleanup = []
        if session is not None:
            cleanup.extend((lambda: profiler_native.finalize(session, ""),
                            lambda: HookManager.unregister(session)))
        if instrumentation_activated:
            cleanup.append(_deactivate_instrumentation)
        if not _active_sessions:
            cleanup.append(set_profiling_off)
        if staging is not None:
            cleanup.append(lambda: shutil.rmtree(staging))
        if bundle_created:
            cleanup.append(bundle_output.rmdir)
        for operation in cleanup:
            try:
                operation()
            except BaseException as cleanup_error:
                if hasattr(error, "add_note"):
                    error.add_note(
                        f"Profiler start cleanup failed: {cleanup_error}")
                else:
                    print(f"Profiler start cleanup failed: {cleanup_error}",
                          file=sys.stderr)
        raise
    if session in _active_sessions:
        if metadata is not None:
            _active_sessions[session]["metadata"] = {
                **(_active_sessions[session].get("metadata") or {}),
                **metadata
            }
        if use_triton_hook:
            _active_sessions[session]["triton_hook"] = True
        if use_instrumentation_hook:
            _active_sessions[session]["instrumentation_hook"] = True
            _active_sessions[session]["name"] = name
            _active_sessions[session]["ir_default_for_triton"] = (
                _active_sessions[session].get("ir_default_for_triton", False)
                or ir_default_for_triton)
        return session
    _active_sessions[session] = {
        "session": session,
        "active": True,
        "backend": backend,
        "effective_mode": effective_mode,
        "context": context,
        "data": data,
        "hook": hook,
        "triton_hook": use_triton_hook,
        "instrumentation_hook": use_instrumentation_hook,
        "native_instrumentation_hook": use_native_instrumentation_hook,
        "ir_default_for_triton": ir_default_for_triton,
        "name": name,
        "staging": staging,
        "bundle_output": bundle_output,
        "metadata": metadata,
        "observation_request": request_spec,
    }
    return session


def activate(session: Optional[int] = None) -> None:
    """
    Activate the specified session.
    The profiling session will be active and data will be recorded.

    Args:
        session (int, optional): Session to activate. None activates all existing
            sessions; explicit IDs must refer to an initialized session.

    Returns:
        None
    """
    if is_command_line() and session not in (None, 0):
        raise ValueError(
            "Only one session can be activated when running from the command line."
        )
    if session is not None and session not in _active_sessions:
        raise RuntimeError(f"Session has not been initialized: {session}")
    targets = (list(_active_sessions.values())
               if session is None else [_active_sessions[session]])
    ir_targets = [
        state for state in targets if state.get("instrumentation_hook")
    ]
    have_active_ir = any(
        state.get("instrumentation_hook") and state.get("active", True)
        for state in _active_sessions.values())
    if ir_targets and not have_active_ir:
        from .observations import ObservationRequest
        state = ir_targets[0]
        request = state.get("observation_request")
        _activate_instrumentation(
            state["backend"],
            ObservationRequest.from_dict(request) if request else None,
            clear_runs=False)
    HookManager.activate(session)
    profiler_native.activate_all(
    ) if session is None else profiler_native.activate(session)
    for state in targets:
        state["active"] = True


def deactivate(session: Optional[int] = None) -> None:
    """
    Stop the specified session.
    The profiling session's data will still be in the memory, but no more data will be recorded.

    Args:
        session (int, optional): Session to deactivate. None deactivates all
            existing sessions; explicit IDs must refer to an initialized session.

    Returns:
        None
    """
    if is_command_line() and session not in (None, 0):
        raise ValueError(
            "Only one session can be deactivated when running from the command line."
        )
    if session is not None and session not in _active_sessions:
        raise RuntimeError(f"Session has not been initialized: {session}")
    HookManager.deactivate(session)
    profiler_native.deactivate_all(
    ) if session is None else profiler_native.deactivate(session)
    targets = (list(_active_sessions.values())
               if session is None else [_active_sessions[session]])
    for state in targets:
        state["active"] = False
    if any(state.get("instrumentation_hook") for state in targets) and not any(
            state.get("instrumentation_hook") and state.get("active", True)
            for state in _active_sessions.values()):
        _deactivate_instrumentation()


def finalize(session: Optional[int] = None,
             output_format: Optional[str] = "",
             *,
             metadata: Optional[dict] = None) -> None:
    """Flush, export and clean up a capture; CLI export phases have a deadline.

    Direct API callers retain control of their process. Native SDK calls cannot
    safely be interrupted in a Python thread; use the CLI for hard deadlines.
    """
    from ._deadline import export_phase
    with export_phase():
        return _finalize_impl(session, output_format, metadata=metadata)


def _finalize_impl(session: Optional[int] = None,
                   output_format: Optional[str] = "",
                   *,
                   metadata: Optional[dict] = None) -> None:
    """
    Finalizes a profiling session.
    Flush and write the profiling data to the file specified by the session name.

    Args:
        metadata (dict, optional): Final context, replacing matching top-level
            start-time sections. Supply actual validation outcomes after checks.
            Invalid JSON updates are rejected after saving the capture and cleanup;
            serializable structure issues are preserved as metadata diagnostics.
        session (int, optional): The session ID to finalize. If None, all sessions are finalized. Defaults to None.
            An unknown or already finalized explicit ID is a no-op.
        output_format (str, optional): The output format for the profiling results.
                                       Available options are ["hatchet", "chrome_trace"].

    Returns:
        None
    """
    if session is not None and session not in _active_sessions:
        return
    finalize_started = time.monotonic()
    metadata_error = None
    if metadata is not None:
        if session is None and len(_active_sessions) > 1:
            raise ValueError(
                "Select a session when attaching final metadata to multiple sessions"
            )
        states = list(_active_sessions.values()) if session is None else [
            _active_sessions.get(session, {})
        ]
        try:
            metadata = metadata_snapshot(metadata)
        except (ValueError, TypeError, RecursionError) as error:
            metadata_error = error
            rejection = dict(phase="finalize",
                             applied=False,
                             raw_preserved=False,
                             reason=str(error),
                             actual_type=type(metadata).__name__)
            try:
                rejection["value"] = metadata_snapshot(metadata,
                                                       require_object=False)
                rejection["raw_preserved"] = True
            except (ValueError, TypeError, RecursionError):
                pass
            for state in states:
                state.setdefault("metadata_rejections", []).append(rejection)
        else:
            for state in states:
                state["metadata"] = {
                    **(state.get("metadata") or {}),
                    **metadata
                }
    if is_command_line() and session is not None and session != 0:
        raise ValueError(
            "Only one session can be finalized when running from the command line."
        )
    states = list(_active_sessions.values()) if session is None else [
        _active_sessions.get(session, {})
    ]
    errors = []

    def attempt(phase, operation, state=None):
        try:
            operation()
            return True
        except Exception as error:
            errors.append(
                (state.get("session") if state else None, phase, error))
            return False

    try:
        stopped = session is not None or attempt(
            "deactivate", profiler_native.deactivate_all)
        runs = []

        def take_runs():
            runs.extend(_take_instrumentation_runs())

        have_runs = not any(
            state.get("instrumentation_hook") for state in states) or attempt(
                "instrumentation snapshot", take_runs)
        if not states:
            attempt("native finalize",
                    lambda: profiler_native.finalize_all(output_format))
        for state in states:
            if state.get("instrumentation_hook") and have_runs and state.get(
                    "name"):
                attempt(
                    "instrumentation recovery snapshot",
                    lambda: Path(state["name"]).with_suffix(
                        ".instrumentation.json").write_text(json.dumps(runs)),
                    state)
            snapshot_ok = attempt("launch snapshot",
                                  lambda: _snapshot_session(state), state)
            native_ok = attempt(
                "native finalize", lambda: profiler_native.finalize(
                    state.get("session", session), output_format), state)
            receipts_ok = attempt(
                "CANN worker receipts",
                lambda: _snapshot_cann_launch_receipts(state), state)
            if not (native_ok and snapshot_ok and stopped and receipts_ok and
                    (have_runs or not state.get("instrumentation_hook"))):
                attempt("native observation recovery",
                        lambda: _export_native_observations(state), state)
                continue

            def export():
                _export_cann_task_identities(state)
                if state.get("instrumentation_hook"):
                    session_runs = [
                        run for run in runs
                        if not (run.get("runtime_metadata") or {}
                                ).get("profiler_association_evidence")
                        or state["session"] in (
                            (run.get("runtime_metadata") or {}
                             ).get("profiler_association_evidence", {}).get(
                                 "session_ids", []))
                    ]
                    _augment_instrumentation_artifacts(
                        str(state.get("name") or DEFAULT_PROFILE_NAME),
                        session_runs,
                        ir_default_for_triton=bool(
                            state.get("ir_default_for_triton", False)))
                _export_native_observations(state)
                _export_session(state)
                state["exported"] = True

            if not attempt("export", export, state):
                attempt("native observation recovery",
                        lambda: _export_native_observations(state), state)
    finally:
        attempt(
            "cleanup", _drop_all_sessions
            if session is None else lambda: _drop_session(session))
    if errors:
        retained = [
            state["staging"] for state in states
            if state.get("staging") and not state.get("exported")
        ]
        if metadata_error is not None:
            errors.append((session, "metadata rejected", metadata_error))
        detail = "; ".join(
            f"session {sid} {phase}: {type(error).__name__}: {error}"
            for sid, phase, error in errors)
        raise RuntimeError(
            f"Profiling finalization failed: {detail}. "
            f"Capture intermediates retained at: {retained}") from errors[0][2]

    from .export_timing import finish_sessions
    finish_sessions(states, time.monotonic() - finalize_started)

    if metadata_error is not None:
        outputs = [
            str(state.get("bundle_output") or state.get("name"))
            for state in states
        ]
        raise ValueError(
            f"Final metadata was not applied: {metadata_error}. Capture finalized and saved at {outputs}"
        ) from metadata_error


def _profiling(
    func,
    name: Optional[str] = None,
    context: Optional[str] = "shadow",
    data: Optional[str] = "tree",
    backend: Optional[str] = None,
    mode: Optional[str] = None,
    hook: Optional[str] = None,
):
    """
    Context manager for profiling. Internally use only.

    Args:
        See start() for the arguments.

    Returns:
        wrapper (function): The wrapped function.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if is_command_line():
            # The CLI owns its session and finalization. A decorator inside
            # that application must not deactivate or finalize the CLI capture.
            return func(*args, **kwargs)
        session = start(name,
                        context=context,
                        data=data,
                        backend=backend,
                        mode=mode,
                        hook=hook)
        try:
            ret = func(*args, **kwargs)
            deactivate(session)
            return ret
        except BaseException as error:
            try:
                finalize(session)
            except BaseException as cleanup_error:
                if hasattr(error, "add_note"):
                    error.add_note(
                        f"Decorated profiling finalization also failed: {cleanup_error}"
                    )
                else:
                    print(
                        f"Decorated profiling finalization also failed: {cleanup_error}",
                        file=sys.stderr)
            raise

    return wrapper


def profile(
    func=None,
    *,
    name: Optional[str] = None,
    context: Optional[str] = "shadow",
    data: Optional[str] = "tree",
    backend: Optional[str] = None,
    mode: Optional[str] = None,
    hook: Optional[str] = None,
):
    """
    Decorator for profiling.

    Usage:

    ```python
    @profiler.profile
    def foo():
        pass
    ```

    Args:
        See start() for the arguments.

    Returns:
        decorator (function): The decorator function.
    """
    if func is None:
        # It's being used with parentheses, so return a decorator
        def decorator(f):
            return _profiling(f,
                              name=name,
                              context=context,
                              data=data,
                              backend=backend,
                              mode=mode,
                              hook=hook)

        return decorator
    else:
        # It's being used without parentheses, so apply the decorator directly
        return _profiling(func,
                          name=name,
                          context=context,
                          data=data,
                          backend=backend,
                          mode=mode,
                          hook=hook)
