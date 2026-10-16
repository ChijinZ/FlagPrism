# Fixed SDK public hardware regression

The frozen public 12-cell experiment passed on Ascend910B NPU4 inside
`chijin_v3.5.x`. Scalar, vector and atomic State observations were exact
integer 1 for both BM16/BM32 and ordinary/default profiling modes. Every
process called the kernel once; math, input/canary, terminal and actual compiler
identity checks passed. The original unmodified public source is unchanged.

This is a public hardware regression, **not full independent product
qualification**. The earlier independent 42/44 profile result and its two real
State failures remain historical failures until the original-source rerun.
No earlier result, input, tolerance or State gate was rewritten.

Product checkout: `cb968eb8d1891bd1ec6ad2574e070747a0f80986`.
Installed Python source: `a829a3312af69c1b961919025053829d7096a2b1`.
Native runtime remains the previously built/verified unchanged native bytes.
The isolated SDK compiler, its actual execution identity, installation wheel,
source pins and public-only authorization are in `sdk-seal.json` and the two
identity/State gate receipts. Subsequent evidence-only commits do not alter
those tested runtime bytes.

The complete retained public archive is:
`artifacts/usability/run-013/state-failure-forensics/r15-strict-preparation/public-state-strict-evidence.tgz`
in the project workspace (1,679,087 bytes, 271 files), SHA256:
`67781c88999fdcb4420d538f1195a090b177c03bbaf43e3bc69c10ebaf1539e7`.
The included original `evidence-index.json` indexes that complete archive;
it is not an assertion that all generated IR/NPUBIN are checked into Git.
This directory retains each actual result/receipt and the terminal/gate/audit
summaries. Full generated public metadata, LLVM and NPUBIN remain in the
hash-indexed archive. No SDK executable, library or SDK bytecode is included.

Root independently verified all 270 indexed files, all 271 archive members,
12 original results and actual identity gate records. A fresh remote `ps`
confirmed both controller PIDs absent. The ownership audit checked 14 PIDs
and 13 groups with no live process, zombie or remaining descendant. No GPU
performance measurement was taken, no retry or hidden replay was used, and
no paper or Study file was changed.
