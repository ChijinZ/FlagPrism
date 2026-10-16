# Ascend v3 engineering checkpoint — full qualification running

Product source: `ec75a9f0592c76f22d64eff443034ab89442b477`.
Native/frontend/parent-patch source: `bd61acdadc8b9582f243ca1ee5dc1869ed73e4ad`.
This checkpoint does **not** declare the overall usability goal complete.

Compact Ascend v2 storage lost writes when actors shared a 64-byte cache line.
A public same-marker dual-write diagnostic retained all 48 cells in isolated
storage while the compact buffer lost 20 cells. V3 uses a 64-byte header and
cache-line-aligned actor banks. All physical padding counts toward admission.
Historical v1/v2 bytes remain readable, with unknown visibility loss and inexact
counts; zero cannot establish non-execution. Regenerated views preserve original
producer evidence and consistently retract historical exactness claims.

True changed-source native builds compiled Ascend 7, NVIDIA 5 and GCU 7
translation units and relinked their affected outputs. SHA-audited unchanged
objects were reused; this was not a full rebuild. Final clean installs contain
exact ec75 Python with identical validated native bytes. Installed CPU checks:
Ascend **320 passed**, NVIDIA/GCU **314 passed each**, with **3 optional browser
skips per backend**, excluded from pass counts.

Real public default hardware checks passed: NVIDIA 5 captures, GCU 3, Ascend
one mixed case and one vector-loop case. The Ascend mixed case retained all 48
cells; the loop case retained eight loop cells with count four. Original source,
path and old cache were kept during the successful upgrade check. Hardware used
the e664 package; its compiler/logger/native bytes are identical to final ec75,
which changes only reader and regenerated-view handling. No NVIDIA device
performance/overhead benchmark was run.

All three extra explicitly requested GPT-6.1-Sol/xhigh code-review seats completed
finite affected-source and final-install receipt review. Confirmed findings are
closed. Tool acceptance proves the requested configuration, but the tool does
not expose the actual resolved model version. See `review-state.json`.

The independent Ascend r13 main cohort naturally completed with **22 eligible
and two ordinary State-assertion failures out of 24 original configurations**.
Of 44 actual cold/warm profiles, **42 passed the full gate and two failed the
original scalar-State assertion in the real CLI**, without timeouts or retries.
One reproduces the historical failure on the same exact configuration: its
current ordinary run and warm profile passed, while the cold profile failed.
The historical failure is preserved; no root cause has been established, and
this checkpoint does **not** meet the overall stable-usability acceptance.

The separately frozen new mathematical kernel passed four ordinary cases and
eight cold/warm profiles, including 16 same-binary runtime calls. Two stronger
known-case profiles also passed their derived full gates and required State
markers. These results do not remove the main failures. The independent final
[safe report](qualification-final/REPORT.md) retains every denominator and failure. The independent
gate passed two actual public positives, 35 structural forgery negatives, eight
layout positives and 63 boundary negatives. A further same-byte CPU supplement
checked the actual generated LLVM inputs against executed driver arguments for
all 42 successful main bundles (52 generated inputs, 2,389,666 bytes). The two
CLI failures lack complete exported compiler bundles and are excluded from that
supplement, rather than counted as passes. Original results and raw evidence
remain unchanged. Private math and verifier sources are not included here; only
explicitly safe aggregate/freeze metadata is copied. The snapshot intentionally
records the pre-authorization state; execution authorization is a separate later
file.

Large archives, SDK libraries/headers, private qualification
code, credentials and caches are excluded from Git. `index.json` records original
workspace evidence paths and SHA-256 values. No paper or Study was edited.


A finite [public diagnostic](scalar-state-diagnostic/public_state_probe.py)
reproduced the scalar-State discrepancy independently of the private mathematical
cohort. Its [results](scalar-state-diagnostic/FINITE_RESULTS.md) distinguish
mathematical/canary success from State correctness; diagnostic exit zero is not
qualification success. All twelve fixed cells completed, and no owned device
process remains. The referenced 1.17 MB raw archive stays in the workspace rather
than Git. Only safe receipts, source and an independently rehashed index are
included here. A compiler-legality candidate is under development in an isolated
SDK source/tool prefix; no compiler repair is claimed by this checkpoint.
