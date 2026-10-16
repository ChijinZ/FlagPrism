# CPU validation receipt summary

The actual isolated build is `/tmp/chijin-r15-sdk-scalar-legality` in Docker
`chijin_v3.5.x`. This is CPU compiler evidence; no kernel or NPU execution was
performed by this engineering task. Device mathematical, State, input/canary
and full qualification criteria remain unchanged and pending.

| Material | SHA256 |
| --- | --- |
| Exact SDK source revision | `428ab8fdab46a879c7349caba4cde705bc8c9bb6` (Git commit) |
| Public LLVM source revision | `cd708029e0b2869e80abe31ddb175f7c35361f90` (Git commit) |
| Separate build compatibility patch | `4c6e07d319ed7b75c9a7d6ec718b8151c8abb0a5640c1e6eac360a6b17321d64` |
| SDK legality patch | `7ce7f7c116b9beade493b6473337e73cedff230a62b1b180d26d6f591e30a4db` |
| Legality-unmodified compiler | `7edd1aa8b4d9cad6a55355997af7d5969d2c277664a9477ca08555e51c7e3822` |
| Fixed compiler | `1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e` |
| Original public NPUBIN, 4576 bytes | `05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e` |
| Isolated baseline NPUBIN, 4576 bytes | `5bdc6ab47c5456d8e6d7c7a1f1ab2a56132bc0d20e251ebed5995548dbb3357b` |
| Fixed public NPUBIN, 4528 bytes | `d5e366436832b147c619d65a467442a23e33a7bb0a49e27a4ebcfc27ce9169c3` |

The original vendor LLVM build stamp is19.1.7/e4ce5939f6e1; the public pinned
LLVM source plus the exact SDK's65 patches is not asserted to be that private
vendor build. The actual isolated baseline is exact428 plus explicit-template
build compatibility, with legality unchanged. Both Bind IR snapshots are
byteequal to the stock SDK replay. The final NPUBIN is **not bitidentical**:
85 different bytes lie exclusively in the nonallocated `.comment` producer
payload and its own section-size field. All other file bytes, ELF/PHDR fields,
section layout/content, symbols, stack/argument records and PT_LOAD content are
identical. Root independently checked this limited classification before
legality compilation. No output was stripped, edited or recompiled with
changed codegen flags to obtain equality.

The newly generated public templates carry the installed CANN ccec producer
`2026-04-25T15:46:25+08:00 clang version15.0.5`, whereas the stock SDK template
producer string reads `AscendNPU-IR Compiler202602 clang version15.0.5` (spacing
is retained exactly in the raw ELF receipt). The official CMake template build
uses `ccec -emit-llvm -c`. Only public CPP template source was rebuilt; SDK
private bitcode, executable and library contents are not in evidence or Git.

Actual controller history remains under the isolated prefix:

- Download1902804 ended by an explicit transport handoff; its two owned curl
  processes terminated with -15. Local official archives were hash-verified
  before transfer, retaining old partial files.
- Build1907341 failed patch31 with `git apply` because the official patch lacks
  a final newline. The official GNU `patch -p1 --merge` path accepted those same
  bytes with its warning. Resume1910107/buildchild1911815 retained that failure.
- The pristine SDK links then failed on the missing five-argument
  `collapseAndReplace<CollapseShapeOp>` explicit instantiation. Source, actual
  U/no-W symbols and link failure were frozen. Compatibility1964783 changed
  one actual Utils object, reused2618 objects and linked both tools.
- Replay1967779 returned driver0 but produced no final NPUBIN because initial
  `BUILD_TEMPLATE=OFF` left five template BC files absent. This remains failed.
- Templates1973190 built51 official public CPP sources and installed all five
  resources, changing no object or compiler bytes (2619 objects reused).
- Resource-complete replay1976637 produced the limited producer-only baseline.
  Actual downstream hivmc/bisheng and libdevice/template path+SHA were recorded.
- The first legality controller1984181 rejected a tuple/list JSON comparison
  before source mutation. Its log remains. Canonical JSON serialization fixed
  the fail-closed comparison; a separate reviewed execution seal binds actual
  input, reference, binary, compiler, source and material manifests.
- Legality1985860 completed four real Ninja actions: partition TU compilation,
  HIVMTransforms archive, and both tool links. Only
  `TileAndBindSubBlock.cpp.o` changed (`d8f70c6b…` to `88a53f9a…`);2618 objects
  were independently hash-verified unchanged. Dependency and compile-command
  manifests were frozen before/after. Original install bytes remain intact.
- Fixed replay1987795 generated its final public NPUBIN using the actual driver
  and all five templates at `install-fixed/lib`. Its pre-pass IR is unchanged;
  after-pass IR has two complete-store SUB0 guards, closed scalar SSA, no
  mapped subblock loop, and synchronization before election.

Actual pass regressions: four baseline cases and five fixed cases passed.
The positive tileable case retains parallel partitioning; the scalar chain
exposes the original bug; odd-size tensor stores retain their preexisting safe
fallback; the multiple-function case verifies processing after a fallback;
the fixed conditional case retains source control and SSA. Early invalid
fixture syntax and an incorrect assumption that odd-size tensors also expose
the bug are retained in `pass-unmodified`, `-v2` and `-v3`. Corrected fixture
inputs and expectations are explicit in `pass-unmodified-v4`; no compiler
behavior was altered to make those tests pass.

The final repository gate suite passed30 normal/optimized-Python subcases,
including producer-only acceptance and text, LOAD, flags, symbol, other section,
comment allocation/overlap/bounds, input/output/reference/tool identity rejection.
Clean first-build compatibility preparation passed normal and `-O` public-source
fixture tests (correct patch, wrong patch, changed source and reapply). It
produces the same Utils bytes already actually compiled; another full LLVM
build was not performed solely to exercise this new preparation entry.

An independent C2 review ran58 frozen subprocess checks: the earlier assertion
based gate erroneously accepted9 negative cases under `-O`; the corrected
explicit-exception snapshot rejected all26 negative cases and accepted6 valid
cases. Later comment bounds/overlap checks and the fresh-build compatibility
source check add stricter validation; they are covered by the final repository
suite rather than falsely attributed to that earlier C2 snapshot.

Safe detailed CPU receipts, original failures and public IR/NPUBIN artifacts
are retained in the workspace's `artifacts/usability/run-013/state-failure-forensics/`
under `sdk428-resource-baseline/` and `sdk428-fixed-cpu/`. SDK resources are
represented only by resolved paths and hashes. Root has separately archived its
independent ELF and fixed-CPU audits. This source commit changes no profiler
runtime or cache selector: the separately installed compiler-identity parent
patch selects this same standalone tool for ordinary and profile compilation.

The subsequent C3 test-route correction exercises both supported baselines.
The test selects the actual rebuild identity/bitidentical preflight for
`state=matched`, and the existing derived-IR/ELF validator for
`state=binary_mismatch`. The preflight was extracted from the rebuild entry
without changing source/resource validation or the producer exception. Both
routes reject changed input/output/reference/tool hashes, state and byteequal
flags, under normal Python and `-O`. Six Docker suite invocations passed: a
clearly marked synthetic matched receipt whose binary is a copy of the public
reference, a synthetic producer receipt copying the earlier public artifact,
and the unchanged actual producer replay, each under normal and optimized
Python. Every suite also exercises normal/optimized child validators. These
are test-only copied receipts, not new compiler replays or claims that the
isolated baseline became bitidentical. No SDK source, tool, template, final
NPUBIN or device execution changed.
