# Final timeline code-review input, R057

This is a review input, not an acceptance certificate. Review the actual code,
public interface, declared measurement semantics and contract. Historical stage
READMEs describe their contemporary state; later evidence may supersede a
specific failure, but no stage summary alone proves complete acceptance.

Runtime implementation freeze: `4bc92861bd8665dfd446332f9af63dca7b64eaf0`.
Later commits add evidence and the controlled test driver (`7daeb7e`);
no later runtime implementation changes have been made. The canonical
`detailed-profiler` is still `20d370a`; the candidate is not merged or pushed.
The working research directory's `timeline_goal_prompt.md` is the active
contract, and `timeline_impl_record.md` is the append-only live history.
`Profiler/docs/timeline_design.md`, `timeline_testing.md`, `timeline_runtime.md`
and `timeline_quickstart.md` give design, tests, scope and user commands.

No paper changes, fourth-backend adaptation or NVIDIA exclusive performance/
overhead certification is authorized in this goal. All imports, builds, actual
kernels, CPU test execution, SDK reference compilation, TP and browser jobs
have to run inside existing server Docker. Reviewers are read-only: do not
execute them locally or access devices. Give root a minimal proposed reproducer
if the code/evidence is insufficient. Do not create new mathematics or repeat
unchanged historical matrices merely for review bookkeeping.

## Evidence entry points

- NVIDIA late native dependencies and physical shared-byte reuse:
  `timeline-native-flows-r047`, `timeline-canonical-retention-r047` and
  `timeline-capacity-codec-r047`; current affected capacity/machine fixes in
  `timeline-independent-deltas-r056` and `timeline-independent-qualification-r057`.
  The root workspace also retains R056's read-only physical-range reuse summary
  at `artifacts/timeline/run-056/preflight/nvidia-retained-reuse-v1.jsonl`.
- Ascend actual final-image native flags, dependency generations, offline, TP
  and UI: `timeline-ascend-native-dependencies-r049`. Mixed AIC/AIV real unit
  traces and standard UI: R055 evidence indexed by R056.
- GCU actual translated buffer addresses, tag generations, two nondefault
  streams, TP/UI: `timeline-gcu-observed-dependencies-r052`.
- Independent original six and two supplemental mathematics, original failures
  and affected-only repairs: live history T074–T080; R056 and R057 checkpoints.
  Original frozen inputs/tolerances/configurations and first failures remain
  separate from repairs. Ascend supplemental 24-call results are terminal and indexed in R057
  (`ascend-supplement-final-result-v1.json`). All 24 math/ns/observed-writer
  and budget gates pass; twelve still retain two unknown reserved slots each
  and all 24 have explicit dependency-unavailable status. See the complete
  first-attempt and affected-repair index, not a combined passing denominator.
- Actual work/tiling controls: maintained
  `tests/timeline/p01_controlled_workloads.py`, R056 results and the runtime
  reference's "Reading the controlled examples". These timings concern
  instrumented execution, not ordinary speedup or engine busy time.
- Owner/fault/cache/raw ABI, public/legacy compatibility and backend integration:
  maintained `tests/timeline`, `Profiler/test`, `integration/patches`, and the
  relevant R016–R052 immutable evidence directories. CPU fixture evidence must
  remain distinct from actual device results.

## Facts that must remain visible

The original NVIDIA six-kernel matrix retained 12 missing-unit and 9 writer
capacity failures. All 12 missing-unit originals were re-exported without
replay; 10 affected/default device calls passed the repaired mapper/full-CTA
policy. Supplemental q08 first retained 12 saturated failures; only those 12
were repeated with sampled policy v3 and now pass all original time/writer/size
gates. Do not silently rewrite the original denominators.

Ascend original 72 numerical/raw/counter-unit/observed-writer/size gates pass,
but only 24 have dynamic dependency exports; 48 retain explicit unavailable
native mechanism coverage. Some compiled AIV reserved slots are still explicitly
unobserved and the full batch remains partial. Review whether the actual
selection/observer contract is satisfied; do not infer an empty slot was absent
or complete, or automatically accept every qualification assertion. Current
source recognizes 40 actually compiled immediate tuples and rejects unknown
final-image instructions. Additional known SET/WAIT(1,0,7) words have CPU SDK
evidence but remain unobserved dynamically; no disjoint-channel exception was
implemented to bypass them. Normal/-O actual-image faults pass on closed q01;
the initial q03 positive failure is retained.

One historical NVIDIA C1 recording had valid headers but seven zero raw records
and was safely rejected. Three finite reproduction captures and later controlled
and independent calls did not reproduce it; no cause/fix is claimed. See live
history T076 and `artifacts/timeline/run-053-nvidia` server paths in that history.
No parser relaxation, guessed global synchronization patch, or erased failure
was introduced.

Counter bracket time, source navigation, proven region bounds, dynamic generation,
scalar readiness, engine busy and ordinary optimization benefit are different
claims. Verify what each exported slice/flow actually asserts and what the code
proves. Trace count or positive duration alone is insufficient. In particular,
check the actual dedicated asynchronous reuse/schedule-perturbation evidence
and controlled ordinary references against testing sections 5 and 8.1–8.9;
missing evidence is a verification gap, not a passing vote.

## Required report

Each of the three fresh independent reviewers reads the complete public chain
and concentrates on its assigned area. Separate confirmed blocker/major/minor
code defects, verification gaps and optional improvements. Give source location,
trigger, evidence, consequence and minimal suggested validation. State what was
and was not read. Do not modify product code or read peer review reports. Root
must verify findings and close confirmed defects with affected-only tests before
merge/push; majority voting does not waive a defect.


The final finite Ascend/GCU density controls are indexed in R057. GCU both
variants pass ordinary/sparse/default. Ascend defaults and BK32 sparse pass;
BK64 sparse retains an actual two-interval gate failure (one positive interval),
with the remaining sparse call not started. This advanced one-site diagnostic
has not been counted as default qualification. Assess the scope and usability
consequence explicitly. All device collection jobs are terminal; the review
freeze includes the evidence-only commit adding these results.
