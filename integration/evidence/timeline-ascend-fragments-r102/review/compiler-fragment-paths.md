# R102 limited compiler review: actor fragment endpoint paths

Review scope: the uncommitted `Profiler/python/flagtree_profiler/timeline_ascend_fragments.py` and `tests/timeline/ascend_fragment_rule_cases.py`, their reused typed index/tuple interface, and the necessary indexer/producer definitions. HEAD at inspection was `405326e6809d09de8a2bbca1412b5a7046a55a2a`; this does not freeze the two new files. The inspected helper snapshot SHA256 was `ab30014b6465fd4b04403ac18dbe98b751884b9953f8bec89044b3cac9612970`, and cases SHA256 was `c34cf9ae372b939cfa870f785945b2fb8883fb3d1975cbe5dcf4c3c91a5ed105`. The helper changed during review to add already-bound local-definition/actor-argument checks; the findings below concern behavior still present in that inspected snapshot.

Requested reviewer configuration remains GPT-6.1-Sol / xhigh; resolved model/effort are not exposed and are **unknown**. No peer report was read. No product, imports, tests, compilation, SDK, device, server, mathematics, TP or UI was executed. Only source/primary-file inspection and this report were performed.

## Conclusion

The intended narrow service is reasonable: identify original operation **structures**, require the actual selected carrier and those structures on every retained reader-to-reader endpoint path, and leave SSA/value equivalence, native scheduling and loop counts unproved. It does not need a complete LLVM/ISA proof framework. Two concrete false-positive cases in the inspected version require repair before its checked status is trusted; one smaller work-accounting issue should also be fixed. No blocker beyond these bounded implementation issues is identified. Repairs discussed with the implementer are not treated as executed or matching until their final source and receipts are available.

## Confirmed major findings

### M1 — opaque indexed types are accepted as complete structural type identity

**Location:** `_signature`, especially the instruction/result and operand `type` dictionaries, initially lines 18–38; `Profiler/llvm/AscendExecutionStructure.cpp`, `Index::type`.

**Trigger:** original and adapted operations have equal opcode/location/other encoded facts but different vector shape or aggregate element structure. The index deliberately represents such types only as a numeric `kind`, without shape or element details. Two different vectors therefore compare equal as dictionaries. `_signature` treats that equality as sufficient to bind the original typed operation structure to a unique adapted candidate and can emit `llvm_observed_fragment_operations_bound`.

**Evidence/reasoning:** the indexer explicitly says aggregate/named types are opaque and rules must not infer their contents. The new signature passes those dictionaries directly into equality; it has no explicit supported-type gate. This is a type-identity omission, independent of the correctly disclaimed SSA/value-equivalence claim.

**Consequence:** the checked row can describe a matching typed operation structure where the actual operation types differ.

**Minimum repair/negative:** conservatively refuse structural matching when a necessary type is opaque, or add only the finite type facts actually needed. A rule-level opaque-vector case must remain unverified; if using actual typed native-index fixtures, use two valid operations with different vector shapes/element types that currently collapse to the same index dictionary. The implementer's proposed initial restriction to explicit integer width, pointer address space and void is a sufficient conservative route for the present target; other regions can stay unverified with their raw data retained.

### M2 — a member before the carrier can be accepted as a required member after it

**Location:** `_Paths` and the candidate/mandatory tests, initially lines 46–80 and 149–169.

**Minimal valid control graph:** global entry `E` branches to `B` or `X`; `B` contains the begin reader and goes to `M`; `M` contains the unique matching body operation and goes to `C`; `C` contains the carrier and branches to end block `Z` or to `X`; `X` goes to `M`. The cycle `M→C→X→M` has external entries through both `B` and `E→X`, so no single cycle header dominates it; LLVM natural-loop backedge removal does not remove this irreducible cycle.

**Evidence/reasoning:** from begin `B`, both `M` and carrier `C` occur on every endpoint path. Thus `mandatory(begin,end,M)` and the carrier test pass. `reach(carrier,...)` reaches `M` through `C→X→M`, so the candidate filter also accepts `M`. Nevertheless the actual endpoint path `B→M→C→Z` has **no body member after the carrier**. The implementation's claimed placement (“after the same actual carrier and before the end”) is false on that path. No SSA or machine semantics are needed for this counterexample.

**Consequence:** the rule can report a bound original post-carrier operation when its only obligatory occurrence is before the carrier.

**Minimum repair/negative:** require the matched member to be mandatory from **carrier to end**, not only from begin to end, or reject residual cycles in the finite relevant corridor. The former directly closes this placement error without building a full CFG proof service. Add the above two-entry-cycle negative using a consistent control graph; retain a straight-line positive. Loop/trip/iteration qualifications must remain separate.

