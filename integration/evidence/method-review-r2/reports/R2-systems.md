# R2 systems review: practical diagnostic service and Operational Systems contribution

Reviewer status: NOT_CALIBRATED. Independent read-only assessment of runtime `a9a28ba258fb95056447c451de262824b5f04392` and the packet's exact manuscript. No earlier reviews, dispositions, live journal or peer outputs were consulted. No hardware experiments were run. I checked actual implementation, retained raw bundles, source manifest and primary literature; this is not an independent re-execution of numerical or timing experiments.

## Overall judgment

**A plausible OSDI Operational Systems contribution exists under the actual, selective offline diagnostic scope.** The candidate is substantially more than three adapters or a common event vocabulary. Its strongest contribution is implementation-informed knowledge of three boundaries: logger ownership versus kernel ownership, invocation identity across worker/SDK contexts, and local diagnostic fidelity versus whole-task perturbation. The code makes these boundaries operational, and the evidence includes counterexamples rather than only successful traces.

**The current manuscript merits major revision, not a structural-contribution rejection.** It is not submission-ready, including obvious drafting placeholders, but I do not find an intrinsic requirement for production deployment, a production-user quota, another backend, or a new profiling IR. The [OSDI '27 CFP, Submission Tracks](https://www.usenix.org/conference/osdi27/call-for-papers) calls for implementation, analysis and experience that expand public systems knowledge; novel research ideas are not mandatory. Its examples do not prescribe a production-user quota. The significance judgment remains competitive and uncertain: the paper must demonstrate what other systems builders learn beyond familiar profiling principles.

The distinctions are important:

- **Functional usability:** supported for pinned environments, declared requests and tested kernels; not a general low-cost profiler for arbitrary operator execution.
- **Diagnostic utility:** supported as a retrospective decision replay in two concrete cases, with independent source-observer-disabled recovery measurements. The GCU diagnosis is primarily structural. The Ascend first intervention has mode-stable qualitative support; the second does not have stable wait-reduction support.
- **Acceptance:** not established by correctness matrices, audit counts or this review. The presently incomplete paper and insufficiently specific prior-work comparison remain material concerns.

## What I verified and credit

The manuscript source hashes all match `integration/evidence/method-review-r2/source-manifest.json`. Runtime implementation files inspected are unchanged from `a9a28ba`; the working-tree semantic-profiling documentation has later edits, so I also read its frozen revision and do not treat those later explanations as frozen implementation evidence. Archive SHA-256 checks matched the packet for GCU diagnostic replay, Ascend source-fidelity and final source-manifest archives. I read selected JSON members directly without extracting or modifying them. I did not reproduce the full independent auditors' work or freshly execute device oracles. Local PDF extraction utilities were unavailable; manuscript assessment used the hash-matched TeX source and frozen figure captions, not a visual layout audit.

### 1. Concrete mapping and honest partial attribution

`Profiler/python/flagtree_profiler/execution_enflame.py:197–209,234–275,285–360,381–404` processes actual `CompiledKernel.asm`, emits binary-qualified sites, symbolic work-item indexing and origin candidates, and preserves partial status. This is useful execution evidence, not merely a backend name. `execution_ascend.py` and `ascend_hivm.py:17–110,129–167,220–268` require retained source/manifest bytes, typed metadata consistency, successful enclosing compilation/job and matching LLVM; readiness is emitted only for a unique typed producer/consumer channel. Missing provenance does not become a verified dependency.

The final Ascend raw bundle (`round2-origin-source-manifest-evidence.tgz`, member `round2-origin-mix-r1/capture/ai/execution.json`) contains one `PIPE_FIX → PIPE_S`, flag-0, AIC/AIV static channel with `dynamic_generation: null` and `dynamic_pairing: not_established`. It also retains verified-origin links with `cost_ownership: not_established`. Its observations contain 232 records across four captures, all associated and locally converted. This supports the manuscript's limited mapping claim, not arbitrary operation-cost attribution. The reported 34 unique/27 ambiguous/13 unassociated origins are a useful boundary, not a failed completeness test.

### 2. Real instrumentation engineering

`Debugger/lib/Instrumentation/Passes.cpp:3019–3048,3050–3057,3139–3153` implements complete-record-per-work-item vector publication and default scalar-word publication under the sole writer. This is a specific answer to the lowering ownership failure. Mathematical correctness alone would miss it. Loss/saturation handling is explicit in the adjacent implementation.

`Profiler/llvm/AscendLateObserver.cpp:44–90,150–207` records repeated dynamic occurrences, separates attempted/committed/dropped counts and brackets existing wait/signal primitives. Semantic selection precedes inserted reads; program selection gates publication after the reads. It introduces no completion barrier to turn issue into engine occupancy. Arbitrary source-site selection and occurrence sampling remain unsupported, as stated in design lines 98–113. These are meaningful but limited mechanisms; not every common request means the same work on every device.

### 3. Invocation identity is more than matching timestamps

`integration/patches/ascend/patch_launch_receipts.py:62–86` queries the actual launch worker immediately after launch and retains original statuses/IDs. `Profiler/python/flagtree_profiler/cann_native.py:49–75,85–98,122–170,193–231` rechecks worker receipts, capture seals, SDK context membership and compute-task foreign-key membership. It rejects a compound dispatch as one source binding. This addresses both cross-thread identity and double counting of mixed dispatch/compute views. `reconstruction.py:20–46,90–111` keeps source identity separate from clock alignment. `profile.py:969–1036,1166–1280` and the hook's `peek/ack` protocol retain recovery evidence before acknowledging captures. This is substantive runtime and lifecycle implementation, not presentation-only schema work.

### 4. The two public-service → decision → recovery chains are real, within limits

**GCU:** `test_enflame_softmax_diagnostic_hardware.py:49–122` invokes the public service with a bounded store-site request and checks actual binary/native association. I read both raw diagnostic JSONs: each contains one associated record and retained passing math/input/canary results; the four-item manifest has two barriers and ten shared-storage static sites, while the one-item manifest has neither. The ownership expression and scratch evidence support testing fewer cooperating work-items. The retained three 30-call batches per configuration provide 1.615–1.621× recovery with the source observer disabled and TOPSPTI enabled. The two-item control retains barriers yet approaches one-item performance. This is evidence for the cooperative-organization intervention, not exclusive barrier cost or measured work-item utilization. Current replay version and historical recovery version are explicitly distinguished in `enflame-diagnostic-20261015/summary.json` and `decision-chain.md`.

**Ascend:** design lines 42–63, evaluation lines 53–94 and the retained wait-fidelity records support actor/readiness/count-based diagnosis. The CSV contains all 120 measured AIV waits. Original producer loop counts 128→16 and header counts 129→17 have independent original-LLVM checks; occurrences are not falsely promoted to induction variables. Increasing BK reduces consumer waits in both all-site and wait-only collection. Independent native recovery is 310.27→164.12 µs. The later output-tile intervention reduces logical cardinality and source-requested loading and reaches 58.45 µs, but its further wait reduction is not stable. Evaluation explicitly refuses that inference. The service does not reproduce the Study's bespoke buffer/iteration identities or conditional shared-clock picture, and does not need them for this limited decision.

## Findings and finite repairs

### W1 — Major: make the contribution comparison specific to the closest already-known failures

**Classification:** expression/evidence gap in contribution positioning; not presently a demonstrated structural deficit.

**Anchors:** paper `08-related-work.tex:4–21`; `07-experience.tex:47–60`; [KPerfIR, §5.2–5.3, Fig. 10, printed pp. 213–214](https://www.usenix.org/system/files/osdi25-guan.pdf); cached PASTA primary HTML §III-G (`S3.SS7`), [primary version](https://arxiv.org/html/2602.22103v1).

KPerfIR already discusses instrumentation-induced asynchronous wait distortion and semantics-based replay correction, as well as a backend-specific AMD collaborative store strategy. Thus neither “instrumentation changes waits” nor “logging needs backend-specific publication” can stand alone as new knowledge. PASTA already normalizes timing/event metadata and exposes vendor handlers. The current related-work section correctly disclaims broad novelty but stops short of explaining these closest overlaps.

**Repair:** compare the actual assumptions and guarantees: GCU tensor-partitioned full-record ownership versus prior collaborative logging; Ascend measured wait redistribution and refusal of unavailable corrections versus KPerfIR's particular replay assumptions; retained worker/context identity versus inherited event correlation. Explain which prior technique can be reused and which environmental fact invalidates a direct assumption. A compact mechanism/assumption/evidence table is sufficient. No cross-device port of a prior tool is required. Validate every comparison against primary text; absence from inaccessible Proton full text is not evidence of absence. The contribution then becomes concrete validation and new failure knowledge in these environments, rather than a generic discovery of profiling distortion.

### W2 — Major: the practical operating regime is narrower than the opening profiling problem

**Classification:** observed implementation limitation plus expression gap; further timing-accuracy claims would have an evidence gap.

**Anchors:** paper `01-introduction.tex:9–15,44–59`; `04-design.tex:149–167`; `06-evaluation.tex:13–25,53–94` and overhead subsection; `07-experience.tex:47–78`; `AscendLateObserver.cpp:168–179`; `ascend-wait-fidelity-20261015/wait-fidelity-audit.json`, measured CSV and minimum-control README.

The implementation gives a developer qualified structural and instrumented-control observations. It cannot generally answer where uninstrumented time is consumed or how engines overlap. GCU has unknown tick frequency and poor all-site compilation; small Ascend RMSNorm remains 60–78% perturbed under wait-only selection; the original fusion wait shifts 77–83% between modes despite low task-level overhead. Host/export/storage costs also make repeated interactive tuning expensive. The minimal zero-tick control does not resolve the wait-error bound. These are not reasons to discard the useful structural decision chains, but they sharply constrain the service's promise.

**Repair:** state selective offline diagnosis and the exact two supported decision types in the abstract/introduction and a compact request/cost/fidelity table. Keep device, host, export and storage costs separate. Treat a stable qualitative mode comparison plus independent intervention timing as decision evidence, not local timing calibration. Make the same boundaries visible when describing the Study's conditional figure. This repair can use existing evidence; no new timer is necessary for the scoped paper.

**Minimal condition for stronger claims:** quantitative uninstrumented wait costs require an independent bound/calibration at the decisive workload scope; cross-actor timelines require actual same-call counter-domain/epoch proof. Neither whole-task ratios, matching frequencies nor zero-tick two-read controls supply either condition. These are unavailable capabilities, not minor wording repairs, if the authors choose to claim them.

### W3 — Major for submission, finite documentation/evidence-presentation repair: expose how an ordinary developer reaches the bounded request and assesses a decision

**Classification:** practical usability evidence/presentation gap, not demonstrated functional failure.

**Anchors:** frozen `Profiler/docs/semantic_profiling.md` public-interface and output sections; `test_enflame_softmax_diagnostic_hardware.py:49–55,80–83,104–122`; `reconstruction.py:179–224`; paper `06-evaluation.tex` diagnostic subsections.

The GCU successful request hardcodes compiler site 29. The report exports substantial JSON evidence and a record table, but the paper does not walk from an initial ordinary kernel to discovering that binary-specific site, choosing safe capacity/mode, finding the ownership clue, comparing the intervention and checking unsupported conclusions. Expert artifact inspection can reconstruct the chain; practical usability beyond that is not yet demonstrated. This does not demand a user study or production adopter.

**Repair:** provide one complete worked public workflow with actual commands, initial mapping inventory, selection rationale, exact output fields and a small excerpt/screenshotted result. Include a changed-specialization check showing that site IDs are re-read, a loss/cost check and the independent native recovery step. A data-only replay against the existing bundle can validate the interpretation; a clean-session run on the already-supported stack would strengthen installation/onboarding claims when authorized. Explicitly call the two cases retrospective replays, as evaluation already does. Do not make their existence imply first discovery by the final public tool.

### W4 — Minor but concrete: unify frozen provenance and completion status in the paper/artifact documentation

**Classification:** expression/documentation gap.

**Anchors:** paper `05-implementation.tex:14–17` calls `1cb15d7` the shared runtime snapshot, while the review manifest pins `a9a28ba`; frozen semantic-profiling documentation ends with static dependency extraction “being completed separately”; the final retained fusion supplies it. `paper/main.tex:30–34`, background and conclusion contain TODOs, and evaluation retains an open metrics TODO.

**Repair:** put the final runtime version beside the historical diagnostic/performance versions and identify which final changes have focused hardware evidence. Update the frozen release documentation to its actual capability status, without relabeling old matrices. Fill the drafting TODOs using established scope; describe unmeasured metrics as unavailable rather than leaving promises. Validate a new source/PDF manifest and ensure the final document is self-contained. These straightforward drafting defects do not negate the method contribution.

## Blocking, structural and external-condition assessment

There is **no demonstrated blocking functional defect in the inspected supported paths**. I did not run all negative contracts, so this is not a correctness certificate. Missing arbitrary selection, shared epochs, low-overhead small-kernel timing, automatic journal resumption and clean-source packaging are explicit limitations rather than silently completed services. Broader usability and quantitative timing claims would be blocked by those limitations; the actual selective offline scope need not make those claims.

The **current submission is blocked by manuscript incompleteness and major contribution/usability presentation work**, all finite. The report's requested repairs do not require production adoption, an extra backend or an externally unavailable paper feature. A finite technical/text/evidence iteration can produce a credible candidate: make the strongest counterexamples and assumptions stand alone, supply the worked workflow, repair provenance wording and retain the adverse results. Stronger calibrated timeline claims would require the external clock/fidelity condition identified in W2, or should remain excluded.

My contribution judgment is therefore positive but bounded: a credible implementation-and-experience paper about trustworthy compiler-assisted operator diagnosis on these pinned stacks, with two useful decision chains and substantial negative operational knowledge. The evidence supports this narrower contribution more strongly than a general fine-grained performance-analysis platform or accurate causal time decomposition.
