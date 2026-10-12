# Independent final story and requirements audit

Reviewed the literal seven-item goal in the attached pasted-text file, current
`paper/main.tex`, Introduction, `03-study.tex`, the fixed region contract,
breadth/operator audit records, Ascend intervention metadata, and the new
Ascend precision summary, comparison CSV, endpoint audit, provenance,
reproduction record and analysis/compiler scripts. No other review reports or
remote servers were consulted. This is a story/claim audit, not a replacement
for independently replaying every experiment.

## Decision

The scientific Study chain is now coherent and adequately evidenced in its
declared scope. I found no P0 scientific/story blocker. Final artifact delivery
is not yet complete at the inspected state: new precision code/data were
untracked, and the experiment record/bundle README still describe the PMU
attempt as ongoing. Resolve the P1 delivery contradictions before claiming
all seven acceptance items complete.

## Literal acceptance status

| Item | Status at inspection | Evidence and limits |
| --- | --- | --- |
| 1 Fixed request and experiment logic | Met | `region_contract.json` and Study define body/output, actor projections, program/invocation identity, endpoints, included readiness/transfer, units and unavailable clock relations. One request governs both real operators on all three backends. |
| 2 Six-operator scope | Met | Breadth re-audit reports 216 passed cases, 1,620 native intervals and 1,296 compiler-artifact hashes across the three stacks. Study explicitly distinguishes duration/configuration behavior from proof of profiling defects. Untuned probes and shared/non-fixed-clock conditions are disclosed. |
| 3 Two real closed-loop cases | Met within stated observations | Fused GEMM+bias+GELU and softmax have source/compiled mapping, synchronization/data paths, body/output observations, generic controls and adapted results or explicit missing observations. Fused AIC/AIV mapping supplies the identity/scope failure; softmax supplies a successful single-AIV contrast and an independently checked internal-region example. No toy recurrence substitutes for either case. |
| 4 Dynamic observation | Met as attempted and measured quantities | Late LLVM probes record actual actor-local fused/softmax brackets and AIV wait/transfer/compute/store components. Figure captions distinguish static dependencies from measured local brackets. Cross-actor overlap and AIC phase decomposition are explicitly unavailable; neither is fabricated from independently reset origins. The goal requests attempts and truthful measured quantities, not a universal cross-actor clock guarantee. |
| 5 Controlled semantic, association and numerical checks | Met for the scoped Study claims | GCU isolation/control establishes window overwrite; fixed 16,384-NOP placement preserves mathematical work, producer fence and AIV code/endpoints while changing readiness wait. Endpoint controls distinguish issue/gate brackets from completion-fenced observations. Actor/native identity is explicit. New independently gated hardware PMU checks real softmax body/output: each selected capture has 32 unique blocks, zero halo violations, observed maximum point differences 15.151/20.606ns and a conditional rounded 41ns comparison bound. CUDA relative checks and GCU coarse calibration retain their weaker scope. This does **not** certify absolute internal accuracy on every backend/phase or unperturbed execution. |
| 6 Method requirements | Met | Three requirement bullets each give measured difference, consequence, generic limitation, mechanism and verification; implemented research probes, verified configuration scope and proposed production/general support are separately marked. |
| 7 Submission/artifacts/three reviews | Pending final delivery | Actual result figures and updated paper exist on disk and the branch is correct. New precision scripts/data were still untracked and the README/experiment acceptance table stale at inspection. This independent review can count toward the requested final three, but root must verify the other two, fix findings, regenerate the final snapshot and commit/push the completed artifacts. |

## Why the story works

Six operators show that execution/configuration behavior varies, while explicitly
not treating performance variation as a profiling defect. The fused and softmax
cases then establish distinct compiled execution objects. The same requested
body/output observations expose three concrete consequences: missing or
ambiguous actor identity, omitted readiness scope, and an incompatible nested
clock protocol. Positive controls prevent the argument from becoming a blanket
claim that common source instrumentation always fails. Interventions test the
specific explanations. Requirements therefore follow from observed failures,
instead of from the existence of vendor diversity alone.

The PMU work strengthens numerical trust without changing that causal chain.
The reference is a separately sampled hardware cycle window, not another
capture of SYS_CNT or whole-task subtraction. Native SYS timestamps serve
association only. Its reported-frequency conversion and gate-order assumption
remain conditions, and the comparison includes added gate/dependency/fence
costs. The paper states these restrictions. It also correctly treats the
32 blocks as correlated within one selected invocation, not 32 independent
launches or a population precision guarantee.

## P1 actions before final delivery

1. Update `study_experiment.md` acceptance item5 and PMU section with the actual
   selected branch-v2 scopes, reference, empirical errors, conditional bound,
   sample unit and retained failed/unmatched paths. Item7 must become complete
   only after final commit/push and three independent reviews are verified.
2. Update the closure README: remove the obsolete claim that the PMU reference
   is still only an attempt; add the precision reproduction/artifact path.
   Preserve CUDA absolute-precision and GCU official-frequency limits, rather
   than replacing them with a broad statement of backend accuracy.
3. Commit the new scripts/data and current figures/PDF snapshot; verify the
   pushed branch includes them. The current working paper already has the PMU
   figure, but an older committed snapshot cannot substantiate its current text.

## Claims to preserve during those edits

- Describe 41ns as a **conditional comparison bound for these instrumented
  softmax windows**, not guaranteed profiler accuracy or a platform-wide bound.
- Keep the selected cold invocation separate from the main prewarmed timing
  captures; no sampling statistics from the latter apply to the former.
- Final machine-code ISA order was not independently decoded. LLVM dependency
  evidence and dynamic gate checks support the conditional interpretation;
  do not silently upgrade it to a decoded-binary ordering proof.
- `csv_cycles_exact_match_all32=false` for the other replay is not a failure of
  the selected reference: selection uses exact cycles plus task/actor association.
  Retain both replay records so readers can see how association was decided.
- Do not label the generic nested probe a reproduction of Proton or KPerfIR,
  and do not infer a same-SIMT-vendor finding from these three backends.
- Operational usage, production integration, all-phase fidelity and generality
  remain future system/evaluation work. They are outside the requested Study
  completion, not evidence that this scoped Study is universally conclusive.
