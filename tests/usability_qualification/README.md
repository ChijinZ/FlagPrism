# Independent held-out usability qualification

Owner: `usability_qualification`. Product engineers must not inspect `kernels.py`
or `workload.py` until product/default/docs freeze. This is an access convention,
not a claim of cryptographic blindness. Root receives names, structural coverage,
manifest SHA and interface needs only. Any accidental exposure must be recorded.

There are six primary kernels: two pointwise/fused-memory, two reductions and
two matrix/fusion programs. Each has two shapes (one with tails) and two tile
configurations, identical mathematical source across backends. A seventh probe
has a runtime device-loaded loop bound with two values in one process. It does
not replace any of the six primary kernels. Each kernel updates an independent
per-program state exactly once per requested call; hidden device replay changes
the checked state. The launch script appends a durable process-start ledger to
detect whole-application replay. None imports a profiler API.

CPU double references, numeric tolerances, input hashes, output guards, state
guards, source anchors and shapes are part of the frozen corpus. CPU references
and even syntax/import checks are executed ONLY in a booked server Docker.
No local execution has been performed during authoring.

`manifest.json` records immutable input/source hashes. The manifest excludes
itself. Hashing/editing files on the workstation is allowed; this is not testing.
No mathematical oracle is computed locally.

Use an independent installed environment from the public documentation; capture
actual module paths, native/plugin hashes, baseline compiler version, install
source/package provenance and device/container in `product-freeze.json`. Never
silently add a private path, patch, scope, explicit site, ABI argument or expert
capture parameter. An ordinary failure stays in the result matrix.

The root issues a device booking JSON such as:

```json
{"backend":"ascend","container":"chijin_v3.5.x","device":"npu:4","owner":"usability_qualification"}
```

Run inside that existing server Docker, after engineering releases the device:

```sh
export FLAGPRISM_QUALIFICATION_SERVER_DOCKER=1
python tests/usability_qualification/qualify.py baseline --backend ascend --device npu:4 --booking /qualification/booking.json --root /qualification/first-pass
python tests/usability_qualification/qualify.py profile --backend ascend --device npu:4 --booking /qualification/booking.json --root /qualification/first-pass --product-freeze /qualification/product-freeze.json
```

For other backends only `--backend`, `--device`, the booking and documented
installation differ. Do not rewrite the kernels or mathematical inputs.

The baseline coordinator runs all 28 combinations without profiling first,
records original failures and seals eligibility. No eligible case can be removed
after seeing profile results. A baseline-ineligible case is never a profile pass.
There are 24 primary combinations plus four loop combinations per backend.
If a mathematical kernel is entirely baseline-ineligible, stop and pre-register
a genuinely different reserve before profiling; preserve the original results.
Tile parameters become "legal" only after actual baseline compilation succeeds.

Profile executes the documented default CLI twice per eligible combination,
once with a new compiler cache then with the same cache. Each independent
process must execute exactly once. The loop probe contains two actual calls;
their bound is runtime input and their compiled binary must be identical.
Profiles are never automatically called successful just because math passes.

Run the separate `check_report.py` on each bundle. It requires the announced
public schema and fails closed. Exit 2 means evidence exists but specific public
protocol checks require completion; it is NOT a pass or skip. At authoring time
the new public schema is planned, not claimed implemented. Once actual documented
schema is installed, adapt only report-field normalization and seal a new harness
revision before baseline execution, without changing held-out math.

For each case preserve startup ledger, complete logs, process PID/terminal code,
receipt, original bundle, plan, inventory, source-linked records and rendered
report. Preserve first failures and every repair pass separately. Inspect actual
source snippets, plan reasons, dynamic semantics, units and losses. Anchor lines
are expected source regions, never fixed profiler site IDs. A compiler may
associate multiple source candidates, but candidate ambiguity needs its reason.
Do not infer true timing, losslessness or device origin from a static field.

The coordinator applies the 64 MiB bundle target and caps total CLI wall time at
`min(300, max(120, 3 * baseline cold compile/launch/sync wall))`. This total-process
cap is stricter than the compiler-only budget, not a GPU performance benchmark.
Exact export duration must separately be demonstrated <=60 seconds using public
timing evidence. NVIDIA latency/throughput/overhead comparisons remain deferred.

First-pass failures are retained. A generic product repair invalidates the
"unseen" label for any disclosed kernel. Re-freeze product and repeat eligible
matrix using new result directories; add an independently authored fresh kernel
in each structure category touched by repairs. Record source exposure explicitly.
Never count repeated known samples as new generalization evidence.
