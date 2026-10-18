# Default NVIDIA late raw timeline (r036)

This checkpoint connects the late LLVM recorder to ordinary
`profiler.start(..., detail="timeline")` and the standard CLI. It is **not full
timeline acceptance**: final-machine counter/source boundaries, counter-unit and
cross-observer clock proofs, late-layout Perfetto, full Ascend/GCU pipelines,
independent qualification and the final three reviewers remain incomplete.

The default hook registers only the post-O3 LLVM-text callback. It binds loaded
metadata, retained ordinary/instrumented LLVM, the actual native executable,
source/compiled artifacts, launch identity, program selection and scratch layout.
It reconstructs the producer manifest with the actual tool/options before
allocation, rejecting a cached manifest that requests a smaller buffer. A warm
session can recover ordinary LLVM from the compiler cache after prior staging
cleanup. Legacy count/native paths and old raw readers remain separate.

Known native async-copy/matrix code retains complete CTA participation for byte
footprints. Other code defaults to four actual threads; no collective coverage
is inferred from those samples. First/last program selection is physical, with
an independent 128-byte allocation guard. Stream-local completion and durable
raw/artifact retention precede device-buffer release. Pending and cumulative
admitted raw budgets are separately bounded at 8MiB. Raw decoding handles
arrived-empty, absent, divergent and overflow outcomes; the collective byte model
has stricter eligibility and never grants hardware busy/source-cost/time-flow
qualification.

The final installed wheel is
`f6bedc677e2615f01234709a05dd38d6cc4ca996eab2ddc8186f6238ae49f306`;
611 installed members were byte-checked. The actual changed standalone native
recorder was rebuilt with LLVM22. Unchanged core ABI3 C++/CMake inputs were
byte-bridged to the real r024 native build, with no core rebuild claim.

Real default API checks cover ten ordinary launches, ten profiled launches,
one Softmax, and two launches in a second warm session: original CPU-double
math, inputs, tail canaries and per-program atomic call counts passed. The first
session has 11 captures, three binary identities, multiple real streams and
725,120 raw bytes; the warm session has two captures. Runtime-K GEMM also passed
ordinary/profile K96/K224 math, two complete 128-actor captures, original guards
and observed byte-dependency/reused-buffer consistency. Groups per sampled
program were 5/9, consumer edges totaled 72/104 and reuse edges 26/42. These are
conditional byte-model facts, not physical timing arrows.

The standard CLI ran the original three recurrences and constant-K GEMM once,
including the legal zero-grid case. It produced exactly four real captures:
three four-thread captures and one full 128-thread GEMM capture. Host-once,
original math/input/tail/side-effect oracles and raw integrity passed.

Installed normal Python and `-O` checks rejected four corrupted actual compiler
metadata cases before allocation. Seven actual-raw-derived CPU fixtures rejected
or withheld dependency interpretation for invalid/missing waits, missing
publication barriers, divergent participation, opaque effects, partial coverage
and unknown ldmatrix geometry. Fixtures were not submitted to a GPU or exported
as measured traces. Earlier shared owner/storage/public contracts passed 38
tests and 32 subtests in normal Python and `-O`. The initial v2 dependency-model
failure is retained: ordinary global/compute observations were not yet handled;
the generic fix preserves their original sequence positions and does not treat
them as shared-memory writers. Unknown memory effects and non-global atomics
stay opaque.

`verification.json` binds the 18 current changed source/test/document files to
actual final installed inputs. The local archive has 7,251 members, 44,762,378
bytes, SHA256
`2262871440873535e387b47ebebf18b4e375814372fecf94f23ce22018809542`.
All 7,249 retained file hashes were audited. Forty-four distinct recorded NVIDIA
process identities were inactive at collection. Per-session compiler attempt
logs/identity receipts still need durable final-bundle retention: they currently
live in temporary staging, although original/instrumented LLVM and bindings are
retained. This gap remains explicit for the next implementation step.

No paper/Study changes, new backend device runs, exclusive performance claims,
Perfetto qualification or final independent code reviews occurred here.
