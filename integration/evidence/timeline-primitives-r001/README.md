# Timeline primitive checkpoint — T005

This is **partial engineering evidence**, not completion of P01, automatic timeline profiling, dynamic dependencies, Perfetto or the goal.

- NVIDIA: 13 explicit real clock/math probe calls, two ordinary GEMM variants, 24 held-out clock inequalities; root checked 18 compiler artifacts. Actual PTX contains `cp.async`, commit and partial wait. No cross-SM epoch/resolution or new automatic profiler claim.
- Enflame: one ordinary and six advanced automatic interval recurrence calls; root verified 228 bundle payloads and all 48 raw interval records against the actual public 64-byte ABI. Independent scale bounds are approximately 0.9774195–1.0222012 ns/tick, not an exact frequency certificate or shared epoch.
- Native source `55119f1e70c23963b215a4231ea831303a7ddc27`: actual new compiler TUs, linkage and integrated wheel build. The first attempt failed because the new parent layout omitted its canonical component link; the unchanged-source resume recorded the added link and preserved all failures. Fresh wheel SHA is in the receipts.
- Independent NVIDIA venv: 597 installed wheel members byte-checked; actual ordinary GEMM TTGIR transformed through the new native scope pass. Normal and optimized Python each passed timer metadata, legacy-mode preservation and four rejection cases. Initial smoke used the wrong pass-manager call signature; its failure was retained, only the test was corrected, and neither wheel nor installation was changed for the second check.
- New `timeline_clock.py`: source-level server-Docker CPU tests passed 27 checks under each of normal Python and `-O`. This arithmetic does not certify a physical timer; backend evidence and context remain mandatory.
- Ascend: connection/device/SDK checked; no new NPU workload or timeline acceptance yet.

Raw archives stay under workspace `artifacts/timeline/run-001/preflight/` and corresponding existing server Docker directories. SDK-private source excerpts are excluded from Git. The retained index gives archive hashes; the small public receipts here do not replace original bytes or final independent qualification. No paper/old Study change or NVIDIA performance/overhead certification was performed.

Next: automatic timeline collection with invocation-owned deferred buffers, backend source/clock/async mappings, common normalized events and genuine Perfetto; complete all three backends and the full frozen acceptance contract before final independent code review.
