# Paired actual-operator counter check

Quantity: output/body interval fraction for the same recording thread in the
same physical invocation. This auxiliary check does not replace the common
request or certify exact internal nanosecond precision.

At each original body/output endpoint, one side-effecting inline PTX bundle
reads `clock64`, `globaltimer`, then `clock64`. Sixteen 64-bit slots retain
four globaltimer timestamps, program/valid fields and eight cycle readings.
Both real operators use the canonical inputs. CPU output checks pass before
and after 15 native-profiled launches: 960 fused program records and 480
softmax records. Emitted PTX and SASS preserve four endpoint bundles and
thread 0 publication, including SASS's final predicated-exit store.

The cycle interval is bracketed by `end_before - start_after` and
`end_after - start_before`. Output/body fractions can be compared without
converting cycles into time **conditional on constant SM frequency during
that program's body interval**. That condition is not established by sampled
NVML clocks. No globaltimer-derived cycle calibration is used. The register
sources differ; distinct physical oscillators are not proved.

Raw fractions fall outside narrow cycle brackets for 715/960 fused and
464/480 softmax records. Permitting a 32 ns margin on each global duration,
based on empirical timestamp granularity, leaves 1 fused mismatch and no
softmax mismatch. The mismatch remains in the CSV. The empirical margin is
not a vendor-guaranteed precision bound, and this result must not be described
as zero-error validation. `summary.json` reports exact medians and counts.

Primary PTX documentation defines clock64 as a 64-bit cycle counter and
globaltimer as a nanosecond timer with target-specific behavior:
https://docs.nvidia.com/cuda/parallel-thread-execution/#special-registers-clock64
https://docs.nvidia.com/cuda/parallel-thread-execution/#special-registers-globaltimer
No frequency conversion or hardware clock change was performed.

Reproduce in the recorded source-built FlagTree runtime:

```bash
source /workspace/study/env.sh
python experiments/study/cuda_dual_clock_operator.py --backend cuda --operator gemm_bias_gelu --shape 128x128x128 --input-dir INPUTS --output RAW/fused-v2 --samples 15
python experiments/study/cuda_dual_clock_operator.py --backend cuda --operator softmax --shape 32x256 --input-dir INPUTS --output RAW/softmax --samples 15
python experiments/study/cuda_dual_clock_analyze.py --raw RAW --output RESULTS
```

Initial existing-container CUDA initialization failed despite working host
NVML. A private image snapshot/new container restored CUDA access; the first
new container exited because it inherited a `/bin/bash` entrypoint and was
passed `sleep infinity` without `-c`. Both failures are retained. Successful
container: `flagprism-study-dual-clock-v2-20261013`; same bind-mounted source
and canonical inputs, GPU UUID in `provenance.json`. Existing containers,
Docker daemon, driver and GPU clocks were not changed. NGC Torch lacks V100
native kernels, so reference math runs on CPU and actual kernels are custom
Triton. Host GPU index 0 has device minor 3: that is the correct mapping and
is not evidence of a stale mapping.

Raw logs/compiled cubins/archive/source are retained in workspace
`artifacts/study-closure-20261013/cuda-dual-clock/`; compact captures preserve
per-program data, native timeline, PTX and SASS for offline review. The archive
hash is in `provenance.json`.

## Fixed-frequency follow-up

A read-only preflight considered selectedGPU0 constant1245MHz locking. The
public NVML header and nvidia-smi query exposed set/reset operations, but no
getter that recovers a prior locked min/maxrange. Idle135MHz and default
application1245MHz therefore do not prove the absence of a prior range lock.
No clock mutation was made because the exact prior policy could not be
restored. `clock_policy_preflight.json` records this unresolved precision path.
The captured source snapshot is `captures/source.py`; the current runnable
script restricts its backend to CUDA only (historical captureSHA is preserved).
