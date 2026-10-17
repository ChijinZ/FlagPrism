# r018: immutable timeline revisions, offline recovery and actual standard UI

Status: **real implementation and retained-data/UI checks passed within the
scopes below; the complete three-backend timeline goal remains unfinished.**
No paper/Study files changed. No final code-review qualification is claimed.

## Implemented behavior

- `timeline_store.py` publishes content-addressed inputs/views/traces and immutable
  completion receipts. Bounded OS locks coordinate cooperating processes; synced
  files precede the receipt; an atomic index discovers complete, content-checked
  receipts. An interrupted revision can be completed without overwriting originals.
- `timeline_perfetto.py` binds revision identity to canonical/raw, proof contents,
  provider/rule implementation fingerprints and pinned protobuf schema. Same
  inputs are idempotent; changed legitimate inputs retain another revision.
  Observer/proof enumeration order does not alter the receipt.
- Public `python -m flagtree.profiler.timeline_reexport BUNDLE/timeline` decodes
  actual retained bytes again in a new process. NVIDIA independently re-parses
  retained target-machine inputs before generating isolated counter-ns views.
  GCU re-exports canonical raw revisions and explicitly returns `raw_only` with
  the missing-unit reason. Neither path replays the application.

Product `f6512a4` introduced the feature; `2b86fd2` fixes ordering determinism.
Formatting-only `4b00244` preserves the AST of all changed product/test sources.
Native source is unchanged:
NVIDIA reuses actual `6e7a7aa`, GCU actual `789757f`, after byte-checking every
native-source input against the separately assembled component. New independent
wheels/venvs retain old installations.

| Current installed product `4b00244` | NVIDIA | GCU |
| --- | --- | --- |
| Docker | `chijin-study-pro6000` | `flagprism-enflame-dev` |
| Python | `/workspace/chijin-timeline-r018/runs/install-v3/output/venv/bin/python` | same path, on GCU server |
| Installed members checked against exact wheel | 599 | 455 |
| Wheel SHA256 | `4fe70c734706bcc2acd102fc832db861004c70aacae1dd3366555b22b517aa18` | `97e7e50b6061f77720186abc3943ed117c9b228921017d811d5414831b46bfa0` |
| CPU contracts, normal / `-O` | 113 / 113 | 89 / 89 |
| Fresh offline processes | 3, 4 real retained captures / 32 traces | 3, 3 real retained captures / no invented ns traces |

These counts exclude the explicitly expected old-version failure. They do not
count CPU fixtures as hardware or independent-new-math qualification.

## Actual captures and UI

The first installed product ran four ordinary recurrence/GEMM mathematical calls
on PRO6000 through the default public entry. Math/input/tail/side-effect checks,
1,344 raw endpoint references, 672 intervals and 32 standard traces passed. The
separate nested-pair fixture is not hardware evidence. Every real trace was
checked using Google's generated protobuf and pinned actual Trace Processor
v57.2-da1d152cf: exact endpoints/identities, no importer error/data loss or flows.

[Six-trace UI record](nvidia-UI-six.json) covers four actual invocations and both
selected-program positions. Pinned standard UI and real Chrome opened files,
expanded invocation/program/site tracks, selected actual event IDs, displayed
source/raw/qualification arguments and focused the selection. Eighteen named
screenshots and before/after hashes of the whole bundle are in the original
archive. No page errors; the bundle was unchanged. Examples:

- [Actual recurrence screenshot](recurrence-details.png).
- [Actual GEMM screenshot](gemm-details.png).
- [Actual standard trace](counter-example.pftrace), SHA256
  `d5f6ea690d653c90c4d6c3440b2b11af5fe319df0d0d38de314e4e5465c02005`.

The storage-order fix and final formatting-only install were tested by
re-exporting the same UI-checked data
from the new install. All 32 trace byte digests match the prior bundle exactly;
Trace Processor checks pass again. This supports reuse of those UI observations
for the storage-only delta, without rerunning unchanged device math or pretending
new hardware/source timing evidence was obtained.

GCU's fresh default API cold/warm run comprises six actual calls, 264 endpoint
references and 132 intervals. Per-observer counts are `[10,10]`, `[14,14]`, `[18]`
in each phase. Real first/last writers, original-stream completion before deferred
readback, math and final raw/canonical retention passed. Unknown units remain
unknown; this does not qualify GCU allocation guards, source boundaries or async.

## Failures and recovery verification

- Browser tool download timed out; offline headless shell first lacked libraries.
  Container APT download-only requests were replaced by a campus login page and
  rejected by digest checks. Thirty official Ubuntu packages were transferred as
  SHA256-checked bytes and extracted into private tool directories. Only the
  browser process uses the private library path; no host/driver/daemon changes.
- The first expanded-UI automation matched nested tracks ambiguously. Its failed
  receipt remains; corrected DOM selection produced actual slice details.
- Both initial install-v2 controllers exited 1 because the new two-observer test
  used an invalid constructed invocation identity. The validator correctly
  rejected it. Only the fixture was corrected to the existing stable-ID contract;
  installed product bytes were not hot-patched. Separate CPU rechecks independently
  checked exact installed wheel bytes and completed normal/optimized tests.
- That corrected regression fails on the old installed product with the expected
  `Same derivative inputs produced different outputs`, and passes on the fixed
  product. Expected failure and first failed install receipts remain distinct.
