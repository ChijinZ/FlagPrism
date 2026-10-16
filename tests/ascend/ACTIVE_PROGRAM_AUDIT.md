# Ascend active-program development audit: historical v1 checkpoint

This file preserves the v1 development checkpoint and its original failures.
The current compact v2 wire layout is documented in
`Profiler/docs/source_site_census.md`; this audit is not a current release or
qualification certificate.

The ordinary workloads in `active_program_developer.py` were frozen before
execution. They contain no profiler markers or extra kernel parameters. The
input/oracle freeze and original source hash are retained at
`artifacts/usability/run-010/ascend-active-program/` in the workspace evidence
root. These are developer examples, not qualification holdouts.

Both launch four source programs. A device tensor supplies loop counts
`[0, N, N, N]`, with runtime N=2 and N=5. `row_increment` repeatedly adds 0.25;
`row_energy` repeatedly reduces squared input plus a step-dependent offset.
The CPU closed-form oracle, original input/count values and output canaries
passed for both N values. Each kernel retained one binary hash across N=2/5.

The original system SDK installation and the sealed r9 product venv each passed
all four ordinary baseline invocations. The r9 product installation was reused
read-only at `/tmp/chijin-usability-r8-final-ascend/final/venv`; this does not
establish a new r10 installation. Its public `detail='auto'` invocation also
passed all mathematical checks, but every capture retained only program 0:

| Kernel | N=2 records | N=5 records | Observed programs |
| --- | ---: | ---: | --- |
| row_increment | 6 | 6 | 0 |
| row_energy | 6 | 6 | 0 |

Per-site counts were identical for N=2/5: five operation checkpoints and one
loop-header control checkpoint. The loop header can be reached once for a zero
trip count; this is not one body iteration. The original auto result reported
`complete` with `programs=[0]`, although programs 1–3 actually performed the
runtime loop. The original report, raw capture, math receipts and compiler
artifacts are preserved without changing that result.

`AscendLateObserver.cpp` selected a single compilation-time program, default 0,
for every timer/checkpoint. Its three actor segments have shared per-actor
cursors, so removing the predicate would introduce concurrent writes. A new
census must use independent program/actor/site cells instead.

The experimental census wire layout is `ascend_source_census_v1`: 32 zero
reserved header bytes followed by 3 actor slots × 128 reserved 8-byte cells per
source program. Both budgets count the actual reserved physical allocation.
Each cell is a saturating u32 visit count plus visited/overflow flags. Padding
and unused actor/column cells must remain zero. Multiple typed actor descriptors
reference one raw capture. They retain stable logical observer IDs; compiler
actor proof belongs to `compiler_site.compiler_actor`. Counts have no clock,
start/end time, iteration identity or inferred data-lane activity.

Source program identity needs a real compiler bridge. The original final LLVM
computes the source x coordinate from BLOCK.IDX and grid extents; the observer's
own BLOCK.IDX call cannot replace that relation, particularly under 3D launch
or AutoBlockify. The independent compiler prototype creates all three actual
`tt.get_program_id` and `tt.get_num_programs` values, extends them to i64, and
carries them in a versioned side-effect-only empty LLVM assembly comment. The
late pass requires a unique operand tuple dominating each selected site and
uses source order `x + grid_x * (y + grid_y * z)`. Missing/ambiguous anchors are
errors; there is no fallback to a physical block number.

Actual capability evidence so far:

- A zero-result Triton elementwise-inline-asm probe failed its verifier.
- Its legal single-result variant failed Triton→Linalg conversion.
- A standard LLVM-inline-asm probe in actual compiler input reached CANN, whose
  backend explicitly required i64 inputs; the i32 failure is retained.
- The corrected i64 empty-comment probe compiled to real `.o`/`.so` files and
  retained all six operands in actual final actor LLVM.
- The census pass transformed that retained LLVM, passed LLVM verification,
  emitted counter metadata with null clock, and compiled with the original
  SDK `bisheng` command to a real actor object.

Those capability fixtures explicitly inject compiler IR and do not establish
an automatic frontend or a hardware census. The independent pinned compiler
build, actual AutoBlockify operand transport, 3D/large-grid/caller-loop tests,
same-stream runtime allocation, and public-default census integration remain
pending until their own execution receipts exist. Original ordinary kernels
that already run remain supported work to complete; a new rejection does not
resolve the observation gap.

The current implementation under development now attaches a versioned marker
**before each actual selected TTIR operation**, after inlining and metadata
assignment. Each marker carries its actual source-operation ID, physical census
column, and its own six coordinate operands. The late pass counts at that marker
position and checks operand dominance there. It does not recover source program
identity from `GET.BLOCK.IDX`, an arbitrary function argument ordinal, an entry
anchor, or a nearby lowered loop. Actual SDK clones contribute to the same
source-site/actor count; this is a reached-control count, not operation completion
or hardware busy time.

The independent snapshot has reached actual core linking with the new facade,
AutoBlockify marker transport, and actual program-info argument role attributes.
An initial import caught stale `Passes.o` reuse caused by preserved archive
mtimes. That failure is retained. The subsequent build explicitly refreshes all
copied C++ inputs and records their hashes. A separate `all` target attempt also
failed linking an AMD test utility; required Ascend core/runtime targets are
tracked separately, without relabeling the failed attempt as passed.

The latest isolated Docker transport suite passed 15 tests (including sparse
actual compiler-actor columns, physical reserved-cell budgets and zero-grid
storage). These are CPU fixtures only, using a package-free transport adapter;
they do not qualify an installed product or NPU producer. Actual new-core API
import, compiler-generated site-marker LLVM, 3D/AutoBlockify geometry, source-loop
2/5 hardware counts, and public-default integration are still pending.
