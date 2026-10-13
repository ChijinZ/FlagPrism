set -eu
mkdir -p /workspace/tmp
export TMPDIR=/workspace/tmp
export PATH=/workspace/venv/bin:$PATH
export TRITON_HOME=/workspace/cache/triton
export TRITON_CACHE_DIR=/workspace/cache/kernels
export TORCH_DEVICE_BACKEND_AUTOLOAD=0
export USE_FLAGCX=OFF
cd /workspace/FlagPrism/experiments/study
mkdir -p /workspace/results/pro6000-smoke
python -m py_compile nvidia_tune.py
python run_case.py --backend cuda --operator gemm --shape 128x128x128 --phase native --profile-launches 15 --output /workspace/results/pro6000-smoke/gemm-native
python run_case.py --backend cuda --operator softmax --shape 32x256 --phase native --profile-launches 15 --output /workspace/results/pro6000-smoke/softmax-native
python nvidia_tune.py --operator softmax --shape 32x256 --quick --output /workspace/results/pro6000-smoke/softmax-tune-quick

python - <<'PYCODE'
import json
from pathlib import Path
for op in ['gemm','softmax']:
    path=Path('/workspace/results/pro6000-smoke')/(op+'-native')/'profile.timeline.json'
    events=[e for e in json.loads(path.read_text())['traceEvents'] if e.get('ph')=='X' and 'cupti_activity' in e.get('cat','') and e.get('dur',0)>0]
    assert len(events)==15,(op,len(events))
    print('NATIVE_KERNEL_INTERVALS',op,len(events),[e['dur'] for e in events])
PYCODE
