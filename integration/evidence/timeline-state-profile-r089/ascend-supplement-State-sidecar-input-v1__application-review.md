# R089 supplemental ordinary State ABI review

Requested configuration: GPT-6.1-Sol / xhigh. Actual resolved configuration: unknown (not exposed). Scope: the eight registered q07/q08 ordinary objects per backend, two shapes × two configurations. Read-only local source/evidence/hash inspection; no product import, tests, SDK execution, device access, mathematical replay, TP/UI run, or peer-review reading.

## GCU: ordinary-supplement8 can receive a derived qualification sidecar

The evidence supports `actual State writer under the reviewed SDK ABI` for exactly `q07-s{0,1}-c{0,1}` and `q08-s{0,1}-c{0,1}`. It does not reopen ordinary32/current96 or grant native, pipeline, or whole-goal qualification. Preserve the original reports' `state_writer_qualified=false`, SDK/native false fields; record this later composition in a new sidecar with the eight object/math/launch identities and reviewed ABI inputs.

I read `preflight/gcu-receipts-v1/supplement-State-input-v1/run.py`, the actual terminal/result/rows, all eight translated `object-*/functions.ll` and corresponding retained fatbins, and the supplemental inventory/cache metadata. The runner binds the original State formal and unchanged public wrapper, original grid and configured physical threads, and checks every original artifact against its frozen math receipt before invoking the original SDK. Its mechanical translation removes only the outer GPU-module container. This is an analysis translation, not a claim that it is postlink/native final IR.

Evidence identities (SHA-256):

| Input / receipt | SHA-256 |
| --- | --- |
| Original ordinary freeze | `179cc20f2f89d2745b25c3fdba24f2569180fe5ae1143d85bc1a088800ab3743` |
| `gcu-supplement-inventory-v1.json` | `8d56b163c500ea4e286d1655608693c541a60dee85f74d852b73f4ee9de060c6` |
| `gcu-supplement-cache-v1.json` | `d34adec38318d2ea516dcffa577d3df8ccbd8a2282cca42b54d72d202292bdd9` |
| Actual runner | `2d597482b7473f37e626fb4e0669ed9af87c5babc8659e915ad27b7e8ac05c21` |
| `terminal.json` | `26456bb3691e6c221dfcb9e97396a8af5e7dfb42a30429add78d27f70bda3de5` |
| `output/result.json` | `33d2cb228d4eb2f049d5692e7e7a337d8d0ae21edcb62d3df5934c03b83f785a` |
| `output/rows.json` | `5c5dd97013f2703e264b440ae7cdeebe3674d5f338789f1feb234aa69885a85c` |
| Unchanged partition checker | `867a00b2599c379acfa49bcad0f3295bc05449100d764c308eb1e50c08241c6d` |

Actual terminal is return code 0, 10.331329702 s; result is 8 registered / 8 checked / 8 partitioned, no failures. I independently joined all eight registration/freeze entries to math report hashes, original source/TTIR/TTGIR/GCU-IR/LLIR/fatbin hashes, cache compiled hashes, and original one-launch/input/guard/State-count facts. Each local SDK-produced whole fatbin has the exact original math-bound fatbin hash and size; each local translated LLVM hash matches its row. The SDK compiler `1b7e13a7…855e40`, translator `f93024f7…361`, and builtin `fa9d8500…944a` are the R082-reviewed identities. This reuses the already-reviewed actual launch/helper semantics; it does not infer semantics from transfer names alone.

Actual launch is gcu300, grid XYZ with block `(num_warps,1,1)`, here 4 or 8 physical threads, not the target object's nominal warp-size 12. Metadata `warp_size=1`, original config, retained LLIR and wrapper forwarding bind that interpretation. The original State pointer is `%3`. The actual integer helpers used in these LLVM files are the reviewed signed `tops_maxsi`, `tops_minsi`, and `tops_remsi`; no unreviewed division rule is needed.

The 262 actual State write instances use only the reviewed 2D functions: 166 `tops_deslice_async_2_si32` and 96 `tops_slice_deslice_async_2_si32`. I independently expanded the recorded descriptors with their actual SDK rules: deslice2 copies the complete source rectangle with **no implicit min**; slice-deslice2 clips requested rows/columns to the remaining destination, requiring valid source windows. Every instance satisfies those bounds and its recorded element count. For each actor I checked block/thread membership, then recomputed every destination index. The resulting maps exactly equal the retained maps: all 17,140 i32 elements have one writer, and no transfer writes outside the State allocation. Four-byte element alignment and exact element spans preserve the adjacent tail/guard boundary under these reviewed helpers. The actual LLVM additionally shows nonzero/tail selection and writeback completion, rather than assuming every launch actor writes a full tile.

