# Enflame automatic profiling installation

Use the Enflame SDK/driver and PyTorch GCU environment supported by FlagTree.
The verified development environment is ZIXIAOC200, driver 1.9.10, Python3.12,
FlagTree `add842f2c495a3974944733ea6b07ff6b5bfcee8` plus
[`flagtree-source.patch`](flagtree-source.patch). The FlagPrism source is this
repository. Apply that patch to an independent FlagTree checkout and place this
repository at `third_party/FlagPrism`, or set `FLAGPRISM_SOURCE_DIR`.

For a new native build, use FlagTree's normal build with
`FLAGTREE_BACKEND=enflame TRITON_BUILD_FLAGPRISM=ON TRITON_BUILD_PROTON=OFF`.
Set `FLAGPRISM_SOURCE_DIR` to this repository. The matching LLVM/MLIR CMake
packages in the verified environment are under
`/opt/flagtree-llvm/llvm-fc83c68-gcc9-x64/lib/cmake/{llvm,mlir}`. Set
`JSON_INCLUDE_DIR` to the installed nlohmann JSON headers if needed. Do not
reuse native binaries after editing C++.

For an existing matching compiler/native build, the checked assembly recipe is:

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
```

The hardware/structure runners accept `--size 137` or `--size 256`, and
`--num-warps 1` or `--num-warps 4`. They assert original math, input,
canaries, source/binary/call identity, multi-site dynamic records, device raw
publication tags, exact ordinals and no loss, plans, clocks and bundle size.
The loop runner requires different runtime trip counts to reuse one binary and
produce repeated visits at the same site. They are development regressions,
not independent unseen qualification. Run all compilation, tests and CPU
references inside the booked server Docker.
