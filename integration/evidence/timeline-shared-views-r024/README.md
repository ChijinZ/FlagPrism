# NVIDIA runtime shared-view checkpoint r024

Automatic NVIDIA timeline records now carry the actual runtime shared-memory
view origin for copy destinations and local-load sources. Users do not add
kernel arguments, scopes or site IDs. This closes a missing mechanism input;
it is **not full timeline/P01 or three-backend acceptance**.

Product source commit: `a22de8828362f057c038744fee59d0f245fe41b0`. Later changes in this checkpoint are test/evidence only.

## Implementation

Physical record v3 is 32 bytes: site/phase, full timer low/high, absolute sequence,
then payload kind, shared-view byte origin and two zero reserved words. The
NVIDIA lowerer reads the converted MemDesc base and affine offset, including
padding. It does not derive a buffer slot from occurrence or commit ordinal.
Two bounded shared stores emit the record; actual kernel completion publishes
the readback. Existing v2 data and explicit v2 compiler IR remain supported.

Mechanism model `nvidia.cp_async.shared_views.v2` associates complete recorded
submits, commits and waits with same-origin loads within one recording observer.
Its generation namespace includes capture, invocation, binary, program, warp
and runtime origin. Missing history yields no generation assignments. Masks can
suppress movement, and equal origins do not prove equal footprints, disjoint
storage, cross-actor visibility or safe reuse. No verified time flows are emitted.
Old v2 records retain `nvidia.cp_async.groups.v1` and do not acquire invented
shared-view information. The common raw event schema stays version 1.

## Actual development workloads

All builds, installs, product tests, mathematical references, device work,
Trace Processor and browser checks ran inside existing server Docker containers.
NVIDIA used `chijin-study-pro6000`, GPU0, RTX PRO 6000 sm_120. GCU's existing
`flagprism-enflame-dev` supplied cached formatting only; no GCU device workload
was run in this checkpoint. These are development kernels, not the independent
six-math qualification matrix.

| Actual request | Result |
| --- | --- |
| Runtime recurrence, device K=3 then 7 | Same cubin; correct output/input/tail, State advances once per request |
| Ordinary FP16 GEMM, FP32 accumulator, 48×192 times 192×56, blocks 32×32×32, stages=3 | Correct against CPU double reference; inputs preserved |
| Three automatic captures | 1536 endpoints, 768 intervals, eight observers per capture, complete histories |
| GEMM shared-view history | 128 committed attempt generations and 96 same-origin wait-covered load associations |

For GEMM program 0 / recording warp 0, the two load sites contain these actual
address-space-3 byte origins:

```text
site 11: 1024, 3072, 1024, 3072, 1024, 3072
site 12: 5120, 7168, 5120, 7168, 5120, 7168
```

These addresses are local to this invocation/program. They are not global
allocation IDs. The numbers describe recorded attempts, not measured traffic.
See [audit.json](audit.json) for byte checks, intervals and current-source bridges.

## Installation and checks

The changed ODS/C++ was independently built through all 558 native build tasks,
with an explicitly local snapshot of the retained patched FlagTree input. The
final Python-only exporter provenance change reused those exact matching native
inputs, then assembled and installed a new wheel; it did not hot-patch an old
installation or claim another native build.

* Final wheel SHA256: `3cd37dd5f4fed50922a3fbe093876b7ee484edb2119a9be7576c51320ba8b9ca`.
* Final Python: `/workspace/chijin-timeline-r024/runs/installed-v2/output/venv/bin/python`.
* 601 installed wheel members byte checked; 271 current native source files and
  77 installed profiler Python files independently bridged by the retained audit.
* Normal and optimized Python: 63 pytest cases plus 32 subtests, 46 standalone
  machine-map/Perfetto/store unittest cases, 27 v2 ring and 29 group checks, native
  timer/boundary/version checks, explicit v2 record lowering and legacy no-anchor
  checks. Raw field kinds, reserved words, missing waits, incomplete history,
  origin mismatches and observer/invocation separation have negative coverage.
* Three fresh offline export processes per format (public module, isolated
  normal, isolated optimized), with GPU hidden and original environments denied.
  Both real v2 and v3 bundles preserve original files and exact trace bytes.
* 48 actual standard Trace Processor imports verify exact ns projections, slice
  identities, raw record references and no importer errors or invented flows.
* Six traces inspected in the pinned standard Perfetto UI, including two GEMMs
  and runtime loops. Native/WASM UI assets and browser identities are retained.
  Optional external services/RPC are blocked in the browser harness. Actual
  slices are selected and checked before screenshots; the overview closes the
  details drawer so all stages remain visible.

The first installed run stopped before user math because old finalization
fixtures omitted the now-explicit record version. Only the fixture was fixed;
the product's version requirement stayed strict. Subsequent UI-only runs exposed
canvas-readiness and screenshot/font waits; failed runs remain retained. The
final browser workflow passes without replaying any mathematical workload.

## Reproduction and retained artifacts

The ordinary public API remains `start(path, detail="timeline")` followed by the
ordinary workload and `finalize(session)`. See [runtime documentation](../../../Profiler/docs/timeline_runtime.md).
The development vertical is `tests/timeline/p01_nvidia_boundary_vertical.py`
with `--shared-views` and a fresh `--output` directory. It is not a certification command.

Large originals and launch/collection commands are outside Git under workspace
`artifacts/timeline/run-024/preflight/`. The final archive includes the full native
receipts, first failures, raw/compiled sources, both installed checks, actual
offline/TP/UI results and process audits. `audit.json` identifies its exact SHA.
The earlier incomplete evidence collection and earlier UI runs remain separate.
An independently checkable stdlib audit is [audit_evidence.py](audit_evidence.py):

```bash
python integration/evidence/timeline-shared-views-r024/audit_evidence.py \
  --archive ../artifacts/timeline/run-024/preflight/shared-view-evidence-v3.tgz \
  --source . --output /tmp/shared-view-audit.json
```

## Remaining gates

Final machine/source boundaries, preservation of the ordinary critical pipeline,
allocation guards, timer precision and cross-observer epoch comparisons remain
unqualified. Same-origin associations are not verified hardware dependencies or
engine-busy intervals. Perfetto currently renders isolated observer counter
brackets; the new buffer generations remain in the retained mechanism facts.
GCU/Ascend complete timing/async paths, independent six-math qualification,
controlled timing cases and the three extra final GPT-6.1-Sol/xhigh code reviews
remain required. No paper or old Study data was changed.
