# Public default automatic driver regressions

The default `detail='auto'` drivers use the all-grid source-site census. The
shared `source_census_assertions.py` checks raw SHA-256, every physical cell and
padding byte, capture/binary/invocation identity, exact loss status, source
metadata, and the complete normalized row set. Derived JSON views are restored
through the lossless `export_refs.restore` contract before inspection. No product
census decoder is used as the raw-byte oracle.

A normalized row represents one nonzero observer/site cell. Its `count` is the
actual source-control visit count, including visits with all-false data masks;
it does not measure active lanes or timing. Loops assert `count`, rather than the
number of rows. The lowest program with primary visits is selected for display;
the complete grid remains in raw storage. Ascend keeps actor-qualified counters
and does not assert checkpoint order or condition-header event multiplicity.

These observation changes preserve the existing kernels, math references,
inputs, tolerances, launch configurations, and baseline checks. NVIDIA
`automatic_manual_compatibility.py` and Ascend `acceptance.py` retain the explicit
advanced interval/checkpoint paths. The default drivers do not switch to those
paths to obtain a passing result.

`source_census_public_regression.py BACKEND ARCHIVE.tgz [...]` replays retained
public bundles inside the assigned server Docker without device execution. It
also rejects changed counts, programs, invocation identity, invented timing,
duplicate/missing rows, changed digests, and missing source origin. NVIDIA/GCU
single-capture driver validators are extracted by AST and called on each real
capture projection after reference restoration. This is maintenance evidence
from already public development data, not independent unseen qualification.

GCU `control_flow_hardware.py` preserves both original while-region assertions:
condition-region counts equal `steps + 1`, body-region counts equal `steps`.
Ascend `automatic_record_budget.py` checks fixed census storage and exact
actor/site counts for its original 64/128-round workloads. Its historical
`--expect-loss` option fails with an explicit explanation before device work:
checkpoint-ring exhaustion is outside the default census contract.
