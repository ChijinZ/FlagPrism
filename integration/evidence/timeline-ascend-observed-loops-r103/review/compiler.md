# R103 limited compiler review: selected LLVM loop brackets

Scope: new `_loop_context` and `selected_loop_bracket` integration in `timeline_ascend_fragments.py`, new `timeline_ascend_loops.py`, and `ascend_loop_rule_cases.py` / `p01_ascend_fragment_observations.py`. This continues the independent compiler review; it does not reopen the prior source-body, reader/tuple, timing or whole-goal reviews.

HEAD at inspection: `b36388ad2fc5584c2f7e9ae8d2803ed65e41e741`; the reviewed delta is uncommitted. Observed working-tree snapshots:

| File | SHA256 |
| --- | --- |
| `timeline_ascend_fragments.py` | `0f8147fd02ba1117f23e77ff61a9d7a621018730174295553f0b41ae5b77e34b` |
| `timeline_ascend_loops.py` | `828b98910792357852324c48b0b543eab541816b3842efb7e46ffaacf50d7e2a` |
| `ascend_loop_rule_cases.py` | `a63954460413afc0765b8f154ec6dafe94b4a054a6629ff51c60aa8c1426b640` |
| `p01_ascend_fragment_observations.py` | `d068e1a154a60eb075d6e5f700e58f4755e79538712e8650a2d5f4a70b954ce9` |

Requested reviewer model/effort: GPT-6.1-Sol / xhigh. Actual resolved configuration is not exposed and is **unknown**. Read no peer report. Performed only source/Git/JSON/text inspection and wrote this report; no product/import/tests/SDK/compiler/device/server/math/TP/UI execution.

## Conclusion and confirmed findings

**No confirmed blocker, major or minor defect was found in the reviewed new loop/context logic.** The implementation supports the stated intermediate fact: conditional on reaching the actual selected begin, every retained indexed LLVM path reaches the paired end before leaving the selected natural loop or traversing its backedge, with residual cycles and unsupported transfers rejected. Its explicit unknowns correctly prevent this from becoming source trip-count, iteration-ID, final native scheduling or exclusive-cost qualification. Final matching source/execution and normal installation remain unverified at this review point.

## Source correctness and limits

- `timeline_ascend_fragments.py:_loop_context` identifies the smallest indexed natural loop containing all supplied instruction blocks, rejecting an equal-size ambiguity. Original and adapted contexts are recorded separately. This is a structural containment fact; it does not identify equal dynamic/source iterations across compilation. The adapted context includes both readers, the actual carrier and all bound members. The original includes the original carrier and its bound original members.
- `timeline_ascend_loops.py:124` walks backward only through a unique-predecessor chain, stopping at multiple predecessors, an outside-loop predecessor, the selected loop's latch/header edge, or the first conditional branch. A branch contributes only the truth value necessarily implied by taking its edge into that chain. Equal true/false successors do not invent a guard fact. This is conservative; it does not infer extra predicates from merely reachable predecessors.
- `_Guards.key` retains stable opaque SSA atoms, keys `icmp` by exact predicate and actual SSA/LLVM-uniqued constant IDs, and canonicalizes only finite scalar-i1 Boolean operations. It does not equate different reloads or solve integer expressions. The Boolean simplifications and three-valued `evaluate` keep both successors when no truth value follows from the necessary fact. No arbitrary solver is needed for this narrow use.
- `_Guards.__init__` conservatively propagates explicit undef/poison dependence through indexed def-use edges. A `freeze` stops that propagation; repeated uses of the same frozen SSA result can legitimately share one branch fact. A directly undefined guard is rejected before its identity or a Boolean cancellation can be used as a selection witness. This is not a claim to analyze all possible LLVM poison/UB sources.
- The iterative DFS (`selected_loop_bracket`, initially lines 150–188) stops at the paired end, rejects unsupported terminal control, outside-loop successors and selected-loop latch→header edges, and detects residual cycles with active/finished colors. Unknown guards explore both successors. Therefore an unknown escape, a bypass to a backedge, or a same-block cycle is not accepted merely because an end is also reachable. This is stronger than the preceding R101 reachability diagnostic, while remaining a typed-index control fact.
- The helper preserves `source_iteration_ids_verified=false`, `trip_count_verified=false` and `native_schedule_qualified=false`. The containing fragment still has `loop_verified=false`; a separately unverified loop bracket does not erase an independently checked fragment-structure fact or turn it into a whole-module pass. `loop_backedge_or_exit_before_end=false` is scoped to the selected, finitely justified LLVM paths, not all hardware executions or engine activity.

