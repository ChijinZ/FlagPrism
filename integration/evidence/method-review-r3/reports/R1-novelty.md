# R1: Closest prior, inheritance, and Operational Systems contribution

Calibration: NOT_CALIBRATED. Independent, bounded review of the supplied round-3 candidate; no earlier reviews, dispositions, live journal, or peer outputs consulted. No hardware access, installation, profiler execution, or candidate edits. Only this report is written.

## Assessment

**A plausible OSDI Operational Systems contribution exists at the stated scope. I identify no blocking or major novelty/contribution defect in this candidate.** The contribution is implementation-informed public knowledge about making a selective offline profiler trustworthy in these compiler/SDK environments, supported by concrete failures and useful retrospective decisions. It is not a new general theory of heterogeneous profiling, a timing-accuracy advance, or evidence of production impact. Acceptance remains uncertain: the breadth of interest and significance of this bounded experience are program-committee judgments.

The current abstract, contribution bullets, evaluation decision table, and engineering lessons make that narrower contribution assessable from the paper itself. In particular, the paper no longer requires the reviewer to equate three adapters with novelty, infer local fidelity from whole-task overhead, or accept the Study's richer probes as final-service features. The structural GCU clue is useful even though its selected store duration is not decisive. The Ascend producer-step intervention retains qualitative support under both observation modes; the output-tile intervention relies on cardinality and independent task timings. This is a coherent diagnostic service with explicit refusal boundaries.

