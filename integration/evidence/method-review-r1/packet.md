# Frozen method review packet, round 1

This is an engineering candidate and method draft, not a pre-decided OSDI verdict. Three fresh independent reviewers receive this same packet. Runtime code is frozen at `1cb15d729e4bed52d27c19b996f97b7ab88ffa80`; later commits contain documentation and retained evidence. Read `source-manifest.json` for exact manuscript/code version boundaries. The sole maintained manuscript remains workspace `paper/main.tex` and its included tex files. The diff/PDF here are immutable snapshots, not another maintained manuscript.

## Read first

- Workspace `method_goal_prompt.md` defines original requirements and allowed negative outcome. Read Sections6–10 rather than inferring completion from green tests. `method_impl_record.md` M020–M022 and its snapshot identify actual experiments, failures and ownership.
- Manuscript: workspace `paper/sections/01-introduction.tex`, `03-study.tex`, `04-design.tex`, `05-implementation.tex`, `06-evaluation.tex`, `07-experience.tex`, `08-related-work.tex`; frozen `manuscript.pdf` and `manuscript-source.diff` here.
- Background, abstract and conclusion still include known drafting TODOs. Classify such fixable text gaps separately from absent implemented mechanisms or structural contribution. The user requested an implementation-informed method draft and substantive review, not guaranteed acceptance. Do not excuse unsupported claims elsewhere in the paper.
- Public interface/limits: `Profiler/docs/semantic_profiling.md`, `Profiler/docs/method_testing.md`, `tests/ascend/README.md`, `integration/patches/{nvidia,enflame,ascend}/`.

## Candidate claims to examine

M1: actual binary/specialization/actor/work-item mapping and surviving origin candidates; typed same-compile HIVM readiness channel, preserving partial or ambiguous source attribution. No exclusive source-operation cost claim.
M2: dynamic bounded records, typed issue/wait/checkpoint versus completion/busy, writer-ownership-safe GCU publication, Ascend compile-time semantic selection; explicit unsupported sites/sampling. No added device completion barrier to manufacture a pipeline.
M3: per-launch metadata identity and retained CANN worker token, SDK epoch seal/context/compute FK, raw activity/record retention, local clock rate conversion and honest unavailable alignment. No names/order/containment as identity certificate, no proportional timestamp scaling.

## Main evidence

- `integration/evidence/final-common-20261015/summary.json`: final exact runtime imports/source manifests, NVIDIA421pass4skip, GCU350pass5skip, Ascend407pass18skip. Every skip is explained. Final NVIDIA public3launch request and GCU6call/2stream/2binary functionality passed. No new NVIDIA performance measurement (explicit user deferral). Harness startup mistakes are preserved and distinguished from product/test outcomes.
- `integration/evidence/ascend-final-raw-20261015/`: original117 and additional24 request full retained-buffer audits. Full matrices precede later typed-IR capture/semantic-selection changes; do not relabel as new final-source matrix runs. Their exact native/plugin/source identities remain recorded.
- `integration/evidence/ascend-static-readiness-20261015/`: actual same-source SDK replay equivalence, 27CPU contracts, actual fused4calls/232records/23debug-origin sites and typed actor peers. Source IDs can be absent; public origin status includes34verified/27ambiguous/13unassociated.
- `integration/evidence/ascend-semantic-selection-20261015/` and `ascend-final-closure-20261015/`: 24 actual LLVM15/compiler/API contracts; RMS6phase selection plus fused functionality; complete independent original-buffer/identity/local-duration audit; 52-module isolated wheel verification; final controlled long-K6phase/180measured-call evidence and all costs.
- `integration/evidence/enflame-two-stream-20261015/`: actual two non-default streams, repeated/different specialization, exact math/canary/native correlation and dynamic isolation. SDK grid/task IDs remain unknown; association uses actual provider/process/context/correlation/scope/binary/stream, not invented task IDs.
- Other backend evidence: workspace `artifacts/method-run/enflame/GCU-I3-evidence.md`, final `current-state.json`, `postformat-final-source-native-manifest.json`; NVIDIA `r25-review-handoff.json` and original hardware/lifecycle/graph logs. See earlier committed `integration/evidence/` for corruption/capacity/recovery tests and raw fixture proofs.
- Large raw archives remain outside Git under workspace `artifacts/method-run/`. Content hashes and independent audit procedures are committed. Do not copy SDK binaries/private headers or full copyrighted papers into reports/Git.