## Resource review

The new passes charge the existing `_Index` budget for loop-block scanning, CFG predecessor edges, explicit undef/poison users, Boolean interning/evaluation, instruction links and DFS visits. Guard construction/evaluation has depth 64 limits. Canonical nodes contain flat IDs rather than recursively expanding expression tuples. Undef/poison propagation visits each newly marked value once; its completed cache is only installed after the scan succeeds. The iterative CFG traversal avoids recursion growth. A work/depth failure returns an unverified loop result; it does not become an empty successful path proof. No concrete resource-bound bypass was identified in this delta.

## Tests and actual evidence read

The eight valid LLVM loop cases are well targeted: selected, literal-constant and frozen selection positives; distinct end guard, reversed edge, early loop exit, residual cycle and explicit undef negatives. They are parsed and verified by the actual LLVM15 indexer rather than relying only on edited graph successor lists. Their direct expected-status checks are retained under `-O`.

The local `observations-status-v1.txt` records terminal **0 / 20.205629937 s**, normal/optimized zero, 46 observer summaries, four indexed loop contexts and two repeated-positive loop regions. It has **no** selected-loop rule or native loop cases and is not evidence that the new rule ran.

`observations-status-v2.txt` records terminal **0 / 19.751567783 s** and both modes zero, with the same raw SHA256 `8bc1d954e65efd2d3a2d03e53f6fe0f3d2ddfe6b11cc052b502a543b1572941c`, 46 summaries, four loop contexts, four selected loop brackets and two repeated-positive loop regions. Its eight loop-case outcomes match the expected positive/negative split. Because **all four** loop contexts are selected-bracket checked, the two repeated-positive regions necessarily lie in that checked set for this particular result. These copied status/results were inspected, but a final executed-source/receipt ledger matching the current working tree was not available here; final matching closure is still required.

The observation test compares each observer separately with freshly decoded raw events, including counts, tick sums/extents, epoch/domain, completeness and raw tick units. It checks that missing observations remain absent and that a source-site mismatch or altered raw file is rejected. These are useful occurrence/data-binding checks; they do not synthesize source iteration IDs from interval ordinals.

## Necessary verification gap

Bind the final formatted freeze to complete CPU receipts and the actual-input reports. The inspected current cases additionally include conservative opaque-structure checks for two FCmp predicates, two atomicrmw suboperations and an indirect target; the v2 copied result predates those additions. This is a same-source receipt closure, not a new matrix or SDK/device replay requirement. Normal wheel/automatic installed entry-point qualification is also not established by the source-loaded v1/v2 evidence and is not claimed here.

## Optional / schema boundary

The observation fixture counts repeated-positive loop regions and selected brackets separately. The actual v2 result's 4/4 selected coverage makes the intersection unambiguous, so this is **not** an open actual-result defect. For future partial coverage, directly reporting/counting regions having both properties would keep a later summary from accidentally joining two different regions. This is a small fixture robustness improvement, not an additional product gate.

The implementer's separate narrow question about missing indexed operation semantics has a conservative answer within the existing structure-identity contract: FCmp without its predicate, atomicrmw without its suboperation, and an indirect/otherwise unknown call target should remain opaque in `_signature`. The inspected current source does refuse those cases. That does not request complete floating-point/SSA equivalence, an enlarged native indexer or new ISA analysis; actual matching execution of the added refusals remains part of the final receipt gap above.

## Final working-source note

