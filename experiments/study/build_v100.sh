#!/usr/bin/env bash
# Run INSIDE the existing CUDA build container. Does not alter Docker/host drivers.
set -euo pipefail
study_flagtree_source_dir=$(realpath "${1:?FlagTree PR1262 source directory}")
study_flagprism_source_dir=$(realpath "${2:?FlagPrism source directory from this branch}")
export TORCH_DEVICE_BACKEND_AUTOLOAD=0
export MAX_JOBS=${MAX_JOBS:-12}
cd "$study_flagtree_source_dir"
# Dependencies must already be installed: see the validated environment record.
env -u PIP_CONSTRAINT -u FLAGTREE_BACKEND \
 TRITON_BUILD_FLAGPRISM=ON FLAGPRISM_BACKEND=nvidia \
 FLAGPRISM_SOURCE_DIR="$study_flagprism_source_dir" \
 TRITON_APPEND_CMAKE_ARGS='-DTRITON_BUILD_UT=OFF' \
 python -m pip install --no-deps --no-build-isolation -e .
# A stale installed namespace can precede pip's editable finder. Use an explicit
# source-priority path in THIS Python environment, not a system driver change.
python - "$study_flagtree_source_dir/python" <<'PY'
import pathlib,sys,sysconfig
source=pathlib.Path(sys.argv[1])
pth=pathlib.Path(sysconfig.get_paths()['purelib'])/'study_flagtree_source.pth'
pth.write_text('import sys; sys.path.insert(0, '+repr(str(source))+')\n')
print('Source precedence installed:',pth)
PY
python - <<'PY'
import torch,triton
from flagtree import profiler
assert hasattr(triton,'jit'),triton.__file__
print('Torch:',torch.__version__,'Triton:',triton.__version__,triton.__file__)
print('Profiler:',profiler.__file__)
print('Use CPU references + DMA + Triton kernels on Volta in NGC25.04; this does not restore Torch CUDA kernels.')
PY
