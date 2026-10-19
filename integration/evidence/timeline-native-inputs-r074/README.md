# R074: bounded retained-native input diagnostics

This is qualification tooling, not a runtime change or whole-goal sign-off.
The installed runtime remains efb2363; native code, raw layout and exporter
are unchanged. All product imports and tests ran in the existing NVIDIA
Docker. No kernel, compiler, device math, performance test, TP or UI replay
was needed for this delta.

The new checkout scripts inspect actual register uses, include 64-bit input
pairs and uniform-branch operands, and keep unknown writers, packed PR
sources and undefined entry roots explicitly unverified. Twenty synthetic
semantic tests pass in normal and optimized Python. They exercise new matrix
or clock dependencies, overwritten physical-register identities, branch
alternatives, pair high words, reuse modifiers and unsupported packed sources.

The actual ordinary/default/sparse objects each have three copy-input cones
without a matrix-result or clock-result register dependency. Fourteen of
seventeen conditional-control cones close; three in default remain
unverified because their necessary cones use packed P2R predicates.
The retained-input CLI therefore correctly exits 1, and its report is partial.
Earlier v3 diagnostics did not model PR and do not certify those controls.

Separately, fresh decoding of the original default/sparse runtime-K3/K7 raw
bytes finds nonempty future-copy groups not yet required complete at 32 of
40 matrix prefixes. Each shown witness has 2048 source-valid shared bytes;
final drain prefixes have no future-group witness. Changing wait limits to
zero removes these witnesses while preserving operation counts. This is
permission to remain uncompleted under the observed waits, not measured
hardware overlap; the shared reads are not yet certified as exact MMA inputs.

Still required for the original pipeline gate: bind ordinary and instrumented
group/shared-slot roles and original cuts, bind matrix operands to those
shared generations, and finish the three necessary packed-predicate cones.
Neither same counts nor these partial diagnostics certify preservation.
Full original objects, native excerpts, failed orchestration attempts and
receipts stay under root artifacts/timeline/run-074 and the server run paths.
The archive SHA in summary.json binds the retained receipt bundle.
