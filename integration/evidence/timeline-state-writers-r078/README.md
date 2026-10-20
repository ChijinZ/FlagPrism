# Original State writer lowering (R078)

This is a CPU-only qualification delta. The profiler runtime, native code, clocks, trace exporters, paper and Study data are unchanged.

NVIDIA: the actual retained PTX thread/predicate/address lowering is bound to each registered mathematical call's PTX/cubin and launch geometry. The finite checker enumerates every thread/program, checks the State store width, requires exactly one physical writer per legal element, and rejects writes to guards/tails. State writes must not be bypassed or occur in a loop; address/predicate operands use actual CFG reaching definitions and an exact typed-operation whitelist. Unknown lowering remains unverified. The original contract does not additionally require interpreting every SASS instruction.

Final `writers-v9` passed 22 fixtures in both normal and optimized Python, all 40 ordinary reports (24 original combinations, 8 runtime-K companions, 8 supplementary combinations), and all 118 registered profile objects, covering 72 distinct PTX/geometry partitions. Each profile object is linked to the frozen ordinary source/input/config/shape/runtime-K, actual mathematical PTX/cubin and host-once receipt. First failures, affected repairs and retained unit repairs remain separate; this does not upgrade a previously incomplete raw capture.

Independent compiler review found three false-pass defects in early checker versions: lexical rather than CFG reaching definitions, imprecise opcode-modifier matching, and unnormalized unsigned immediate arithmetic. The report retains these findings and closes them against the final byte-matched source and actual negative/positive results. Earlier checker passes are superseded by `writers-v9`.

`summary.json` identifies full SHA-indexed receipt archives retained in the workspace. Full private compiler objects stay there. The copied result files and review reports describe this limited scope; original frozen mathematical reports are not edited to change their historical `not_inspected` flags.

GCU and Ascend: their original 24 ordinary plus 8 runtime-K reports and compiler artifacts were rebound to the eligibility freezes, but their physical State writer lowering is still unverified. Their final source/loop boundaries and the original ordinary/default/sparse dependency-preservation work also remain open. This is not whole timeline-goal completion. No device application, old mathematical matrix, TP/UI matrix, SDK build, or performance measurement was repeated.
