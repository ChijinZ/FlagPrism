"""Capture or import TCU counters as a standalone FlagPrism profiling artifact.

Run directly with Python; requires no native FlagTree module for CSV import.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

DESCRIPTIONS = {
    "SIP/BUSY":
    "SIP busy cycles including wait stalls; not useful-compute utilization.",
    "SIP/1D_EFFICIENCY":
    "1D instruction execution cycles (M-slot + V-slot) as a percentage of total cycles.",
    "SIP/2D_EFFICIENCY":
    "2D instruction execution cycles (M-slot) as a percentage of total cycles.",
    "SIP/MSF_EFFICIENCY":
    "MSF instruction execution cycles (M-slot) as a percentage of total cycles.",
    "SIP/L1_ICACHE_MISS":
    "L1 instruction-cache miss-fetch requests to SDTE; not a cache miss rate.",
    "SIP/L1_ICACHE_HW_PREFETCH":
    "L1 instruction-cache hardware prefetch requests to SDTE.",
    "SIP/L1_ICACHE_SW_PREFETCH":
    "L1 instruction-cache software prefetch requests to SDTE.",
}


def number(value):
    # Preserve integer counters exactly; averages in TCU CSV may be fractional.
    result = int(value) if re.fullmatch(r"[0-9]+", value) else float(value)
    if result < 0 or not math.isfinite(result):
        raise ValueError(f"Invalid TCU counter value: {value!r}")
    return result


def count(value):
    result = int(value)
    if result < 0:
        raise ValueError("TCU counts must be nonnegative")
    return result


def duration_us(value):
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(ns|us|µs|ms|s)", value)
    if not match:
        raise ValueError(f"Unknown TCU duration: {value!r}")
    return number(match[1]) * {
        "ns": .001,
        "us": 1,
        "µs": 1,
        "ms": 1000,
        "s": 1000000
    }[match[2]]


def import_csv(path):
    """Parse TCU 1.9.29 summary CSV without inventing launch timestamps/IDs."""
    groups, summaries = [], []
    group = metric = None
    expect_kernel = False
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        for line, fields in enumerate(csv.reader(stream), 1):
            row = [field.strip() for field in fields]
            if not row or not any(row):
                continue
            try:
                if row[:2] == ["Type", "Time(%)"]:
                    continue
                if row[:2] == ["", "Kernel Name"]:
                    expect_kernel = True
                    metric = None
                    continue
                if expect_kernel:
                    if len(row) != 3 or row[0] or not row[1]:
                        raise ValueError(
                            "Expected kernel configuration and invocation count"
                        )
                    group = dict(name=row[1],
                                 scope="kernel_config_aggregate",
                                 source="tcu_csv",
                                 invocations=count(row[2]),
                                 metrics=[])
                    groups.append(group)
                    expect_kernel = False
                elif row[0] == "GCU activities":
                    if len(row) != 8:
                        raise ValueError(
                            "Unexpected GCU activity summary columns")
                    summaries.append(
                        dict(name=row[7],
                             count=count(row[3]),
                             total_us=duration_us(row[2]),
                             mean_us=duration_us(row[4]),
                             min_us=duration_us(row[5]),
                             max_us=duration_us(row[6]),
                             source="tcu_csv"))
                elif row == [
                        "Type", "Die", "SIP", "Minimum", "Maximum", "Average",
                        "Invocations"
                ]:
                    continue
                elif row[0] == "GCU Metric":
                    if metric is None or len(row) != 7:
                        raise ValueError(
                            "Counter instance without metric header")
                    metric["instances"].append(
                        dict(instance=
                             f"Die {count(row[1])} / SIP {count(row[2])}",
                             minimum=number(row[3]),
                             maximum=number(row[4]),
                             mean=number(row[5]),
                             count=count(row[6])))
                elif not row[0] and len(row) == 4 and group is not None:
                    metric = dict(
                        name=row[1],
                        unit=row[2],
                        value=number(row[3]),
                        description=DESCRIPTIONS.get(
                            row[1],
                            "TCU-reported metric; consult the SDK for its semantics."
                        ),
                        instances=[])
                    group["metrics"].append(metric)
                else:
                    raise ValueError(
                        "Unsupported CSV record; refusing partial import")
            except (ValueError, IndexError) as error:
                raise ValueError(f"TCU CSV line {line}: {error}") from error
    if expect_kernel or not groups or any(not g["metrics"] for g in groups):
        raise ValueError("TCU CSV contains no complete kernel counter groups")
    return dict(
        schema_version=1,
        backend="enflame",
        importer="tcu_csv",
        associations=[],
        counter_groups=groups,
        kernel_summaries=summaries,
        degrade_reasons=[],
        capture_notes=[
            "TCU CSV contains configuration-level aggregates, not per-launch timestamps or correlation IDs. No timeline association is inferred.",
            "Invocation totals may include application replays. Per-metric sample counts may differ; counters from different passes are not simultaneous observations.",
            "Counter collection perturbs execution. TCU timings are instrumented measurements, not an unprofiled performance baseline.",
            "The CSV has no device identity. Die/SIP indices are tool-local and must not be interpreted as global device IDs.",
        ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",
                        type=Path,
                        required=True,
                        help="New capture directory")
    parser.add_argument(
        "--import-csv",
        type=Path,
        help="Import an existing TCU CSV without running an application")
    parser.add_argument("--tcu", default="tcu", help="TCU executable")
    parser.add_argument("--metrics",
                        default="SIP/BUSY",
                        help="Comma-separated TCU metrics")
    parser.add_argument("--kernel", help="TCU kernel-name filter")
    parser.add_argument(
        "--replay-mode",
        choices=("none", "application"),
        default="none",
        help=
        "Application replay reruns your command; use only for replay-safe workloads"
    )
    parser.add_argument("command",
                        nargs=argparse.REMAINDER,
                        help="-- executable arguments")
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if bool(args.import_csv) == bool(command):
        parser.error(
            "Provide either --import-csv or an application command after --")
    if not args.import_csv and not shutil.which(args.tcu):
        parser.error(f"TCU executable not found: {args.tcu}")
    try:
        args.out.mkdir(parents=True, exist_ok=False)
        provenance = dict(tool="tcu",
                          captured_at=datetime.now(timezone.utc).isoformat())
        csv_path = args.out / "capture.csv"
        if args.import_csv:
            shutil.copyfile(args.import_csv, csv_path)
            provenance.update(mode="import",
                              version="unknown",
                              replay_mode="unknown",
                              original_path=str(args.import_csv))
        else:
            version = subprocess.run([args.tcu, "--version"],
                                     capture_output=True,
                                     text=True,
                                     check=True).stdout.strip()
            invocation = [
                args.tcu, "--enable-metrics", args.metrics, "--replay-mode",
                args.replay_mode, "--export-csv",
                str(csv_path.resolve()), "--export",
                str((args.out / "capture").resolve())
            ]
            if args.kernel:
                invocation += ["--kernel-name", args.kernel]
            invocation += command
            provenance.update(mode="capture",
                              version=version,
                              command=command,
                              cwd=str(Path.cwd()),
                              requested_metrics=args.metrics.split(","),
                              replay_mode=args.replay_mode)
            # Never use a shell, silently enable replay, or retry application execution.
            with (args.out / "capture.log").open("w") as log:
                result = subprocess.run(invocation,
                                        stdout=log,
                                        stderr=subprocess.STDOUT)
            if result.returncode:
                raise ValueError(
                    f"TCU exited {result.returncode}; see {args.out / 'capture.log'}. No profiling artifact was generated."
                )
        artifact = import_csv(csv_path)
        artifact["enabled_metrics"] = sorted({
            m["name"]
            for group in artifact["counter_groups"]
            for m in group["metrics"]
        })
        if not args.import_csv:
            requested = {
                name.strip()
                for name in args.metrics.split(",") if name.strip()
            }
            for group in artifact["counter_groups"]:
                missing = requested - {
                    metric["name"]
                    for metric in group["metrics"]
                }
                if missing:
                    raise ValueError(
                        f"TCU omitted requested metrics {sorted(missing)} for {group['name']}"
                    )
        artifact["capture"] = provenance
        output = args.out / "profile.vendor.json"
        output.write_text(
            json.dumps(artifact, indent=2, allow_nan=False) + "\n")
        print(output, flush=True)
        # Run the device-independent reporter without importing native package init.
        subprocess.run([
            sys.executable,
            str(Path(__file__).with_name("report.py")),
            str(output), "--out",
            str(args.out / "report")
        ],
                       check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
