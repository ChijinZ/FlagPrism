# Clock call provenance and real GCU append samples (T020 / r013)

This checkpoint is incomplete P01. It delivers installed static-call metadata and
real GCU adapter inputs, not a clock/source-region/preserved-pipeline certificate.
No paper or old Study changed. Product/tests/oracles ran in existing server
Docker; workstation checks only read retained bytes and Git sources.

## Product and verification

- Component freeze `39e95f42135a0ec761ede1b4a0f8f1524fb3188e`, installed NVIDIA
  `/workspace/chijin-timeline-r013/runs/install-v2/output/venv/bin/python`.
  Wheel SHA `9a43ee79a78184ac395e57670ea5499b5771276ceba29f0193e5fe1434a996f4`;
  607 installed members checked. Seven native members remain byte-identical to
  the preceding installed native build; no changed C++ was falsely repackaged.
- `static_model_version=1` adds exact calls, counter-to-caller relationships and
  synchronization positions/operands. Text/JSON targets and synchronization
  operands must agree. Indirect/unknown calls stay unresolved; no prefix matching.
  Multiple callers/readers remain explicit, inline readers can have no caller.
  Caller grouping avoids a full cross-function scan; expanded references are
  bounded to 65,536. Overflow preserves raw with mapping unavailable.
- Final Docker CPU: 25 mapper tests and four public contracts, normal and `-O`.
  Before the small reference-budget fix, 24 mapper tests passed and five actual
  ordinary dtype captures passed math/input/canary/once checks: 320 intervals,
  80 real getter and direct-call references. That earlier source freeze is
  `3b237e8fb054d4d7b24cef0c2b9c06169fbc0e6f`; it is retained separately.
- Both installations reprocessed the seven real r012 cubins without GPU/application
  replay, normal and `-O`: 140 getters/calls and 13 static synchronization sites.
  These are counts of code locations, not executed operations. The original
  ordinary-control failure and copy/wait/dot interleaving change from r012 remain
  unresolved; this metadata does not certify original scheduling.

## Real GCU samples

In Docker `flagprism-enflame-dev`, the existing published advanced automatic
producer ran one ordinary baseline and three explicit profiled calls, using an
unannotated recurrence with runtime K=3/7/11. All three profiles share binary
`95a3bba3bcf06e4cd9232d408dece697ca6d536bc37542cf6fd86d2d40876ec6`.
They contain 10/14/18 actual intervals (42 total), eight source sites; the selected
loop-body site repeats exactly 3/7/11 times. Math/input/tail and once-state passed.

The 32-byte header and 64-byte complete-pair append records are audited directly:
program 0, work-item 0, exact sequence/ordinal, commit tags, 46-bit ticks and
raw hashes. This is not a warp/SM model. Each buffer is 32,800 bytes; these samples
have no overflow and no sampling omission. The selected sites are leaf intervals;
there is no observed start/end regression in these samples. They do not prove
all nested pairs have globally ordered endpoints.

GCU remains on the **existing advanced entry** and old published native producer,
not the new default `detail="timeline"` integration. Installed dependency hashes
are in [pins](gcu-installed-pins.json). Clock units/epoch and machine boundaries
stay unverified; no ns values or time arrows are invented. A common adapter must
preserve complete-pair provenance, producer-specific loss accounting and unique
session/owner identity: existing `ir-capture-0`/`launch-1` labels are local to their
exports, not globally unique IDs. Neither packet shape nor actor names should be
copied from the NVIDIA ring.

## Reproduce the byte audit

[Raw index](raw-artifact-index.json) binds three immutable archives: NVIDIA v1,
NVIDIA final v2 and GCU. The original r012 archive is also required to compare
new call metadata with its actual retained text/JSON disassembly. Original raw
and SDK-containing compiled artifacts stay outside Git. Small receipts/results
are included here.

```bash
python FlagPrism-method/integration/evidence/timeline-call-model-r013/audit-retained-bytes.py \
  --repo FlagPrism-method \
  --nvidia-v1 artifacts/timeline/run-013/preflight/nvidia-call-model-original-evidence.tgz \
  --nvidia-v2 artifacts/timeline/run-013/preflight/nvidia-call-model-v2-final-original-evidence.tgz \
  --enflame artifacts/timeline/run-013/preflight/gcu-dynamic-original-evidence.tgz \
  --prior-nvidia artifacts/timeline/run-012/preflight/outlined-final-original-evidence.tgz \
  --output /tmp/flagprism-call-model-audit.json
```

The audit uses source bytes from their actual Git freezes, so later unrelated
changes to the current worktree do not invalidate historical identity checks.
It independently checks call targets/sync operands against original tool bytes
and reconstructs GCU payloads against exported intervals. It does not re-run a
math oracle on the workstation.

An initial v2 collection selected the v1 installed module path; the byte audit
rejected it. [Failure](initial-collection-failure.json) preserves its identity.
Only the collection path was corrected into a new final archive; no math or
product test was replayed to repair evidence. The failed collection is retained
outside Git and is not used as v2 installation proof.

## Still required

A post-O3 compiler insertion point exists after `llvm.optimize_module`; current
clock/logger insertion runs earlier. [Actual source inspection](late-hook-source.txt)
identifies a possible route to reducing optimization interference, not an
implemented late logger or proof that this route will preserve all scheduling.

Still open: source/control/participant boundaries and perturbation assessment,
clock scale/endpoint/epoch qualification, real buffer/flag reuse, common GCU and
Ascend producers and complete three-backend P01, standard ns/Perfetto SQL/UI,
independent math, controlled cases and the final extra three specified reviewers.
No final reviewers were started early. Goal remains active.