- Early GCU offline testing denied an old r016 prefix, which did not fully cover
  the new source/cache environment. Final testing corrects this: both backends
  deny their actual original capture/cache and package-source paths, and the
  harness requires denied paths to cover the original timeline. No earlier weaker
  restriction is treated as complete original-environment isolation.
- Actual final offline checks run the public module and new normal/`-O` processes,
  with empty cwd/cache, Python file/exec access to original source/cache and child-process launches
  denied by audit hooks in the two audited runs (not an OS sandbox). NVIDIA has no GPU visible. Original artifacts
  remain unchanged except the intentionally mutable HTML index. CPU cases also
  cover proof/view forgery, two-process publication, completion
  receipt/index failures, held-lock termination, corruption and bounded conflicts.

Final formatter/linter checks ran inside Docker with pinned YAPF 0.43.0 and
Ruff 0.9.1. The first format pass needed a second pass for one audit dictionary;
its failed check is retained. Two passes converge and all 18 source ASTs remain
identical; the additional final audit script was checked separately. New v3
installs pass outright, with the same exact CPU counts; three new-process
re-exports again preserve originals and NVIDIA trace bytes/TP results. No
unchanged native source was rebuilt, and no unchanged device math was replayed
for a formatting-only change.

## Clock investigation and remaining requirements

The GCU SDK property query succeeded: `clockInstructionRate=1000` kHz and
processor `clockRate=1416000` kHz. The retained SDK has different clock and
`global_timer` getter implementations. These generic properties are **not** used
as the observed global-timer unit. Private SDK IR stays on the server; only
function/source hashes and our property-query receipts are retained here.

Current NVIDIA views are `counter_unit_only`: unknown read precision and source
boundaries, isolated observer origins, no temporal flows or engine busy. GCU
remains raw-only; Ascend's new automatic timeline producer remains to implement.
No backend passes full P01. Still required: final region boundaries/preserved
ordinary pipeline, clock/epoch and async physical-generation evidence, GCU guard
qualification, full three-backend traces/UI, independent six-new-math matrix,
controlled cases, remaining fault/budget gates and the three extra final
GPT-6.1-Sol/xhigh code reviewers. This milestone does not lower those gates.

## Evidence and reproduction

All product imports/builds/tests, CPU oracles, TP and browser execution occurred
in existing server Docker. Workstation audits use stdlib bytes only.

| Workspace original archive | Bytes / members | SHA256 |
| --- | --- | --- |
| `artifacts/timeline/run-018/preflight/nvidia-original-evidence.tgz` | 6,808,225 / 613 | `289675914edf937a8359ca76352ececc47b1871e43ad18e8be8e000c5af8d8bd` |
| `artifacts/timeline/run-018/preflight/gcu-original-evidence.tgz` | 6,859,319 / 228 | `ecc5964714f647a785bd22da155e35f6d692405ee21d4164e3f971580b2535ad` |
| `artifacts/timeline/run-018/preflight/nvidia-delta-v2-evidence.tgz` | 2,291,075 / 621 | `4cfdad4804e153da4b78aa16ff690ac01cce9ca2cb8d8bb94242e2e50db0d327` |
| `artifacts/timeline/run-018/preflight/gcu-delta-v2-evidence.tgz` | 1,762,155 / 395 | `e14b273240b8775bcbdeeb38faa73b4f75954e17b8a656f5efe38387454a4b80` |
| `artifacts/timeline/run-018/preflight/nvidia-final-v3-evidence.tgz` | 2,248,926 / 347 | `87f9b6853794a066099fcf4873ae37cb82aa0b3fae3591e244b31e638c1d854f` |
| `artifacts/timeline/run-018/preflight/gcu-final-v3-evidence.tgz` | 1,710,374 / 92 | `3ed3b1ba397b43c8c6f9460591601f4f64886b81f84d1896994941de53320073` |

[Initial NVIDIA byte audit](nvidia-byte-audit.json),
[GCU byte audit](gcu-byte-audit.json),
[final NVIDIA delta audit](nvidia-delta-byte-audit.json),
[final GCU delta audit](gcu-delta-byte-audit.json).
Final formatted-install audits: [NVIDIA](nvidia-final-byte-audit.json),
[GCU](gcu-final-byte-audit.json). Scripts: [NVIDIA](audit_nvidia.py),
[GCU](audit_gcu.py), [delta](audit_delta.py), [final](audit_final.py).
Style evidence: [18 source files](style-result.json),
[final audit script](audit-style-result.json). JSON summaries have normalized
final newlines; the workspace archives retain byte-original controller records.
The final delta command, from workspace root, is for example:

```bash
python FlagPrism-method/integration/evidence/timeline-reexport-ui-r018/audit_final.py \
  artifacts/timeline/run-018/preflight/nvidia-final-v3-evidence.tgz \
  --backend nvidia --output /tmp/r018-nvidia-audit.json
```

Controller/worker identities, first failures and actual terminal results are in
these archives. The final NV/GCU process audits find no live matching r018 task;
observed original controller handles are missing or Z. This does not audit other
users' work or confer device qualification. The sole live engineering log remains
workspace `timeline_impl_record.md`; this directory contains an immutable snapshot.
