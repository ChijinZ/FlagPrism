# Ascend default counter-unit exports — r031

This checkpoint adds the inspected Ascend910B c220-vector path to the existing
shared counter-unit view and standard Perfetto exporter. It does not complete
source-region, asynchronous pipeline or three-backend acceptance.

## Actual result

- Reused `chijin_v3.5.x`, NPU4, actual runtime `Ascend910B4-1`.
- Independent installation: `/tmp/chijin-timeline-r031/runs/installed-v1/output/venv/bin/python`.
- Ordinary unannotated runtime-K recurrence (K3/K7, two streams) and Softmax
  passed numerical/input/tail/state/guard checks: three captures, 50 intervals,
  100 endpoint references, six observer-relative `.pftrace` files.
- Actual loaded ELF/function/DWARF clock markers bind SYS_CNT reads. The unit
  provider also requires the actual runtime model/device, exact raw records and
  a bounded host observation window. No per-operator special case was added.
- Public/normal/optimized fresh-process offline re-export kept all 36 original
  files unchanged, without application replay, NPU initialization or subprocess
  execution in the audited decoder. Retained ELF/DWARF are rechecked offline.
- Actual Trace Processor 57.2 imported all six files, SQL matched exact ns and
  raw identities, and reported no importer errors or invented flows.
- Standard Perfetto UI v57.2-da1d152cf with Chromium 140.0.7339.16 opened all six,
  expanded tracks, selected actual positive slices, inspected source/raw/quality
  details and focused them. Screenshots and original file hashes are retained.
- Installed tests: Ascend runtime/legacy 21 normal + 21 optimized; machine and
  unit negative checks 23 normal + 23 optimized; shared view/clock/store/export
  regression 19 normal + 19 optimized. Source-overlay checks are recorded
  separately and are not counted as an independent installation.

The [documented A2 SYS_CNT](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/API/ascendcopapi/docs/en/api/SIMD-API/basic_api/tool_interface/system_resources_and_variables/GetSystemCycle_ISASI.md)
is 50 MHz, giving 20 ns per tick. The getter belongs to PIPE_S; this
implementation adds no completion barrier for other engines. The rule does not
extend to other Ascend generations or compiler targets.

## Product path

`ordinary launch → runtime model snapshot → raw retention → optional final ELF/DWARF inspection → Ascend unit provider → shared CounterUnitProof/views/exporter → standard Perfetto`.

`timeline_ascend_machine.py` is the backend instruction/marker mapper;
`timeline_unit_ascend.py` supplies bounded, identity-bound unit evidence. The
common exporter contains no new Ascend instruction parser or vendor branch.
Missing tools/markers/unit evidence preserve raw and report the missing fact.
Old captures without runtime model snapshots remain raw; they are not retrofitted.

## Limits and retained failures

These are counter brackets, with unknown read precision and source-operation
boundaries. They are not certified instruction costs, engine busy, cross-observer
alignment or asynchronous flows. Two separate observer files must not be merged
as evidence of overlap. Matrix/AIC, source elapsed, real buffer reuse/async,
independent six-kernel qualification and final three code reviews remain open.

Source-v1 retained two malformed-fault-fixture failures: the canonical endpoint
validator correctly rejected them before the intended unit checks. Source-v2
fixed the fixtures without weakening that guard. Checks-v1 retained a harness
error naming a nonexistent test file; the installed normal mapper passed before
that error. Checks-v2 ran only the remaining optimized mapper and corrected
shared regression. UI-v1 retained a missing Perfetto dependency in the browser
venv; UI-v2 used the established separate TP tools environment. These failures
did not cause a device math replay.

The first offline harness denied obsolete `install-v1/cache` and `tmp` paths
instead of this run's `installed-v1` directories. An additional bounded offline
job tested both original recurrence and Softmax bundles while denying the actual
source/cache/tmp/device-output roots. Public/normal/optimized re-export passed
for both; see `offline-actual-environment.json`. No device math was replayed.

The test-only offline harness received whitespace formatting after the source
upload; product Python hashes in `verification.json` match the actual installed
input snapshot. Native/frontend sources are unchanged: the r030 rebuilt marker
plugin and previously built version-3 frontend are reused, with actual hashes
in `wheel-receipts.json`. No new C++ build is claimed.

## Evidence and replay

Workstation archive directory: `artifacts/timeline/run-031/preflight/`.
`verification.json` records archive hashes, product source hashes and exact real
capture identities. `ascend-owners.json` and `view-owners.json` record terminal
jobs and actual inactive process identities.

```bash
python integration/evidence/timeline-ascend-counter-unit-r031/audit.py \
  --repo . --preflight ../artifacts/timeline/run-031/preflight
```

This command audits retained bytes/JSON only. Product/device/TP/browser tests ran
inside existing server Docker containers. Original trace bytes are also exposed
under the archive directory's `traces/`; UI artifacts are in
`ascend-TP-UI-evidence-v1.tgz`, `browser-v2/output/UI/`.
