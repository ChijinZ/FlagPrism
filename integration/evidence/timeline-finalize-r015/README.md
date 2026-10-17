# Actual multi-invocation salvage and decoder recovery

The public NVIDIA timeline collector now saves all completed invocation originals
before decoding, releases safely persisted device owners independently of derived
work, and continues salvaging/decoding other invocations after one fails.
Unresolved writers/readback/release remain owned. Per-attempt immutable records
preserve failures; the index is atomically replaceable. Retry uses the same raw
and metadata without replaying application kernels or device readback.

Product freeze: `f17071ccd6a7514507e583a71b27fe6030752ff9`, branch
`detailed-profiler`. Existing Docker: `chijin-study-pro6000`; actual installation:
`/workspace/chijin-timeline-r015/runs/install-v2/output/venv`.
Wheel SHA: `a69d9d047c798db2fc768db1ab376bc044313c6a8c50499249464f24b757bb97`.
608 installed members are checked against the wheel. Seven native libraries are
byte-identical to the prior actual native build; no native rebuild was needed.

## Actual checks and first failures

- Normal and Python -O each passed 16 owner, seven finalization fault, and four
  public-interface CPU contracts. Synthetic transports are fault-contract
  evidence, not GPU execution or timing proof.
- `tests/timeline/p01_nvidia_finalize_recovery.py` executes ordinary unannotated
  runtime recurrence K=3/7/11 and tiled GEMM via the public API. Four real owners
  are read and released before any decoder. The first decode is deliberately
  failed: the other three captures complete, all four originals remain, no
  device owners remain. Retrying the retained hook recovers all four with zero
  additional transport operations and unchanged originals/first-failure history.
- A new public session executes the same four explicit requests normally.
  Eight successful captures contain **2688 endpoint records / 1344 intervals**;
  original math, input, tail and per-program side effects pass. Actual endpoint
  tags/ticks/sequences and canonical pairs are audited directly against bytes.
- First attempt `fault-recovery-v1` failed in the harness: it assumed user bundle
  and internal staging paths were identical. The first product attempt after
  that correction, `fault-recovery-v2`, exposed JSON list vs decoder tuple slot
  mismatch. Both failures and their originals remain in the archive. The fix
  restores slot tuples when reading persisted inputs; the final
  `fault-recovery-v3` terminal is rc=0. No failure is relabeled unsupported.
- Journal-write failures also preserve the first decoder exception; this is
  covered by CPU fault injection. Recovery into a different evidence directory
  is explicitly rejected rather than mixing per-invocation file references.

The actual final device controller was PID 48456/startticks 10681664, worker
48457/10681667, rc=0, wall 9.729s. All seven owned build/install/device jobs have
terminal receipts and matching workers absent (controllers only Z or absent).
Final GPU state: 15 MiB, 0% utilization, no compute applications. This is a
functional test, not throughput or profiling-overhead certification.

## Originals and reproduction

Archive: `artifacts/timeline/run-015/preflight/finalize-original-evidence.tgz`,
1951765 bytes / 315 members,
SHA `1d861e0b9bd31e6730ad14d2a5eb9016c28d30bb7e53a4868c518d28118fe4eb`.
It contains both successful and failed runs, actual scripts, normal/-O logs,
installation/source/native receipts, both successful capture sets and failed-run
intermediates, and exact installed hook/runtime source bytes. Large wheels and
venvs are not duplicated. The full member SHA index and selected receipts are here.

From the workspace root, reproduce the stdlib/Git byte audit:

```sh
python FlagPrism-method/integration/evidence/timeline-finalize-r015/audit-retained-bytes.py \
  --repo FlagPrism-method \
  --archive artifacts/timeline/run-015/preflight/finalize-original-evidence.tgz \
  --output /tmp/timeline-finalize-audit.json
```

The device case command (inside the existing Docker) was the installed interpreter
with `-I`, `check-input-v2/p01_nvidia_finalize_recovery.py`, and a fresh `--output`;
actual argv, script SHA, owned timeout/cleanup identity and terminal are in
[device-terminal.json](device-terminal.json). The live owner controller sets
isolated cache/TMPDIR and a 180s deadline. Reuse the retained original results
for inspection; do not rerun merely to repeat already-passed checks.

## Limits

This checkpoint is not full P01 or standard Perfetto acceptance. Raw clock and
source-region boundaries remain explicitly unverified, dynamic physical buffer
reuse remains incomplete, and GCU/Ascend default timeline producers still need
completion. Static machine maps do not certify source costs or hardware busy.
The tested retry retains the hook in-process; a standalone public cross-process
recovery command has not been delivered. Three-backend ns, async dependencies,
Perfetto SQL/UI, independent math and the final three code reviews remain required.
