# Late inline native wait control (r038)

This milestone adds final-object native wait-order facts to the default NVIDIA
late path and public offline reexport. It does not certify shared clocks,
source costs, hardware busy, or complete time flows. It adds no device
instruction, application replay or synchronization.

## Actual installation and immutable evidence

- Docker `chijin-study-pro6000`, RTX PRO 6000 SM120, GPU0.
- Installed Python `/workspace/chijin-timeline-r038/runs/install-public-v1/output/venv/bin/python`.
- Wheel SHA256 `4f633eb2bf90b46f67c1e8eb3a08b01328445acd685b4a0ec0ef03e77b40f31f`;
  615 archived installed members checked byte for byte.
- Core ABI3 and the r036 standalone recorder have unchanged sources/executable
  and explicit native bridges. This is a Python component update and actual
  wheel installation, not a new native build.
- Archive `artifacts/timeline/run-038/preflight/late-wait-control-evidence-v1.tgz`:
  25,576,006 bytes, SHA256 `1fa5ed73cef7ae5e0937386c8c795f3b87790a7fa32319bf2e92206391df04e2`.
  Its 3,210 file hashes were verified (3,212 total members). All 61 distinct
  recorded NVIDIA process identities were inactive at collection.

`verification.json` binds all four changed product/test files to actual installed
input and preserves full normal/optimized control results, recovery, offline
results and terminal receipts. Runtime prose and this evidence were added after
installation; no executable source changed after the installed tests.

## Mechanism and tests

`timeline_nvidia_late_control.py` consumes a freshly validated final-object map
and rebinds SASS text/JSON through the common control parser. For each selected
native wait it requires one static inline entry/exit reader pair in the same
function, exactly one unpredicated `DEPBAR.LE SB0` with a supported actual limit,
and checked control paths through that wait. External branches/reconvergence
cannot enter after the entry reader. Unknown syntax or ambiguous mapping gives
an explicit per-site unverified reason. The report binds the common helper
implementation digest as well as the actual binary and rules revision.

Default capture JSON references `native_wait_control_file` under
`machine/<binary_id>/late-wait-control.json`. Offline reexport uses the same
backend component and versioned derived control report. Legacy helper-call
behavior remains separate.

The first source-component run used retained actual r037 captures and passed;
this was explicitly not an installed acceptance run. A subsequent independent
wheel installation passed the following in the server Docker:

- Normal and optimized shared event/renderer/machine/legacy-control regressions:
  81 tests plus two subtests in each mode.
- Real default API math, streams, warm session (13 captures), and runtime-K GEMM
  (two full-CTA captures). Each GEMM default output includes the new native
  control report; all previously required mathematical/raw/counter-ns checks
  remain enabled.
- New actual-object/dynamic test in normal and optimized Python: the two static
  native wait sites have actual limits 1 and 0. For K96/K224, 1,024/2,048 dynamic
  recorded wait occurrences across full selected CTAs exactly match those
  limits. Original files remain unchanged; there is no device replay in this
  postcapture check.
- Duplicate reader and changed-disassembly negatives lose control qualification.
  Explicit CPU fixtures reject wait bypass, wrong wait operand, predicated wait,
  missing wait and an external entry after the wait. Fixtures are not device
  positives or complete self-consistent binary-mutation qualification.
- Actual compile/derive/copy fault recovery still passes with two successful
  launches, no failed-compile launch and no replay after recovery.
- Public/normal/optimized offline reexport reproduces all 16 new-layout traces
  byte for byte while denying the original environment. Actual TP SQL checks
  pass. This milestone changes no canonical/view/Perfetto encoder code; r037's
  actual grouped UI evidence remains the renderer evidence, not a new r038 UI run.

No failed product run is hidden. The installed controller exited zero in
124.329 seconds. Source checks and final prose formatting have separate receipts.

## Outstanding full-goal requirements

This is conditional control order between actual reader PCs. It does not prove
raw timer register-to-record value flow, all CTA participation, complete native
submit/commit/barrier/consumer boundaries, source-region costs, read precision,
cross-observer epochs, time-flow qualification or hardware overlap. The existing
collective byte model retains its narrower flags. Full Ascend/GCU timelines,
independent six-new-math qualification, controlled cases and the final three
fresh specified code reviewers remain required.
