# Independent compiler integration

The profiler Python package, native runtime, compiler bindings and FlagTree
backend callbacks must be built from matching source. These patches preserve
changes outside this repository; they do not include installed vendor SDK files.

Apply each backend patch only to its recorded baseline in a separate worktree.
First run `git apply --check` and inspect the diff. Do not apply focused historical
patches on top of a combined patch that already includes them. Keep the previous
working compiler available until the fresh core/runtime passes its acceptance
tests. Backend build and test entry points live in `tests/` and
`Profiler/docs/method_testing.md`.

## NVIDIA

`nvidia/flagtree-source.patch` applies to FlagTree commit
`57d348b08455ff9a03902016c0fd6054ab44343e`. It includes FlagPrism build policy
and preservation of explicit instrumentation mode in JIT options/cache identity.
This patch was used by the actual NVIDIA full-core build. Do not use its build
success as evidence of compatibility with another FlagTree baseline.
Layer `nvidia/automatic-scopes.patch` afterwards for automatic unannotated
profiling. The [NVIDIA build/install recipe](nvidia/README.md) and
`nvidia/build_automatic_wheel.sh` use the actual integrated native build.

## Enflame

`enflame/flagtree-source.patch` applies to FlagTree commit
`add842f2c495a3974944733ea6b07ff6b5bfcee8`. It exports the actual SDK bridge
debug-location and bounded-index timer integration used by the dynamic and
held-out hardware checks. The expanded detailed operator matrix and overhead
checks remain in progress. The earlier timer patch forced global
`enable_i64=True` and is not the current integration recipe. The bounded dynamic
path preserves the application's option rather than changing it globally.
Installed SDK bitcode remains a runtime prerequisite and is never redistributed
here. The hardware is ZIXIAOC200; `gcu300` is the compiler/SDK target name.

## Ascend

See [Ascend pinned integration and packaging](ascend/README.md). Apply its
complete patch first, then `automatic-source-origins.patch` and
`automatic-import-order.patch`. These layered changes preserve automatic source
locations and initialize the vendor Torch runtime before importing Triton.
The earlier gateway interruption has been resolved; independent API/CLI and
native task/source checks have run in the existing server Docker.
The upstream LLVM15 observer must run out of process before the SDK toolchain;
loading it directly into the vendor LLVM15 fork is unsupported. Independent developer checks do not substitute for the common held-out
qualification or final code reviews. The late plugin is packaged in the wheel;
normal automatic profiling uses its package-local path and retains compiler
receipts without developer-only environment variables.
