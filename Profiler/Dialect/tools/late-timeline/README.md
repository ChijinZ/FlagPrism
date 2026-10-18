# Experimental late NVPTX recording component

This component inserts records into an ordinary kernel's optimized LLVM IR.
It is an isolated development implementation; default timeline API integration,
final machine binding, clock qualification and Perfetto delivery are pending.
It does not complete the three-backend timeline contract.

Build inside the server Docker with the matching LLVM SDK:

```bash
python integration/patches/nvidia/build_late_timeline_tool.py \
  --llvm-root /path/to/matching/llvm \
  --output /new/late-tool-build
```

The recipe records source/config/executable hashes, the compiler command and
actual process identity. It uses the existing owned-process cleanup helper.
The tested SDK is LLVM 22 `f6ded0be` paired with the retained FlagTree build;
NVIDIA math was tested on sm_120a in `chijin-study-pro6000`.

The internal tool accepts already optimized ordinary LLVM IR and an explicitly
validated, unused profile-scratch argument index. It refuses a used argument,
non-global pointer, multiple kernels, mismatching block size or missing dynamic
shared symbol. No user source annotation is involved. It recognizes actual
native submit/commit/wait/barrier operations, shared-memory loads/stores and
matrix issue regions. Ordinary global-memory operations and scalar arithmetic
are not yet selected by this experimental component.

The full-actor path currently targets `nvvm.reqntid=128`; it retains all 128
thread records for physical byte-footprint analysis. The optional compact mode
records first/last logical programs in at most two physical slots. Logical
identities are retained; sampling does not renumber the application's programs.
Matrix grouping preserves all native/source members in the execution manifest.
Reads are inserted at selected optimized LLVM operations; final instruction
placement remains unqualified. Publication is batched at original basic block
exits. The pass adds no completion barriers.

## Private experimental record layout

Words are stored as `program / logical_word / actor` with 64-bit words.
Each actor has six header words: published count, overflow flag, magic, actual
logical program ID, actual dynamic-shared symbol base, and actual thread ID.
Records contain site ID, begin tick, end tick and a typed payload. Point events
have equal begin/end ticks. Capture guards and unused words are independently
checked. Source cost, physical engine busy and cross-actor clock alignment are
not granted by the data format.

Shared addresses are original device addresses. The tested dynamic region starts
at address 1024, so a size-only check assuming a zero base is incorrect. All range
checks use the captured symbol base and the actual ordinary kernel's shared size.

A copy payload retains its shared address and source-valid byte count; its
16-byte destination can be zero-filled even when the source-valid count is zero.
Shared stores/ordinary shared loads retain the actual DataLayout access width.
The modeled ldmatrix forms are explicitly m8n8/x4/b16, including transpose.
Other ldmatrix geometry requires a distinct participation/footprint mapping.
These distinctions follow the native operations documented in
[NVIDIA PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/).

## Real-byte model and development checks

`timeline_nvidia_late_model.py` decodes original allocation bytes, validates
publication/guards/identities and checks byte producers, thread-local commit
ordinals, wait limits, CTA visibility cuts and reuse generations. Its current
model requires a uniform observed CTA path. It checks logical consistency;
its result explicitly withholds machine-site binding and time-flow qualification.

Run the retained-byte development test inside Docker:

```bash
python -I tests/timeline/p01_nvidia_late_model.py \
  --input-root /retained/math-run/output \
  --model-module Profiler/python/flagtree_profiler/timeline_nvidia_late_model.py \
  --output /new/byte-check
```

The input includes the retained successful parent terminal receipt, original
allocation binaries, metadata and manifests. The test checks three real math
captures and corruptions derived from their bytes; it does not replay the device
application. A separate optimized Python invocation exercises the same checks.
This is development evidence, not independent six-math qualification.

The runtime-K development GEMM mixes synchronous shared producers with async
copy producers; the constant-K GEMM preserves its ordinary unrolled math body.
The implementation and tests must keep both execution structures visible.
The final tool still needs the default compile/launch/owner/decoder interface,
actual machine/timer binding and standard Perfetto integration before promotion.
