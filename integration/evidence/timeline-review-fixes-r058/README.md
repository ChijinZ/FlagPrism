# R058 targeted final-review fixes and actual regressions

Runtime implementation freeze: `46c23c65fced45e7afb22412a08953a40fc71fe2`.
This is affected evidence, **not a full P01–P10 qualification certificate**.
No paper or Study text changed. No performance measurements were run.

The original three independent reviewers are recorded in
[the R057 review input and reports](../timeline-final-review-r057/README.md).
Their limited followups closed the confirmed source defects after inspecting
actual source/CPU receipts. R1 additionally caught a bare-opt PATH resolver
boundary; `3e51bae` fixes it, with two actual JIT entrance fixtures. Requested
model/depth remain GPT-6.1-Sol/xhigh; resolved serving configuration is unknown.
Followups did not review each other's reports, modify code or run device tasks.

## Fixes

- `ea23c0f`: reinstall unmanaged Ascend/GCU timeline collectors on resume.
- `e0c24b4`: GCU native prefix/suffix guards, complete physical readback,
  ambiguous-free quarantine, and physical cumulative admission accounting.
- `426729b`: forward timeline site budget into the counter child.
- `d2d6d53`, `3e51bae`: bind plugin/tool/link-resource identity before both
  Ascend JIT lookup entrances; match actual opt PATH execution.
- `f73870a`: preserve historical dependency receipts but recommend only the
  currently qualified traces; current refusal revokes old recommendations.
- `607c137`: fingerprint GCU's actual delegated native decoder.
- `46c23c6`: use validated canonical invocation identity for qualification.
  GCU's canonical namespace is deliberately different from its physical owner;
  identity checks are preserved, not weakened.

## Results and original failures

`*-current-install.json` describe the final matching wheels. Changed native
runtime/Bindings sources were normally built on all three servers; subsequent
Python-only fixes reused those byte-matched native inputs. Actual initial builds
and normal imports are in root run058 archives. Each process has a bounded
controller identity and terminal record. Final install members were checked
against the actual wheel, not a source overlay.

NVIDIA and Ascend resume receipts each cover three C1 mathematical calls and two
captured internal timelines. GCU's first composite test completed the resume
subcase (28 positive intervals and two ns exports per capture, both physical
guards intact), then failed because its test searched the public output rather
than the exception's retained staging path. Preserve its terminal 1. The next
test failed before any mathematical call due to a test import scope error.
The final GCU guard-only attempt covers two mathematical calls: actual SDK
prefix corruption, native readback detection, raw preservation with no derived
trace, then a successful new session. Both failed test attempts remain here.

Actual retained Softmax reexport moved two old dependency traces out of current
recommendations while preserving all 31 original artifacts. No application or
device execution was involved.

The first GCU retained reexport failed due to the canonical/owner namespace
mix-up above. The final installed reexport of the same two actual captures
passed, explicitly included the delegated decoder SHA in its canonical inputs,
reproduced four counter traces byte-for-byte and preserved 47 original files.
There was no kernel replay or repeat UI browsing.

CPU evidence in root run058 archives is explicitly source-overlay development:
normal/-O each 8 Python + 21 native-source SDK-stub cases for the initial fixes;
46 + 11 subtests for identity/store/registry; 29 prepare/cache tests plus two
actual JIT PATH fixtures for bare opt; 13 affected store/qualification tests for
the canonical namespace fix. It does not substitute for the device receipts.

## Remaining full-contract work

The original review verification gaps are not waived by these bug fixes:
Ascend unknown reserved slots/default selected-observer completeness; final
source-region/runtime-loop boundary evidence; ordinary/sparse/default dependency
and schedule preservation; and a complete SHA-linked actual TP/SQL index for
independent accepted traces. Reuse retained objects/traces and existing actual
receipts; run only missing deltas. Keep Ascend BK64 sparse1 failure, unavailable
native mechanisms and the old unreproduced NVIDIA zero-record anomaly explicit.
Canonical branch merge/push and final contract audit have not occurred.
