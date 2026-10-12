# Cross-backend study measurements

Six fixed-source Triton workloads: GEMM, GEMM+bias+tanh-approximate GELU,
row softmax, affine layernorm, row reduction, and out-of-place transpose.
These are study probes, not vendor-best kernels or a production benchmark suite.
GEMM inputs are FP16 and accumulate/output in FP32; other kernels use FP32.
GEMM bias is a vector of length N. All references run explicitly on CPU.

Run inside an already configured FlagTree/FlagPrism environment:

```sh
python3 sweep.py --backend enflame --pilot --output /tmp/study-pilot
python3 sweep.py --backend cann --phases baseline --output /tmp/study-baseline
python3 sweep.py --backend cuda --phases baseline --output /tmp/study-cuda
```

Each case runs in a fresh process on device 0, with a 240-second timeout.
The sweep stops on timeout or recognized device faults. It never overwrites
existing case directories. A failed case remains a failed observation; inspect
its log/result before changing the workload or environment.

The full sweep uses three shapes per operator (aligned small/large and a masked
tail case), with two configurations: GEMM requested stages 1/2; row grouping
1/2; transpose tile M 16/32. Requested settings and effective compiler metadata
are separate. A stage knob is not evidence that the pipeline changed: inspect
the saved IR. Source and compiler artifacts are hashed. Capture snapshots must
record the environment used; the runtime can differ from this checkout.

Baseline: five warmup calls, seven samples of twenty launches, host submission
and submission+final synchronization, plus device event intervals if available.
Device events enclose a stream interval; they are neither isolated kernel busy
time nor an internal source-region timer. `null` and error fields retain missing
event support; no substitution of host time for device time.

Native: three prewarmed launches with FlagPrism's vendor collector and host
fallback disabled. CANN explicitly selects the legacy native hook because its
normal `hook=triton` defaults to IR instrumentation. Internal: CANN explicitly
disables the native CANN collector and uses IR instrumentation. The Enflame
internal timing hook is not assumed supported. Profiled correctness is checked
again. The current runtime may expose collection degradation in its artifacts;
a successful Python call alone is not proof of valid device observations.

Read `result.json`, `asm/*`, profiler raw exports, and the stdout log together.
Baseline and instrumented timings are different executions and cannot be
joined as one run. SYS_CNT cycles are not converted to ns without a validated
clock mapping. Different IR stages do not form a common operation-count metric.
Compile output describes lowering; observed device execution needs dynamic
records, not a guess from static instruction names.

Pilot outputs captured before the explicit CANN hook selection was introduced
are retained as pilot evidence only; CANN's `native` filename in that first
pilot requests the normal hook, which actually defaults to IR instrumentation.
Use collector metadata to interpret it, not the filename.

The initial hardware event calibration showed that tiny kernels are often host-launch limited. Use vendor kernel/task intervals for device-duration comparisons; stream event intervals remain a separate metric. Native profiling currently records three prewarmed launches per case, so min–max spans are descriptive and are not confidence intervals. Fixed clocks and exclusive device use were not enforced.

`lowering` enables compiler diagnostic dumping without calling the profiler. The Ascend GEMM and fused-GEMM diagnostic binaries were checked against their baseline SHA-256, allowing their emitted HIVM IR to describe the same compiled baseline kernels. Static dependencies cannot establish overlap or busy durations.

`summarize.py` extracts raw observations and explicit unknowns; `plot_results.py` creates PDF/PNG/SVG artifacts from those observations. Archive snapshots and every per-case JSON are retained separately. The initial CPU seed is fixed, but exact cross-backend tensor identity was not captured; compiler and CPU-library versions are recorded.


## Completed three-backend round (2026-10-13)

Generate immutable inputs once with `make_inputs.py`; copy the resulting input
folder unchanged to every backend. Run `sweep.py --input-dir INPUTS
--profile-launches 15 --backend BACKEND --output RAW/full`. The new round has
216 passing cases and byte-identical tensor hashes for all 72 matched groups.
The earlier three-launch/seed-only descriptions above apply to the initial round.

`timing_probe.py` tests region brackets, not engine busy time. For nested tests,
use `--loops 256 --nested --sync 1 --before Q` with Q in 0,32,64,96,128;
repeat with `--capture-region both`, `outer`, and `inner`, each in a new output
folder. Single-region references use the same clock primitive in separate
captures and do not establish independent physical-time accuracy.

`endpoint-v2` is the valid single-factor endpoint experiment: input-readiness
barrier always present; `--sync` changes only the end barrier. The preceding
`timing` captures changed both barriers; `endpoint` mistakenly left the end
barrier unconditional. Both are retained as exploratory evidence and excluded
from final endpoint plots. Zero-work controls do not independently separate
barrier overhead from completion effects.

V100: source-build FlagTree PR1262 (57d348b) with the FlagPrism runtime exception
patch committed in this branch. The NGC 25.04 Torch binary does not support
Volta Torch CUDA kernels. These study kernels use Triton with CPU references
and DMA, which was validated; this is not general Torch-on-V100 compatibility.
Disable `TORCH_DEVICE_BACKEND_AUTOLOAD` and ensure the source Triton path takes
precedence over stale installed namespaces. See the bundle environment records.

TCU: four controlled GCU captures use GEMM/fused GEMM, shape128³, BK32,
output tile16²/64². `--unique-output` permits application replay without
overwriting outputs. Export individual records from the saved TCD with
`tcu --import counters.tcd --print-gcu-trace --export-csv invocations.csv`.
`tcu_invocations.py` retains device/ID/per-SIP detail; these IDs are local to
TCU captures and must not be joined to TOPSPTI by kernel name.

Freeze and audit with `freeze_results.py` and `analyze_deep.py`;
`plot_results.py --breadth-only` and `plot_deep.py` draw measured figures.
`ascend_unit_probe.py` is an unsuccessful experimental late-HIVM injection,
not a working profiling mechanism or a data source for the Study. Even the
unmodified final-HIVM roundtrip crashed this compiler configuration. It was
not launched on the device and contributes no numeric measurements.
