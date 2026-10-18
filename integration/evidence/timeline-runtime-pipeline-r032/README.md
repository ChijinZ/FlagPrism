# Runtime-K pipeline and timeline density — r032

This checkpoint adds a public observation-density control, a real unannotated
runtime-K GEMM case, and two general NVIDIA machine-reader compatibility fixes.
It does not complete source-region, hardware-overlap or three-backend acceptance.

## Product changes

Use `start("capture", detail="timeline", timeline_max_sites=4)` or CLI
`--detail timeline --timeline-max-sites 4`. The integer logical-site budget is
1..128, default 8. Invalid values and use outside timeline mode are rejected
before runtime discovery. NVIDIA's required cp.async boundaries remain additional
to the logical budget. Ascend/GCU requests receive the same budget; their new
nondefault-density device qualification was not run in this checkpoint.

PTXAS erases DWARF `.b64` code-label address entries. The reader now accepts
only complete source-defined symbols inside debug sections, with exact original
line slots and blank replacements. Unknown labels, expressions, code erasure
and executable-line changes still fail. nvdisasm 13.2 also represents the PR
source of an unpredicated P2R instruction as a JSON predicate. A shared backend
normalizer restores that source operand and checks the complete textual operands;
PR never becomes an execution guard. No compiler/native ABI or logger changed.

## Actual observations

The development GEMM loads K from a device input and computes the requested
matrix product, with input/tail checks and a per-program scalar atomic invocation
oracle. It uses the public API without scopes, site IDs or custom allocators.
K3 and K7 share one ordinary binary and one instrumented binary per density.
These are exposed development samples, not the independent six-kernel qualifier.

| Density | K3 intervals / consumer operations | K7 intervals / consumer operations |
| --- | --- | --- |
| 1 logical site + required async | 136 / 0 | 264 / 0 |
| 8 logical sites + required async | 224 / 24 | 416 / 56 |

Both retain 40/72 logical commit groups and runtime shared-view generations.
The source addresses support committed-attempt and wait-coverage facts. They do
not certify equal footprints, active byte movement, safe buffer reuse or time
flows. The sparse view omits consumer detail; no missing consumer is invented.

Actual ordinary/sparse/default SASS each has the same number of key mechanisms,
but their issue ordering differs. Ordinary interleaves a copy between the last
two HMMA instructions; both instrumented variants issue the copy after all four.
The function instruction counts are 280/923/1395. These are static observations,
not throughput/overhead measurements. Lowering density did not resolve schedule
perturbation. `mechanisms.json` retains the actual PCs, operands and loop bounds;
this remains an open implementation problem, not a preservation certificate.

## Installed validation

- Existing Docker `chijin-study-pro6000`, GPU0; functional work only.
- Final Python: `/workspace/chijin-timeline-r032/runs/installed-v5/output/venv/bin/python`.
- Wheel SHA `7708ff5f3ecd620ff379c5546f0f70f5c39fff49d8530665dac2deeb3d4a23df`;
  604 installed members checked byte-for-byte. NVIDIA native sources match the
  existing r024 build. Standalone Ascend LLVM15 plugin sources are outside that
  NVIDIA build; the bridge excludes that separate directory explicitly.
- Installed public/machine/wait-control contracts: 70 tests + 2 subtests in each
  normal/optimized mode. Source-overlay tests are recorded separately.
- Actual API budgets 1/8 and CLI budget 1 passed math and requested invocation
  checks. CLI kept four captures and all required async sites.
- Those initial runtime-K captures exposed the two reader bugs and kept raw with
  explicit unavailable status. The fixed wheel recovered 32 observer traces from
  the same originals in fresh GPU-hidden processes, with actual Trace Processor
  checks; no application or device math replay was needed for recovery.
- A final fresh default run passed math, guards, invocation counts and the new
  mandatory trace-export assertion, producing 16 standard traces directly.
- Old v3 compatibility: 24 traces retain exact prior bytes. Actual TP checked
  32 recovered + 16 fresh + 24 old files, with no importer errors or invented
  flows. Standard Perfetto UI opened six real new traces, expanded tracks,
  selected positive slices, checked source/raw/quality details and focus.
- The UI/TP step kept all 239 original files unchanged. Files remain isolated
  observer-relative counter-ns views with unknown precision and source bounds.

## Retained failures and evidence

Initial installation harnesses selected a build interpreter without pybind11,
then a nonexistent interpreter path; neither reached device math. Both failures
are retained. The first source recheck passed normal tests but had a missing JSON
import in its audit bootstrap; the next job ran only remaining checks. Initial
UI input had no exports because the new real case exposed the reader bugs; that
failure was not reclassified as success. The first collector included a large
wheel staging library and stopped; subsequent collection excludes staging/native
binaries while retaining installation receipts. Original statuses are immutable.

Workstation archive: `artifacts/timeline/run-032/preflight/pipeline-density-evidence-v3.tgz`.
Its length/hash and exact current product hashes are in `verification.json`.
The archive contains original captures, raw bytes, compiled objects, disassembly,
traces, TP reports, screenshots, tests, failures and terminal job identities.

```bash
python integration/evidence/timeline-runtime-pipeline-r032/audit.py \
  --repo . --archive ../artifacts/timeline/run-032/preflight/pipeline-density-evidence-v3.tgz
```

This is only a retained byte/JSON audit. Product import/build/test, real math,
TP and browser execution all occurred in existing server Docker containers.
Full source timing, physical async/time-flow interpretation, six independent
new kernels, full three-backend acceptance and the final three code reviews
remain pending. No paper/Study or NVIDIA exclusive performance certification changed.