## Essential adverse/limited results

- GCU explicit-vector full36 detailed matrix:4599retained/21996declared drops, all math checks pass. Scalar full-site GELU had a900s compiler timeout; explicit vector completes but selected-store device overhead26.47–26.95%. Scalar selected-store3.08–3.57%, host about5.2ms; not universal/end-to-end low overhead.
- Ascend small RMS all-site61.2–67.6% device overhead; compiler wait-only still60.1–78.0%. Fewer events did not solve small-kernel cost.
- Prespecified Ascend long-K P32_K32 three paired30call batches: −0.08/+1.30/+0.87% device task changes, but host12.33–12.46ms vs267–272us, export15.62–17.21s and221–229MB per detailed33call session. No native-versus-off device≤5% proof.
- Source MOV SYS_CNT and native ACSQ reported clock origins remain unverified. Typed static readiness does not pair dynamic generations. Old Study pipeline placement is explicitly conditional on a common reported-counter interpretation; its unique campaign window match is not an independent runtime/domain certificate.
- There are no claimed production users/deployment history. Three research machines and controlled operator studies are the actual experience.

## Nearest prior work: use primary material

- KPerfIR OSDI25 primary https://www.usenix.org/system/files/osdi25-guan.pdf ; local `artifacts/method-run/prior-work/kperfir-osdi25.pdf`. Fine-grained compiler IR scopes, circular buffering/selectivity/async issues and NVIDIA+AMD are prior.
- Proton CGO26 official https://2026.cgo.org/details/cgo-2026-papers/23/Proton-Towards-Multi-level-Adaptive-Profiling-for-Triton , DOI10.1109/CGO68049.2026.11395207. Author-primary LLVM25/HPCA25 slides and locator JSONs are in `artifacts/method-run/prior-work/`. Full CGO text was unavailable after a finite primary search; missing access is not proof of absent features. Adaptive, fine-grained, custom metrics and multi-backend mechanisms are prior.
- PASTA primary full text https://arxiv.org/html/2602.22103v1 ; local `pasta-cgo26-arxiv-v1.html` and locator JSON. SectionIII-G explicitly normalizes semantic/timing metadata and uses vendor-specific handlers. These are not first contributions here.
- Inherited Proton/Debugger/FlagTree infrastructure must be credited. A common schema, an IR name, adapter count or amount of engineering is not sufficient novelty on its own.
- Official OSDI27 CFP https://www.usenix.org/conference/osdi27/call-for-papers (checked2026-10-15): Operational Systems does not require novel research ideas, but does require substantive system implementation/analysis/experience and public systems knowledge. Assess this track; do not invent a mandatory production-user quota or assume research experiments are production deployment.

## Required independent output

Read actual code/evidence/primary material, not this index alone. Give blocking/major/minor findings with claim→code/evidence/source anchors. For every issue classify: implementation gap, evidence gap, expression gap, or structural contribution deficit. Identify supported/unsupported contributions; distinguish engineering validity and OSDI Operational Systems contribution. Give a finite repair with predicted validation, or explain why current available conditions cannot fix it and the minimal new condition needed. Be candid; neither approval nor rejection is a required outcome. Do not lower requirements or demand an unrequested Proton/KPerfIR cross-device port/tool benchmark.

Each reviewer must independently answer whether the current three mechanisms and contribution could support OSDI Operational Systems, and whether a short implementation/text/evidence iteration can fix the identified gap. Do not read peer reports, coordinate opinions, modify code/manuscript, launch hardware experiments or install dependencies. Report to your assigned output path and finish. Review agents use the default model with independent contexts; no claim of three different model families is made.
