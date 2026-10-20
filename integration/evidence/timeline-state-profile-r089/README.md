# Finite State writeback follow-up (R089)

This change updates only the Ascend QA partition checker and its tests. It does
not change the runtime recorder, SDK, clock, device trace ABI, or installed native
component. No device/application/math/Trace Processor/UI replay was performed.

Both retained ordinary supplementary sets (q07/q08, two shapes, two configurations)
now have actual State-under-reviewed-SDK sidecars: GCU 8/8, 262 transfers; Ascend
8/8, 66 transfers including two zero extents. Each backend covers 17,140 i32 State
elements with exactly one physical writer. Actual CPU codegen reproduced every
original whole binary byte for byte. The independent ABI review and contracts
limit those conclusions to these retained objects.

Ascend's final profile-State-v4 uses the exact committed checker/test bytes
(source-freeze-v4). Forty-one normal and optimized fixtures pass. All 96 current
actual profiling rows partition successfully, using 40 distinct analysis keys,
132 actor parts, 1,143 transfers, and 183,048 State elements. Actual adapted LLVM
inputs and linked resources come from the original recorded codegen handoff;
this check does not recompile the SDK or rerun profiling. Profile partition alone
does not grant SDK ABI, native-boundary, pipeline, or whole-goal qualification.
The separately reviewed profile sidecar completes successfully in 4.772533455 s,
with 96 State/SDK-ABI qualifications. Native boundaries and pipeline remain false.
Its contract fixes 63 resources including reviewed inventory/partition row bytes,
actual executed sources, terminal, compiler and linked libraries.

The exact SYS_CNT register-read and empty source-census assembly comment are
recognized. All other assembly is rejected before ordinary direct-call parsing.
This closes the independently identified @fake() comment parser bypass. Unknown
clock-derived State offsets still fail conservatively. The independent compiler
report binds the final executed files, not the earlier formatting snapshot.

All earlier failed attempts remain in the workspace/server archives: rejected
360-second launcher, old-checker SYS_CNT refusal, initial clock-result KeyError,
and pre-M1 execution. They are not current mathematical failures or final passes.

Full private LLVM/SDK inputs remain in the workspace/server, outside Git. Archive
indices and SHA audits, scoped reports, runners, compressed row chunks, terminal
receipts and exact stdout are included here. QA formatter used yapf/check-ast;
Ruff skipped this directory. This is progress, not final whole-goal acceptance.
