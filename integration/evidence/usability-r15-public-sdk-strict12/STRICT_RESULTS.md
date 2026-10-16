# Fixed SDK public strict12 result

All 12 frozen public cells passed. Controller, independent exact-integer State==1
gate and actual compiler identity gate each exited 0; suite exited 0. No cell was
retried, skipped, warmed up or timed out. Each process attempted and returned one
kernel call and synchronized. All eight math/input/canary checks passed per cell.

| Configuration | State | Ordinary | Default detail auto |
|---|---|---|---|
| BM16 | scalar | [1,1] | [1,1] |
| BM32 | scalar | [1,1] | [1,1] |
| BM16 | vector | 1024 values, all 1 | 1024 values, all 1 |
| BM32 | vector | 2048 values, all 1 | 2048 values, all 1 |
| BM16 | atomic | [1,1] | [1,1] |
| BM32 | atomic | [1,1] | [1,1] |

Public source remains b09827d6f088e3b1d6484e8a3dbd8b341ce467e6eb6821164028dee2e49b774e.
Root-approved seal is a10392fe518b3be04f505d6c31c19878803d3521c03cb169d710de2999e90f7b;
pending candidate bb534 remains preserved. Every actual compiled metadata identity
matched fixed compiler realpath and SHA
1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e.
Every default actual finished driver receipt/handoff and command also matched.

Actual suite PID/PGID 2004238/2004238, startticks315412548; controller
PID2004273/PGID2004238, startticks315412608. Terminal audit checked 14 owned PIDs
and 13 groups: owned_live0, rows[], zombies[], remaining_descendants{}. Both suite
and controller no longer exist in /proc. Post-run vendor proc-mem reports no
process in device. NPU4 lease returned to root; no further device work started.

Safe archive public-state-strict-evidence.tgz has 271 files/1,679,087 bytes,
SHA256 67781c88999fdcb4420d538f1195a090b177c03bbaf43e3bc69c10ebaf1539e7.
Its evidence-index.json records exact public result/receipt/source/generated
LLVM/final npubin hashes. SDK libraries, archives and bytecode are excluded.
Raw complete State values, plans, host ledgers, actual metadata, driver receipts,
capture argument/launch pointer evidence and generated LLVM are retained.

This is the fixed public 12-cell hardware regression, not the full qualification
matrix. Prior R14 diagnostic results and the two original qualification failures
remain historical evidence requiring the independent original-source rerun.
