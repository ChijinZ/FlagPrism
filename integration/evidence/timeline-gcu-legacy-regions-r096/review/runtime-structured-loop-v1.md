# R096 finite runtime review: structured loop fallback

Requested reviewer: GPT-6.1-Sol / xhigh; actual resolved model/configuration remains unknown. Reviewed candidate freeze: `f46cb0cd47bcd733606c96d5889fd4143b899c13` (Git verified, clean at inspection).

Scope: `_natural_loops`, `_structured_loop`, their fallback connection to the existing direct rule, and the targeted loop fixtures. This is a continuation of this seat's finite R095 review, not another whole review. I did not execute product code, import it, run tests, contact a server/device, or read peer reports. Local stdlib reads included JSON/SHA and AST comparison of the executed Python input with the frozen formatted source.

## Conclusion

The hidden reset-entry finding is fixed and its targeted CPU regression is closed at the frozen-source level. No other confirmed open runtime defect was found in this finite loop delta. The record-cycle negative also rejects the previously accepted repetition, and the source retains separate unverified outcomes and `termination_qualified=False` / `source_iteration_id_qualified=False`.

Matching normal installation of `f46cb0c` was still running when this report was written. That distribution check remains pending; it is not substituted by source-loaded results. This review grants neither current-33/current-96 coverage nor whole-goal, SDK native scheduling or source-exclusive authority.

## M1 — Major, fixed: a non-dominated exit could hide an induction-reset entry

**Location.** `_structured_loop`'s initial-predecessor acceptance, now `Debugger/python/flagtree_debugger/gcu_llvm_regions.py:957`, with the added rejection at lines 970–982. `_natural_loops` recognizes only dominance backedges, as intended for natural loops.

**Trigger.** Start from the `continued-runtime` positive. Give entry a conditional edge directly to the ordinary exit as well as the normal header(0) edge. Change that exit to branch to header(0). The header no longer dominates this exit because of the independent entry edge. Consequently, the exit is outside the natural loop and is not counted as a second natural-loop latch. Previously it passed the initial-predecessor checks merely by being outside the natural body and forwarding zero. The selected-body traversal inspected the header's true edge and could still return `llvm_runtime_iteration_checked`, overlooking the exit/reset continuation.

**Consequence.** The analysis claimed its finite 0/+1/no-extra-reset loop family for an unsupported reset path. This is a qualification error; no raw ABI or hardware failure is alleged.

**Minimal verification.** `test_external_entry_does_not_hide_an_exit_reset_backedge` at `Debugger/test/gcu_llvm_regions.py:322` implements exactly this typed-CFG mutation. The retained old-version run returns `llvm_runtime_iteration_checked` and fails the required unverified assertion. This is a CPU structural counterexample based on a native-generated index, not a new device execution.

**Fix.** After identifying zero-valued initial predecessors, the rule now traverses actual CFG successors from the header and rejects any of those predecessors that can be reached again. The check includes paths outside the natural body and therefore closes this non-dominated-exit case. It uses the existing work budget and does not purport to prove termination. The strengthened no-reset boundary is consistent with the existing direct rule.

**Closure status.** The old-version negative failure is retained; the fixed normal and `-O` semantic suites each pass all 28 tests. The exact executed rule/test input and the frozen formatted files have identical ASTs. M1 is closed for code and the targeted structural regression. Matching installed execution is the sole pending distribution check below.

## Other finite checks

The natural-loop builder computes entry reachability and dominators, merges natural backedges by header, and limits dominance-set size and traversal work. The structured fallback requires one header/latch, the supported guarded 0/+1 induction, a dominating nonconstant loop-entry trip bound, and no external body entry. Unsupported cases preserve an unverified loop result rather than silently qualifying an arbitrary loop.

With the outer latch cut, the selected CFG is checked using two-pass SCC traversal. A cyclic component containing this region's begin, body, end or record is rejected. This matters because begin/end booleans alone can merge a second record traversal into an already ended state. The retained `test_continuation_cycle_cannot_repeat_a_record_before_the_latch` demonstrates that old acceptance and the fixed rejection. This report does not attribute that independently added negative to this seat's discovery.

The separate `(block, begun, ended)` propagation then requires each reached latch state to contain one begin and one end; paths leaving the declared body/header boundary fail. Inner control cycles that avoid this region's protected members can remain accepted with termination explicitly unqualified. I found no additional concrete false-pass in these bounded rules. This is not a general CFG/ISA or all-path liveness claim.

## Primary receipts read

All evidence paths below are under `artifacts/timeline/run-096/preflight/`.

