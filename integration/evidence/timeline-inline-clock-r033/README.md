# Inline clock candidate: real native build and unresolved pipeline changes

Canonical product remains `82c29610e008d1688af3c2dc259cd2bbe95731aa`.
The isolated candidate is `115d5e5f4d6f0e50d51cb218a06db1bf7f89c351`;
`candidate.patch.json` retains its seven-file source delta. It is not promoted.
No paper or Study files were changed.

## Change and actual installation

Boundary version 4 emits the marked timer in the guarded caller block, retaining
runtime-zero control/data dependencies and the compiler memory clobber. It adds
no completion barrier. Explicit versions 2 and 3 remain supported; raw ABI is 3.
This is a compiler-placement experiment, not a clock or source-boundary proof.

The first native build failed on the MLIR `CallOp.getResult(0)` API. The fixed
`getResult()` build reused the same objects after verifying the original owners
were inactive, changing only the mutable build copy of TargetInfo.cpp and
retaining the original source and failure. The official build recipe completed;
its new wheel is 391364132 bytes, SHA-256
`9f895d8db232ce4ff850d728dcfe6b621d4b8d48ea8ec5f7178a066a91fe1164`.
All 668 candidate source files match the actual build input snapshot.

NVIDIA Docker: `chijin-study-pro6000`, GPU 0. New isolated interpreter:
`/workspace/chijin-timeline-r033/runs/installed-native-v2/output/venv/bin/python`.
The initial installation controller rejected a 900s harness deadline before
starting a worker. The retained failure was corrected using a fresh directory
and the existing 300s limit; no product/device tests were repeated from it.

Installed v2 completed all 12 steps, including wheel-member byte verification,
actual ABI 4, normal/optimized compiler-boundary and public-contract checks,
five dtype math kernels, unchanged constant-K GEMM and both observation densities
of runtime-K GEMM. The dtype regression checks exact outputs, inputs, tails,
per-program side effects and the actual four-byte runtime-zero module global.
Runtime-K cases check original math, inputs, tails, atomic invocation counts and
default ns exports. This is development evidence, not independent qualification.

## Actual issue order: problem remains

| Kernel / variant | Function instructions | Math loops retained |
| --- | ---: | ---: |
| Runtime-K ordinary | 280 | 1 |
| Runtime-K inline, sparse budget 1 | 912 | 1 |
| Runtime-K inline, default budget 8 | 1256 | 1 |
| Runtime-K previous outlined default | 1395 | 1 |
| Constant-K ordinary | 200 | 0 |
| Constant-K inline default | 1488 | 1 |

The runtime-K ordinary loop issues copy between its final two HMMA instructions.
Both inline variants still issue copy after all four HMMA instructions; removing
the clock calls does not restore that ordering. The constant-K ordinary kernel
has no retained math loop, whereas the inline instrumented kernel does.
These are actual compiled instruction/control observations, not measurements of
throughput, hardware busy, or loss of all physical overlap. No exclusive NVIDIA
performance/overhead experiment was run.

The candidate therefore does not solve the pipeline-perturbation issue. The
actual parent compiler places automatic scopes before LLVM O3; LLVM O3 enables
loop unrolling. That stage order motivates investigating later recording
insertion, but does not alone prove which optimization caused each difference.
Do not fix the test by changing the user's kernel or forcing a kernel-specific
unroll policy. Preserve the two ordinary/instrumented comparisons.

## Retained evidence and next work

Workstation artifact:
`artifacts/timeline/run-033/preflight/native-inline-evidence-v1.tgz`.
It contains immutable initial/fixed inputs, native and installation receipts,
first failures, real raw captures, compiled artifacts and six machine comparisons.
`verification.json` records archive SHA, actual sources, step results and native
instruction facts. Actual native/install/inspection owners were checked inactive.
No new Trace Processor/UI acceptance is claimed for this candidate; prior r032
unit-only exports do not qualify these new bytes or a full internal pipeline.

A separate Enflame internal clock-anchor prototype completed nine explicit
launches with selected actor, guards, frozen training-rate bounds and independent
held-out samples. Artifact:
`artifacts/timeline/run-033/preflight/gcu-clock-anchor-evidence-v1.tgz`.
Its archive identity is retained separately. The empirical rate applies only to
that probe window; it is not user math, a future-capture time certificate, shared
epoch evidence, or completion of Enflame's timeline service.

Full three-backend source-region/async pipelines, clock comparison, independent
six-math qualification, controlled cases and the final three fresh reviewers
remain required. Next work must address the ordinary/recording compilation path
and interpretable dynamic dependencies, rather than add unit-only qualification.
