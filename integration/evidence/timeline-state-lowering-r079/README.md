# R079: original State-lowering inspection, still incomplete

This is engineering qualification evidence. It changes no product runtime, native recorder, ABI, exporter, SDK, paper or Study input. No mathematical application, device measurement, Trace Processor or UI case was replayed. The two full receipt archives and their per-file SHA256 ledgers are retained under root `artifacts/timeline/run-079/preflight/`; hashes and counts are in `summary.json`. All archived CPU jobs have authoritative terminal receipts.

## Ascend: bind the missing LLVM to the original binary

The original ordinary `q03-s0-c0` used system SDK `4a1312e7`, not the current fixed instrumentation SDK. A passive `bisheng` wrapper copied its actual LLVM and linked bitcode inputs without transforming them. The effective original backend options were reconstructed from the frozen cache. The resulting entire 3,648-byte executable equals the frozen original npubin, SHA256 `86d3a4b717d38cd23cf5ddf912ebdb130c0b08944a6b8a9e12beb2b8ae12c322`. This establishes an object-bound path to inspect the original State lowering; it does not itself certify unique writers.

LLVM15 extracted the actual linked `_mlir_ciface_store_ubuf_to_gm_1d_int32_t` definition and its recursive dependencies. They include scalar GM stores and the actual `MOV.UB.TO.OUT.ALIGN.b32.V220` intrinsic path, offset arithmetic and flag/wait calls. Their reachability for this invocation, physical actor mapping and exact write range still need to be resolved. Original installed launcher excerpts show task type10 maps to AIV, no mixed ratio; the ordinary launch computes the block count and passes grid dimensions. These are ABI inputs to that analysis, not a completed proof.

An additional standard LLVM15 link/inlining view is only an analysis derivative. Vanilla opt rejects the proprietary `hiipu64` architecture; the derivative removes only that triple line and retains the original data layout before target-independent passes. **It is not vendor final IR, a newly executed program, or a final machine boundary certificate.** Its provenance and adaptation are explicit in `ascend-analysis-view-result.json` and the executed script.

Earlier failures remain in the full archive: the SDK removed its temporary `kernel.ll` after the passive compile; the first follow-up did not use the retained copy. Further driver probes rejected `-S`, `-emit-llvm` and `-print-after`. Standard LLVM initially rejected `hiipu64`. None is a device/math failure, and none supersedes the successful byte-identical original reproduction.

## Enflame: inspect the real primitive definitions

The installed SDK's `gcu300_tops_builtins.bc` was hashed and inspected using its LLVM11 opt. Internalization/global-DCE preserves the selected thread/block getters and DMA/deslice routines. The actual getters use `llvm.dtu.read.tid.{x,y,z}` and `llvm.dtu.read.bid.{x,y,z}`; actual deslice definitions expose clipped extents, byte offsets and native transfer descriptors. This avoids inferring semantics from function names. The missing standalone llvm-extract attempt is retained; LLVM11 opt succeeded.

These definitions are not yet bound to every original compiled object's actual link closure or finite State partition. Neither Enflame nor Ascend is marked writer-qualified. This work also does not close the original final source/loop boundaries, ordinary/default/sparse stage and buffer-reuse relations, or the whole-goal final review.

The independent delivery review in this directory specifies the finite original contract and remaining facts. It does not request all-ISA interpretation or another device/math/TP/UI matrix. Private SDK IR and libraries remain outside Git; the scripts, small results, identities, terminal receipts and review are retained here for reproducibility.
