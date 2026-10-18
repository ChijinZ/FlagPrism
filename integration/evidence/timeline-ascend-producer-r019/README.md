# r019: real Ascend paired timestamp producer

This is a **development producer checkpoint**, not P01, a public Ascend timeline
collector, or final three-backend acceptance. No paper/Study change or final code
review is claimed. Only the existing `chijin_v3.5.x` Docker on Ascend NPU4 was used.

## Implementation

- The native v3 source marker transports real source IDs and six program/grid
  coordinates. It is reused as a carrier; its census count layout is not reused.
- The new standalone LLVM15 plugin writes `ascend_source_timeline_v1`: compact
  first/last logical programs, isolated 64-byte actor headers and paired records,
  real SYS_CNT reads, bounded loss and saturating counters. Empty lowered
  fragments are explicit skips. Source-operation boundaries remain unverified.
- Frontend/compiler metadata distinguishes the carrier ABI from runtime storage.
  The historical debugger allocator rejects the new layout before initialization.
  Public default Ascend collection remains unfinished, rather than using that
  incompatible allocator. The development test's generic collector explicitly
  synchronizes and is not deferred-owner/concurrency evidence.
- Packaging retains hashes of both late-observer headers as well as its TU.
  Stable v3 core/native ABI is reused; the new LLVM plugin is actually rebuilt.
  There is no claim that the entire current core/native source tree was rebuilt.

See [raw protocol](../../../Profiler/docs/timeline_events.md#ascend-paired-producer-development-checkpoint)
and [current public limitations](../../../Profiler/docs/timeline_runtime.md).

## Evidence

| Check | Actual result |
| --- | --- |
| LLVM writer construction/verification and explicit host-JIT fixture | 36 selection/actor/pair/overflow/saturation cases; fixture substitutes the timer only on the host |
| Actual LLVM15 plugin build/transform | AIC/AIV positive transformations; legacy census transformation; wrong columns/semantics rejected |
| Independent wheel installation | 397 wheel members byte-checked; 97 reused native/header/helper members compared with the old wheel; new plugin separately built |
| Installed CPU protocols | 22 normal and 22 `-O`; explicit invalid-version/layout/capacity rejection, and legacy-allocator rejection before allocation |
| Actual ordinary runtime-K math | Two baseline calls and two profiled calls, K=3/7; each mode retains one binary across K; math/input/side effects/tails/allocation guard checks passed |
| Raw records | Program 0/4, actual AIV actor 1: 8/12 pairs per actor for K=3/7; loop site repeats 3/7; 40 pairs, 22 positive durations, no invented width |
| Old public census development regression | Vector-loop math and 1,024 once-only side effects passed; not the full old qualification matrix |
| Own process audit | All 18 recorded controller/worker identities missing, zombie, or replaced; all have terminal receipts |

[Actual device result](actual-device-result.json), [independent byte audit](audit.json),
[LLVM results](llvm-plugin-results.json), [installed wheel](installed-wheel.json),
[source/native byte bridge](source-native-binding.json), [final checks](final-checks-result.json)
and [terminal receipt](final-checks-terminal.json) retain the concrete scope.

The final installed Python is
`/tmp/chijin-timeline-r019/runs/package-v3/output/venv/bin/python`.
Wheel SHA256: `3d355c0339aee70830f7c2d6c9c541c53c2adc5eb08cb01313138b4089e0a78c`.
Actual new plugin SHA256:
`4e641e6ae68d092f6da549a6c5b3e35fde32e27a088bff8db33ca4d0839ebb5f`.

Full immutable original archive:
`artifacts/timeline/run-019/preflight/ascend-final-evidence.tgz`, 291,986 bytes,
135 files, SHA256 `91ce6815c127c9d1fb77a625a47c9e658e18ff3d07e3457b56bd3b8cf4b2a829`.
It contains actual raw/metadata, compiler artifacts and successful/failed receipts.
The stdlib-only [audit](audit_originals.py) can recheck retained bytes without
importing the product or replaying an application:

```bash
python integration/evidence/timeline-ascend-producer-r019/audit_originals.py \
  /path/to/ascend-final-evidence.tgz --output /tmp/ascend-byte-audit.json
```

## Failures retained and limits

The first wheel controller failed because the isolated parent lacked real Git
metadata; the next snapshot used its actual local parent Git base. Two CPU runs
then correctly rejected incomplete positive fixtures: first missing source IR,
then missing driver source. Fixtures were completed; production checks were not
weakened. The final checks reuse the unchanged installed v3 wheel. Its installation
controller's earlier failing test receipt is retained, not overwritten as green.

Raw times remain ticks. Unit/precision, source boundaries, cross-observer epoch,
async association, the broader exclusive-writer conditions, public default owner,
canonical/offline adapter and Perfetto are unfinished for Ascend. Empty actor
slots do not prove execution. No throughput/overhead/optimization benefit is
claimed. Pinned formatting checks remain pending for this checkpoint.

The complete objective, independent math, full regression and three fresh final
code reviewers remain required. Development success does not reduce those gates.

Git log snapshots use JSON text envelopes so the exact pytest whitespace is
preserved without introducing source-tree whitespace errors. Their byte lengths
and SHA256 hashes refer to the decoded text; plain originals remain in the
immutable archive. This is an evidence representation change, not a new test.
