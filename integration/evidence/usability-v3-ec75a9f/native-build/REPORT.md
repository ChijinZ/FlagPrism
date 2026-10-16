The three final packages passed native, package provenance, and installed CPU validation. Full delivery source is `2bc91bf`; packaged Python/source is `e6644ff`; actual native build input is `bd61acd`. The only difference between delivery and packaged source is `Profiler/docs/automatic.md`. `delivery-source-bridge.json` verifies 604 Python/native/patch files by Git blob and SHA256; each remote `native-e6644ff-source-bridge.json` independently verifies unchanged native inputs.

| Backend | Real compiled translation units | Reused objects | Relinked outputs | Installed CPU |
|---|---:|---:|---|---|
| Ascend | 7 | 476 | libtriton, triton-mlir-opt, debugger runtime, LLVM15 observer | 309 passed, 3 skipped |
| NVIDIA | 5 | 379 | libtriton, debugger runtime | 303 passed, 3 skipped |
| GCU | 7 | 348 | libtriton, debugger runtime | 303 passed, 3 skipped |

These are audited incremental native builds, not full core rebuilds. The original Ninja command graphs and dependency lists are preserved. All changed source/header dependencies forced compilation, including Ascend parent AutoBlockify.cpp. Reused objects were SHA256 verified and their dependency bytes compared with the frozen new source. Actual compiler argv, PIDs, logs, link inputs, and output SHA256 are in the evidence archives. Ascend used LLVM22 clang++ for core/runtime and LLVM15 /usr/bin/c++ for its observer. All compilation, installation, and tests ran in the existing remote Docker containers.

Final interpreters:

- Ascend: `/tmp/chijin-r13-ascend-census-v3/venv-e6644ff/bin/python`
- NVIDIA and GCU: `/workspace/chijin-r13-census-v3/venv-e6644ff/bin/python` on their respective hosts.

Every packaged Python file was matched against its component or parent source. Every package file was independently compared across stage, wheel ZIP, and fresh installed environment. Native imports resolved inside the new venv. Ascend CPU validation left NPU uninitialized. Browser tests have three existing opt-in skips on each backend.

The supplemental HOST probe checks 14 column/grid cases per backend: two physical-budget negatives and five layout downgrade negatives per case, before allocation. A legal HOST allocation must either reject the exact missing 64-byte alignment requirement or verify actual complete byte count, zero header/padding, and exact zero-observation decoding. Rejected allocations are followed by a successful ordinary HOST transaction. The C++ rollback frees device storage before any context registration; no allocation counters are exposed for a direct leak census. This CPU probe does not establish an NPU producer. Actual aligned allocation positives were Ascend 5/14 and GCU 1/14; all NVIDIA HOST addresses in the final supplemental run were rejected explicitly. Initial overstrict HOST-positive probe failures remain archived.

NVIDIA and GCU also passed one limited public default functional regression from the final installation, using fresh caches and unchanged public numerical/raw/source assertions. NVIDIA produced five captures (loop visits 0/1/3/7 and reduction); GCU produced three (loop visits 2/5 and reduction), with a separate unprofiled baseline. No device performance benchmark ran. Both owned process trees reached terminal state and the NV0/GCU0 leases were returned. Ascend NPU4 verification belongs to the visibility engineer; its device outcome is deliberately outside this report.

`summary.json`, `package-evidence-verification.json`, and `functional-evidence-verification.json` contain machine-readable results. Three package evidence archives include full native/dependency/package/test receipts; two functional archives retain every public bundle, raw capture, source snapshot, and cache artifact. Offline verification checked each package index member and every functional bundle manifest's bytes and SHA256.

Earlier provisional fbca package attempts were stopped when root required a final source gate. Missing-test-path and HOST-alignment probe harness failures were retained, corrected in the artifact harness, and rerun without changing production source or rebuilding/reinstalling successful final native libraries. No old installation, compiler prefix, driver, or daemon was modified.
