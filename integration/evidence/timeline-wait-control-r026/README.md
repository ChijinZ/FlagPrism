# Native wait control paths r026

Product commit: `df48ae5`. This implements a missing automatic machine-path
check; it does **not** complete source timing, P01 or three-backend acceptance.
No paper or old Study files changed.

## Behavior

Default NVIDIA timeline finalization now adds
`machine/<binary>/wait-control.json`. Offline re-export derives the same kind
of report under `derived/control/<revision>/`, with a `wait_control_file` in
the returned capture result:

```bash
python -m flagtree.profiler.timeline_reexport BUNDLE/timeline
```

The backend-specific checker binds the two actual disassemblies, resolves
branch labels, retains conditional BRA.U operand predicates, checks unique
counter callers and leaf helper bodies, follows return-register moves back to
the caller's explicit return address, and checks finite forward paths through
the matching native wait. An entry-guard fact is used only when other control
edges cannot bypass it, and writes to its predicate invalidate that fact.
Unknown control, backedges, helper side effects, ambiguous callers or operands
retain a concrete unverified reason. This adds no device instructions or sync.

`wait_control_order_checked` means only native wait control order between the
inspected clock helper calls. It does not prove logged-value provenance,
complete source boundaries, participating lanes, elapsed-time precision or
hardware overlap. The report keeps those qualifications false. Optional
analysis failure remains a diagnostic and does not suppress otherwise valid
counter-unit exports. Old raw bytes, canonical events and original reports
remain unchanged.

## Actual object results

The unchanged r024 FP16 GEMM is 48×192 times 192×56, blocks 32³, four warps,
three stages. The production postprocessor freshly disassembled its retained
CUBIN using the final installation; no user math was replayed.

| Compiler site | Native wait limit | Begin call PC | Wait PC | End call PC | Checked control states |
| --- | ---: | --- | --- | --- | ---: |
| 10 | 2 | `0x2130` | `0x2240` | `0x2280` | 21 |
| 20 | 0 | `0x4ea0` | `0x4fa0` | `0x4fe0` | 20 |

Both sites obtain control-order facts automatically. Runtime-loop recurrence
objects have no cp.async wait sites and gain no invented waits. The source
stage initially exposed `BSSY.RECONVERGENT` spelling and nvdisasm 13.2 JSON's
omitted comma before a bracketed LDS operand. Original failures are retained;
the parser binds the full registers/immediates/address expressions after that
separator normalization.

Self-review after the first installation found that the printed return symbol
alone did not bind the dynamic return address. The final revision follows the
actual register transfers, including the second word of MOV.64, and requires
the caller's return PC initialization. Wrong RPC and clobbered RPC negatives
were added before the final installation and object replay.

## Installation and verification

All product tests, installation, actual-object parsing, Trace Processor and
browser work ran in existing server Docker. NVIDIA used
`chijin-study-pro6000`; GCU's `flagprism-enflame-dev` supplied cached formatting
only. There were no new user-math launches or exclusive performance tests.

* Final interpreter:
  `/workspace/chijin-timeline-r026/runs/installed-v2/output/venv/bin/python`.
* Final wheel SHA256:
  `3543b4f5fd1b69d39806f5b99f725d5d15c83603e68d0ca4a0c94cea5e5d42b7`.
* 602 installed wheel members byte checked; 78 installed profiler Python files,
  271 unchanged native inputs and 1,982 source files bridged to current source.
  The actual native core is unchanged from r024; this is a new Python package
  and independent installation, not a claimed new C++ build.
* First installation: 15 new unittest cases plus the unchanged machine/store/
  Perfetto tests, and 63 pytest cases plus 32 subtests, normal and optimized.
  Final RPC delta: 16 new unittest cases in both modes and fresh production
  postprocessing. The optimized pytest run retains its expected warning.
* Final v3 and v2 actual bundles: three fresh re-export processes per format
  (public, isolated normal, isolated optimized), GPU hidden, old environments
  and subprocess application replay denied in isolated runs. Each format
  retains three captures and 24 traces; actual TP SQL verifies exact ns/raw
  references, no importer errors and no invented flows. All 48 trace byte
  hashes also match their original exports.
* Six final traces inspected in standard Perfetto UI, with actual event
  selection/details and readable overview screenshots. Browser
  `140.0.7339.16`, UI index SHA256
  `00f30fc225e83616ff084fee6126dfcd41d73ac923cb267be683867dbf9f0815`.
  Root visually inspected the retained GEMM overview.
* Actual process audit: 76 recorded NVIDIA identities inactive; no owned active
  descendants by script paths or deadline ownership. GCU formatter identities
  are audited separately. Nothing was killed outside owned work.

## Retained evidence

Workspace archive:
`artifacts/timeline/run-026/preflight/wait-control-evidence-v1.tgz`

15,652,174 bytes, 1,597 regular members; SHA256
`9a54254077506a0b67e878acc1b932d61ca0535aa73952b3037cadab07cce53e`.
It contains source-stage failures, final relevant source, full source manifests,
install/test receipts, original inputs, fresh disassembly, derived control
reports, real TP checks, UI screenshots and ownership audit.

Local unchanged originals copied for review are under
`artifacts/timeline/run-026/review/`: `gemm-program0-warp0.pftrace`,
`overview.png`, `details.png`, and `wait-control.json`.

[verification.json](verification.json) summarizes the actual byte audit.
[audit_evidence.py](audit_evidence.py) checks originals and source bridges using
only the standard library; from the repository root:

```bash
python integration/evidence/timeline-wait-control-r026/audit_evidence.py \
  --archive ../artifacts/timeline/run-026/preflight/wait-control-evidence-v1.tgz \
  --source . --output /tmp/timeline-r026-verification.json
```

Next: bind recorded values and source regions to the inspected machine paths,
then complete clock/participation and dynamic async qualifications. GCU/Ascend
time qualification, independent six-math acceptance and the final three extra
specified code reviewers remain mandatory and incomplete.
