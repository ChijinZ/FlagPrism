# Actor-proof report fields and GCU stream regression

Report changes preserve the decoder's explicit `compiler_actor` proof and show
the compiler kind/function only when its verified raw slot equals this record's
measured actor. Plan declarations retain the actual function's emitted binding;
unmatched declarations and older records do not acquire that proof.

CPU-only report/source regression ran in Docker `chijin-study-pro6000`, using
`/workspace/venv/bin/python`: 60 passed, one preexisting optional report test
skipped. Tests include verified/unassociated actor evidence, mismatched raw-slot
presentation, binding-to-function matching and legacy plan compatibility.
YAPF0.43.0 preserved the tested ASTs; Ruff0.9.1 passed. This is engineering
validation, not independent qualification or a new Ascend device observation.

Evidence archive in the engineering workspace:
`artifacts/usability/run-002/c1-r2-report-evidence.tgz`, SHA-256
`2c9f3cd7f4078fb4f90fde9cc9c947c7a8ff78f06ddb0e1694c73ec64e98a6c5`.

The maintained GCU two-stream hardware test now covers the existing explicit
request and pure default `detail="auto"` modes. Both passed in existing Docker
`flagprism-enflame-dev`, independent installed source6098df5 environment, on
device0: six actual launches per mode, two actual streams and two compiled
specializations, exact CPU mathematical/input/output guards, retained raw bytes,
SDK process/context/domain/correlation/stream identity and capture isolation.
Typed mode retained80 records, default automatic48; no overlap, aligned-clock or
performance claim is made. Native task/grid identity remains unknown when the
SDK does not report it. Source formatting preserved the actual tested AST.

The initial automatic test incorrectly combined `detail="auto"` with an
explicit request; the documented API rejected it before launch. That harness
failure remains separate. The corrected default-mode test uses no explicit
request and expects default program0; explicit mode retains program1. Original
and corrected scripts/logs/results/raw bundles are preserved in
`artifacts/usability/run-002/c1-gcu-two-stream-evidence.tgz`, SHA-256
`97143028c66bc9ea546313ace5864cfcfd1eff48133ba25ae0b95f5aaf3143c6`.
Root controller220327 reached exit0, then device0 was handed to independent P2;
P2 additionally audited these bytes and identities. None of this substitutes
for the pending final version's frozen qualification matrix.