Rechecked the current loop and fragment source after the implementer's v3/v4 update: their hashes remain respectively **`828b98910792357852324c48b0b543eab541816b3842efb7e46ffaacf50d7e2a`** and **`0f8147fd02ba1117f23e77ff61a9d7a621018730174295553f0b41ae5b77e34b`**. The source conclusions above therefore apply to the current reviewed rule, not only an earlier loop draft. No new confirmed code defect was found.

The observation test has subsequently changed to SHA256 **`c19eb192aa18d76c1dfb1c1acd2e489656694a76da2ee2a4fdd177f5c08556a9`**. It now requires a nonempty `repeated_checked_regions` intersection, explicitly reporting each matching function/site and its repeated-positive observer IDs. This resolves the optional future-summary ambiguity at source level. It also adds a small nested/nonmonotonic-interval reference fixture; this compiler report does not independently close the separate observation-store temporal-reference issue.

The implementer reports v3 source QA normal/`-O` success with all 13 native-index cases and v4 in progress. Those new terminal/full-source receipts were not yet independently available in the inspected local evidence, so this statement is progress information, not final matching execution or normal-install closure. A later finite addendum can bind the final formatted rule, these targeted cases and actual reports without rerunning the previous mathematical or SDK matrices. Whole-goal, source iteration IDs/trip count, SSA/value equivalence and final native qualification remain ungranted.

## Final formatted source / CPU / installed closure

Final freeze: **`092017f9ed23a56b508e9167a974dd349b959041`**. Independently read `observations-receipts-v4` and `install-receipts-v2` and verified their **25** and **33** indexed file sizes/SHA256 values respectively; no mismatch. The candidate's final server-formatted source is byte-identical to the v4 executed input:

| Source | Final SHA256 |
| --- | --- |
| `timeline_ascend_fragments.py` | `629e857e8e57830c9b2718c8c2e1cd16756966bceffc75cc00f1f2f118aca3a8` |
| `timeline_ascend_loops.py` | `49567db4a633f6c9f0fb32572c872b8dda9f59f743a43dd8ddf967db1fc23936` |
| `ascend_loop_rule_cases.py` | `6c2f5d3025dd422c71aa4c90db434c5ba8dc64ebbb1a1be389b9d22f1c783c41` |
| `p01_ascend_fragment_observations.py` | `dc50dbf3899a9969b779ac3fc124f99080a696945918ef966395484d6891c091` |

The earlier `828b…` / `0f8147…` values identify pre-final-format source inspections, not the delivered bytes. The final values above are the matching source/installation identity used for this closure.

`observations-v4` is terminal **0 / 20.196588736 s**. Normal and `-O` each pass the eight loop cases and five conservative opaque-operation cases (13 total), as well as the raw-observation checks. Both report 46 observer summaries, four loop contexts/four selected brackets, and the same two explicitly intersected repeated-positive checked regions: AIC site 21 (two observers) and AIV site 31 (four observers). Source iteration IDs/trip/native qualifications remain false. The nested interval reference fixture, absent-observation preservation, wrong-source rejection and altered-raw rejection also report success. This is CPU reinspection of actual retained raw, not another application or SDK run.

`install-v2` is terminal **0 / 90.905437584 s**, with **450** installed wheel members byte-checked and all listed steps zero. Wheel SHA256 is `4cf35fce8fc13b235c122dc55f82bf47c6b32d8e795657f1613a552720c9b363`. The assembly receipt records the exact final loop and fragment module hashes above. Installed store and observation checks both run normal/`-O`; the installed observation results repeat all 13 cases and the same actual two-region/six-observer intersection. Existing matched native/compiler/plugin inputs are reused rather than falsely described as rebuilt.

**The matching final-source CPU and normal-install gaps for this loop delta are closed.** No new confirmed defect remains from this limited review. This does not establish current96 applicability, source iteration IDs, source-exclusive cost, final native scheduling, or whole-goal completion. In particular the AIC/AIV repeated regions share frontend source op 43: they are two actual actor views of one source origin, not by themselves two distinct source regions for the separate qualification requirement. No product/tests/SDK/device execution was performed by this reviewer.
