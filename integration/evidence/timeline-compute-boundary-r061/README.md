# R061 finite NVIDIA compute-boundary regression

Implementation freeze: `77401f1c3ba3cc35d3367460664381d882bad293`.

An actual retained R058 recurrence object had adjacent entry/exit readers at
0x3f0/0x400, with the FFMA outside at 0x520. The old raw/canonical artifacts
remain unchanged (109 files). They are not upgraded into compute cost data.
The added finite checker rejects that actual empty bracket in both captures.

The new standalone tool was normally built from the exact formatted source,
then packaged/installed in `chijin-study-pro6000` (639 wheel members checked).
Other matching native/core inputs are explicitly unchanged and reused; the
separately built Ascend LLVM plugin is not a NVIDIA core build input.
Actual new tool SHA and source/SDK/compiler argv are in the build receipt.

Actual release-mode C1 first profile -> paused ordinary -> resumed profile
passed mathematical/input/tail/state-once checks (three mathematical calls).
The loaded profile object is bffb05682586487ad10e0510abb7c90115486a7cb20346ec00168777cc34efee.
Both captures freshly validate the actual object/PTX/native reader map, and
show entry 0x3f0 -> FFMA 0x400 -> exit 0x410. FMA contraction is preserved.
Each of eight displayed selected observers has three loop intervals in each
capture. Both have eight counter-ns exports. No performance claim is made.

The first CPU prototype accidentally retained the PTX debug flag; its native
placement is NOT the release qualification. A second CPU probe used the
actual parent mad-wide option and debug stripping. The final installed device
run also explicitly rejects debug PTX. No shipping O0/debug workaround.

Fourteen finite-rule tests passed in normal and Python -O modes in the
existing GCU Docker; two-pass formatter reached a fixed point and Python AST
was unchanged. The archive includes the exact formatted tested Python bytes.
The finite rule checks scalar FP32/int32/global32 instruction issue placement,
not arbitrary source regions or hardware completion. Source-exclusive cost,
engine busy time, predicate identity and overall goal qualification stay false.
No extra math matrix, UI sweep, SDK or core rebuild was performed.

Evidence archives contain bounded receipts/reports, not full private kernel
sources or vendor binaries. Full raw/object/PTX remain in their server bundle.
