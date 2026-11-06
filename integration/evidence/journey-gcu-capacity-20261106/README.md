# Explicit timeline capacity extension, 2026-11-06

Source commits: `44f06baa` (GCU producer/runtime/decoder and API), `215ccafe` (existing Ascend support exposed through API). Defaults are unchanged. Explicit GCU/Ascend requests accept at most 16384 native pairs; other backends retain the public 4096 bound.

The native recorder and all eight debugger runtime source files were rebuilt in the existing `flagprism-enflame-dev` container, isolated under `/root/chijin-journey-capacity-20261106`. The runtime used compile/link flags from the retained FlagTree CMake graph, with source/object/output paths redirected. The recorder used its supported standalone CMake graph. Installed libtriton, SDK and active environment were not modified.

Verification: 11 native producer/preservation tests, 3 byte-decoder/allocation tests, and 12 public-capacity tests passed. The public tests include passing 16384 through the Ascend request and rejecting it for NVIDIA. The synthetic decoder stream matches the observed 8875-pair event count, but is explicitly not hardware evidence. The 4096 fixture drops 9558 endpoints; the 16384 fixture retains all 17750 endpoints. Two GCU selected-program slots allocate 4194368 bytes. Full real-kernel capture is the subsequent integration check.

A complete staged Python package is available at `/root/chijin-journey-capacity-20261106/output/python`; use it through `PYTHONPATH` with the existing venv Python. Four Python modules and the two rebuilt native artifacts were replaced only in this staging copy. The receipt records their SHA256 values. No device kernel was launched during this work.

Ascend already supports 16384 end-to-end in `Profiler/llvm/AscendTimeline.h`, `Profiler/llvm/AscendLateObserver.cpp`, `Profiler/python/flagtree_profiler/ascend_compiler.py`, the debugger compiler adapter, the storage planner, and the decoder. It requires the public API update, not a new native ABI.

Real-kernel follow-up: GCU DSA with capacity 16384 exhausted compiler-reported local memory (required 1572480 bytes, available 1572352 bytes). The producer uses a local ring in addition to global output slots; the API ceiling does not guarantee a particular kernel fits the device. The same capture succeeded at 8192 according to the root experiment task. Hardware limits were not changed.
