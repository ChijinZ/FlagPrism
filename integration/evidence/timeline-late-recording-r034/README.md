# Late NVPTX recorder: actual math and byte dependencies

Source component commit: `d0f91f4` (experimental). The default timeline API and
existing product paths were not switched to this component. No paper/Study
files were changed. These results are development evidence; three-backend
qualification, independent six-math tests and final reviewers remain pending.

## What the new component does

The LLVM tool inserts records after ordinary LLVM optimization, using an
explicitly checked unused profile-scratch argument. Original kernels have no
manual scopes or added source arguments. The experiment's driver harness supplies
the existing hidden ABI; it does not stand in for the public launch path.

Records cover actual AS3 loads/stores, cp.async submit/commit/wait, CTA barrier
checkpoints and grouped matrix issues. All source/native group members are
retained. No completion barrier is added. Each selected program records all 128
threads, with a private coalesced layout; first/last logical programs map to two
physical slots without renumbering their identities.

The actual dynamic shared-symbol base is captured. On this target it is 1024;
comparing raw addresses directly against a size with assumed base zero was an
incorrect prototype validation rule. The original failure is retained. The fixed
checks use the real base plus the ordinary kernel's actual allocation length.

## Actual native and device results

Server Docker: `chijin-study-pro6000`, GPU 0, sm_120a. The new standalone recipe
built the final native tool against the actual LLVM 22 SDK. Final tool source and
executable hashes are in `verification.json`. The final v9 tool emitted exactly
the same LLVM IR and manifests as the successful v8 tool for both real inputs;
the added geometry rejection did not require replaying unchanged device math.

Actual compact samples, each with one explicit mathematical launch:

| Ordinary workload | Actual mathematical programs | Recorded logical programs | Recorded actors per program | Device records |
| --- | ---: | --- | ---: | ---: |
| Runtime-K GEMM, K=96 | 4 | 0, 3 | 128 | 13056 |
| Runtime-K GEMM, K=224 | 4 | 0, 3 | 128 | 24320 |
| Constant-K GEMM, K=96 | 4 | 0, 3 | 128 | 14848 |

All three passed the original FP16-input/FP32-output math against CPU FP64 with
frozen 1e-2 tolerances, unchanged inputs, output tails, allocation guards,
publication/identity/clock-order checks and actual shared bounds. Runtime-K
atomic side effects checked one update per requested program, including the
unrecorded middle programs. Warmup ordinary LLVM IR matched the retained input
exactly before the driver launch. Raw bytes are saved before validation.

The constant-K body retains 12 native HMMA instructions and has no backward
branch spanning HMMA, matching its unrolled ordinary structure. Runtime-K
retains its loop. This closes the observed change from unrolled ordinary math
to a retained instrumented loop in the earlier approach. It does not establish
identical instruction scheduling, source-operation cost, or physical overlap.

The final instrumented function sizes are 1736/2168 instructions for runtime/
constant. They include much richer full-actor address data than earlier sparse
experiments. These counts are not overhead or speedup measurements. Exclusive
NVIDIA performance/overhead experiments remain deferred.

## Dynamic byte-model checks

The analyzer reads original allocation binaries, not cached decoded events or
success fields. It validates all participating actors, original absolute
addresses and widths, actor-local commit ordinals, native wait limits, CTA
publication cuts, byte producers, consumers and retirement before reuse.

The runtime-K case mixes a synchronous shared producer with an asynchronous
copy producer. Treating every shared consumer as a cp.async consumer would lose
one side. Both producer families and actual shared-load widths are retained.

Four retained-byte analyses passed: full/compact sampling, each in normal and
optimized Python. The tests preserve original file hashes and reject missing or
mixed actors, invalid waits, missing completion/publication/retirement cuts,
out-of-range copies and oversized valid-source counts. The richer manifest also
rejects an unmodeled ldmatrix geometry. Six actual native CLI negatives reject
used scratch, invalid capacity/actor count, wrong block size, multiple kernels
and an unknown shared-symbol ABI.

This is a conditional byte consistency model. Its results explicitly keep
machine-site binding, clock comparison, time flows, source costs and hardware
busy unqualified. Standard Perfetto/API acceptance is not claimed here.

## Preserved first failures and artifacts

The first math harness hit the parent's PTX IRSource module bug before executing
math; the corrected harness used the actual selected ptxas with recorded argv,
process identity and tool hash. The first full-actor range check failed on the
wrong base-zero assumption. One early failed prototype lacked its raw snapshot;
the subsequent reproduction retained original allocation bytes before checking.
No failed output was overwritten or counted as first-pass qualification.

Original archive:
`artifacts/timeline/run-034/preflight/late-recording-evidence-v1.tgz`.
It contains source inputs, native receipts/final executable, actual compiled
artifacts, raw snapshots, math results, normal/optimized byte checks, negative
results and failure history. Verification binds four final source files to the
actual native/analysis inputs and all 160 recorded process identities were
inactive at collection. Formatting ran separately in the Enflame Docker with
fixed-point/AST checks; it did not run Enflame device math.

Next work is the actual default compile/launch/owner/decoder/Perfetto chain,
including target timer and final instruction association. The experimental CLI
and byte model must not replace those requirements.
