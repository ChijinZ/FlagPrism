"""Internal collection orchestration and automatic human/machine export."""
import json
import os
from pathlib import Path
import sys
import tempfile
import shutil

from . import _report
from ._metadata import snapshot as metadata_snapshot
from ._backends import capture_backend

INTERNAL_ENV = "FLAGPRISM_CAPTURE_INTERNAL"


def sanitize_call_tree(value):
    """Runtime IDs/configuration were summed by the legacy tree; discard them."""
    if isinstance(value, list):
        return [sanitize_call_tree(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if isinstance(value.get("metrics"), dict):
        omitted = [
            key for key in value["metrics"]
            if key.startswith(("activity.", "runtime.", "vendor."))
        ]
        result["metrics"] = {
            key: item
            for key, item in value["metrics"].items() if key not in omitted
        }
        if omitted:
            result["omitted_nonadditive_fields"] = omitted
    if "children" in value:
        result["children"] = sanitize_call_tree(value["children"])
    return result


def capture_software(backend=None):
    versions = {"python": sys.version.split()[0]}
    for name in ("triton", "torch",
                 "flag_gems") + capture_backend(backend).software_modules:
        module = sys.modules.get(name)
        version = getattr(module, "__version__", None)
        if version is not None:
            versions[name] = str(version)
    return {
        "versions": versions,
        "source": "capture_process",
        "status": "partial"
    }


def export_capture(base, output, counters=None, context=None):
    base = Path(base)
    if not any(
            base.with_suffix(suffix).exists()
            for suffix in (".vendor.json", ".hatchet", ".chrome_trace",
                           ".timeline.json")):
        raise RuntimeError("Collector produced no profiling data")
    vendor = base.with_suffix(".vendor.json")
    document = json.loads(vendor.read_text()) if vendor.exists() else {
        "backend": "native",
        "associations": []
    }
    metadata = base.with_suffix(".meta.json")
    if metadata.exists():
        document["session_metadata"] = json.loads(metadata.read_text())
        document["session_metadata"]["session_name"] = str(output)
        document["session_metadata"].get("config",
                                         {}).pop("artifact_layout", None)
    launches_path = base.with_suffix(".launches.json")
    if launches_path.exists():
        snapshot = json.loads(launches_path.read_text())
        # The hook snapshot already filters by active session membership. Keep
        # launches even when a backend cannot associate device events yet.
        launches = snapshot["launches"]
        document["launches"] = launches
        document["binaries"] = snapshot["binaries"]
        document["software"] = snapshot.get("software", {})
        document["metadata_rejections"] = snapshot.get("metadata_rejections",
                                                       [])
        if context is None:
            context = snapshot.get("context")
        if launches:
            document.setdefault("capture_notes", []).append(
                "Launch metadata extraction adds host-side profiler overhead; host gaps are not unprofiled application timings."
            )
    else:
        document["software"] = capture_software(document.get("backend"))
    if counters is not None:
        for key in ("counter_groups", "kernel_summaries"):
            document.setdefault(key, []).extend(counters.get(key, []))
        document.setdefault("capture", {})["external_counters"] = counters.get(
            "capture", {})
        document.setdefault("capture_notes",
                            []).extend(counters.get("capture_notes", []))
        external_availability = counters.get("availability", {})
        document["external_counter_availability"] = external_availability
        if "counters" in external_availability:
            document.setdefault("availability", {}).setdefault(
                "counters", external_availability["counters"])
    document.setdefault("availability", {}).setdefault(
        "counters", {
            "status": "unknown",
            "reason": "Collector did not declare counter availability"
        })
    rows = document.get("associations", [])
    # Older collectors lack activity classification. Preserve their records and
    # call trees without inventing device event kinds or hardware timings.
    normalized = not rows or any("activity.kind" in row.get("metrics", {})
                                 for row in rows)
    result = _report.analyze(
        document if normalized else dict(document, associations=[]))
    if not normalized:
        result["rejected"] = {
            "Collector does not provide normalized activity kinds": len(rows)
        }
    native_trace = base.with_suffix(".timeline.json")
    if not native_trace.exists():
        native_trace = base.with_suffix(".chrome_trace")
    if native_trace.exists() and not result["events"]:
        result["native_trace"] = json.loads(native_trace.read_text())
    tree = base.with_suffix(".hatchet")
    payload = sanitize_call_tree(json.loads(
        tree.read_text())) if tree.exists() else None
    _report.write_bundle(result, document, output, context, complete=False)
    # Retain native call-tree data for backends that have richer scope metrics.
    # This is machine-readable data, not another legacy user-facing artifact.
    if payload is not None:
        (Path(output) /
         "ai/call_tree.json").write_text(json.dumps(payload) + "\n")
    _report.write_manifest(output, result)


def run_capture(args, target_args, execute):
    """Own collection, optional process wrappers, and automatic bundle export."""
    if not target_args:
        raise ValueError("Provide a Python script or pytest target")
    backend = capture_backend(args.backend)
    if args.counters and backend.collect_counters is None:
        raise ValueError(
            f"External counters are not supported by {args.backend}")
    output = Path(args.name or "profile-run").expanduser().resolve()
    context = None
    if args.metadata:
        context = json.loads(Path(args.metadata).read_text())
        context = metadata_snapshot(context)
    output.mkdir(parents=True, exist_ok=False)
    stage = tempfile.mkdtemp(prefix="flagprism-capture-")
    try:
        base = str(Path(stage) / "capture")
        counters = None
        if args.counters:
            child = [
                sys.executable, "-m", f"{__package__}.cli", "--backend",
                args.backend, "--name", base, "--context", args.context,
                "--data", args.data
            ]
            if args.mode:
                child += ["--mode", args.mode]
            if args.hook:
                child += ["--hook", args.hook]
            child += target_args
            counters = backend.collect_counters(child,
                                                output / "raw",
                                                metrics=args.counter_metrics,
                                                replay_mode=args.replay_mode,
                                                env={
                                                    **os.environ, INTERNAL_ENV:
                                                    "1"
                                                })
        else:
            old = os.environ.get(INTERNAL_ENV)
            original_name = args.name
            try:
                os.environ[INTERNAL_ENV] = "1"
                args.name = base
                execute(args, target_args)
            finally:
                args.name = original_name
                if old is None:
                    os.environ.pop(INTERNAL_ENV, None)
                else:
                    os.environ[INTERNAL_ENV] = old
        export_capture(base, output, counters, context)
    except BaseException as error:
        message = f"Capture intermediates retained at {stage}; output: {output}"
        if isinstance(error, Exception) and hasattr(error, "add_note"):
            error.add_note(message)
        else:
            print(message, file=sys.stderr)
        raise
    else:
        shutil.rmtree(stage)
    print(output)
