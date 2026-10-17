# Compiler timestamp dependencies and memory motion (T016 / r009)

Status: **implemented LLVM constraints with real development regressions; not final machine-boundary/clock/P01/Perfetto qualification**. No paper or Study changed. The implementation is generic compiler lowering, not an operator/shape/site repair list.

## Implementation

Automatic source scopes retain their actual observed operation. Timeline lowering now connects `begin counter → bit-preserving operand anchors → observed operation → end counter`. Register-like scalar/tensor values retain their exact storage bits, including pointers, narrow float formats and 64-bit values. Tokens and memory descriptors are not reinterpreted as ordinary register values. The backend implements clock-input and value-anchor primitives; the shared conversion handles type/packing. NVIDIA opaque asm inputs constrain LLVM SSA motion. Timeline getter asm also carries `~{memory}` for memory operations such as stores that have no SSA result. No GPU completion barrier was added by the clobber.

These are **LLVM constraints**. PTXAS may independently schedule code, so the plan explicitly says `llvm_ssa_pending_machine_audit`, and canonical `boundary_status` remains `unverified`. Neither the version flag, asm comments nor a memory clobber certifies a source region's final boundary, hardware completion or engine busy.

Native `TIMELINE_BOUNDARY_VERSION=1` and module version are exposed and checked. The public hook rejects an old compiler before activation; the boundary implementation participates in cache identity. Legacy count/interval paths do not acquire the new operand forwarding. Actual runtime documentation: [timeline_runtime.md](../../../Profiler/docs/timeline_runtime.md).

## First failure and corrections

The initial `bc460c8` native build and independent install passed existing contracts and the new positive dependency/legacy checks. The new version-negative test then found that plan extraction accepted boundary version 99. The original failure is retained. `4280bab` added explicit rejection in both plan extraction and lowering, plus pre-activation old-plugin rejection. Normal and optimized Python both reject unknown and string-valued boundary versions.

After the first device pass, inspection of actual LLVM identified a remaining omission: value dependencies alone did not cover memory motion for result-free stores. `a9ea010` adds the getter memory clobber. A fresh native build, fresh independent install and fresh device runs validate that version; prior device results are not substituted. The five-type test now checks **actual generated getter LLVM lines** for `asm sideeffect` and `~{memory}`.

## Actual execution and results

Server alias `zhangquan_pro6000`, existing Docker `chijin-study-pro6000`, GPU0 RTX PRO 6000 SM120. Final native/source freeze `a9ea010`; installed product `/workspace/chijin-timeline-r009/runs/install-v3/output/venv`. Its wheel is 390909021 bytes, SHA `3b2e045f0994abcd60f2cccc1dc64f3b9177b621ee5d2408b3c1471d192d9c1a`. Parent launcher stays admission ABI 2. Native builds genuinely compiled changed C++/TableGen and linked libtriton; they are not Python overlays on an old native. Exact builds and source bridges are indexed here.

| Check | Actual result |
| --- | --- |
| Real ordinary TTGIR, compiler contract normal / `-O` | 34 value anchors, 17 counter dependency lists; unknown/string boundary version rejected by both plan and lower; legacy intervals unchanged |
| Common raw / owner / storage contracts, normal / `-O` | 15 / 16 / 7 tests pass |
| Public rejection/finalization, normal / `-O` | 3 tests pass, including old boundary plugin early rejection |
| Legacy automatic hook | 3 tests pass |
| Five ordinary storage types | FP16, BF16, FP32, FP64, int64; exact CPU math, input, tail, three-program side effects `[1,1,1]`, default selected programs 0 and 2; actual LLVM dependencies and memory clobbers pass |
| Existing real public API/CLI development regression | Cold/warm loaded handles, runtime recurrence, masked GEMM, two streams, zero grid, export failure and same-raw recovery, subsequent session, real ring overwrite, separate legacy count all pass |
| Final raw audit | 26 timestamp captures, 11456 retained physical records, 5720 paired intervals, 16 orphan endpoints, 400 logical commit groups; 12352 overwritten records explicitly reported |
| Final compiled objects | All seven new cubins produce actual source/PTX-line SASS, JSON and full CFG with pinned nvdisasm 13.2.86; no `--no-dataflow` fallback |

Five-type kernels are development regression inputs, **not the independent six-new-math qualification**. Their source is [p01_nvidia_boundary_math.py](../../../tests/timeline/p01_nvidia_boundary_math.py); the installed compiler contract is [nvidia_boundary_binding_smoke.py](../../../tests/timeline/nvidia_boundary_binding_smoke.py). Kernels contain ordinary math and no profiler annotations. Each requested math call increments a legal program-local side effect exactly once. The existing public suite separately verifies host-once and recovery without application replay.

The final ordinary recurrence has 392 static instructions / 16 globaltimer reads; GEMM 920 / 44; each type case 344 / 16. All seven have zero MEMBAR instructions. Static counts are not runtime work, dependency closure, source-cost attribution or a complete perturbation analysis. Final objects and source lines must still be audited per declared region/participant. No claim is made that every unselected machine-level timer read is eliminated.

## Originals and byte audit

- Docker originals: `/workspace/chijin-timeline-r009/{native-bc460c8,native-4280bab,native-a9ea010}` and `runs/{install-v1,install-v2,install-v3,type-math-v1,type-math-v2,device-public-v1,device-public-v2,ssa-object-inspection-v1,ssa-object-inspection-v2}`. Final device jobs use the v3 independent install. Compiler/launcher/source/raw/decoded/canonical/async snapshots and actual function handles are retained in each bundle.
- Final workstation archive: `artifacts/timeline/run-009/preflight/ssa-boundaries-final-original-evidence.tgz`, 10906722 bytes, SHA `131a217673aff295a41698585434b57cb9f2227cce746cb58b39e3ecd41417e5`. It includes all original failures, inputs, install/test/build logs and actual objects, excluding wheel/venv/cache/SDK binaries. Earlier archives remain immutable. An intermediate export omitted new input/native directories; its missing-entry audit failure was corrected by a new complete export, with no product/data rerun.
- `audit-retained-bytes.py` uses only retained bytes/stdlib: independently rederives physical record sequences/ticks/offsets, canonical pairing/orphans/IDs, raw/source/artifact/bundle hashes and warm handles; checks actual LLVM clobbers, test sources and CPU contract outputs. It never imports product or reexecutes an oracle on the workstation. Device numerical assertions come from the actual executed harness, not this byte audit.
- `owned-terminal-status.json` checks actual PID/startticks/process groups for twelve owned jobs: all terminal, no live owned worker group; controller zombies are left to container PID1. Final GPU state is retained; no other user's process was modified.

The public evidence set is bound by `INDEX.json`. Raw output remains `partial_clock_unverified`; no certified ns view, verified time arrows or `.pftrace` is supplied by this checkpoint. Actual clock scale/error/window, final per-site machine/source boundaries, participants and physical buffer/flag reuse, GCU/Ascend timeline producers, independent math, real Trace Processor/UI and the final three additional code reviews remain required for the full goal.
