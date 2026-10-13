# Independent frozen-N NVIDIA measurements

All120 captures ran inside existing `chijin-study-pro6000` on PRO6000 after
completion of tuning; no source/config retuning. Same31 canonical files.

`overview-independent-r008/`:36 requested configurations (18 workload shapes,
frozen native-selected winner plus next distinct shortlisted config),3 randomized
measurement batches and30 kernel intervals/capture. Total108 captures /3240
intervals. Its `plan.json` uses the shared three-backend plan schema. All ports,
CPU references, post-profile math, requested configs and input hashes verified.

`case-controls-independent-r008/`:fixed-grid Softmax127x769, ROWS1, warps1/2/4;
plus frozen fused GEMM512x512x4096 with BM/BN/BK32/32/32, warps4, stages4.
Case order randomized separately in each of3 batches,30 consecutive launches
per case. This is12 captures /360 native intervals, independent of tuning.

Softmax medians per batch:

| batch | w1 | w2 | w4 |
|---|---:|---:|---:|
|0|1.248|1.2155|1.152|
|1|1.248|1.216|1.152|
|2|1.248|1.216|1.152|

All times are microseconds from positive native CUPTI kernel intervals.
Frozen w4 is faster than w1 in all3 batches. Long-K N batch medians are
17.648,17.728,17.728us; median17.728us. Native kernels are uninstrumented;
external runtime collection and five-launch warmup follow the shared runner.
These measurements do not certify device peak performance or fixed clocks.

Reproduce inside Docker with `/workspace/venv/bin` on PATH,
`TRITON_HOME=/workspace/cache/triton`, `TRITON_CACHE_DIR=/workspace/cache/kernels`,
`TORCH_DEVICE_BACKEND_AUTOLOAD=0`, `USE_FLAGCX=OFF`:

```
python porting_sweep.py --backend cuda \
  --selection /workspace/results/pro6000-n-search/selection.json \
  --input-dir /workspace/chijin-study-canonical-inputs-r007 \
  --output /workspace/overview-independent-r008 --batches 3 --launches 30
python nvidia_case_controls.py \
  --selection /workspace/results/pro6000-n-search/selection.json \
  --input-dir /workspace/chijin-study-canonical-inputs-r007 \
  --output /workspace/case-controls-independent-r008
```

Use fresh output directories for new observations. Completed overview cases
can be verified/resumed by shared runner; controls refuse overwriting.
Compact JSON traces/results/plans are here; all ASM and logs remain in
`artifacts/study-goal-run/pro6000-independent-r008.tgz` and remote `/workspace`.
`manifest.json` records archive/file hashes and verification coverage.