| Registration | Grid | Physical threads | State i32 count | Write instances |
| --- | --- | ---: | ---: | ---: |
| q07-s0-c0 | 3 × 2 | 4 | 3072 | 24 |
| q07-s0-c1 | 2 × 2 | 8 | 3072 | 32 |
| q07-s1-c0 | 4 × 3 | 4 | 3657 | 36 |
| q07-s1-c1 | 2 × 3 | 8 | 3657 | 36 |
| q08-s0-c0 | 3 × 2 | 4 | 768 | 24 |
| q08-s0-c1 | 2 × 2 | 8 | 768 | 32 |
| q08-s1-c0 | 4 × 3 | 4 | 1073 | 40 |
| q08-s1-c1 | 2 × 3 | 8 | 1073 | 38 |

No confirmed blocker or additional SDK/mathematical replay requirement was found in this finite GCU composition. Minimum remaining bookkeeping: derive the eight-entry sidecar with these identities and the R082 ABI/launch contract, without changing historical raw receipts.

## Asc: pending the actual terminal and full eight-object evidence

At this review point `preflight/ascend-supplement-State-poll-v2.json` records `terminal.json=null`, `output/result.json=null`, and progress 3 checked / 3 partitioned / no failures. This is not eight-object completion. I read the proposed supplemental runner and its original inventory/cache inputs, but do not grant qualification from the partial progress.

The finite follow-up is to read the completed eight rows and retained actual passive codegen inputs, verify whole-npubin equality and frozen math/cache/host-once/artifact joins, and apply the existing R081 actual State wrapper/helper and pure-AIV/mixed launch semantics to those actual descriptors. No new math, TP/UI, general ISA proof, or full SDK matrix is required by this remaining evidence inspection. Native/pipeline/whole qualification remains outside this report.

### Completed Asc evidence received: actor/partition checks pass; actual library identity bridge remains

The earlier partial-progress status above is historical. The actual `ascend-supplement-receipts-v1/runs/supplement-State-v2/terminal.json` is now return code 0 / 53.842491611 s. Result: 8 registered / checked / partitioned, eight distinct passive CPU codegen jobs, no failures. I read the actual two runner scripts, unchanged checker (`bfad3bcf27fcd193ac625b5b0dbd7eca17dde84c5d743742fee5a138031d621b`), all retained actor sources, actual codegen receipts, original metadata/inventory and result rows. I independently verified all 147 regular members against `supplement-index-v1.json` bytes/SHA.

The local original npubin and newly produced **whole** `kernel.o` bytes are identical for all eight registrations and have the frozen math-bound npubin SHA. The original bcmlir bytes, math/cache compiled hashes, all artifact hashes and original one-launch/input/guard/State-count facts also join. Intermediate mixed AIC/AIV objects are correctly kept distinct from the complete npubin. This supports the caller/object relationship without a device replay.

All eight actual State `store_ubuf_to_gm_2d_int32_t` wrappers have exactly the R081-reviewed definition SHA `bd9ea7c995aa89d1b30240bf4929e67282639fab1113f12d1d2df21541461b9e`: source then destination descriptors, allocated/aligned/offset/size/stride fields in their actual ABI positions, atomic0. State is actual user argument `%6` following the hidden prefix; the final three parameters are the original grid. The four q07 objects have metadata `mix/32`, AIC body with no State use, and two AIV subblocks; c0 has a subblock0 writeback guard, c1 partitions rows between AIVs. The four q08 objects use `aiv/10` and one AIV. This fits the R081 reviewed launcher/GET.SUBBLOCKID mechanism without adding hypothetical NV lanes.

I independently expanded the 66 State transfer descriptors (including two zero-row no-ops) into destination indices. All 17,140 i32 elements have exactly one writer, no destination escapes the State allocation, and the recomputed maps equal the actual recorded per-actor maps. All source offsets are 0, source byte bases are 32B aligned, source/destination sizes agree, source strides are `[32,1]` (q07) or `[16,1]` (q08), destination strides are `[64/69,1]` or `[32/37,1]`, respectively. Sizes fit the R081 scalar/tail/continuous-last-dimension SDK algorithms; `[16,1]` is a valid aligned UB row stride, not a reason to invent a new gate from the old batch's observed `[32,1]`. The distinction between UB block stride and GM byte length, and the exact GM tail span, must still be supplied by the **actual linked** helper semantics.

One concrete verification gap remains before granting Asc supplementary8 qualification: these eight actual AIV codegen receipts bind `meta_op.aiv.bc` SHA **`c816c724c8d0455ff1a85cd08b1f6097131f67809dfc0fbe31209d66139d04a6`**, whereas R081 hand-reviewed State writeback library SHA is **`d5c10fbdcb1a976e888a2ddb2bcccd0b66febc10e959e044d141ad2760b63fa0`**. The whole-npubin identity establishes which codegen inputs explain the original objects; it does not establish that two differently hashed SDK libraries implement the same writeback ABI. The caller wrappers being identical also does not establish that library premise. This is an evidence identity gap, not a confirmed device writeback bug.

