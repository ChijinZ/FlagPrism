set -eu
study_url=https://oaitriton.blob.core.windows.net/public/llvm-builds/llvm-f6ded0be-ubuntu-x64.tar.gz
mkdir -p /workspace/downloads /workspace/cache/triton/.triton/llvm
python3 /workspace/download-llvm.py
tar -xzf /workspace/downloads/llvm-f6ded0be.tar.gz -C /workspace/cache/triton/.triton/llvm
printf '%s' "$study_url" > /workspace/cache/triton/.triton/llvm/llvm-f6ded0be-ubuntu-x64/version.txt
sha256sum /workspace/downloads/llvm-f6ded0be.tar.gz
/workspace/cache/triton/.triton/llvm/llvm-f6ded0be-ubuntu-x64/bin/llvm-config --version
