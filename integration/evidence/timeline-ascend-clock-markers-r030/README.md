# Ascend automatic clock debug locations (r030)

Product source: `4ed2aab` (the actual build input records its f7be925 base plus
exact dirty-source hashes). The LLVM15 plugin is genuinely rebuilt; the matching
census-v3 frontend core is reused. No paper/old Study files changed.

## Implemented behavior

The automatic late producer gives each SYS_CNT read a private DWARF file and
site/phase line: `__flagprism_sys_cnt_v1__`, entry `2*site-1`, exit `2*site`.
Only that clock call gets the new debug location. User source and lexical/inline
scope are preserved. Missing debug scope is explicit in the site manifest;
raw collection stays usable. Counter units, source bounds, epochs and engine
activity are not certified by the marker flag. Physical record/launch ABI and
legacy census behavior are unchanged. No per-operator adaptation is added.

`tests/timeline/ascend_clock_marker_probe.py` runs real opt15 transformations for
AIC/AIV with and without debug scopes, normally and with Python `-O`. It checks
site/phase locations, original source navigation, missing-scope behavior, and
complete transformed fixture function equality after stripping debug info.
Legacy census and invalid column/semantic fixtures also run against the rebuilt
plugin. Cached full pre-commit checks converge in GCU Docker before compilation.

## Real installation and machine evidence

Existing Docker `chijin_v3.5.x`, NPU4 `Ascend910B4-1`:

- Plugin SHA: `986dec30a0e598c3ecd62bb6965815d125fb85061e31c32beea51ef35cde1143`.
- Wheel SHA: `2942d1c6d4e99f910fa281df9103ab90225e1e749a9d68fc8ece84f971d4abcb`.
- Python: `/tmp/chijin-timeline-r030/runs/install-v1/output/venv/bin/python`.
- Byte checks: 400 installed wheel members, 88 component Python files, 664
  source inputs, matching actual plugin sources and binary. The related CPU
  contract delta passes 21 tests normally and 21 optimized; unchanged full
  runtime/store contracts are not rerun from r029's 102+102 matrix.
- Actual public recurrence K3/7 (same binary, two streams) and Softmax pass math,
  state, input/tail and guard checks: 3 captures, 50 raw internal intervals and
  100 raw endpoint references. Public/normal/optimized offline re-export passes
  without application replay and with original environments denied.

A CPU-only SDK reference compiles all X0..X31 SYS_CNT destinations in one
132-byte executable section (32 four-byte reads plus return); X32..63 and X64
are rejected. Generic and fixed-register references agree, while MOV X0,0 has a
different encoding. This is a small target-specific reference, not a general
instruction decoder. Sources, commands, objects and warning/error outputs are
retained.

The final **loaded ELF**, not just LLVM text, retains exact clock DWARF rows.
The independent inspection checks every planned entry/exit row against an actual
reference SYS_CNT word in executable code: recurrence 12/12 and Softmax 10/10
static positions. No nearest-PC matching is used and phase aliases are rejected.
Both complete executable-section byte sequences equal the r029 instrumented
images. That establishes no extra instruction perturbation for these two
samples; ordinary-kernel equivalence or universal source bounds are not inferred.

## Failed harness stages remain visible

All ten recorded installation/CPU/math/offline/dwarfdump steps return zero.
The enclosing installation controller then returns **1**, because its final
summary variable was shadowed by an actor-object receipt, causing a KeyError.
No original receipt, failed script or finalization status is overwritten.
A separate inspection consumes those exact successful stage outputs and records
both the failed controller and its own success; no math/SDK compilation is
replayed to repair a summary.

The first inspection rejects a private-file DWARF line-zero row. The actual
outputs show one such compiler-generated/no-source row per image. Version 2
ignores only line zero, while still requiring column zero, every planned phase,
unique executable extent, exact opcode and non-aliasing addresses. The failed
version remains in the archive. These are development-harness failures, not
hidden passes of the enclosing job or full P01.

## Retention and remaining work

Workspace archive:
`artifacts/timeline/run-030/preflight/ascend-clock-marker-evidence-v1.tgz`
(7,438,468 bytes, 1,304 members,
SHA `d9efe10eec1b2fbd2add97b1d2b5a1707defcf5c6e7dc01afd2e11b894fe3a52`).
`verification.json` records exact binary/row/word checks and explicit false
unit/source/async qualifications. Twenty-eight recorded process identities are
inactive; `owners.json` additionally checks 16 nested opt identities and finds
no active private-namespace candidates. Formatter identities are inactive too.
All product/compiler/math checks run in server Docker; workstation inspection
uses stdlib byte reads only.

The producer labels are now automatic. The machine inspector is currently an
independent experiment, **not yet default postprocessing or a public clock-unit
provider**. Next implement the small backend ELF/DWARF checker with exact
function/site scope, retain its tool inputs, revalidate them offline, bind the
actual runtime target, and connect appropriate SYS_CNT unit evidence to the
common Perfetto exporter. Full time/async gates, independent six-math matrix,
controlled cases and three extra final code reviewers remain open.
