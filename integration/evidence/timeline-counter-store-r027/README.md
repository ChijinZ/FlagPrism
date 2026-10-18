# Native timer-word store witnesses r027

Product commit: `5317093`. NVIDIA machine analysis now follows the actual
64-bit counter words through helper/caller moves into the logger's shared
vector-store inputs. This is a further component of the original timeline
goal; full source timing and three-backend qualification remain incomplete.

## Implementation

`nvidia.cp_async.wait_control.v2` adds `endpoint_store_value_flows` to each
recognized wait site's report. The normal finalizer and public offline
re-export already call this backend component, so no kernel annotations,
site names or per-operator adapters are added:

```bash
python -m flagtree.profiler.timeline_reexport BUNDLE/timeline
```

The checker tracks the getter's low/high register pair, helper and caller
MOV/MOV.64 transfers, the phase/site tag and STS.128 inputs. Overlapping wide
moves snapshot both input words before updating the output pair. Conditional
values are valid only under the same predicate generation; an intervening
predicate write invalidates the old condition. Unknown opcode families do
not inherit scalar-MOV semantics. The control checker also drops entry-guard
facts on unknown register writers instead of silently keeping them.

`counter_to_shared_store_values_checked` is explicitly conditional on executing
that call and store. It does not establish call dominance, private-buffer
addressing, sequence fields, publication, full raw-record provenance, clock
precision or source-region timing. Those qualifications remain false. An
`unverified` result is missing evidence, not permission to diagnose corrupted
timestamps or rename an ordinary kernel unsupported. Old v1 reports, raw
bytes, canonical events and trace semantics are retained.

## Actual-object results

Fresh production postprocessing of the retained r024 ordinary GEMM object
automatically finds all four endpoint value-flow witnesses:

| Site / phase | Getter PC | Caller PC | Shared store PC | Tag / low / high inputs |
| --- | --- | --- | --- | --- |
| 10 / entry | `0x6620` | `0x2130` | `0x2230` | R20 / R21 / R22 |
| 10 / exit | `0x6650` | `0x2280` | `0x2360` | R16 / R17 / R18 |
| 20 / entry | `0x6d30` | `0x4ea0` | `0x4f90` | R24 / R25 / R26 |
| 20 / exit | `0x6d60` | `0x4fe0` | `0x51d0` | R28 / R29 / R30 |

These are derived from the actual CUBIN and two disassemblies, not addresses
used in product selection rules. The original FP16 GEMM is 48×192 times
192×56 with blocks 32³, four warps and three stages. Its input/output/tail
and CPU-reference checks belong to r024; this Python-only change does not
replay that math or count it as new independent qualification.

## Installed validation

All installation, product tests, actual-object analysis and TP ran inside
existing Docker `chijin-study-pro6000`. Existing GCU Docker
`flagprism-enflame-dev` supplied cached formatting only. No device code, native
ABI, logger synchronization or mathematical kernel was changed.

* Final Python:
  `/workspace/chijin-timeline-r027/runs/installed-v1/output/venv/bin/python`.
* Wheel SHA256:
  `95e0eab2fc3d023294156820c26f3f0267c416ad101400e340447b541f511504`.
* 602 installed wheel members byte checked; 78 profiler Python files,
  271 unchanged native inputs and 1,987 current source files matched.
  The native core remains r024's actual built core; no new C++ build claimed.
* 26 installed unittest cases in normal and optimized Python: both phase tags,
  reversed/clobbered words, overlapping/wide moves, changed predicates,
  unknown writers, unknown move families and the prior control/RPC negatives.
* Fresh real disassembly through the production postprocessor verifies both
  native waits and four conditional word-flow witnesses. Recurrence objects
  gain no invented cp.async sites.
* Both real record formats: three fresh offline processes, three captures and
  24 traces each. Actual TP SQL again verifies all 48 traces' ns/raw references,
  no importer errors and no invented flow arrows. Original data is unchanged;
  isolated exports deny the old environment and application subprocess replay.
* All 48 current **trace and view** files match r026 byte for byte. Its six
  actual standard Perfetto UI checks are reused on that basis; the browser
  is not rerun or represented as newly run. Only the separate machine report
  changes. See [r026](../timeline-wait-control-r026/README.md).
* No new user-math launches, exclusive performance claims or paper/Study edits.

## Evidence and remaining work

Workspace archive:
`artifacts/timeline/run-027/preflight/store-value-flow-evidence-v1.tgz`

6,249,588 bytes / 621 members, SHA256
`541530117e82ef9b67c4a7fa08432f977688b9f28f50ec116a49f39357879159`.
The inventory covers source/input manifests, CPU tests, actual disassembly,
control/value-flow reports, actual TP results, exact UI-input comparisons and
37 inactive owned NVIDIA process identities. The collector also scans script
paths/deadline ownership and finds no active owned descendants.

[verification.json](verification.json) records the retained-byte/source/install
audit. Launch, collection, source and installation scripts remain in workspace
`artifacts/timeline/run-027/preflight/`; an unchanged actual report is copied
to `artifacts/timeline/run-027/review/wait-control.json` for inspection.

Call/store conditions and raw-storage binding still need closure; this does
not grant complete source timing or verified time arrows. GCU/Ascend time and
async support, three-backend P01, independent six-math acceptance, controlled
cases and the final three extra specified code reviewers remain mandatory.
