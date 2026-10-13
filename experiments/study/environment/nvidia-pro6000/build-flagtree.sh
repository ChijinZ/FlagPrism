set -eu
mkdir -p /workspace/tmp
export TMPDIR=/workspace/tmp
export PATH=/workspace/venv/bin:$PATH
export TRITON_HOME=/workspace/cache/triton
export TRITON_CACHE_DIR=/workspace/cache/kernels
export MAX_JOBS=12
# Single-device kernels do not use TLE distributed collectives.
export USE_FLAGCX=OFF
export TORCH_DEVICE_BACKEND_AUTOLOAD=0
export TRITON_BUILD_FLAGPRISM=ON
export FLAGPRISM_BACKEND=nvidia
export FLAGPRISM_SOURCE_DIR=/workspace/FlagPrism
export TRITON_APPEND_CMAKE_ARGS=-DTRITON_BUILD_UT=OFF
while test ! -f /workspace/prefetch-llvm.exit; do sleep 5; done
test "$(cat /workspace/prefetch-llvm.exit)" = 0
ln -sfn /workspace/FlagPrism /workspace/FlagTree-pr1262/third_party/FlagPrism
cd /workspace/FlagTree-pr1262
python -m pip install --no-deps --no-build-isolation -e .
python - <<'PY'
import pathlib,sysconfig
path=pathlib.Path(sysconfig.get_paths()['purelib'])/'study_flagtree_source.pth'
path.write_text("import sys; sys.path.insert(0, '/workspace/FlagTree-pr1262/python')\n")
PY
python - <<'PY'
import torch,triton
from flagtree import profiler
print('torch',torch.__version__,torch.__file__)
print('triton',triton.__version__,triton.__file__)
print('profiler',profiler.__file__)
print('GPU',torch.cuda.get_device_name(),torch.cuda.get_device_capability())
print('cuda_arch_list',torch.cuda.get_arch_list())
print((torch.arange(8,device='cuda')*2).cpu())
PY
printf 'BUILD_DONE\n'
