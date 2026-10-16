# Final admission and counter replay fix: real native builds and installed checks

Source: clean Git commit `1638a899d80c2ff134efbdb703aa695dbb39c39d`.
No paper/Study edits; no product edits by this build task; no GPU performance
benchmarks. This task is not an additional final code review.

## Real native builds

All three actual previous Ninja debugger targets consist of eight translation
units. The new `Bindings.cpp` was compiled from the exact new Git archive in a
new prefix using the original real compiler argv and unchanged flags. Each new
DSO was linked and stripped using its original real linker/strip argv, with
seven unchanged, SHA-audited objects and unchanged runtime/support libraries.
The seven objects' actual Ninja dependency sets were independently retained and
hashed (NV 1,826 / GCU 1,902 / Ascend 1,875 dependency entries). Every reused link
input's hash was checked before and after. Only the changed translation unit
was rebuilt; the core compiler and unchanged profiler module were explicitly
reused, not misrepresented as another full native build.

The public Enflame/Ascend assemblers and NVIDIA's actual setup Distribution,
`build_py` and `bdist_wheel(skip_build=True)` created new wheels containing the
newly compiled debugger DSO. No wheel ZIP patching or installed overlays occurred.
Each was installed into a new venv with the matching third-party dependencies.

| Backend | New prefix | Wheel SHA-256 |
| --- | --- | --- |
| NVIDIA | `/workspace/chijin-final-admission-fix` | `a9090e30a6efa9be2f81460b023ef600d068b391fd79dcdbcee100628944ca31` |
| GCU | `/workspace/chijin-final-admission-fix` | `b6f1df8454f34a14e2afb2808b567d04524dfa6e20177c6b8181386d0bc3100e` |
| Ascend | `/tmp/chijin-final-admission-fix-r2` | `c26ef419b3d64852f055ed131e60c305019c33d59a882239e644de87b2d4d88a` |

New interpreter: `<prefix>/venv/bin/python`. Actual compiler, profiler native,
and debugger runtime imports resolve inside these venvs. Ascend retains its
documented Torch/Torch-NPU import order; CPU import/test smoke did not initialize
NPU. Full Git archive (947 files), 68 component Python sources, parent Python,
stage, ZIP and installed members match. NV/GCU/Asc package entry counts are
597/438/379; native membership remains the same, with exactly one changed DSO.

## CPU checks and red baseline

Each new installed package: **171 passed, 3 skipped**. Existing optional browser
skips are explicitly excluded from pass counts:

- `test_untimed_and_unknown_browser`
- `test_evidence_browser_provenance[False]`
- `test_evidence_browser_provenance[True]`

These require `FLAGPRISM_TEST_BROWSER=1`; no browser implementation changed.
The passing set includes fine-grained source/report tests, export references,
portable capture/replay preflight tests, GCU grid/layout/stride tests and all
five actual native HOST admission tests. Fixture changes only redirect imports
to the installed package; original assertions are preserved. HOST tests dispatch
zero kernels and check the actual 104-cell/6,688-byte capacity.

Old ce00 installed NV native safely reproduces the bug on HOST: all three wrong
runtime layouts are unexpectedly accepted (red exit 1). The new native rejects
them; old failure logs remain alongside new evidence.

## Short functional checks

After root explicitly assigned device ownership, original public hardware drivers
ran unchanged mathematical, canary, source, full raw matrix and dynamic-count
assertions against the new installed packages. NVIDIA uses GPU 0 and its driver
contains uninstrumented and default calls. GCU uses GPU 0, baseline then default;
Ascend uses NPU 4, baseline then default. Controllers NV 18965 / GCU 353103 /
Ascend 1744938 naturally finished with exit 0 and no children.

GCU additionally submits three conflicting layouts to the actual new native
binding using real compiler metadata from the newly captured bundle. All reject
before dispatch. The same process then runs the unchanged original default
hardware driver successfully, proving recovery after rejection. This extra test
is an explicit engineering request, not hidden product replay. The initial
metadata-test script incorrectly assumed the exported resource map included
`debug_backend_name`; its KeyError occurred before prepare or kernel dispatch
and is retained. The corrected harness preserves the original compiler metadata.

All three device leases were returned to root; this task owns no device jobs.
Results do not close the separate pre-existing Ascend qualification state failure.

## Failures retained and evidence

Ascend first source-comparison attempt stopped before compilation because its
previous public build source intentionally omits NVIDIA-only
`tests/nvidia/reference_cupti.cpp`. The new r2 harness explicitly records this
non-build test omission; runtime native source changes remain exactly
`Debugger/python/Bindings.cpp`. The first prefix was preserved.

`summary.json` contains package/import/native/dependency/archive details;
`functional-summary.json` contains captured bundle totals and per-phase exits.
The three `*-evidence.tgz` archives hold exact small build/install/audit receipts,
original compiler/linker commands, dependency hashes, CPU logs and new DSOs.
The `*-functional-evidence.tgz` archives retain complete default bundles and
actual compiler caches; every archived file is SHA-verified offline. Original
failed probes, old HOST red log, Ascend first failed source comparison, and GCU
initial metadata-harness failure remain separate.
