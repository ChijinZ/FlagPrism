"""Read-only checks of the announced public bundle, not profiler internals.

Schema announced by root on 2026-10-16; actual installed output has not yet
been inspected. Unsupported/unreviewed metadata stays pending, never passes.
Run this only inside booked server Docker along with qualification.
"""
import argparse
import json
from pathlib import Path

REQUIRED = ["id", "invocation_id", "binary_id", "program", "actor", "site",
            "semantic", "occurrence", "source_locations", "operation", "clock",
            "association_status"]


def inspect(bundle, receipt_path, case):
    failures, pending = [], []
    fine_path = bundle / "ai" / "fine_grained.json"
    plan_path = bundle / "ai" / "observation_plan.json"
    observations_path = bundle / "ai" / "observations.json"
    report_path = bundle / "report" / "index.html"
    for path in [fine_path, plan_path, observations_path, report_path]:
        if not path.is_file():
            failures.append(f"missing_public_output:{path.relative_to(bundle)}")
    if failures:
        return {"failures": failures, "pending": pending, "status": "fail"}
    fine = json.loads(fine_path.read_text())
    if fine.get("schema_version") != 1:
        failures.append("unexpected_fine_grained_schema")
    records = fine.get("records", [])
    receipt = json.loads(receipt_path.read_text())
    if not records:
        failures.append("no_dynamic_internal_records")
    source_path = Path(__file__).with_name("kernels.py")
    lines = source_path.read_text().splitlines()
    function_start = next(i for i, line in enumerate(lines, 1) if line.startswith(f"def {case}("))
    function_end = next((i for i in range(function_start + 1, len(lines) + 1)
                         if lines[i - 1].startswith("def ")), len(lines) + 1)
    anchors = {i: line.split("QUAL_ANCHOR ", 1)[1].strip()
               for i, line in enumerate(lines, 1)
               if function_start <= i < function_end and "QUAL_ANCHOR " in line}
    positions, sites, invocations, binaries, actors = set(), set(), set(), set(), set()
    by_site_call = {}
    for record in records:
        missing = [key for key in REQUIRED if key not in record or record[key] is None]
        if missing:
            failures.append(f"incomplete_dynamic_record:{record.get('id')}:{','.join(missing)}")
            continue
        if not record["source_locations"]:
            continue
        valid_locations = []
        for loc in record["source_locations"]:
            line = loc.get("line", 0)
            if (Path(loc.get("file", "")).name == "kernels.py"
                    and function_start <= line < function_end):
                valid_locations.append(line)
        if not valid_locations:
            continue
        positions.update(valid_locations)
        site = str(record["site"])
        invocation = str(record["invocation_id"])
        sites.add(site)
        invocations.add(invocation)
        binaries.add(str(record["binary_id"]))
        actors.add(str(record["actor"]))
        by_site_call.setdefault((site, invocation, str(record["program"]),
                                str(record["actor"])), []).append(record["occurrence"])
    if len(positions) < 2 or len(sites) < 2:
        failures.append("fewer_than_two_source_linked_internal_sites")
    if len(invocations) != len(receipt["calls"]):
        failures.append("dynamic_invocation_count_does_not_match_requested_calls")
    if case == "runtime_recurrence":
        if len(binaries) != 1:
            failures.append("runtime_loop_calls_do_not_share_one_binary")
        repeated = [group for group, visits in by_site_call.items()
                    if len(set(map(str, visits))) > 1]
        if not repeated:
            failures.append("no_same_site_same_actor_same_program_repeated_visits")
        # Exact iteration multiplicity depends on documented observer semantics
        # (body vs loop-header); never equate these without reading the plan.
        pending.append("verify_loop_body_2_and_5_visits_or_documented_header_3_and_6")
    # These are deliberate fail-closed review gates until the actual public
    # protocol has been read. A numeric receipt or static inventory cannot pass
    # the dynamic-device, loss, report-usability, and timing contracts alone.
    pending.extend([
        "verify_plan_selected_sites_bind_actual_binary_and_source_anchors",
        "verify_record_semantics_device_origin_and_clock_units_scope",
        "verify_attempted_committed_dropped_sampled_or_exact_backend_loss_protocol",
        "verify_report_direct_source_record_actor_navigation",
        "verify_cached_export_wall_s_at_most_60_from_public_timing_evidence",
        "verify_two_specializations_have_correct_distinct_binary_associations",
        "verify_tail_masks_and_unexecuted_vs_uncollected_distinction",
    ])
    return {"status": "fail" if failures else "pending_protocol_review",
            "failures": failures, "pending": pending,
            "dynamic_record_count": len(records), "source_positions": sorted(positions),
            "sites": sorted(sites), "invocations": sorted(invocations),
            "binaries": sorted(binaries), "actors": sorted(actors),
            "expected_source_anchors": anchors}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bundle", type=Path)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--case", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = inspect(args.bundle, args.receipt, args.case)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(1 if result["failures"] else 2)


if __name__ == "__main__":
    main()
