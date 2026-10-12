# Hardware observations, 2026-10-12

`summary.json` records coverage and interpretation limits. `cases.csv` records
correctness and software versions. `kernel_intervals.csv` contains native
kernel/task durations (microseconds), three prewarmed launches per case.
`baseline_samples.csv` separately records host and stream-event intervals.
All saved compiler artifacts were checked against their per-case SHA-256.

Configurations: GEMM stages 1/2; row grouping 1/2; transpose M tile 16/32.
GEMM shapes: 128³, 512³, 257×193×320. Row shapes: 32×256, 256×1024,
127×769. Transpose shapes: 256², 1024², 513×257. GEMM input FP16, FP32
accumulation/output; other probes FP32. Seed 1729, CPU PyTorch references.

`evidence/` holds actual emitted IR and diagnostic provenance. Both Ascend
GEMM diagnostic binaries match their corresponding baseline binary hashes.
The fused source becomes AIC and AIV functions with workspace/sync-block
coordination, while its native collector records one MIX_AIC task per launch.
This establishes decomposition/observation-scope differences, not internal
execution overlap or an attribution error.

GEMM stages 1/2: Ascend's emitted IR changes double buffering and event-ID
selection; Enflame's three corresponding final binary pairs are identical.
A configuration name alone does not establish an equivalent intervention.

Complete raw outputs, logs, binaries, profiler exports and archive snapshots
are retained under the project `artifacts/study-20261012/`. The raw-case column
locates these files in that workspace; generated HTML reports are not duplicated
in this compact Git bundle. Profiling capture itself changes execution.
Do not interpret these measurements as peak performance or submission-ready
cross-architecture causal evidence; see `summary.json` for outstanding limits.