Minimum closure: decode/extract the actually linked `c816…` library's relevant State 2D writeback recursive definitions and bind them to its actual byte hash; establish equality to the reviewed R081 definitions/attributes, or manually inspect any finite differences affecting descriptor order, atomic0, scalar/tail/no-op, DMA source stride and exact destination byte span. Reuse the existing actual launch/target/header semantics where unchanged. The actual linked libdevice SHA `9142883f2a38a17980b83c5d1e777744d823ddd4af370674015364dfc7eee11f` already occurs in the prior R079/R080 chain. This needs neither eight new SDK compilations nor new math/TP/UI. Until this bridge is supplied, keep the Asc sidecar pending and preserve the raw false fields.

Asc principal SHA-256 identities: terminal `6d2b5d96b8f147d01fba16882562aef901cb402aa394e274c7221a6e54618d39`; result `7519a4ca0de11556dd8f37173e3527a6567d86282dd3b911a414b8b5ee5fc16c`; rows `9bea159d18e1e96b277914ee2b23ef447215cf0d04a14f293dd2506db4170fe9`; actual runner `69c2f8c44fbbb939b13a8ea8176455c9437d9808696136a8c48967e56cc3f086`; passive child `073b1d3c78e9c5d8c563aea328caad2a73e74b13a3c78d3848ba6bacc46a6451`; original ordinary freeze `718714b13c80b2edea60f65753576ead4aea8a16fd4dd21ec9ce00c0e2ec6b11`. No current Asc profile qualification is covered here.

### Final finite closure: actual Asc library bridge supplied

I subsequently read `preflight/ascend-State-closure-receipts-v1/State-closure-input-v1/run.py` and the actual `runs/State-closure-v1/{terminal.json,output/result.json,output/state-writeback.ll}`. Terminal is return code 0 / 8.287888251 s. The actual runner checks the retained `c816…` library bytes against all eight original AIV codegen inputs, then uses the original `llvm-extract-15 --recursive --rfunc=^_mlir_ciface_store_ubuf_to_gm_[12]d_int32_t$` roots. This is passive extraction, not another SDK kernel compilation. I verified its nine indexed regular members and rejoined all eight library/receipt hashes to the actual codegen receipts already examined.

The actual closure SHA is `f0a994d665633b4179388b24f297bccf80a2bf8bfcd89c555b3e45ddf8f8f8e6`; the prior R080/R081 reviewed closure is `baeb0d48d5a3c80b1e00622282722e4f28b3eee47efc8585999a21c85306a6e2`. I independently diffed the complete texts. Only two lines differ: the comment `; ModuleID = ...` and `!0`'s producer string (`AscendNPU-IR Compiler 202602 ...` versus `2026-04-25T15:46:25+08:00 ...`, with the same clang/flang revision). The `!0` node is referenced only by `!llvm.ident`; no instruction, function attribute, target layout/triple, module flag, transfer parameter, or control flow changes. Removing exactly those two lines makes the complete texts equal. All **27 function definitions and 9 attribute groups** are unchanged. Producer identification and a ModuleID comment do not alter the reviewed State transfer semantics. The receipt's stricter `complete_closure_equal_ignoring_ModuleID=false` is accurate and remains unchanged; this conclusion explicitly accounts for the additional producer-string difference.

This closes the actual-library identity gap described above. Combined with the eight whole-object identities, actual wrappers/actors/descriptors and original math/host-once/guard receipts, **Asc ordinary-supplement8 can also receive the finite `actual State writer under reviewed SDK ABI` sidecar**. The SDK no-op, source-stride, scalar/tail and exact GM byte-span conclusions from R081 apply to these identical definitions. No confirmed State writer defect or remaining substantive ABI verification gap was found in these eight objects.

Closure terminal SHA: `d04529b50898cca120ff51656f32756d1578c737dd769de5e2ccba10edde8cdb`; result SHA: `5b403e153c01606d438df58a5eff4c4e37cc356538acec98beed469f1345b347`; actual extraction runner SHA: `792686adff249d3ab2cd8da2fdb26f2bbedbf50c71f77462cb0f96b129a12022`. Candidate HEAD observed during this review: `61e47e0dd16ca6ccea2ee07865110cca7844c50c`; reviewed execution inputs are pinned independently by the checker/runner/object SHA values above.

Final scope is **GCU supplemental ordinary8 + Asc supplemental ordinary8 only**. Derive new limited sidecars; retain historical partial/failed/raw-false records. Existing ordinary32/current96 decisions remain untouched; Asc profile, native boundaries, pipeline and whole-goal acceptance are not granted by this report.
