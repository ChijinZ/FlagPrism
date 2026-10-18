# Default shared CTA counter coordinates (r040)

The default NVIDIA late path now publishes standard Perfetto files containing
multiple actual observed threads on one shared counter coordinate. Each file
belongs to one actual invocation/program. It preserves original counter offsets;
it does not individually zero observers, fit offsets from counts, certify read
precision, infer physical overlap, or generate temporal flows.

## Actual installation and evidence

- Docker `chijin-study-pro6000`, RTX PRO 6000 SM120, GPU0.
- Installed Python `/workspace/chijin-timeline-r040/runs/install-public-v1/output/venv/bin/python`.
- Wheel SHA256 `e81b9cd24d035d378ffb9f9a0a119b0f7b024a79b8492fa2d7d1085e705e5814`;
  all 617 installed archive members verified. Core ABI3 and standalone recorder
  source/executable are unchanged, with explicit reuse bridges. No new native
  compilation is claimed.
- Archive `artifacts/timeline/run-040/preflight/shared-axis-evidence-v1.tgz`:
  94,374,094 bytes, SHA256 `6aef36fc253ef502bf576c5aa34c161d2f14d929714cf9c7e8313b87f6832477`.
  All 4,681 retained file hashes were checked (4,684 members); all 99 distinct
  recorded NVIDIA process identities were inactive at collection.

`verification.json` binds current product/tests to actual installed source,
records the later runtime-prose and UI-click-checker deltas, and retains full
scope negatives, real SQL/UI results and remaining qualifications. Formatting
of final prose/evidence is separate and does not replay products or math.

## Clock and projection boundary

The backend combines actual marked full-width SM120 object readers, complete
raw/manifest binding, a completed single native CTA, actual device/stream and
host completion window with NVIDIA's documented device clock semantics. The
provider retains a short excerpt/reference, content digest, machine-map digest
and capture-context digest. The source is the
[NVIDIA CCCL Time Library](https://nvidia.github.io/cccl/unstable/libcudacxx/standard_api/time_library.html).
It supports a common nominal counter epoch within that scoped invocation/CTA;
it is not a quantitative physical read-error bound or host-clock correlation.
Other targets do not inherit this provider merely from a vendor or timer name.

The common `SharedCounterProof` binds raw/canonical/capture identity and explicit
observer/program scope. A new schema-2 derived view subtracts one common raw
origin before exact rational conversion. It retains unknown endpoint precision
and false physical-comparison/time-arrow rights. Old canonical events and
isolated exports remain available. Full-CTA recordings select actual threads
0/32/64/96 in the four-warp tests; a recorder that captured only four threads
cannot invent other warp data. Those are actual recording threads, not measured
warp-wide elapsed times or native engine lanes.

A common renderer emits compact per-thread observation tracks with original
event labels/categories/source/raw/lifecycle references. Its public isolated
path still validates the old unit proof, and its bytes remain unchanged.
Capture JSON adds `shared_counter_exports`/`shared_counter_status`; public
offline reexport adds `shared_exports`. The navigation index labels shared
counter groups and preserves both old/new committed links.

## Actual checks

The independent installation exited zero in 161.438 seconds. Default API
math/streams/warm sessions (13 captures), runtime-K GEMM math (two full-CTA
captures), compile/derive/copy-fault recovery, normal/optimized lifecycle,
async, raw-view and native-wait regressions all passed. Shared regressions each
passed 81 tests and two subtests in normal and optimized Python. New shared
contracts require the default collector itself to publish both actual program
traces; a separate offline prototype is not counted as default success.

The final shared tests select four real distinct-warp threads per program,
check every raw eight-byte field and exact common-origin coordinate, and reject
wrong invocation/canonical, cross-program subjects, changed coordinates, forged
flow rights, loss and Boolean native geometry. They test idempotent publication
and reproduce all 16 original isolated traces exactly. Actual fresh first-read
offsets include `[0,0,32,32]` and `[0,0,0,32]` ns; these are retained offsets,
not independently zeroed traces or a claim about physical read accuracy.

Actual TP/protobuf checked eight shared files from two fresh captures and two
historical r039 captures upgraded with the installed public command. All slice
endpoints, raw references, observer identities, common-origin/domain metadata
and four-subject coverage match. No flow was invented. Six distinct files across
all four actual calls were opened in standard Perfetto v57.2-da1d152cf and
Chromium 140.0.7339.16; the checker selected real slices, read source/raw/quality
and shared-origin details, and expanded all four observed threads. Screenshots
and exact selected IDs are under `runs/ui-only-v2/output/UI/` in the archive.

Current public/normal/optimized offline processes reproduce the 16 fresh
isolated files byte for byte. A separate installed legacy check reexports three
real r024 captures and their 24 files byte for byte, with actual TP checks and
original environment/GPU access denied. No application is replayed.

## Failures and remaining requirements

The initial format pass caught an offline-branch indentation error before any
installation. It was corrected; the successful format fixed point is retained.
The first UI checker clicked the middle of a multi-height canvas, which was an
empty slice depth. Actual screenshot inspection localized the issue; only the
checker click moved to the first slice row. The final six-file UI pass uses
that exact server-formatted checker. Failure text/screenshots remain.

The root byte audit compares historical private originals to r039's archive and
checks copied immutable inputs; only regenerated copied `index.html` navigation
may change. It checks links to every old and new committed trace. This page is
derived navigation, not immutable raw evidence.

The complete goal still requires quantitative clock/endpoint evidence where
needed, native producer/publication/consumer and record-value facts, actual
dynamic temporal arrows, full Ascend/GCU implementation, independent six-new-math
qualification, controlled cases and three fresh specified code reviewers.
NVIDIA device throughput/overhead certification remains deferred. No paper or
Study was edited. This milestone is not full three-backend acceptance.
