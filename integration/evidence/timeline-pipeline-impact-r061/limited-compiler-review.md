# Finite compiler review of pipeline disturbance

Existing independent compiler reviewer: /root/timeline_final_sol61_compiler_r057. Requested configuration was GPT-6.1-Sol/xhigh; resolved provider model/depth remains unavailable. This follow-up is not a new full-goal acceptance vote. Read-only; no source edits or device runs.

The reviewer inspected the actual ordinary/default/sparse objects and the negative CPU clobber-removal probe. Conclusions:

1. The actual runtime-K example exhibits native scheduling disturbance. This cannot pass ordinary-pipeline-preservation acceptance, but does not quantify physical overlap loss.
2. All readers use side-effecting inline assembly with a memory clobber. Timestamp/payload values live to block-end publication. Those are concrete extra ordering/liveness constraints; a unique root cause has not been demonstrated. The new scalar compute fences do not directly fence MMA. Removing only the two matrix-reader memory clobbers did not restore the schedule.
3. Reducing constraints/liveness or using coarser observation boundaries are possible engineering directions, not validated universal repairs. Do not blindly remove all clobbers or force a fixed instruction sequence. Preserve the counterexample and explicitly distinguish instrumented execution from ordinary execution.
4. Existing qualified dependency arrows can still describe the instrumented binary: they bind actual binary, raw ordinals and observed endpoints. This example does not refute independently qualified submit/wait/publication/LDSM-consumer/reuse relationships. It provides no ordinary-overlap, engine-completion, or hardware-busy proof. Sparse dependency qualification remains rejected as recorded.

Root updated the quickstart interpretation note. No product proof right or acceptance requirement was weakened. The scheduling-impact acceptance gate remains open.
