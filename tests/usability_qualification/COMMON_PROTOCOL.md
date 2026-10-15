# Q2 common-cohort acceptance protocol

This document supplements the immutable Q0 README and manifest. No candidate
profiling has run. The held-out source convention covers all math files,
including both reserve files. Root and engineers receive names, structure and
hashes; this is an access convention, not cryptographic blindness.

The preregistered common cohort is rational_blend and cubic_window (pointwise),
weighted_covariance and absolute_deviation (reduction), symmetric_cross and
bilinear_difference (matrix/fusion). Each uses two shapes and two configurations.
The frozen JSON contains 72 actual passing ordinary baseline receipts across
three backends, plus 12 runtime-loop combinations. The same mathematical source,
input hashes, original tolerances and canaries apply everywhere. The matrix
reserves use non-idempotent output dependency; the other common workloads use
per-program state. Every process also appends exactly one host ledger entry.
Runtime bounds 2 and 5 must produce repeated visits under one actual binary.

Original results remain evidence: NVIDIA original 28/28 passed; GCU original
24/28 passed with four compiler timeouts; Ascend Q1 original 23/28 initially
passed, with five matrix scalar-probe failures. Two of the three originally
passing Ascend matrix combinations failed an ordinary repeat. CPU math, input
and canaries passed in the scalar-only failures. A separate ordinary diagnostic
observed one native launcher call with unexpected state counts. Actor task
counts were not observed. Original Q0 Ascend pre-device import failures are also
retained. These outcomes are not profiler failures and have not been erased.
The reserve math was registered before candidate profiling, then independently
qualified on all three backends. No candidate failure may remove an eligible
common-cohort combination or change its oracle.

Only run in server Docker after explicit ownership and final product/docs/install
freeze. Ordinary baseline compilers and candidate environments differ; candidate
must use an independently installed public package. No private profiler imports,
site names, transform hooks or expert capture parameters are allowed. Ascend
uses the same ordinary vendor-initialization wrapper as its corrected baseline.

The runner requires a root-supplied freeze JSON with `candidate_frozen: true`,
`product_revision`, `public_docs_sha256`, and `installed_native_sha256`, plus any
additional install provenance. This records the authorization and evidence;
independent native/install provenance must be checked before issuing it.
Booking JSON uses an integer device (the old Q0 README example was descriptive):

```json
{"exclusive":true,"backend":"ascend","device":4,"container":"chijin_v3.5.x","owner":"usability_qualification"}
```

From the independently installed environment, with the test directory copied
unchanged to the server:

```sh
/path/to/installed/python /workspace/qualification/run_common.py \
  --backend ascend --device 4 --freeze /workspace/freeze.json \
  --booking /workspace/booking.json --pass-kind first \
  --output /workspace/qualification-results/ascend-first
```

Use backend `nvidia` with logical device 0 or `enflame` with device 0 as appropriate.
The runner sets only the documented vendor backend environment, removes private
profiler overrides and PYTHONPATH, and invokes the public command:

```sh
/path/to/installed/python -m flagtree.profiler.cli --detail auto --device 4 \
  -n NEW_BUNDLE ORDINARY_STARTUP.py ORIGINAL_WORKLOAD_ARGUMENTS
```

It runs all 28 combinations twice (cold/warm independent processes, shared cache
only within each combination), keeps stdout/stderr/PID/exit/wall-time and receipts,
and writes immutable per-run decisions plus a growing summary. Its outer guard
is the sum of documented startup, baseline compile, export and supervision grace;
the public CLI must independently enforce startup/compile/export deadlines.
A later repair uses a new output directory and `--pass-kind repair`; first-pass
results must remain available. No overwrite is allowed.

`check_common_report.py` reads only documented public files. It verifies complete
bundle size <=64 MiB, exact manifest coverage and hashes, actual binary/call joins,
source snapshots and compiler stages, at least two actual internal sites and two
source positions per invocation, automatic candidate inventories and reasons,
backend-specific primitive/actor/timeline loss accounting, clock conversion
claims, loop repeated visits, full finalize/export <=60 seconds, deadline metadata,
and links/source/call identities in HTML. The original `check_report.py` is retained
unchanged; the new checker supersedes its provisional interface assumptions.

For this corpus, dropped or saturated records fail acceptance. GCU temporal
sampling is counted separately from overflow; sampled visits fail the exact-loop
qualification rather than being mislabeled as drops. Partial unresolved records
remain visible and require documented limits; they do not satisfy the two-site
minimum. HTML interactive browser controls and independent implementation review
of device origin are explicitly outside this file verifier. Those are separate
review obligations, not claimed passes.

Synthetic checker rejection tests run in server Docker without device use:

```sh
cd /workspace/qualification
/path/to/python -m unittest -v test_public_checker
```

These fixtures test rejection logic only. They are never device observations or
qualification success evidence. No tests, imports, CPU math or GPU programs were
executed locally during authoring.
