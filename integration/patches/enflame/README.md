# Enflame automatic profiling installation

Use the Enflame SDK/driver and PyTorch GCU environment supported by FlagTree.
The verified development environment is ZIXIAOC200, driver 1.9.10, Python3.12,
FlagTree `add842f2c495a3974944733ea6b07ff6b5bfcee8` plus
[`flagtree-source.patch`](flagtree-source.patch). The FlagPrism source is this
repository. Apply that patch to an independent FlagTree checkout and place this
repository at `third_party/FlagPrism`, or set `FLAGPRISM_SOURCE_DIR`.

The complete source-build entry is [`build_from_source.py`](build_from_source.py).
It needs Git, a C++17 compiler, CMake, Ninja, Python 3.12 with setuptools, wheel,
pybind11 and pip, matching installed Torch/GCU packages, and these dependency
prefixes. None of them is a prebuilt FlagPrism checkout:

- Enflame SDK root containing `include/tops/tops_runtime.h`, `lib/libtopsrt.so`,
  `extras/TOPSPTI/lib64/libtopspti.so` and its GCU compiler/toolkit libraries.
- FlagTree's matching LLVM/MLIR development distribution, with
  `lib/cmake/llvm/LLVMConfig.cmake` and `lib/cmake/mlir/MLIRConfig.cmake`. For this
  pinned FlagTree revision the package is `llvm-fc83c68-gcc9-x64` (LLVM23), as
  specified in its `python/setup_tools/utils/enflame.py`. Its public archive is
  [enflame-llvm23-fc83c68-gcc9-x64_v0.4.0.tar.gz](https://baai-cp-web.ks3-cn-beijing.ksyuncs.com/trans/enflame-llvm23-fc83c68-gcc9-x64_v0.4.0.tar.gz).
- An include directory containing `nlohmann/json.hpp`.

From this component checkout, with those prefixes assigned to the variables:

```bash
git clone https://github.com/flagos-ai/FlagTree.git ../FlagTree-enflame-input
git -C ../FlagTree-enflame-input checkout add842f2c495a3974944733ea6b07ff6b5bfcee8
python3.12 integration/patches/enflame/build_from_source.py \
  --component "$PWD" --flagtree ../FlagTree-enflame-input \
  --llvm-prefix "$FLAGPRISM_LLVM_PREFIX" \
  --tops-prefix "$FLAGPRISM_TOPS_PREFIX" \
  --json-include "$FLAGPRISM_JSON_INCLUDE" \
  --workdir "$FLAGPRISM_BUILD_DIR" --jobs 8
```

The work directory must be new. The script independently clones the pinned
FlagTree commit, applies the maintained patch, snapshots this component, and
configures a new build. It actually compiles `triton`, both FlagPrism native
modules, both `triton-gcu*-opt` frontend tools and their Python bindings, and the metadata unit executable;
then runs that executable, builds the normal FlagTree wheel, installs a fresh
venv and verifies installed import/native/header/tool provenance. Every stage
retains its exact command, log and exit code; source bytes have a SHA manifest.
LLVM and SDK distributions are reused as dependencies. Native outputs from an
older FlagPrism build are not a prerequisite. Do not reuse native binaries after
editing C++.

To resume a failed build or packaging stage, repeat the command with `--resume`.
This verifies and retains the original immutable component snapshot; it does
not import edits from `--component`. CMake reuses completed matching objects,
and new attempt logs, wheel directories and venvs retain previous failures.
Use a new work directory when changing component source. The final `result.json`
identifies the actual wheel and venv paths, including any resume suffix.

The default vendor dependency path is detected from the selected Python's Torch
installation. `--vendor-site-packages /path/to/vendor/packages` can explicitly
select that existing installation. The venv adds this as a literal directory,
without processing editable `.pth` hooks from the vendor installation. Activate
the resulting installation without a source path:

```bash
unset PYTHONPATH
export FLAGTREE_BACKEND=enflame
"$FLAGPRISM_BUILD_DIR/venv/bin/flagtree-profiler" --detail auto --device 0 \
  -n /tmp/my-capture my_script.py
```

For advanced reuse of an existing matching compiler/native build, the assembly
recipe is:

```bash
python3.12 integration/patches/enflame/build_automatic_wheel.py \
  --flagtree /path/to/independent/patched/FlagTree \
  --component /path/to/FlagPrism \
  --native-python /path/to/matching/python-output \
  --core-library /path/to/matching/libtriton.so \
  --backend-build /path/to/matching/cmake-build \
  --output /path/to/new/wheel-output
```

This uses FlagTree's actual setup metadata, package mapping, `build_py` and
`bdist_wheel`, and explicitly reuses matching native artifacts. It does not
claim to build them. The backend build must contain `bin/VERSION`, both
`triton-gcu*-opt` tools, and backend libraries. `VERSION` is required: a missing
file makes the backend assume Triton3.5 and choose an incompatible pass-manager
API on Triton3.6. The recipe checks archive bytes against source Python and
native artifacts, including this ABI selector, tools and the runtime header.
It refuses accidental CMake/Ninja/Make builds during assembly.

Install the wheel into a fresh venv with `pip install --no-deps wheel.whl`.
Existing matching Torch/SDK dependencies may be reused. In the verification
venv, a literal `vendor-dependencies.pth` line points at the installed vendor
package directory; it does not process that directory's editable `.pth` files.
No `PYTHONPATH` or `sitecustomize.py` is required. Check actual imports:

```bash
unset PYTHONPATH
export FLAGTREE_BACKEND=enflame
python -c 'import triton, flagtree.profiler, flagtree.debugger; print(triton.__file__, flagtree.profiler.__file__, flagtree.debugger.__file__)'
flagtree-profiler --detail auto --device 0 -n /tmp/my-capture my_script.py
python -m http.server 8000 --directory /tmp/my-capture
```

Open `http://localhost:8000/report/index.html` (forward the port when remote),
then follow the source-linked internal records link.

All three imports, native modules and backend libraries must resolve within the
venv. Driver/SDK libraries and Torch may resolve to the documented installed
vendor dependencies. Use a fresh `TRITON_CACHE_DIR` for cold compilation.
The default auto route selects at most eight real internal sites, one logical
program and one actor. GCU raw timers are 46-bit ticks without a calibrated
nanosecond frequency. Source-control intervals do not establish engine busy
intervals or operation completion. Block-pointer kernels use real dynamic
interval capture; numeric/address summaries retain their existing boundaries.

Development regressions use ordinary unannotated kernels:

```bash
python tests/enflame/automatic_hardware.py /tmp/baseline --baseline-only
python tests/enflame/automatic_hardware.py /tmp/automatic
python tests/enflame/automatic_block_pointer.py /tmp/block-baseline --baseline-only
python tests/enflame/automatic_block_pointer.py /tmp/block-auto
python tests/enflame/automatic_structures.py /tmp/structure-baseline --baseline-only
python tests/enflame/automatic_structures.py /tmp/structure-auto
python tests/enflame/control_flow_hardware.py /tmp/control-baseline --baseline-only
python tests/enflame/control_flow_hardware.py /tmp/control-auto
```

The hardware/structure runners accept `--size 137` or `--size 256`, and
`--num-warps 1` or `--num-warps 4`. They assert original math, input,
canaries, source/binary/call identity, multi-site dynamic records, device raw
publication tags, exact ordinals and no loss, plans, clocks and bundle size.
The loop runner requires different runtime trip counts to reuse one binary and
produce repeated visits at the same site. They are development regressions,
not independent unseen qualification. Run all compilation, tests and CPU
references inside the booked server Docker.
