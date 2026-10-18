# Ascend public raw timeline checkpoint r020

This checkpoint adds the CANN public `detail="timeline"` collector, deferred
stream-local ownership, paired raw → canonical schema 2 conversion and public
offline re-export. **It does not complete P01, ns, source boundaries, comparable
epochs, async generation or three-backend Perfetto acceptance.** No paper/Study
files were modified. Final additional three code reviewers have not started.

## Actual installation and commands

All installation, formatting, product tests, CPU math/oracles and device runs
used the existing server Docker. Ascend: `zhiyuan_ascend`, `chijin_v3.5.x` as
host user `chijin`, NPU4. Formatting only: NVIDIA `chijin-study-pro6000`, with
YAPF 0.43.0 / Ruff 0.9.1, fixed point and AST identity. No NVIDIA performance
experiments were run.

Ascend installed Python:
`/tmp/chijin-timeline-r020/runs/install-v2/output/venv/bin/python`.
Wheel SHA256: `3c8f4cd06550f4536fcb5fd12750d5e6d0773433dec6c05ab37a5333beac37c5`.
All 399 installed wheel members were byte checked, see
[installation](install.json) and [byte bridge](installed-byte-bridge.json).

LLVM plugin is the actual r019 rebuilt producer,
SHA256 `4e641e6ae68d092f6da549a6c5b3e35fde32e27a088bff8db33ca4d0839ebb5f`;
its three LLVM source/header inputs were unchanged and byte checked before
reuse. Core/native version 3 carrier artifacts are explicitly reused; this is
not a claim that the complete current native sources were rebuilt. The
[previous producer checkpoint](../timeline-ascend-producer-r019/README.md)
records their native-byte and plugin-build provenance. The fixed SDK is
`/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile`,
SHA256 `1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e`.

Run inside that Docker with the installed Python and compatible SDK selected:

```bash
export TORCH_DEVICE_BACKEND_AUTOLOAD=0
export TRITON_ASCEND_COMPILER=/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile
/tmp/chijin-timeline-r020/runs/install-v2/output/venv/bin/python -I \
  -m flagtree.profiler.cli --backend cann --detail timeline --device 4 \
  -n new-trace my_script.py
```

API requires the actual NPU device to be selected before `start(...,
backend="cann", detail="timeline")`. No profiler annotations, extra scratch
arguments or handwritten sites are required. Real math probes currently use
`enable_auto_blockify=False`; other lowering/writer ranges remain unqualified.

## Evidence and limits

| Actual check | Result | Evidence |
| --- | --- | --- |
| Installed CPU contract tests | 95 normal + 95 `-O` | Original logs in archive; [audit](audit-result.json) |
| Default API, real two-stream runtime-K recurrence plus Softmax | 50 intervals / 100 exact raw endpoint references, 128-byte guards; same profiled binary for K=3/7 | [device result](device-result.json) |
| Public CLI ordinary int32 fused math | One user launch, actual raw/guard/canonical output, exact output/input/state/tail checks | public-checks-v1 CLI terminal 0, original bundle in archive |
| Fresh process public/normal/optimized offline re-export | Two actual captures, deterministic revisions, originals unchanged; source/cache access denied by Python hook in audited modes, no NPU context initialization | [offline](offline-result.json) |
| Controlled first decode failure | All completed originals saved before decoding; both recover with public re-export | [recovery](recovery-result.json) |
| Controlled bad guard after actual readback | Original corrupted host guard retained, invalid interpretation rejected, next legal session works; four real user calls checked | [recovery](recovery-result.json) |
| Old default count mode | Actual vector-loop math / 1,024 unique side effects passed | [legacy](legacy-result.json) |

The first recovery **test harness failed** because it looked for the requested
output's `.timeline` rather than the actual staging directory preserved after
failed finalization. The actual staging index showed two original captures,
one successful later decode, the injected earlier decode error, and no retained
owners. Only the test path changed; the same installed product then passed.
The original failure is preserved in [first-recovery-failure.json](first-recovery-failure.json)
and [terminals](terminals.json), not replaced by the repaired test result.

Unwritten admissible AIV slots remain unobserved and canonical `complete=false`;
the collector does not pretend they executed. Source navigation does not
establish final operation boundaries. SYS_CNT remains raw ticks. Host injected
faults do not prove recovery from actual device faults. Python access hooks and
visibility environment variables are not an OS sandbox or proof that the NPU
is physically inaccessible. CPU/byte audits do not grant hardware qualification.

## Final-object investigation

The actual vendor `llvm-objdump` returned `<not available>` for the final ELF's
1,146 instruction positions with default/CPU/feature disassembly; the standalone
`--disassemble-aicore` variants produced only a file header and no instructions.
Successful tool exit is not successful instruction decoding. Generic `-S` and
`-mllvm -print-after=...` were explicitly rejected by this SDK; `-save-temps=obj`
produced an object without the desired assembly. The pipeline structure
inspection succeeds but is not final instruction or boundary evidence.
[Assembly rejection](machine-assembly-rejection.json) and
[print-after rejection](machine-print-after-rejection.json) are retained.
These observations limit the tested tool routes, not all possible methods or
hardware feasibility. No unit/boundary qualification was created from them.

The [official GetSystemCycle documentation](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/API/ascendcopapi/docs/en/api/SIMD-API/basic_api/tool_interface/system_resources_and_variables/GetSystemCycle_ISASI.md)
was checked during investigation: its A2 counter conversion and PIPE_S scope
must not be interpreted as vector-engine busy or common actor epoch. No new
clock provider was implemented in this checkpoint.

## Retained originals and reproducibility

Workstation archive:
`artifacts/timeline/run-020/preflight/ascend-final-v1-evidence.tgz`,
16,608,487 bytes / 1,600 files,
SHA256 `a35e268f6a55c7c4f4778850ba01d1a8e6dc453f4c7eccda99a4f2971d149222`.
It preserves v1/v2 installations' receipts, successful and failed runs, complete
actual bundles and failed staging timelines, final source snapshots, machine
probes, native/wheel byte inventories and all 22 Ascend process identities.
All matched processes were missing or terminal zombies at collection; no
matching live owned job remained. Style-v2/v3/v4 have separate original
archives in the same preflight directory; v1 formatter harness syntax failure
also remains in its original receipt. SDK headers/tools/binaries remain only
in the local/server originals, not this Git evidence directory.

Run the stdlib-only byte audit without importing the product:

```bash
python integration/evidence/timeline-ascend-public-r020/audit_retained.py \
  /absolute/path/to/ascend-final-v1-evidence.tgz --output audit.json
```

[audit-result.json](audit-result.json) verifies original SHA/lengths, real raw
field offsets/guards, runtime-K identity/counts, explicit unobserved coverage,
actual successful terminals and preserved first failure. Its scope is retained
bytes and recorded outcomes, not independent execution of the math.

Next: qualify final getter/boundaries and time scale, close real async physical
reuse and comparable clocks, and run complete three-backend P01/SQL/UI,
independent math, budgets/build/compatibility and final three code reviews.
