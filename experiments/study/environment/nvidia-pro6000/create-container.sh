set -eu
study_root=/storage/Ext_01/chijin-study-pro6000
mkdir -p "$study_root"/workspace
if ! docker container inspect chijin-study-pro6000 >/dev/null 2>&1; then
  docker run -d --name chijin-study-pro6000 --gpus all --network host --shm-size=8g -v "$study_root/workspace:/workspace" -e PIP_CACHE_DIR=/workspace/cache/pip -e XDG_CACHE_HOME=/workspace/cache -w /workspace ubuntu:22.04 sleep infinity
fi
docker inspect chijin-study-pro6000 --format '{{.Id}} {{.Image}} {{json .Mounts}}'
docker exec chijin-study-pro6000 nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv
