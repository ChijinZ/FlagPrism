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

The independent Ascend r13 cohort is now running on the final ec75 installation:
24 original ordinary configurations, then all baseline-eligible configurations
with cold/warm default profiling, plus separately reported strong state-writer
regressions. Its independent gate passed two actual public positives, 35
structural forgery negatives, eight layout positives and 63 boundary negatives.
Private math and verifier sources are not included here; only explicitly safe
aggregate/freeze metadata is copied. The snapshot intentionally records the
pre-authorization state; execution authorization is a separate later file.

The preceding cohort's original scalar-state failure remains preserved and
unexplained. Public cases and code reviews do not erase it or substitute for the
new complete matrix. Large archives, SDK libraries/headers, private qualification
code, credentials and caches are excluded from Git. `index.json` records original
workspace evidence paths and SHA-256 values. No paper or Study was edited.
