# Real-operator Study closure

Shared request: `experiments/study/region_contract.json`. Named body/output
control-path projections, actor/program/launch identities, explicit endpoints,
clock units and unsupported relations. Operators: fused GEMM+bias+GELU128³ and
softmax32×256. Three backend stacks; this does not establish same-SIMT vendors.

## Evidence and scope

- `breadth_reaudit.json`: original six-operator set rechecked against all raw
  artifacts:216 passing cases,1620 native intervals,1296 compiler-artifact hashes.
- `operator_audit.json`, `captures/`, `operator_intervals.csv`:32 passing CUDA/GCU
  real-operator cases,15 serial launches each, explicit program-slot validation.
- `protocol_comparison.csv`: generic nested vs same-provider single-active controls.
  This is not a reproduction or capability comparison of Proton/KPerfIR/TCU.
- `isolation.csv`, `isolation/`:one selected program reproduces GCU window-counter
  overwrite. Other programs are intentionally not executed in this auxiliary control.
- `ascend/`:generic source probes pass math/program checks, but fused AIC is not
  returned, two AIV subinstances share a program-only record slot, and generic
  output starts after readiness wait. No observed mixing/mismatch rate is claimed.
  Late-LLVM probes retain64AIC+128AIV identities per fused launch and32AIV softmax.
- `ascend/endpoint-policy-corrections.json`: original transfer/compute subdivision
  used issue/gate endpoints lacking scalar completion provenance. Final pipeline
  figures use separate completion-fenced captures; extra fences perturb execution.
- `ascend/intervention-metadata.json`: fixed16384NOP count, identical producer
  completion fence, unchanged AIV code/endpoints. Wait medians222/367.5/1036ticks
  for0/8192/16384NOPs before signal. Unfenced unsuccessful control is retained.
- `gcu-global-timer/`:research-only SDK timer adapter + explicit leader staging and
  GM publication. Final six captures use work-item0, not a group elapsed envelope.
  Joint nesting is preserved; softmax shows about24% extra-read perturbation.
- `cuda_record_writer_audit.json`:selected CUDA PTX T stores select thread0.
- `cuda-dual-clock/`: same-endpoint clock64/globaltimer sandwiches in two real
  operators (1440 program records). Independent relative-fraction checks are
  conditional on constant SM frequency; the empirical32ns margin leaves one
  fused residual, retained. Absolute internal precision remains unverified.
- `native_scale_calibration.json`, `gcu-global-timer/calibration.json`:single-program
  independent native-reference scale checks, declared fit/holdout partition,
  residuals and raw sensitivity. No internal precision certificate is established.
- `cuda_independent_outer_bounds.csv`:6960 internal durations fit within same-launch
  CUPTI whole-kernel durations. Ascend corresponding consistency checks use
  documented SYS_CNT50ticks/us. These are bounds, not exact per-region truth.

GCU official timer frequency, cross-program/SIP origin and cross-actor Ascend
origin remain unverified. Raw ticks are retained. Its near1ns/tick empirical
scale uses TOPSPTI whole-kernel references; distinct physical oscillators are
not established. `clockInstructionRate` is not bound to this helper; applying
its reported kHz as a conversion fails duration bounds.

## Reproduction

Use the recorded runtime stacks from the preceding bundle and new per-capture
source/SDK/compiler hashes. Keep canonical inputs unchanged.

1. `make_inputs.py` (or retained immutable input folder), then `sweep.py` with
   `--profile-launches 15` for the six-operator breadth (see code README).
2. `operator_sweep.py --backend cuda --input-dir INPUTS --output ROOT/operators`
   (use `--backend enflame` on the GCU stack).
   `operator_regions.py` retains negative pilot results and never overwrites cases.
3. Ascend:`ascend_llvm_compile.py` uses an isolated PATH wrapper
   `ascend_llvm_intercept.py` in the original vendor compiler pipeline;
   `ascend_llvm_regions.py` loads the preserved-ABI object and checks CPU outputs.
   `ascend_llvm_analyze.py` audits native association, actors and controls.
4. GCU:`gcu_global_timer_prepare.py` extracts only the installed read-only SDK
   helper into an alwaysinline private shim. `gcu_global_timer_operator.py` and
   `gcu_global_timer_adapter.py` select that helper and guard all recording staging
   and publication. `gcu_global_timer_analyze.py` audits records, units and controls.
   No vendor installation or production backend is modified. Required generated
   shim, library hashes and exact commands are in the retained raw provenance.
5. `audit_operator_regions.py`, `audit_native_scale.py`, and
   `plot_operator_closure.py` generate the audit tables and figures.

Complete raw logs/IR/binaries/profiler exports are under workspace
`artifacts/study-closure-20261013/`; archive hashes identify them. SDK binaries are
not redistributed here. Canonical input hashes and source versions are retained.

Thoughts/body remain only in `paper/main.tex` and referenced sections. This
bundle contains a PDF snapshot and experimental artifacts, not another paper
source tree. Methods/generality/operational deployment still require evaluation.
Final independent reviews and their resolutions are under `reviews/`.

Current acceptance: common request, breadth, two real cases, dynamic research
probes, and method-requirement chains are present in their stated scope.
Semantic/identity controls pass; absolute internal precision is still open.
Three independent reviews were completed and critical presentation issues fixed.
An additional CANN PMU attempt is in progress; no successful PMU reference is
claimed by this snapshot.
