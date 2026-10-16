# Usability engineering checkpoint — qualification incomplete

Runtime source: `1638a899d80c2ff134efbdb703aa695dbb39c39d`.
This checkpoint publishes tool code and small, public evidence indices. It does
**not** declare the full usability goal achieved.

Three independently requested `gpt-6.1-sol` / `xhigh` code reviews and their
bounded fix deltas are in `code-review/`. The tool accepted those requests but
does not expose the actual resolved model version. Both confirmed major defects
(GCU compiled/runtime layout admission and implicit Ascend external-counter
replay) and the confirmed documentation findings are closed for this source.

`native-delta/` records actual rebuilding of one changed C++ translation unit,
linking seven SHA-audited unchanged objects, new independent wheel installs,
171 passing CPU tests plus three optional browser skips per backend, and short
real default hardware checks. This is not a claim of a full core compiler rebuild.
NVIDIA GPU performance/overhead benchmarks remain deferred.

`qualification/` preserves the preceding runtime cohort's public aggregate
facts: NVIDIA 48/48 and GCU 48/48 full gates passed. Ascend's original eligible
46 profiles have 45 full-gate passes and one unexplained state assertion failure.
That original failure remains eligible and open. Later successful controls do
not erase it. These full-cohort results used the preceding ce00 runtime; they
must not be presented as a fresh 48-case run on 1638. Affected CPU/native and
short real hardware checks were run on 1638.

Large raw archives and SDK/cache inputs are deliberately excluded from Git.
Their original workspace paths, sizes and SHA-256 values are in the indices.
The ongoing investigation and complete execution history remain in the root
workspace `method_impl_record.md`; no paper or Study was edited for this work.

## Subsequent diagnostic: actor counter inconsistency remains open

A separately frozen **known-case diagnostic**, not another unseen cohort,
passed two ordinary launches and two default profiling CLI runs on 1638 with
unchanged numerical tolerances. An actual SDK/LLVM ownership proof established
four disjoint vector-state writer regions, covering 1,024 elements, and excluded
AIC state writes. All state values were exactly one. However, both captures
retained zero visits for one AIV actor at the unconditional State premarker,
while the other AIV actor retained one. The additional proven-writer/marker
invariant therefore passed **0/2**, despite the preceding common gate accepting
2/2. See the new safe diagnostic aggregates and ownership proof.

This is a concrete counter/source evidence inconsistency requiring public
reproduction and a general fix. Its cause is not yet established. It is not
explained away by successful numerical results or the preceding common gate.
The original historical scalar-state failure remains preserved and unassigned;
a different ordinary kernel's failure cannot be used to explain it.
