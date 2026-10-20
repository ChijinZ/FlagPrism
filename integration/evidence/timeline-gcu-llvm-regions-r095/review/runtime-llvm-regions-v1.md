# R095 finite runtime review: LLVM region/record binding

Requested reviewer configuration: GPT-6.1-Sol / xhigh. Actual resolved model/configuration: unknown; not exposed to this reviewer.

Initial reviewed freeze: `734e0968046326e8de3ee00f2b312106d84b55b3`. Corrected product freeze: `4ae3561735a186a5ad2352ac901a168a93517709`, verified with Git. The later working-tree modification to `Profiler/docs/timeline_runtime.md` was read as documentation, not represented as part of that commit.

This was a finite review of the new GCU LLVM boundary rule and its normal/offline integration. No product was imported or executed locally; no tests, SDK, device, SSH, application, SQL or UI were run by this reviewer. Local operations were source/Git/text/JSON/tar reads, SHA checks, and writing this report. No peer review was read or used.

## Result

The continuation misclassification confirmed below is closed in `4ae3561`, including matching normally installed tests. No other confirmed blocker, major or minor remains from this finite runtime review. The tuple/record checks and the normal/offline connection support the stated local LLVM facts, with runtime-loop qualification reported separately. This is not a whole-goal or current-96 applicability sign-off, and it does not grant native schedule, source-exclusive cost, source iteration ID or hardware-busy authority.

## Confirmed finding and closure

**M1 — Major, fixed: a continuation could repeat end/record without a new begin and be classified as having no enclosing runtime loop.**

- Location: original `_loop` in `Debugger/python/flagtree_debugger/gcu_llvm_regions.py`, immediately after the forward traversal from the record/full join; corrected branch is now lines 656–665. Local result handling is at lines 625–637.
- Trigger: the selected begin executes once, then the continuation branches back to the previously accepted body, end or record block without returning through begin. The first begin→end tuple can be valid, while later records reuse that begin. Originally, absence of begin from the continuation's reachable set immediately returned `no_enclosing_runtime_loop`.
- Consequence: a consumer treating that result as an ordinary single execution could miss the unsupported repeated-record lifecycle. This affected the analysis claim, not the recorder ABI or the existing raw bytes.
- Minimal reproducer: start with the actual native-indexed straight fixture, replace its join terminator with a conditional edge to the existing end block and an edge to its original exit, and analyze it again. `test_continuation_cannot_repeat_end_without_a_fresh_begin` at `Debugger/test/gcu_llvm_regions.py:394` implements this typed-index mutation. It is a CPU structural negative, not a new device execution or native scheduling proof.
- Direct old-version evidence: `preflight/delta-receipts-v5/runs/regions-v5/output/previous-freeze-regressions.log` retains the assertion failure against the previous freeze: actual result `no_enclosing_runtime_loop`, expected `unverified`.
- Fix: before returning the no-loop result, the corrected code intersects continuation reachability with every accepted path's body, end and record blocks. Any intersection rejects the no-loop claim. The existing `ValueError` handler produces `loop.status=unverified` and a concrete reason.
- Scope of retained positive facts: keeping `region.status=llvm_observer_boundary_checked` is acceptable for the local begin→first end/record tuple. It cannot establish fresh pairing for repeated dynamic executions. Such a claim separately requires `loop.status=llvm_runtime_iteration_checked`. The documentation now makes this distinction explicit.
- Closure evidence: source-loaded V5 normal/`-O` each ran 20 tests successfully; the old continuation negative failed on the old source. Matching normal-install-v3 at source `4ae3561` subsequently ran the same 20 native-index semantic tests and 39 binding tests successfully in both modes, with controller terminal 0. No additional test is required to close this particular finding.

## Reviewed runtime/record behavior

`gcu_timeline.tool_identity()` includes `gcu_llvm_regions.py` in the existing content fingerprint. `bind_execution_structure()` checks the supplied final LLVM SHA against `debug_execution_native_ir_sha256`, obtains the native typed index, validates its schema and unchanged rights, and calls `analyze_regions()` with this object's manifest. The wrapper retains the actual LLVM, index-output and manifest digests; later binary attachment uses the existing exact input/binary binding.

Offline `inspect_native_execution(binary, metadata, llvm_ir=...)` snapshots the binary, validates the original fatbin/ELF/target binding, checks the supplied LLVM digest, and invokes the same structure builder and rule. It does not return cached `boundary_report` as fresh authority. Missing LLVM stays unverified. A legacy fabs capture lacking the actual linked input stays unverified. The original producer metadata is preserved. The four-mode fixture covers supplied/missing/different/legacy input; these mocked integration checks are distinct from the actual installed reinspection below.

