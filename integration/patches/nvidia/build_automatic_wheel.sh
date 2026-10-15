#!/usr/bin/env bash
# Full native build through FlagTree's official setuptools/CMake integration.
# Apply the two pinned NVIDIA integration patches before invoking this script.
set -eu
if [ "$#" -ne 4 ]; then
    echo 'Usage: build_automatic_wheel.sh FLAGTREE_SOURCE FLAGPRISM_SOURCE BUILD_DIR WHEEL_DIR' >&2
    exit 2
fi
: "${LLVM_SYSPATH:?Set LLVM_SYSPATH to the matching FlagTree LLVM distribution}"
: "${JSON_SYSPATH:?Set JSON_SYSPATH to the matching JSON dependency directory}"
flagtree_source=$(realpath "$1")
component_source=$(realpath "$2")
mkdir -p "$3" "$4"
build_output=$(realpath "$3")
wheel_output=$(realpath "$4")
test -f "$flagtree_source/setup.py"
test -f "$component_source/python/flagprism_build.py"
export TRITON_BUILD_DIR="$build_output"
export FLAGPRISM_SOURCE_DIR="$component_source"
export TRITON_BUILD_FLAGPRISM=ON FLAGPRISM_BACKEND=nvidia TRITON_BUILD_PROTON=OFF
export CUPTI_INCLUDE_PATH="$flagtree_source/third_party/nvidia/backend/include"
export ROCTRACER_INCLUDE_PATH="$flagtree_source/third_party/amd/backend/include"
export USE_FLAGCX=OFF TORCH_DEVICE_BACKEND_AUTOLOAD=0
export MAX_JOBS="${MAX_JOBS:-12}"
export TRITON_APPEND_CMAKE_ARGS='-DUSE_FLAGCX=OFF -DTRITON_BUILD_UT=OFF -DTRITON_BUILD_TESTS=OFF'
cd "$flagtree_source"
python setup.py bdist_wheel --dist-dir "$wheel_output"
