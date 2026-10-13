set -eu
mkdir -p /workspace/tmp
export TMPDIR=/workspace/tmp
export PATH=/workspace/venv/bin:$PATH
while test ! -f /workspace/download-torch-resume.exit; do sleep 5; done
if test "$(cat /workspace/download-torch-resume.exit)" != 0; then exit 126; fi
python -m pip install --no-index --no-deps /workspace/wheels/*.whl
python -m pip install --find-links /workspace/wheels /workspace/downloads/torch-2.8.0+cu128-cp310-cp310-manylinux_2_28_x86_64.whl
python -m pip install 'cmake>=3.20,<=4.0.3' ninja 'pybind11>=2.13.1' pybind11-stubgen numpy psutil scipy
sh /workspace/build-flagtree.sh > /workspace/build-flagtree.log 2>&1
printf '0\n' > /workspace/build-flagtree.exit
sh /workspace/smoke.sh > /workspace/smoke.log 2>&1
printf '0\n' > /workspace/smoke.exit
sh /workspace/tune-sweep.sh > /workspace/tune-sweep.log 2>&1
printf '0\n' > /workspace/tune-sweep.exit
