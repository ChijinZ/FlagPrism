# Finite native iteration paths (R073)

The automatic NVIDIA native boundary report now contains `native_loop_sites`.
For already checked source/matrix reader pairs, the finite checker finds the
innermost natural loop, records its actual header, latches, exits and native
instruction PCs, and cuts all latch-to-header edges. The resulting iteration
must be a single-entry DAG; every return/exit path must pass both readers.
This uses iteration-local dominators, so a reader in an earlier iteration
cannot justify a later bypass. Work/node/backedge budgets are explicit.

Compiler review found M1 in the first freeze: the reused value-flow CFG retains
only fallthrough for conditional EXIT, which is insufficient for a loop exit
proof. The final efb2363 separately treats every potentially taken EXIT as an
exit obligation, including one whose fallthrough remains inside the loop.
Before-pair and before-end conditional exits are rejected; after-pair and
never-taken exits are handled without unnecessarily rejecting them. A partial
edit initially missed the new argument and result field, which the CPU tests
rejected; complete source and final normal installation pass. Failed attempts
remain in the full receipt archive.

Normal wheel installation verifies 641 members and byte-identical unchanged
native sources. The 22 loop and 13 existing matrix fixtures pass in normal and
optimized Python. Six retained actual captures (default/sparse runtime K3/K7,
and the original two-member scalar recurrence K3/K3) pass native path, raw
endpoint and independently requested count checks in both modes. The scalar's
final one-member expression outside the loop is not selected as that registered
recurrence; its loop diagnostic remains unverified. No SDK, native producer,
GPU mathematics or unrelated qualification/UI matrix is repeated.

Public offline reexport automatically includes the new loop report, preserves
8 identical counter trace bytes, and produces 2 new dependency traces. Only
those two changed traces receive fresh pinned actual Trace Processor checks
(180 endpoints/404 flows and all 263 stats each, no positive error/data_loss).
The counter checks and unchanged UI/exporter behavior reuse prior evidence.

This is native CFG iteration structure, not a source iteration number,
source-exclusive elapsed cost, participation, hardware completion, termination
or ordinary pipeline preservation. No iteration_id is inferred from record
order. The current ordinary/default/sparse objects have separately been located
for continuing the remaining pipeline gate; that diagnostic grants no schedule
qualification. The entire three-backend timeline goal remains open.

The maintained tests and commands are in Profiler/docs/timeline_testing.md.
Full immutable receipts, raw captures, actual TP stats and failed attempts stay
in the root workspace/server paths identified in summary.json. SDK binaries
and private compiler inputs are not included in this evidence directory.
