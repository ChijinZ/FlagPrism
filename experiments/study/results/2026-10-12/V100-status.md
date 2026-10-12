# V100 attempt: excluded from the measured dataset

Host alias: `ai_shuimu`; hardware: eight Tesla V100S-PCIE-32GB, driver 535.216.03.
A task-owned container `flagprism-study-v100-20261012` was created from the
already available `nvcr.io/nvidia/pytorch:25.04-py3` image. It mounts only the
experiment workspace at `/workspace/study` and exposes host GPU 0.

The official FlagTree 0.7.0 wheel compiled and executed GEMM 32³, passing the
CPU reference check. This used CPU PyTorch references and CUDA memory services;
the base NGC PyTorch CUDA kernels do not support Volta, as verified by a failed
CUDA `torch.ones` probe. This does not establish general PyTorch GPU support.

The published wheel lacked FlagPrism. A source build used FlagTree PR #1262,
commit `57d348b08455ff9a03902016c0fd6054ab44343e`, plus this FlagPrism checkout.
One runtime build error required enabling C++ exceptions for
`FlagTreeDebuggerRuntime`; the patched source then built successfully.
The subsequent minimal native-profiling case failed during package import:
`AttributeError: module 'triton' has no attribute 'jit'`.
No working FlagPrism/CUPTI measurement was obtained on V100.

At the author's request to skip V100 if it did not run, further debugging and
CUDA measurement were stopped. The container and source/build trees are
retained for later inspection. This attempt is excluded from all numerical
results and graphs. The two-backend dataset remains 144 passing cases and
216 vendor device intervals.

Raw attempt logs are retained locally at
`artifacts/study-20261012/nvidia-setup/v100-attempt-logs.tgz`.
The remote experiment directory is
`/home/chijin/workspace/flagprism-study-20261012`.
