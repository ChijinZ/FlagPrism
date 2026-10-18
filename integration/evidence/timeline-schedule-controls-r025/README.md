# NVIDIA scheduling controls r025

This checkpoint investigates whether observation changes the ordinary kernel's
pipeline. It changes **no product implementation or acceptance requirement**.
All actual compilations ran in existing Docker `chijin-study-pro6000` using
the r024 installed-v2 Python/native wheel, on PRO 6000 sm_120. There were zero
user-math launches; the output canary remained unchanged. These are development
controls, not independent mathematical qualification or performance results.

Product input: `8fc1058408a9403a1e3acb6c842801329090affc`, clean worktree.
Installed wheel/native/source bridges remain those in
[r024](../timeline-shared-views-r024/README.md). The frozen ordinary GEMM is
48×192 times 192×56, blocks 32³, four warps and three stages.

## Findings that change the implementation decision

1. The production ordinary LLVM IR and PTX retain a loop with four matrix
   instructions; the final ordinary SASS has 24. Thus the separate LLVM `opt`
   diagnostic in r023 is not sufficient to explain the production decision.
   Moving logging after LLVM O3 alone is not an established fix for PTXAS
   scheduling or unrolling.
2. Default observation and a sparse selection both retain the loop and put
   its four matrix instructions before the two future-copy instructions.
   Ordinary SASS interleaves future copies with matrix instructions. Reducing
   the logical-region budget does not remove required async sites; sparse is
   not a one-site capture (15 selected scopes versus default 22).
3. An **unqualified diagnostic** removes boundary/marker attributes and uses
   the retained v2 inline timer path. This eliminates helper calls but neither
   restores the ordinary expansion nor its instruction interleaving. It is not
   a valid replacement for the public boundary implementation.
4. A fixed six-fold MLIR expansion, applied before automatic site selection,
   restores 24 static matrix instructions but does not restore the original
   interleaving. The factor comes from this frozen control's six iterations;
   it is deliberately **not a product policy or a per-kernel workaround**.
5. Deferring the inline control's shared log stores to the end of their own
   LLVM basic blocks does not restore interleaving. It adds 35 and 78 static
   local spill-store instructions in sparse/default controls. This transform
   has not been merged into the product.
6. Removing log stores altogether also eliminates the unused timer reads in
   final SASS. Although this changes interleaving, it is **not a storage-only
   causal experiment**, nor a functioning profiler.

| Actual compiled control | Static HMMA instructions | Future copies interleaved with the first four HMMA | Static local spill stores |
| --- | ---: | --- | ---: |
| Ordinary | 24, unrolled by final compilation | Yes | 0 |
| Current default | 4, loop retained | No | 0 |
| Sparse inline diagnostic | 4, loop retained | No | 0 |
| Explicitly expanded sparse inline diagnostic | 24 | No | 0 |
| Expanded sparse inline with deferred log stores | 24 | No | 35 |
| Expanded default inline with deferred log stores | 24 | No | 78 |

CS2R opcode totals include zero-register operations and must not be presented
as timestamp-read counts. Only actual getter operands identify timer reads.

## What the pipeline evidence does and does not show

The compiled observed loop still contains `DEPBAR.LE SB0,0x2`, followed by
the current shared loads / matrix computation, two future copy commits and
the next iteration. Its epilogue uses `DEPBAR.LE SB0,0x0`. Expanding this
frozen six-iteration control's critical sequence gives the same counts of
16 copy/commit attempts, 24 matrix instructions, six wait-2 instructions and
one final wait-0 as ordinary. There is no inserted wait-0 in the loop.

This matters: **loss of fine instruction interleaving does not, by itself,
prove that all cross-iteration asynchronous pipelining has disappeared**.
The observed ordering still admits committed groups whose completion is not
established by the preceding wait while matrix computation is issued.

The audit's queue projection describes only recorded commit attempts and
wait guarantees along this frozen control's projected critical path. Groups
not covered by a wait may already have completed; copies may be predicated
empty. This is not measured hardware overlap, a full CFG/participation proof,
safe physical-buffer reuse, or a qualified source interval. The actual runtime
shared-view evidence from r024 remains separately scoped. No performance
benefit or unchanged throughput is claimed.

The next implementation step is to bind actual source wait/submit regions,
their paths and buffer associations to the final object and retained records.
Compare preserved critical dependencies and observation-induced dependencies,
rather than requiring identical instruction order or granting qualification
from equal instruction counts. Do not merge blind forced unrolling, inline
timers without endpoint constraints, or deferred logging with unmeasured costs.

## Originals and audit

Workspace archive:
`artifacts/timeline/run-025/preflight/schedule-evidence-v1.tgz`

* 743,175 bytes, 164 regular members.
* SHA256 `bb3d18c7380fff3cf6a689823721d19b69f9592ecd151a67596a48747c0c3b9d`.
* Includes compile scripts, original workload, TTGIR/LLVM/PTX/CUBIN, actual
  nvdisasm JSON, selection plans, transformed inputs, canary results and
  terminal/process audits. No device-math execution or synthetic timestamps.
* First expansion harness failed because `pass_manager.run` requires a stage
  string. Its terminal/logs remain; corrected v2 uses a fresh source/run path.
* Inline-v1's selection plan is pre-transform record-v3 metadata; it must not
  be mistaken for the effective record-v2 physical plan. The first inline
  diagnostic overwrites its common transformed-input file between variants.
  Later expansion/deferred diagnostics retain per-variant effective inputs.
* All 12 recorded controller/worker identities were terminal, missing, zombie
  or replaced identities; no owned active diagnostic jobs remained. GPU query
  at collection: 15 MiB, 0% utilization. Other users' jobs were not modified.

[audit_evidence.py](audit_evidence.py) checks every inventoried member, each
CUBIN hash, all terminal outcomes and the finite critical-sequence projection;
[audit.json](audit.json) retains detailed outcomes and explicit limits. The
auditor uses only the Python standard library and never imports the product:

```bash
python integration/evidence/timeline-schedule-controls-r025/audit_evidence.py \
  --archive ../artifacts/timeline/run-025/preflight/schedule-evidence-v1.tgz \
  --output /tmp/timeline-r025-audit.json
```

This checkpoint adds no P01, clock precision, source-boundary, cross-observer,
three-backend or final code-review qualification. No paper/Study files changed.
