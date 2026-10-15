# NVIDIA automatic profiling build and installation

Use the NVIDIA FlagTree baseline
`57d348b08455ff9a03902016c0fd6054ab44343e`, this FlagPrism component,
Python 3.10, and the matching FlagTree LLVM distribution. The verified device is
RTX PRO 6000 Blackwell (`cuda:120`). Apply these patches in order to a separate
FlagTree checkout; they do not modify the user kernel:

```bash
compiler=/absolute/path/to/FlagTree
component=/absolute/path/to/FlagPrism

git -C "$compiler" apply --check "$component/integration/patches/nvidia/flagtree-source.patch"
git -C "$compiler" apply "$component/integration/patches/nvidia/flagtree-source.patch"
git -C "$compiler" apply --check "$component/integration/patches/nvidia/automatic-scopes.patch"
git -C "$compiler" apply "$component/integration/patches/nvidia/automatic-scopes.patch"
```

The first patch supplies the integrated build and cache identity policy. The
second adds the completed-TTGIR hook for automatic scopes in Triton and Gluon.
The pass and Python bindings are built from this component; replacing only the
Python package cannot supply this feature.

## Build the integrated wheel

Activate a build environment containing the dependencies listed in FlagTree's
`pyproject.toml`, plus `wheel`. Set the matching LLVM and JSON dependency paths.
The following public helper invokes FlagTree's ordinary setuptools/CMake build;
it builds the native compiler and component modules, then packages them together.
Use a fresh build directory for the first build of a source version.

```bash
export LLVM_SYSPATH=/absolute/path/to/llvm-f6ded0be-ubuntu-x64
export JSON_SYSPATH=/absolute/path/to/json
export TRITON_HOME=/absolute/path/to/dependency-cache
export TMPDIR=/absolute/path/to/temporary-directory
export MAX_JOBS=12
bash "$component/integration/patches/nvidia/build_automatic_wheel.sh" \
  "$compiler" "$component" /absolute/path/to/build /absolute/path/to/wheelhouse
```

`TRITON_OFFLINE_BUILD=1` is supported when the required LLVM, JSON and backend
binary dependencies are already present. The helper's CUPTI and ROCtracer
include paths come from the pinned compiler checkout. It does not install or
alter the host driver. Keep dependency caches and build output on a volume with
sufficient space; the verified wheel contains debug information and is about
387 MiB.

## Install into an independent environment

The verified runtime combination is Torch `2.8.0+cu128`, NumPy `2.2.6`, and the
integrated FlagTree wheel, whose Triton namespace reports `3.6.0`. Torch's wheel
metadata requests upstream `triton==3.4.0`; installing that dependency would
replace the required compiler namespace. Install the matched Torch wheel and
its matching CUDA dependency wheels explicitly, then the integrated compiler
wheel. `--no-deps` here is intentional. The wheel sets must be obtained and
verified for the target Python/CUDA environment.

```bash
python3.10 -m venv /absolute/path/to/runtime-venv
runtime=/absolute/path/to/runtime-venv/bin/python
"$runtime" -m pip install --no-deps /path/to/torch-2.8.0+cu128-cp310-cp310-manylinux_2_28_x86_64.whl
"$runtime" -m pip install --no-deps /path/to/matching-cuda-wheels/nvidia_*.whl
"$runtime" -m pip install filelock 'typing-extensions>=4.10' 'sympy>=1.13.3' \
  networkx jinja2 fsspec 'numpy==2.2.6'
"$runtime" -m pip install --no-deps /absolute/path/to/wheelhouse/flagtree-0.7.0-cp310-cp310-linux_x86_64.whl
```

For an offline installation, add `--no-index --find-links /path/to/dependency-wheels`
to the pure dependency command. The qualification environment used original
cached dependency wheel bytes, without source-directory imports. NumPy is
required by the NVIDIA host ring export path.

Check the installed modules with an isolated interpreter, then run an ordinary
application script. Do not add compiler or component source directories to
`PYTHONPATH`:

```bash
"$runtime" -I -c 'import triton, flagtree.profiler; from flagtree.profiler.native import compiler_binding, runtime_binding; print(triton.__file__); print(flagtree.profiler.__file__); print(runtime_binding().__file__); assert hasattr(compiler_binding(), "add_automatic_proton_scopes")'
/absolute/path/to/runtime-venv/bin/flagtree-profiler --device 0 --detail auto \
  -n /absolute/path/to/result /absolute/path/to/application.py
```

Open `result/report/fine_grained.html`. The bundle contains source-linked dynamic
records, the selected-site plan, raw capture evidence and `ai/export_timing.json`.
The timing receipt declares whether it includes full finalization and export;
its hash is recorded in `manifest.json`. Host engineering wall times are not
NVIDIA device latency or overhead measurements. A measured budget pass does
not establish deadline enforcement.

## Retained installation evidence

The first independent installation completed 557 build steps from clean
source and installed the real wheel into a fresh virtual environment. A later
refresh used this public helper and the same verified native build directory;
its normal wheel installation and isolated module/source hashes are retained
under `artifacts/usability/run-001/nvidia/refresh-root-r1-*` in the engineering
workspace. The server artifacts are under
`/workspace/usability-run-001/nvidia/refresh-root-r1/`.

Short functional checks cover unannotated loop visits with one binary,
source/operation/invocation attribution, masked reduction and matrix development
kernels, ordinary CLI execution with one host-side effect, and explicit manual
scope compatibility. These development and installation results do not replace
frozen unseen-kernel acceptance or a final release freeze. NVIDIA performance
benchmarks remain deferred.
