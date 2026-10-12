# Final independent evidence audit

Original objective read first from the named attachment. No earlier reviewer reports or remote machines were consulted. This audit uses current raw experiments, code, compiler artifacts, compact results and the referenced Study section.

## Verdict

The five-link Study chain is supported within its explicitly stated research-probe scope. No P0 numerical contradiction was found. The new Ascend hardware PMU experiment supplies an appropriate independent reference for **instrumented real-softmax body/output projections**, rather than another capture of SYS_CNT or a whole-kernel surrogate. It does not supply universal accuracy for all operators, phases or backends. Criterion 7 remains pending the new PMU commit, updated final records and completion of this review round.

## Independent checks performed

- Re-ran `freeze_results.py` against the three breadth raw directories: 216 passing cases, 1,620 native intervals, 1,296 verified compiler artifacts.
- Re-ran `audit_operator_regions.py`: 32 real-operator cases verified; all 6,960 CUDA internal-duration/whole-kernel containment checks pass.
- Re-ran `ascend_llvm_analyze.py` with the completion-capture root: 11 cases, 98,880 interval rows, no containment violations.
- Re-ran `gcu_global_timer_analyze.py` on **leader-workspace**, selecting `leader-global`: 1,440 jointly nested records, no ordering violations. The softmax nested/single-active body ratio remains 1.239355742; it must not be presented as near-zero perturbation.
- Re-ran `ascend_precision_analyze.py` into an independent temporary output. Separately recomputed selected branch-v2 source durations from raw actor words, and PMU durations directly from integer cycle counts divided by reported 1,650 MHz. Exactly 32 matching blocks per selected body/output invocation are present. Max differences are 15.151515/20.606061 ns using unrounded cycle conversion; the compact CSV reports 15.151/20.606 ns. All points meet the conditional comparison bound.
- Checked both selected compiler receipts against actual LLVM and final object hashes. Inspected the emitted LLVM: mathematical/load/store helper sequence is preserved; stop-word preparation follows the store helper, selected final PIPE_ALL precedes the branch-controlled end clock, and the stop gate follows recorded clock halos.
- Viewed the new PMU plot. Its values match the selected experiment, but its legend overlaps the x-axis labels in the current PNG.

## Seven acceptance conditions

| Requirement | Assessment | Evidence and limit |
| --- | --- | --- |
| 1 Fixed request | Satisfied | `region_contract.json` and Study explicitly define body/output, actors, endpoints, included wait/transfer, units and unsupported cross-actor relations. Both real operators and all three stacks use it. |
| 2 Six-operator breadth | Satisfied | Fresh audit reproduces the full six-operator/three-shape/two-config/native-baseline dataset. Study correctly says duration differences alone do not prove a profiling defect. |
| 3 Two real closed cases | Satisfied within stated scope | Actual fused GEMM+bias+GELU and softmax have source/lowering/execution/request/generic/adapted evidence. GCU overwrite occurs in both; Ascend fused actor/scope failures are emitted-code facts; Ascend softmax is a successful single-AIV contrast. No measured mixed-writer rate is invented. |
| 4 Dynamic observation attempts | Satisfied | Actual actor-local body/output, AIV wait and completion-fenced subdivisions exist. Pipeline plots use measured brackets with separate row origins. AIC phase decomposition and cross-actor overlap remain explicitly unavailable; the requirement asks for attempts and quantity declarations, not fabricated universal coverage. |
| 5 Controlled checks | Satisfied for the declared propositions and bounded precision experiment | Fixed-work producer delay preserves inputs/math/NOP budget and unchanged AIV observer LLVM; completion intervention preserves math/layout while changing declared endpoint fences. Numerical verification now uses same-invocation/block hardware PMU for real-softmax body/output. It supports these instrumented windows only. The original wording does not require an all-region/all-backend absolute-accuracy certificate; do not claim one. |
| 6 Method requirements | Satisfied | Each of the three requirement items contains measured difference, concrete consequence, generic limitation, mechanism and verification, with implemented/verified/proposed statuses. Production compiler provenance, concurrent attribution and portable guarantees remain proposed. |
| 7 Delivery/reviews | Pending final action | New PMU scripts/results were untracked at audit time; closure README and `study_experiment.md` still describe PMU as in progress. The new reviews, fixes, final figures/PDF snapshot and commit/push must finish before reporting delivery complete. |

## Conditional-bound assessment

For each actor, measured gate-duration lower/upper hulls come from SYS timestamps around SET.CTRL. Comparing the recorded source duration to that hull gives at most 20 ns padding in final branch-v2 captures. Adding 20 ns SYS floor-duration uncertainty and one 1,650-MHz PMU cycle gives 40.606061 ns, below the rounded 41 ns bound. This is a **comparison bound conditional on reported core-frequency conversion and physical gate ordering**, not a frequency-independent accuracy guarantee, confidence interval or unperturbed busy-time bound. The source compiler cannot independently decode final ISA order; that limitation remains stated.

## Required reporting/presentation fixes

1. **P1: stale completion records.** Update closure README and `study_experiment.md`: a successful PMU reference now exists, with 64 correlated block records across two separate selected invocations. Replace the obsolete “in progress/no successful reference” statements. Keep V100 absolute precision, GCU official absolute units/precision, Ascend fused/individual-phase absolute precision and cross-actor overlap explicitly unverified.
2. **P1: numerical formatting assumption.** Analyzer adds 0.5 ps for six-decimal CSV rounding, but final CSV/raw-cycle discrepancies reach 0.545455 ps (body) and 0.515152 ps (output), consistent with additional conversion formatting. This does **not** invalidate the rounded 41 ns bound. Prefer direct raw-cycle/1,650 conversion for the numerical reference, eliminating CSV-rounding dependence; otherwise use the already checked 2 ps conversion tolerance and explain it. If reporting exact raw-cycle maxima rounded to three decimals, they are 15.152/20.606 ns; 15.151 is the native CSV-derived maximum.
3. **P1: PMU plot overlap.** Reserve space between x-axis labels and bottom legend or move the legend lower. A scientist reading the figure should not need to infer obscured labels.

Do not turn the residual limitations into an unrequested demand for universal numerical verification. Conversely, completing this Study cannot be described as certifying absolute accuracy of every adapted backend or proving overlap between Ascend actors.

## Fix verification before final commit

All three P1 issues above are resolved in the current worktree. The analyzer and bound metadata use the verified 2 ps vendor-conversion tolerance, preserving the rounded 41 ns bound. The closure README and experimental acceptance table report successful scoped PMU verification and retain the outstanding precision/generalization limitations. Re-viewing the regenerated PMU PNG confirms its legend no longer overlaps either x-axis label.

The added 91-file `ascend-precision/replay-data/` subset supplies original native PMU records, vendor reports and matching source observations without proprietary SDK libraries. Re-running `ascend_precision_analyze.py` on that subset independently reproduces both the full 416-row `comparison.csv` and `summary.json` **byte for byte**. Criterion 7 now only awaits the root's final commit/push and final delivery-state verification; no additional scientific P0/P1 remedy remains from this audit.
