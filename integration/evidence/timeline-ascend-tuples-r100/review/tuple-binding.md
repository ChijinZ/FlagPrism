# R100 finite review: Ascend LLVM tuple endpoint association

Requested reviewer configuration: GPT-6.1-Sol / xhigh; actual resolved model/configuration unknown. Reviewed freeze: `18abd94322e39ef7e0886515b07da98df1ca3314`, Git verified. Helper SHA: `b5131fce115940f244903afc63b6a93c4705078b749e87447490745275d39c7c`.

Scope: the new `timeline_ascend_regions.py`, `ascend_record_rule_cases.py`, the final LLVM README explanation, and the primary phase V2/V3 receipt/input bindings. This was read-only source/Git/text/stdlib JSON/SHA work. No product import, checker/test execution, server connection, SDK/device run or peer review was used. The two findings below are static counterexamples; this reviewer has not executed them.

## Result

Two necessary issues remain in the reviewed freeze: discovery can miss an equivalent computed descriptor when deciding tuple uniqueness, and nested expression sorting can expand a compact SSA DAG exponentially outside its work budget. Both concern the finite association routine itself. Neither finding requests selection/body/loop/public/native qualification or a complete writer proof.

## Confirmed major findings

**M1 — Equivalent constant descriptors can evade duplicate discovery.**

- Location: `Profiler/python/flagtree_profiler/timeline_ascend_regions.py:196`, where discovery uses only `index.literal(store_value_id)` and skips nonliteral SSA values; compare the implemented finite constant arithmetic in `_Index.expr` at lines 82–108 and the final single-candidate decision.
- Trigger: reuse the existing `two_complete_tuples` negative, but make the second tuple's descriptor field an actual unflagged `add i64 <same descriptor>, 0` instruction. Its seven other fields and commit expression can remain unchanged. This is valid LLVM arithmetic and the exact same descriptor value; the rule already understands its constant normalization.
- Evidence/reasoning: the second field-0 ID belongs to an instruction, not `self.constants`, so `index.literal()` returns `None`. Discovery immediately skips it. The existing first complete tuple remains the only recorded candidate for that site, even though the same finite constant semantics identify a second complete tuple. The current duplicate test copies the literal operand and therefore does not cover this variant.
- Consequence: `llvm_tuple_endpoints_bound` can be returned using an incorrect unique-tuple assumption, contrary to the documented ambiguous-tuple downgrade and the existing duplicate negative. This finding does not require interpreting arbitrary dynamic descriptors or proving every writer effect.
- Minimum correction/verification: include descriptors provably constant under the already implemented bounded expression semantics in candidate discovery, or otherwise make that finite case explicitly unverified. Add this one duplicate variant to the existing real-graph fault helper and require rejection in normal/`-O`. No broader SSA/ISA machinery is needed.

**M2 — `repr` sorting can defeat expression resource limits.**

- Location: `_Index.expr` at line 107 (`terms.sort(key=repr)`); the commit normalizer at line 241 also sorts nested expressions with `repr` and must share the corrected bound.
- Trigger: a compact valid i64 SSA chain starting with an opaque runtime value `x`: `v1 = add x,x`, `v2 = mul v1,v1`, `v3 = add v2,v2`, then alternate add/mul. Reference the final value in an examined GEP offset or recorded commit input. All arithmetic is unflagged, within the current supported semantics.
- Evidence/reasoning: each level has two terms and depth can remain below 64. Caching stores a shared expression DAG and work charging is roughly linear in the number of definitions. Alternating operators prevent same-operator flattening, but `repr` recursively expands both references at every level: its text grows as `2**N`. This allocation/sorting work happens without corresponding budget charging. Neither the local 1,024-term cap nor the million-unit counter limits that expansion before it occurs.
- Consequence: a small, native-verifiable actor input can cause disproportionate CPU/memory use or fail through allocation rather than the explicit bounded-analysis outcome. This affects the internal component before any future public integration.
- Minimum correction/verification: bound cumulative expanded expression/sort-key work before materializing keys, or use genuinely bounded interned structural keys. Cover both sort sites and any analogous structural expansion. A targeted shared-DAG fixture should demand an explicit budget rejection before large text is allocated; it need not actually exhaust host memory or run on a device. Existing 97-tuple positives can be reused for regression.

No confirmed blocker/minor is separately identified. Both major findings were sent to root with their minimal constructions; no implementation file was changed by this reviewer.

## Positive scope and direct evidence

The routine explicitly takes the declared actor function and trace argument index; it does not guess a definition or final pointer. It checks the indexed global pointer, eight volatile non-atomic i64 stores, one typed GEP root with consecutive offsets, site/semantic descriptor, actual marked side-effecting SYS_CNT call identities, direct tick or two-edge tick/zero PHI, and its finite commit expression. Budget exhaustion during discovery is rethrown rather than converting an earlier checked prefix into a unique result. Returned selection, source body, actor identity, loop and native fields are false as documented.

These are endpoint-association facts only. I did not treat absent selection/body/actor/loop/public machinery, intervening writer effects, or complete native scheduling as a falsely completed gate in this review.