## Confirmed minor finding

### m1 — signature operand work is outside the work counter

**Location:** `_signature` and its invocation for every candidate, initially lines 20–23 and 156–162.

**Trigger:** a valid bounded actor has many high-arity calls in a source fragment. Each candidate comparison is charged once, but rebuilding its signature traverses/allocates a tuple for every operand; equality can also traverse those operands. The native index's 16 MiB input, 32 MiB output and one-million structural-work bounds still allow hundreds of same-sized calls containing hundreds of operands. Repeated candidate scans can consequently perform tens or hundreds of millions of operand operations before the new helper's one-million work counter is exhausted.

**Consequence:** the existing visit budget does not bound this newly introduced inner work; a bounded index can consume much more CPU/allocation effort than the counter suggests. This is not a demonstrated wall-clock timeout or product failure.

**Minimum repair/negative:** charge operand extent before signature construction/comparison, or cache bounded signatures while charging their potentially long comparisons. Exceeding the unchanged work limit should leave the affected region unverified. A compact high-arity fixture with a deliberately tight work allowance can validate that the guard accounts for the inner work; no new mathematical matrix is needed.

## Necessary verification gaps

- The three findings need final matching source and targeted negative results. The seven inspected fault cases cover input identity, selected-source membership, direct callee mismatch, missing carrier, a bypass edge and declared body length; they do not cover opaque type identity, the residual-cycle placement case, or operand work accounting.
- The local R102 poll text files inspected are poll **commands**, not terminal/result output. Initial AIC/AIV counts communicated by the implementer are not a substitute for matching final receipts. This review does not claim the in-progress v2/v3 source passes, a normal installation, or automatic product entry-point integration.
- The outer reader must continue binding freshly indexed original/adapted bytes to the actual handoff and actor ABI. Comparing the graph's recorded digest with a supplied digest is an interface check; it does not authenticate an arbitrarily edited JSON graph. Existing fault tests intentionally edit that graph to test rule behavior. This is an existing external binding precondition, not a request for a new cryptographic or SSA framework.

## Correct limited behavior and optional clarification

The delete-node reachability test is a suitable finite way to show that a member cannot be bypassed on paths that **do reach the paired end**. It does not claim paths that exit or never reach that end have completed the source body. Removing natural-loop backedges conditions the result on the retained graph; it neither counts iterations nor certifies the source loop. Matching remains deliberately structural: unbound external SSA inputs, physical execution/completion and exclusive cost remain unknown.

The exception for debug locations is confined to the two exact `llvm.hivm.SET.FLAG.IMM` / `WAIT.FLAG.IMM` callees and retains the encoded literal operands/callee; it does not waive locations for arbitrary helpers. Original source-body derivation stops at the next actual carrier or terminator and is compared with the declared extent. Function-local carrier uniqueness and a complete tuple are checked before a row can succeed. Rows for other semantics are not relabeled as source fragments. There is no top-level “all regions/module checked” status; a budget error in a later per-region search does not invalidate an earlier independently complete per-region result.

One optional schema clarification is advisable: `selection_verified=True` here follows frontend selected-source membership, not the runtime program/actor guard that the tuple layer explicitly leaves unproved. Name or document that scope explicitly before a later consumer combines the facts; it must not silently upgrade the tuple's runtime-selection unknown. No native/source-exclusive/loop participation/engine-busy qualification follows from this helper or from a positive observed interval.

## Repair-progress addendum: source inspection only

Subsequently read helper SHA256 `681338184651bf698c5573cfeeb87a43a4e37baab47af82c84f122d04755a4e3` and cases SHA256 `19b37935dfbc8b3726772dc187bd77bb7915e471ad75c77d59fc3359b53dc664`. These are working-tree snapshots, not a matching executed freeze.

