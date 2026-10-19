# R076 owned tool child registration cleanup

Runtime source: `61cb831` (four Python call sites plus 12 regression cases). Native code, recorder ABI, clock/decoder/export schema unchanged. Three normal wheels installed in the existing server Docker containers; all wheel package members checked byte-for-byte and native sources matched before explicit object reuse.

The old installed NVIDIA runtime reproduced 10 failures / 2 passes with real owned sleep children. The source-loaded fix passed all 12; this is separate from the final normal installed results. Each of NVIDIA, Enflame and Ascend then passed the same 12 fixtures in normal and optimized Python (72 installed cases total). The tests check direct-child returncode and reaping before their own cleanup fallback.

Positive CPU tool checks use retained actual inputs: NVIDIA native LLVM transform (43 sites), Enflame execution MLIR rewrite (13 sites) and SDK identity bitcode compilation, Ascend actual ELF DWARF inspection. No device execution, math replay, new TP/UI run or performance claim.

Enflame first install stopped because system Python has no ensurepip; that terminal1 remains in the archive. A separate bounded resume used existing system pip --python to install the same generated wheel in its new venv, checked its installed members, and completed both test modes. No assembler or native build rerun.

`summary.json` contains actual installation paths and archive hashes. Full receipts stay at root artifacts/timeline/run-076/preflight/*-receipts-v1.tgz. The original three independent R075 whole reviews are preserved here, frozen to their original revisions; they do not certify later edits. Their whole-goal gaps remain open. The finite R076 runtime review only closes the owned-child finding after its installation addendum.
