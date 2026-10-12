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
