set -eu
mkdir -p /workspace/tmp
export TMPDIR=/workspace/tmp
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3 python3-venv python3-dev build-essential git curl ca-certificates pkg-config libnuma-dev zlib1g-dev libxml2-dev libffi-dev
python3 -m venv /workspace/venv
/workspace/venv/bin/python -m pip install --upgrade pip setuptools wheel
/workspace/venv/bin/python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
/workspace/venv/bin/python -m pip install 'cmake>=3.20,<=4.0.3' ninja 'pybind11>=2.13.1' pybind11-stubgen numpy psutil scipy
printf 'INSTALL_ENV_DONE\n'
