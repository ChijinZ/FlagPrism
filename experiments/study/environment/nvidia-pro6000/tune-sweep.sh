set -eu
mkdir -p /workspace/tmp
export TMPDIR=/workspace/tmp
export PATH=/workspace/venv/bin:$PATH
export TRITON_HOME=/workspace/cache/triton
export TRITON_CACHE_DIR=/workspace/cache/kernels
export TORCH_DEVICE_BACKEND_AUTOLOAD=0
export USE_FLAGCX=OFF
cd /workspace/FlagPrism/experiments/study
python nvidia_tune_sweep.py --output /workspace/results/pro6000-n-search --input-dir /workspace/chijin-study-canonical-inputs-r007