Read and size/SHA-verified both evidence indexes: `preflight/phase-receipts-v1/phase-index-v1.json` has 92 matching entries; `phase-receipts-v2/phase-index-v2.json` has 26 matching entries. V2's actual tuple task is terminal 0 / 2.769244435 seconds. The stronger sealed V3 task is terminal 0 / 2.769557723 seconds, with the same helper SHA and normal/`-O` results:

| Exact retained actor input | Sites bound |
| --- | ---: |
| q01-AIV | 20/20 |
| q03-AIV | 22/22 |
| q05-AIC | 22/22 |
| q05-AIV | 33/33 |

The 97 total positive associations and eight existing semantic negatives pass in both modes. The negatives include start/end swaps, wrong commit, missing field, wrong pointer, wrong semantic, duplicate literal tuples and interrupted uniqueness discovery. They do not contain M1's computed descriptor or M2's shared-DAG expression.

I read V3 `tuples-input-v3/probe.py`. It hard-binds the original R099 native-index receipt SHA `db9199e99367b8c36b8b70ad15d618b1163d5d31ffbc85928e345db5618c5092`, then verifies each graph SHA, actual actor-input SHA, graph input SHA and compiled artifact's adapted LLVM bytes before applying the rule with the recorded actor ABI. That is stronger than inheriting an unsealed cache status. It supports these four retained inputs only, with `device_executed=False` and `source_loop_qualified=False`; it is not current-96 or whole-goal qualification.

## Remaining verification and optional scope

The minimum remaining work is the two targeted corrections/negatives above, followed by the same bounded existing positive/fault checks against the actual corrected source identity. No new mathematics, clock, SDK/device, Trace Processor/UI or broad matrix is requested. Optional expansion: none. Future public integration and complete writer/source/loop/native qualification remain outside this delta's advertised result and are not additional findings here.

## M1/M2 exact-source closure addendum

Both findings above are now closed for this finite internal component. This addendum supersedes their open status at the original `18abd94` freeze; the original findings and V3 evidence remain preserved as history.

Reviewed corrected freeze: `25c76ee978715ae6229af5e2f5e1b1fe16a14ccd`, verified by Git with a clean working tree. Exact helper SHA is `15eeb9e91036548d6c9324eabe4a4c8c1b6072b16c0d1141a9f7df8e5b857482`; fault-case SHA is `3d9694c9a43c7bbec8c593ddc9f4a1a7ef338bc396ff7a93fbc067e77b8d924b`. Both are byte-identical to the formatted inputs retained in `preflight/phase-receipts-v3/tuples-input-v4/`.

**M1 closure.** Candidate discovery now calls the existing bounded `expr` normalizer and recognizes a constant descriptor computed by supported arithmetic, including the reported `add(desc,0)` case. A marked end-field hint also associates an opaque/flagged descriptor window with its possible site so it contributes an unverified candidate instead of disappearing from uniqueness. That hint only downgrades unsupported input; passing still requires the actual descriptor/semantic and complete tuple checks. The two new `duplicate_with_computed_descriptor` and `duplicate_with_opaque_descriptor` faults both return unverified in both tested modes. This closes the reported duplicate-discovery hole without introducing a general dynamic-descriptor proof.

**M2 closure.** Both former `sort(key=repr)` paths now use `index.sort_terms`. Before materializing a sort key, it sums cached expanded-node size estimates, applies a 32,768-character per-node limit and an 8 MiB cumulative key budget, then invokes `repr`. Cached compound expressions retain the estimate. The bounded leaf estimate relies on the declared fresh native-index ID/literal bounds; it is not a claim about arbitrary unvalidated Python objects. Commit normalization uses the same gate. `_BudgetExceeded` remains global, so an interrupted later candidate cannot return an earlier unique prefix. The added 24-layer alternating add/mul DAG fault reaches `Actor expanded expression budget exceeded` in normal and optimized runs. This specifically tests early rejection rather than deliberately exhausting host memory.

Read `preflight/phase-receipts-v3/phase-index-v3.json`: all 26 listed files match local size/SHA. `runs/tuples-v4/terminal.json` records terminal 0 / 3.570416604 seconds. Both normal/`-O` results bind the exact corrected helper SHA and retain 20/20 + 22/22 + 22/22 + 33/33 = 97 associations on the same four actual retained actor inputs. Each mode passes all 11 targeted negatives, including the original eight and the three new computed-descriptor, opaque-descriptor and shared-DAG cases.

The V4 probe is byte-identical to the V3 sealed probe already read above: it retains the hard binding to R099 receipt `db9199e99367b8c36b8b70ad15d618b1163d5d31ffbc85928e345db5618c5092` and the graph/input/compiled-artifact checks. Thus the new positive results are tied to the corrected helper and those exact inputs, not inherited from old V3 status. The negative mutations are CPU structural checks on a retained real graph; they are not new SDK/device evidence.

No additional confirmed defect or necessary verification gap is identified in this limited correction review. No new execution was performed by this reviewer. Closure is confined to M1/M2 and the internal `llvm_tuple_endpoints_bound` association component; it grants no public integration, selection/body/actor/loop, complete writer, native scheduling, clock or whole-goal/current-96 qualification.
