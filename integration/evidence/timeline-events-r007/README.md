# Canonical raw events and real loss checkpoint (T013)

This implements an actual common raw event contract consumed by public timeline
collection. It **does not certify clock scale/epoch, source machine boundaries,
Perfetto, P01 or independent qualification**. All captures remain
`partial_clock_unverified`.

## Implementation

`867b0cfa016c9f6f3caaf8ade2afa2d486da779e` adds `timeline_events` and the actual
NVIDIA adapter. Common tables describe source navigation, binary sites,
recording observers, raw records and interval/incomplete/point events. IDs bind
capture/invocation/binary, observer and absolute sequence, so reparenting a
capture or binary cannot silently reuse identities. Unknown required semantics,
false endpoints/iterations, duplicate durations, missing refs, raw span aliases,
invalid ticks and budgets fail explicitly. The common validator has no vendor
instruction parser or warp/SM topology requirement. Source navigation is not
promoted to exact execution cost attribution.

The NVIDIA adapter preserves actual program coordinates and records the header
SM only as `nvidia.finalize_smid`, not proof of a fixed physical execution
location for every earlier event. Properly nested complete streams produce
actual interval pairs. Lost history retains known in-window pairs and explicit
orphan boundaries, never joins across missing history or fills a kernel-end.
Occurrence is retained entry/boundary order, not a proven loop iteration or
physical buffer generation. Explicit namespaced record maps connect existing
logical async facts to the common records without guessing names/proximity.

`99c2e308dea889a181a91e0c89ac22476b74dbc5` adds real overflow math using the public
path. `d15933a777e0be39fabc2d1efa25e8613ba152e0` makes the immutable predecode journal
explicitly `raw_persisted_pending_decode`: a failed decode must not leave a
snapshot claiming complete history. Original raw/identity/source metadata are
persisted before canonicalization and retained on later failure. The actual
compiler selection policy replaces the old misleading auto-mode metadata alias.
New model/adapter hashes participate in timeline cache identity.

## Actual execution

Existing RTX PRO 6000 GPU0 Docker `chijin-study-pro6000`, no host/driver changes,
other-user interference, paper or old Study modification. Both Python-only
packages report Ninja no work; seven native wheel members are byte-identical
through the prior actual `545bf8a` native build. Final wheel: 390643425 bytes,
SHA `85b1e82aeffbef59464bed333db5d7aa113528a6e52a81efd5b6635b98b1b557`.
Fresh venv: `/workspace/chijin-timeline-r007/runs/install-v2/output/venv`.

Both original runs are retained. The final real public test exercises API
cold/warm loaded handles, two streams and mixed recurrence/GEMM binaries,
zero-grid, injected export failure/raw recovery/next-session, real CLI and
separate old count CLI. Normal numerical/input/tail/side-effect checks pass.
It additionally runs one original recurrence with runtime K=1021, overrunning
the default ring without an artificial busy loop or operator-specific collector.

Final timestamp data:

- **21 captures, 10816 physical records**.
- **5400 actual paired intervals**, including valid retained-window pairs.
- **16 explicit orphan endpoints**, with no fabricated counterpart.
- **12352 overwritten records**, reported as lost rather than silently complete.
- **400 logical commit groups** from complete cases; the lossy capture produces
  no group/dependency guesses. These are not physical buffer generations or
  verified time arrows.

Root independently compares every canonical record/pair/orphan to physical
header/counter/tag/sequence/tick/byte-offset data, verifies all namespace and
mechanism record maps, original source snapshot hashes, compiled artifacts and
standard bundle hashes. Cold/warm sessions reuse actual function handles.
Input journals are pending-decode snapshots even for overflow; final captures
and canonical loss status remain separate. No product module was imported by
the root retained-byte auditor.

Fresh-installed CPU contracts: 15 new canonical methods, 16 owner methods,
seven storage methods, each normal and `-O`; two public fault/old-ABI methods in
both modes; three existing automatic-hook methods and CLI help. Synthetic loss
and extra-role fixtures are only contract checks, not hardware/new-chip ports.
Actual overflow uses the default bounded ring; this is not a separate tiny-
buffer public-request qualification. Legacy real auto-count still yields four
captures. No performance/overhead or engine-overlap certification was attempted.

## Evidence and limits

[Common contract documentation](../../../Profiler/docs/timeline_events.md).
Actual normal/overflow canonical files are referenced by
`/workspace/chijin-timeline-r007/runs/device-public-v2/output/{api-cold,api-overflow,cli}/timeline/index.json`.
There are no certified `.pftrace` files yet. Physical clock/final ISA proof,
actual buffer/flag reuse proof, GCU/Ascend paths, full P01, independent math,
real Trace Processor/UI and three final requested code reviews remain required.

Root original archive `artifacts/timeline/run-007/preflight/events-original-evidence.tgz`,
9139936 bytes, SHA `dbd58d06e69418306bd7ab98b0607a757e98f962b7c613ef6fd53763dbc5301e`;
[raw index](raw-artifact-index.json) enumerates 913 retained members. Audit script:
`artifacts/timeline/run-007/preflight/audit-canonical-events.py`.
All six owned jobs are terminal with worker PIDs gone; PID1 retains controller
zombies. Final GPU query shows 15 MiB, util 0 and no compute applications.
`cuobjdump`/`nvdisasm` were not found on PATH; this is a preliminary tool-location
finding, not proof that final disassembly is impossible.

[Package](package-terminal.json), [source](source-bridge.json),
[native bridge](native-byte-bridge.json), [install](install-result.json),
[device](device-terminal.json), [result](device-result.json),
[root audit](root-audit.json), [processes](owned-terminal-status.json).