The official [OSDI 2027 CFP, Submission Tracks](https://www.usenix.org/conference/osdi27/call-for-papers) permits contributions that deepen public understanding or validate known techniques in new environments without requiring novel research ideas. It still requires significant, compelling systems knowledge and a paper that stands alone. I apply those criteria, without adding a production-user quota or requiring a port of another tool.

## Frozen inputs and verification

I read the packet, manuscript sections, public workflow documentation, relevant implementation, retained technical evidence, and primary overlaps. I independently checked every manuscript/documentation hash in `method-review-r3/source-manifest.json`, plus its manuscript PDF hash: all match. Runtime is `a9a28ba258fb95056447c451de262824b5f04392`; release documentation is separately pinned `ff68f1d`. I do not promote historical hardware captures into final-runtime performance evidence or independently certify the full 469-test campaign.

Read-only examination of original data reproduced these facts:

- `artifacts/method-run/enflame/cooperative4-vector-publication-before.tar.gz`: archive hash `bbaa004719f023569295234541c3fb687b4e908683307b8dc1fb2b7363f7552e`; embedded raw bytes match their retained hash. All 59 records have words 4–15 zero; first record is `[7,8,1,0,0,...,0]`.
- `artifacts/method-run/ascend/round2/origin-source-manifest-extracted/round2-origin-mix-r1/capture/ai/cann_native_tasks.json`: four canonical tasks, four associated tasks, four retained dispatch-context views, and unverified clock alignment. This supports the illustrative eight-versus-four counting counterexample; it does not demonstrate a measured legacy importer failure.
- The two original `artifacts/method-run/enflame/round2/root-extracted/i3-evidence/round2-softmax/w{4,1}/test_public_softmax_organizati0/` inventories and bundles have distinct binary IDs, independently contain store site 29, expose work-item counts 4/1, and retain one observation each with zero drops and passing mathematical/input/canary checks. A shared numeric site ID does not establish cross-binary identity.

I inspected the retained counterexample scripts without executing them because they write preparation outputs. I reproduced the relevant reads inline without writes.

## Closest prior and inherited mechanisms

| Primary anchor | Overlap already established | Candidate's defensible increment |
|---|---|---|
| [KPerfIR](https://www.usenix.org/system/files/osdi25-guan.pdf), §§4–5, especially §5.2 and §5.3 | Compiler-associated regions/iterations, bounded recording, hidden scratch storage, AMD collaborative publication, and asynchronous-wait distortion with conditional replay correction are prior. | The GCU failed-record ownership case and concrete repair, plus qualified Ascend observations and SDK association, are implementation/qualification results in different execution environments. They neither discover these general problems nor supersede the replay correction. |
| [Proton official CGO abstract](https://2026.cgo.org/details/cgo-2026-papers/23/Proton-Towards-Multi-level-Adaptive-Profiling-for-Triton), and [author HPCA slides](https://www.jokeren.tech/slides/HPCA25_slides.pdf), PDF pp.10–11,21–30 | Multiple vendors, selective/custom metrics, compiler-linked instrumentation, generic/target-specific dialect lowering, configurable recording, and fine-grained traces are established foundations. | Candidate-specific compiler/SDK boundary handling and its tested limits; not the generic interface, pipeline view, or instrumentation architecture. |
| Retained `pasta-cgo26-arxiv-v1.html`, §III-G; [primary version](https://arxiv.org/html/2602.22103v1#S3.SS7) | Normalization of semantically equivalent events and timing metadata, with specialized handlers retaining device-specific features. | Actual compiled-actor/source relationships and evidence for invocation association at the evaluated boundaries, rather than semantic normalization itself. |

The KPerfIR comparison is especially important: `paper/sections/08-related-work.tex:13–31` explicitly credits both nearest overlaps and limits the new claim. This is materially better than an argument that prior tools supply only coarse counters. The implementation also visibly retains Proton dialect/runtime infrastructure and Debugger instrumentation infrastructure; `paper/sections/05-implementation.tex` credits these foundations instead of claiming a new IR is the contribution.

Proton full-paper access remains incomplete. I read the official abstract and an author slide deck; the other retained LLVM slide URL timed out through the web tool. These materials establish positive overlap, not absence of any unpublished-in-slides mechanism. No exclusivity conclusion rests on missing access.

## Supported claim → implementation → evidence

**Publication correctness is a separate obligation from operator correctness.** `Debugger/lib/Instrumentation/Passes.cpp:3021–3047` repeats a full 16-word record per work-item ownership slice for the explicit vector alternative. Its `emitDynamicTimelineStores`, particularly `:3138–3156`, emits scalar words by default inside the selected-writer branch. This directly addresses the retained partial-word counterexample. `paper/sections/07-experience.tex:11–29` states the failure, bytes, repair, and reusable one-versus-several-worker validation. The increment is concrete and technically nontrivial despite familiar general principles. No concurrent release/acquire guarantee follows from a final tag checked after synchronization.

**Invocation association crosses two real boundaries.** `integration/patches/ascend/patch_launch_receipts.py:61–86` queries last task first on the actual launch worker and retains original query statuses. `Profiler/python/flagtree_profiler/cann_joint.py:150–173,250–385` checks context membership, explicit compute `globalTaskId`, capture/worker identity, uniqueness, and rejects ambiguous compound dispatches. This is substantive integration logic, not merely schema renaming. `paper/sections/04-design.tex` explains the separate caller/worker and dispatch/compute boundaries; `07-experience.tex:31–52` gives the four-launch counterexample and invariant. Source identity and clock alignment remain separate.

**Readiness/source relationships are qualified compiler evidence.** `ascend_hivm.py:17–110` validates retained source/manifest/LLVM bytes and enclosing completed compilation facts. `:113–267` extracts typed set/wait sites and emits a channel only for a unique cross-actor pairing; it explicitly leaves dynamic generation and clock alignment unestablished. This supports the limited static channel claim, not bespoke dynamic buffer/iteration pairing or complete source attribution. `execution_enflame.py:197–215` likewise describes compiler SSA ownership and partial origin relationships rather than claiming dynamic utilization or exclusive cost attribution.

**Diagnostic utility is narrower than precise measurement.** `paper/sections/06-evaluation.tex:150–243` contains the public evidence-to-decision table and binary-scoped worked request. `Profiler/docs/semantic_profiling.md:326–382` supplies inventory inspection, exact selection, command, outputs, and discovery-cost caveats. `integration/evidence/enflame-diagnostic-20261015/decision-chain.md` connects the structural clue to independently retained recovery and the two-worker control. `integration/evidence/ascend-wait-fidelity-20261015/README.md` and the paper's paired-mode table reject precise local fidelity while preserving the first intervention's direction. The final service provides useful selective diagnosis; the evidence does not establish automatic discovery, improved general replay correction, engine occupancy, or broad low overhead.

## Findings and finite repairs

### N1 — Intro's NVIDIA reference can obscure the credited cross-vendor overlap

**Severity: Minor. Class: expression gap.** Anchor: `paper/sections/01-introduction.tex:40–42`, versus the specific AMD acknowledgement at `08-related-work.tex:13–24` and the primary KPerfIR/Proton anchors above.

The sentence limiting discussion to NVIDIA implementations can sound as though AMD evidence is excluded from the contribution comparison. The later related-work paragraph correctly includes it, so this is not a false novelty claim or missing technical result.

Finite repair: clarify that NVIDIA is the study's optimization starting point, while the closest-prior comparison includes existing AMD mechanisms. Validation: reread the introduction and related-work paragraphs together; no hardware or new tool comparison is needed.

### N2 — Contribution is clearer in the examples than in the mechanism names

**Severity: Minor. Class: expression gap.** Anchors: `01-introduction.tex:72–96`, `06-evaluation.tex:150–243`, and `07-experience.tex:11–67`.

“Execution manifests,” “typed dynamic observations,” and “invocation reconstruction” are broad labels with substantial inherited territory. The paper now gives enough concrete content to support them, but readers can still initially interpret them as architectural novelty. This is a presentation risk, not a structural contribution deficit.

Finite repair: add one compact sentence to the contribution framing stating that the added public knowledge is the three demonstrated trust failures, the concrete implementation responses, and the diagnostic decisions that survive qualification. Preserve the existing explicit inheritance and retrospective labels. Validation: each contribution sentence should point to an existing counterexample, implemented response, and supported inference; no new feature catalog is necessary.

## Decision boundaries

Functional usability is supported in the finite, documented backend regimes; arbitrary instrumentation and clean-source packaging guarantees do not follow. Diagnostic utility is supported by structural explanation and qualified intervention decisions. Timing accuracy and production benefit are not established and are not required to rescue the scoped claim.

There is no demonstrated structural deficit requiring more hardware, new users, a new backend, or an automatic optimizer. A finite text-focused iteration can address the identified concerns using existing code and evidence. The unresolved Proton full-text comparison limits exhaustive novelty certainty; the current nonexclusive Operational Systems positioning can remain honest without asserting feature absence. A stronger claim of uniquely new architecture or precise causal timing would require additional unavailable comparative/fidelity evidence and is not justified by this review.
