# Automatic counter-site to machine-PC mapping (T017 / r010)

Status: **real automatic counter-PC mapping and development regressions passed; region boundaries, clock, physical buffer reuse and full P01/Perfetto remain unqualified**. This checkpoint changes tool implementation, tests and tool documentation only; no paper/Study edits.

## What changed

Automatic compiler markers bind the actual scope ID and entry/exit phase to each timeline counter read. Native marker ABI 1 is checked before activation and included in compiler/cache identity. The public timeline path optionally invokes a compatible local `nvdisasm`, retains its identity and actual text/JSON output, then binds the compiler marker through the cubin's embedded PTX-debug line to every actual static getter PC. [Runtime documentation](../../../Profiler/docs/timeline_runtime.md) describes tool discovery and capture fields. No manual scope, operator-name repair, nearest-counter guess, network download or application replay is used.

The decoder compares all executable PTX tokens at their exact line positions. It allows only explicit `.loc`/`.file` erasures and typed DWARF data erasures inside declared debug sections. Every selected site/phase must appear; actual text/JSON opcode, predicate and getter operands must agree. An absent tool or unsuccessful mapping preserves raw data with a reason. Counter PCs are static candidates when code is duplicated; they do not prove dynamic exact-PC attribution, source-region boundaries, participant suppression or hardware completion. All canonical clock/boundary states remain unverified.

## Preserved failures and generic corrections

1. The first fresh install found that mismatched getter operands in text/JSON were accepted. `f5731a0` fixed that comparison; the initial CPU failure is retained.
2. The first five-type device run collected correct ordinary math/raw records but all mappings were rejected. Actual bytes showed marker whitespace before the semicolon and PTXAS-erased `.loc`, `.file` and DWARF data lines. `5d042b0` adds strict handling of those actual forms while continuing to reject executable changes, line shifts and unknown transforms. The initial device failure and five original captures remain immutable.
3. The new CPU tests cover accepted metadata erasure plus hidden instructions, data outside debug sections and metadata replacement rather than erasure. They run both normally and with `-O`. They are synthetic contract tests, not extra device coverage.

## Actual installation and device results

Existing server alias `zhangquan_pro6000`, Docker `chijin-study-pro6000`, GPU0 RTX PRO 6000 SM120. Native markers were genuinely built at `34fe5e2`. Final Python/source freeze is `5d042b05de8dda800392db10086c9f96fd19310c`; the Python-only packaging bridge verifies all seven native members byte-identical. Parent launcher remains preallocation admission ABI 2. The independent product is `/workspace/chijin-timeline-r010/runs/install-v3/output/venv`; wheel SHA `d41bd2c0f2da1625feeb538415d00878359a2f6e43fd360beef9ac957455faf4`, all 607 installed compiler/component members byte-checked. Official `nvdisasm` 13.2.86 is installed offline into this same prefix; executable SHA `6df0054fac801e7ab7d251506cfe52a1171c207de0923d8a3d57fdd5a1f6d982`.

| Check | Actual result |
| --- | --- |
| New mapping contracts, normal / `-O` | 17 methods each, including bounded tool failure/output/timeout and strict metadata/PC checks |
| Public ABI contracts, normal / `-O` | 4 passed each |
| Same native/source line before final Python-only parsing correction | canonical 16, owner 16, storage 7 each normal/`-O`; native 34 anchors / 17 dependent reads / 10 version negatives each mode; legacy hook 3 passed |
| Five ordinary types through public API | FP16, BF16, FP32, FP64, int64 exact CPU math/input/tail and per-program state `[1,1,1]`; five requests, 320 intervals |
| Public API/CLI | cold/warm loaded handles, runtime loop and async GEMM, two streams, zero grid, same-raw export recovery, next normal session, overflow, CLI and separate old count passed |
| Independently audited final raw | 26 captures, 11456 physical records, 5720 paired intervals, 16 orphan endpoints, 400 logical groups, 12352 overwritten records |
| Actual static counter mapping | all 26 captures reference complete maps; 7 unique cubins, 140 unique static counter PCs; 48 unique actual tool commands, referenced 78 times across captures |
| Final owned processes | nine build/package/install/device jobs terminal; actual PID/startticks checked, no live owned worker; final GPU 15 MiB / 0% / no compute applications |

The static instruction/counter counts are recurrence 392/16, GEMM 920/44, and each type 344/16. All seven actual objects have no MEMBAR. These counts do not certify no perturbation, true hardware engine activity or region boundaries. The cases are **development regressions**, not independent six-new-math qualification. NVIDIA throughput/speedup/overhead certification remains deferred; this checkpoint verifies functionality and provenance.

## Originals and reproducible retained-byte audit

- Server originals: `/workspace/chijin-timeline-r010/` with `native-marker`, `package-parser`, `package-debug-lines`, three independent installs, two type runs and final public API/CLI run. Original source, raw, LLVM/PTX/cubin, disassembler outputs, receipts and math/side-effect results are retained.
- Workstation archive: `artifacts/timeline/run-010/preflight/counter-mapping-original-evidence.tgz`, **6125781 bytes**, SHA **`7b84ed777b229752ac29a79402199a9fd7fefcf247308fb7e5570ade505b7f86`**. It preserves both initial failures and final data; excludes wheels, venv/cache, and SDK private libraries. Git carries this small index, not that archive.
- [Audit result](retained-byte-audit.json) independently binds physical raw ticks/IDs/pairs/loss, source/compiled/bundle SHA, actual ELF debug PTX, exact machine getter PCs/phase, real text/JSON/tool identity, once/math harness results and terminal process identities. It uses retained bytes and stdlib only, with no workstation product import/oracle or new device execution.

From the workspace root, with the retained archive available:

```bash
python FlagPrism-method/integration/evidence/timeline-counter-map-r010/audit-retained-bytes.py \
  --archive artifacts/timeline/run-010/preflight/counter-mapping-original-evidence.tgz \
  --repo FlagPrism-method --output /tmp/flagprism-counter-map-audit.json
```

`INDEX.json` binds the public evidence members. Future source/test revisions may need the recorded source freeze to reproduce source-equality checks. Current CPU/device originals are never overwritten to fit a new verifier.

## Remaining full-goal requirements

Exact machine **counter** locations now make further auditing possible; LLVM SSA constraints and memory clobbers still do not certify source-region instruction scheduling. Per-site region/path/participation proofs, usable scale/quantization/endpoint error/window/epoch, real physical buffer/flag generation, GCU/Ascend automatic timeline producers, common ns view/export, real Trace Processor/UI, independent new math and the final three additional requested GPT-6.1-Sol/xhigh code reviews remain required. No `.pftrace`, P01 or full completion is claimed by this checkpoint.
