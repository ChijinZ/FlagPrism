# Compact timeline storage development checkpoint (T010)

This is a real NVIDIA storage/compiler development result, **not full P01, a public timeline interface, or Perfetto qualification**. NVIDIA RTX PRO 6000 GPU0, existing Docker `chijin-study-pro6000`; device was idle at preflight. No NVIDIA overhead/performance certification was run. No paper or old Study data changed.

Source build: `545bf8a75af369c893ecc7331cb9c157c4151159`. The matching stable-source object directory recompiled changed native TUs (15 Ninja steps), completed in 90.616 seconds. This is not a Python wrapper around the old native. The resulting wheel SHA is `2698327dc5b73fe1b974a53163534e0ede9c28c1066b5c7c0e2aa3c83c0fdcab` (390626917 bytes). A fresh isolated installation byte-checked 601 wheel members. Installed venv: `/workspace/chijin-timeline-r004/runs/install-v1/output/venv`.

Test source deltas are explicitly separate: native binding smoke at `546a488`, device probe at `bee1f81`. Original executed script bytes/SHA are retained; these are test-only changes, not undeclared product source replacements.

## What passed

- `timeline_storage_version=1`: compact slots are distinct from actual program IDs in the header. Fixed selection preserves list order; default selection uses actual runtime first/last program. Selected-program predicates cover logger/finalize and context initialization/save/restore. Legacy no-storage ABI retains full-grid addressing.
- Seven CPU admission test methods passed normally and with `-O`; 11 installed native negative cases per mode passed, including unsupported storage version and empty/duplicate compact selections. This is compiler/contract evidence, not device epoch proof.
- Ten real captures, ten ordinary invocations and ten instrumented invocations. Compile-only discovery does not add a device launch or allocation. Recurrence K=3/7/11 reuses its binary; two GEMMs retain real async group facts; one grid-map binary handles `(1,1,1)`, `(7,1,1)`, `(3,5,1)`, then `(1,1,1)` again. A separate fixed-selection binary uses physical slots `[0,1,2]` for logical programs `[14,0,7]`.
- Actual per-slot stride is 32896 bytes, including alignment. Single-program capture uses 32896 bytes; grid 15 default capture uses 65792 bytes rather than the driver's full-grid request of 493440 bytes. Fixed three-program selection uses 98688 bytes. These are storage sizes, not an overhead claim.
- Original numerical outputs, tail sentinels, inputs and per-program side-effect counts passed; every allocation retained its 256-byte canary. Root independently checked 2528 retained physical records, headers, exact slot/program mapping, all counter/sequence/site/phase/full-64-bit-tick offsets and compiler artifact hashes against raw bytes without importing product code. Runtime-grid captures share the actual compiled binary hash.

## Failure and scope

The first device probe failed before its first ordinary launch because `kernel[grid]` supplies `warmup=False`, conflicting with the test's explicit compile-only parameter. Preserve [first failure](device-v1-failure.log). The test now uses explicit JIT `.run(..., warmup=...)`. v2 passed, then v3 added the reordered three-slot device case; both original outputs remain in the archive. No native rebuild or tolerance relaxation was used for this test-only correction.

The test collector deliberately synchronizes each owned capture. It does **not** implement or qualify production deferred owners, concurrent submissions, graph support or the public timeline CLI/API. Mathematical correctness/canaries do not alone prove every possible writer/partition case; warp-specialized and broader final qualification remain pending. Raw ticks and positive intervals do not certify final machine boundary ordering, physical ns/epoch or cross-observer comparison. Logical cp.async relations still have `time_arrow_verified=False`. No Trace Processor/UI or independent new-math acceptance has passed here; no backend has completed full P01.

## Evidence

[Raw artifact index](raw-artifact-index.json) records every retained member and the archive SHA. Root original archive: `artifacts/timeline/run-004/preflight/compact-original-evidence.tgz`, 1147214 bytes, SHA `4f31ae247eb543f5829b3f67fc8e4b4cc57f3dce51e87b2493d98012e59ed017`. Remote raw/IR/PTX/cubin/plan/decoded/pair/async originals remain under `/workspace/chijin-timeline-r004/runs/device-compact-v3/output`; previous failures and v2 remain separate. Large binaries and proprietary dependencies are not committed.

[Root audit](root-audit.json), [native build](native-build-terminal.json), [source bridge](source-bridge.json), [independent install](install-result.json), [native normal](native-normal.json), [native optimized](native-optimized.json), [device terminal](device-v3-terminal.json), [device result](device-v3-result.json).