- **M2 source repair is correct for the reported trigger:** each matched member now additionally satisfies `mandatory(marker,end,member)`, while retaining the begin→end obligation. The new valid LLVM fixture exactly encodes the two-entry irreducible cycle above; it checks that LLVM reports no natural loop, begin→end requires the body, and carrier→end does not. This addresses the concrete placement flaw without requiring a global acyclic graph.
- **m1 source repair addresses the reported hidden inner work:** `_signature` now charges twice per operand before constructing/comparing signature components. The new valid 128-argument call fixture leaves only ten work units and requires a budget rejection. The intended one-million budget is unchanged.
- **M1 is partly repaired:** `_complete_type` accepts the explicit integer/pointer facts and the complete LLVM15 scalar floating/void kinds, and rejects opaque result/operand types. The two valid vector add fixtures test this rejection. One occurrence of the same issue still requires correction in the inspected snapshot: the GEP `element_type` field also enters the signature but is not passed through `_complete_type`. A GEP with complete pointer/integer result/operand types and opaque vector/aggregate source element type can still collapse distinct typed structures. Apply the same gate when `element_type` exists and add an opaque-source-element GEP negative; no new index representation is needed.
- **Selection labeling is clarified:** successful rows now use `frontend_selection_verified=True`; rows explicitly retain `runtime_selection_guard_verified=False`. The earlier optional ambiguity is resolved at source level.

No new test or actual-input success is claimed for these repair snapshots. Final formatted source, invocation of the new edge fixtures, actual-actor results and terminal records remain to be matched in a later finite addendum. The original findings/history above are retained.

## Final matching closure: `00d8104`

Read the final helper/cases in candidate commit **`00d810450e92f827b9205b434f26865ac0bfaa76`** and `run-102/preflight/phase-receipts-v1`. Independently checked all **123** indexed file sizes and SHA256 values: no mismatch. Candidate helper and cases are byte-identical to the actual `fragments-input-v5` inputs, including the final formatting:

| Source | SHA256 |
| --- | --- |
| `timeline_ascend_fragments.py` | `c55720ccf49a3342c84b4dacfc22a3f60d8ebc5f056b526a9bf97d9afc466f6a` |
| `ascend_fragment_rule_cases.py` | `a1a53f7ff7d705bb6d8122334f8034acbe1947a3d54258cd20320ac1ac4eb705` |

**M1, M2 and m1 are closed at the reviewed helper's source and matching CPU-execution scope.** The final signature additionally applies `_complete_type` to a present GEP `element_type`, closing the remaining M1 omission. Result/operand/source-element opaque types cannot obtain a structural identity. The carrier→end mandatory check and operand work accounting remain present. Frontend source selection and the still-unproved runtime selection guard are explicitly separate fields.

`fragments-v5` is terminal **0 / 20.657926982 s**, with both normal and `-O` child return codes zero and the reported helper SHA exactly matching the candidate. The runner actually invokes `check_native_fragment_edges`; its valid LLVM module passes the existing LLVM15 IRReader/Verifier and contains the irreducible-cycle, vector, opaque-GEP and high-arity functions. The retained indexed cycle has no natural loop, as required by the original M2 counterexample. Both modes report rejection of all four targeted groups:

- `irreducible_carrier_after_body`: the begin→end requirement alone passes in the fixture, while the required carrier→end body requirement fails.
- `opaque_vector_shape_and_element_type`: both different opaque vector structures are refused.
- `opaque_gep_element_type`: the GEP source element cannot bypass the supported-type gate through an otherwise complete pointer/integer signature.
- `high_arity_signature_work`: the actual 128-argument call exhausts the deliberately remaining ten work units and is refused.

The same two modes also reject all **14 actual-index fault applications** (the seven previously described faults applied independently to AIC and AIV). They retain **5/7** checked AIC fragments and **6/8** checked AIV fragments. The remaining two in each actor are explicitly unverified for ambiguous operation candidates; their status is not upgraded by successful neighboring regions.

The actual original/adapted input digests in these reports equal the already reviewed R101 public q05 actor digests. In particular, AIC source op 43 / site 21 binds original carrier 197 and members 199 (`icmp`) and 200 (`mma_tile_half_to_float`) to adapted carrier 2127 and members 2129/2130, between readers 2124/2141. The AIV source op 43 / site 31 binds its five actual flag/cast/barrier/vector-call structures between readers 2807/3105. Both keep `source_value_equivalence_verified=false`, `runtime_selection_guard_verified=false`, `loop_verified=false` and `native_schedule_qualified=false`. This is the stated structural, observed-endpoint-path fact, not a newly claimed SSA/native or iteration-count result.

`format-v1` is terminal zero and records the same helper/cases SHA values; the format receipt covers seven files, but this addendum only reviews these two original-scope files. The successful mode logs retain the non-fatal `npu-smi info` availability line; their explicit runner steps and terminal records are zero. Earlier terminal/results remain historical records, not silently replaced.

No remaining confirmed defect from this limited review is open. **Normal installed execution, the new automatic store/entry-point integration, and any source/native/loop or whole-goal qualification remain outside this closure and pending separate review/evidence.** No new products, tests, SDK tools, servers or devices were executed by this reviewer.