The reviewed `_record()` checks the fresh attempted-count load after the end reader, unsigned manifest-capacity guard, `INT_MAX` saturation and sequence increment, normal/full rejoin, and the entire straight record block. It requires exactly 32 unique i32 field stores at the guarded sequence's slot, including magic, site, kind, sequence, begin/end low/high, physical identity fields and seal. Unknown effects, extra stores, overlapping/foreign field addresses and stale/wrong required fields are rejected. I found no prefix-only acceptance in this record check. This remains a finite LLVM shape and tuple check; it does not independently re-prove native publication or State payload semantics.

The loop check remains finite and conservative: a supported runtime header/induction/latch must pair each selected path with begin and end, and unsupported cycles/entries become a separate unverified loop result. The corrected continuation branch does not lower record integrity or broaden accepted native/clock rights.

## Direct evidence read

All paths in this section are under `artifacts/timeline/run-095/`.

- `preflight/delta-receipts-v5/`: read the semantic normal/optimized logs, old-freeze regression log, source/actual result, formatter result and relevant typed fixture. Its 69 indexed files matched their recorded size/SHA. Formatter output gives rule SHA `5c99a53f1ca21b3447046a64b49e970d17e52f647159535ad2d5dfc09598eab6` and test SHA `bea3838c80c0a9372bbccb5ad97ab9d757581247c04dde2a90dd90ea71bdbfe5`; both equal the corrected local files. The integration source SHA is `3823c0fd9ce494ef8b1004f8ec9ddae3dd69bf56fabb72d36c76d723d93cff8c`.
- `preflight/installed-receipts-v1/runs/normal-install-v3/`: terminal 0, 55.300713808 seconds, source `4ae3561`, 503 installed members, wheel SHA `a115e6ceb2ecb1e5794709b18642728e149138255e7d2e5a2156d603c6a083cc`. Read result, all step return codes, test logs, native input record and assembly/install output. The matching installer script SHA is `75bd4b3ca0ce40bfa7e58d6981576b317f71671d417788b7e2a95e7224667a4d`; its member loop compares installed files to the wheel. Both modes pass 39 binding tests and 20 native-index tests. The `-O` pytest warning is retained; the separate rule tests use unittest assertions. The 32-file installed evidence index matched size/SHA.
- `preflight/installed-receipts-v1/runs/public-regions-v1/`: actual installed read-only reinspection of two retained captures produces 11/13 and 10/13 local boundary checks, respectively; only the first has one checked runtime loop. Original capture SHA/metadata remain unchanged. Both recorded SDK decoder children are terminal 0. In the first object sites 9/12, and in the second sites 9/12/13, remain unverified with `No original source body/caller in selected clock bracket`.
- The same task's math result records ordinary 2/profiled 2 calls, math/input/tail guard/host-once success and 22/20 events. **The task's original controller result remains 1.** Its traceback is the later checker resolving a capture-relative filename from the wrong root; the success-named intermediate JSON does not override that terminal result.
- `preflight/post-receipts-v2/runs/public-post-v1/`: separately read the actual public `load_capture` checker, matching script SHA `55f429236fc3efd51aa08c18d73ff36bf6720cf45295de54157c4228124fd59d`, terminal 0 / 0.715718437 seconds, and result. This CPU-only followup reads those already produced captures using their proper root; it confirms 11/13 and 10/13 local checks, loop counts 1/0 and 22/20 events. It binds the original math result SHA and records no application replay. Its five indexed files matched size/SHA. The misleading v1 post archive, which only repeated older directories, is not used as post evidence.

## Verification gaps and optional work

There is no remaining verification gap necessary to close M1 or this finite normal/offline record-rule integration. The two real objects are evidence for their reported sites and the finite implemented rules. They do not, by themselves, close the previously outstanding whole-goal source/loop applicability inventory: unsupported sites still need their existing required applicability decision before being claimed. That is not a reason to replay the already passed mathematics or SQL/UI, or to add a general native ISA/CFG prover.

No optional expansion is requested by this review. Previously closed clock, image parser, owner/release, State, budget and pipeline gates were not reopened.

Read scope: new rule module, relevant normal/offline `gcu_timeline.py` changes, semantic rule tests, structure/location binding fixtures, the corrected continuation delta, documentation clarification, and the primary receipts listed above. Not read/revalidated here: peer reports, complete historical matrices, whole current-96 applicability, all SDK private native code, or unrelated product changes. Other conservative expression/loop-entry changes in the corrected commit were read in the delta and covered by the installed suite; this report does not attribute another reviewer's finding to this seat.