- `phase-receipts-v2/runs/loop-fixes-v1/terminal.json`: terminal 0, 4.921716710 seconds, script SHA `76963d6b1e46c9ca96d57493d99c2d14da12d01dd90dd5fea2874cee8d642bdd`.
- `output/previous-regressions.log`: both the repeated-record and hidden-reset tests fail against the old helper because it returns `llvm_runtime_iteration_checked`. These old failures remain explicit.
- `output/semantic-normal.log` and `semantic-optimized.log`: 28 tests in each mode, all passing. `output/result.json` binds executed rule SHA `9ba6e785a46f616ac3c4b53b064e26cbcc8eb9de69652c5666ac9da780707f7e` and records `device_executed=False`.
- `phase-receipts-v2/runs/format-v3/output/result.json` and `formatted.tgz`: rule freeze SHA `dc53b79749476bf6be646c8939fad23de5d0cb5c7ce4bd254b0dd53ad7642fe8`; test freeze SHA `4ae12a7ccfe53cfdb720edec0ad3e7cbc3c8038ae883c478aa93a87ce61ae72f`. These match the local freeze. Reading `loop-input-v1.tar` and comparing stdlib ASTs independently confirmed both executed Python inputs are AST-identical to those frozen files.
- The 22 entries in `phase-index-v2.json` all match their local size/SHA.
- The same result records representative retained-object local checks of 24/26, 40/60 and 31/76, and marked-object local checks of 11/13 and 10/13 with loop counts 1/0. Those denominators are local region results, not a runtime-loop coverage claim for the legacy inventory. The previously reported legacy loop count of zero is not upgraded by this report.

## Remaining verification and scope

The matching normal wheel/import and installed 39-binding/28-rule/10-index normal/`-O` checks were reported in progress, with no terminal receipt supplied to this review yet. The minimum remaining action is to read that matching terminal/result and logs when available; no new test matrix, device run, mathematics, SQL or UI is requested.

The legacy call-role/source inference and native index ownership changes are outside this requested loop review. The representative local checks do not prove their whole applicability. Previously closed image, clock, owner, State and pipeline gates were not reopened. No optional additional proof engineering is requested.

## Matching installed closure addendum

The pending distribution check above is now closed. This addendum only updates that finite verification status; it does not change the whole-goal/applicability limits.

Read `preflight/installed-receipts-v1/installed-index-v1.json`: all 40 listed files match their local size/SHA. `runs/normal-install-v1/terminal.json` is terminal 0 / 55.644590683 seconds. Its result binds source `f46cb0cd47bcd733606c96d5889fd4143b899c13`, 503 installed members and wheel SHA `7df283276425f632b04813437447bb8317cc0ffbad3988bbe0693a99593862c1`. All 17 recorded steps return 0. The actual normal/optimized logs each show 39 binding tests, 28 rule tests and 10 native-index tests passing. This includes the installed execution of the hidden-reset and record-cycle negatives, so M1 now has matching distribution closure as well as the earlier source/fixture closure.

`runs/installed-actual-v1/terminal.json` is terminal 0 / 39.171288621 seconds. The matching script (`4133c5f133ee547ab655bbb2ecafc077ebdb7809a8bbe5c73f19415b2e9b7792`, read directly) loads the normally installed helper; its output binds rule SHA `dc53b79749476bf6be646c8939fad23de5d0cb5c7ce4bd254b0dd53ad7642fe8`. It checks packaged tool SHA `dbf87c0b27eee010b88fcd2371002fd1aadf037d9dca4d56fd3b896dccc8ceae`. The run reevaluates 33 retained objects with the installed rule, reusing an existing typed index where the retained LLVM bytes match. It is not evidence of 33 fresh SDK/device executions. Reading its result gives 1,013 local region checks, at least 19 per object, and **zero checked runtime loops** in that legacy inventory. `device_executed`, `application_replayed` and `native_schedule_qualified` remain false.

The narrowly corrected barrier/getter negative was also read. It now obtains positive `body_refs`, modifies only those rows, and directly requires `_body_family(..., legacy=True)` to reject with the intended `typed compute body` reason before checking the complete region. That prevents a damaged counter/record from accidentally satisfying the intended negative. Normal and `-O` logs each show that one method, with both callee subcases, passing against the installed product. This is a test-only change after the product freeze; it does not require or imply a different product installation.

No additional confirmed defect or necessary test is identified by this limited addendum. The finite M1 and its matching distribution gate are closed. The 33-object local inventory does not supply current-96/whole or SDK native qualification, and the earlier scope exclusions remain in force. No product, test, SDK or device was executed by this reviewer for this addendum.
