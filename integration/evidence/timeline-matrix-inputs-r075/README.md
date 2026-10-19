# R075: native matrix operand words and dynamic shared generations

This delta adds qualification tools; runtime efb2363, native code, ABI,
recorder, clock rules and exporter are unchanged. Existing SQL/UI and math
are reused. All product imports and checks ran in the existing NVIDIA Docker.
No kernel, GPU performance test or SDK compilation was replayed.

## Direct result

The final suite is terminal 0 / 16.844s. Forty-eight synthetic semantic tests
pass in normal and optimized Python (25 register-cone and 23 matrix-input
cases). Their role is bounded regression testing, not hardware evidence.

The original ordinary object has four HMMA instructions, with all 24 A/B
input words traced to exact LDSM output words. Each actual default/sparse
runtime-K3/K7 capture then freshly validates the native object and the existing
raw-address/payload/clock dependency chain. The four captures yield
144/336/144/336 = 960 native input-word to dynamic generation associations.
The programs and trip counts remain the original registered calls.

The checker cuts the current natural loop's return edges and rejects a
remaining cycle. An earlier-loop load cannot stand in for a fresh current
load. Every checked native matrix-group member and all A4/B2 words must be
covered. At each dynamic matrix group, each required load site has exactly
one current occurrence. Its entire collective footprint must have one fresh
byte-model producer generation; otherwise the association is unverified.
This covers any subset of the loaded words without inventing a lane/byte
permutation for the two-word B operand.

## Bounded register dependency property

Canonical P2R is conservatively treated as reading P0..P6, its merge register
and execution predicate. No exact mask-bit selection is assumed. NVIDIA's
[Binary Utilities reference](https://docs.nvidia.com/cuda/cuda-binary-utilities/)
names P2R as predicate-register to register movement; the
[CUDA-GDB register documentation](https://docs.nvidia.com/cuda/pdf/cuda-gdb.pdf)
lists the P0..P6 bank. Modified/unknown forms remain unverified.

All 26 actual copy/control register cones exclude a reaching definition from
this function's matrix or clock results. This is a separate negative property,
not a claim that every input value is defined. Three default control cones
still have unresolved entry predicate values and retain
`unverified_entry_registers`; their full input CLI correctly exits 1.
Through-memory, implicit scoreboard, physical activity and full pipeline
preservation remain unverified. Prior R074 results are not silently rewritten.

## Scope still open

This does not finish the three-object ordinary group/shared-slot/CTA-cut/reuse
role comparison. Ordinary has no recorder raw, so its generation binding stays
false. Native operand/generation associations do not grant tensor completion,
source-exclusive elapsed time or measured overlap. The final whole-goal
review also audits the original source/loop and independent-qualification
requirements across all three backends; it is not replaced by this delta.

The full per-word results and original receipts remain in root
`artifacts/timeline/run-075/preflight/receipts-v1` and on the server under
`/workspace/chijin-timeline-r075-nvidia/runs/final-suite-v1`. summary.json
binds those results and the six exact executed source files by SHA256.
